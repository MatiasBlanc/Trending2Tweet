"""Scheduler automático para recolección de métricas.

Se ejecuta como worker y colecta métricas periódicamente.
Diseñado para correr en Heroku, Railway, o cualquier plataforma con workers.
"""

import time
import signal
import sys
from datetime import datetime, timedelta

from metrics_db import (
    init_db,
    obtener_tweets_pendientes_colecta,
    actualizar_metricas,
    guardar_historial,
    _get_connection,
)
from metrics_collector import crear_cliente, obtener_metricas_tweet


# Intervalos de colecta (en minutos después de publicación)
VENTANAS_COLECTA = [
    {"minutos": 30, "label": "T+30min"},
    {"minutos": 120, "label": "T+2h"},
    {"minutos": 1440, "label": "T+24h"},
    {"minutos": 10080, "label": "T+7d"},
]

# Cada cuánto revisar si hay tweets pendientes (en segundos)
CHECK_INTERVAL = 300  # 5 minutos

# Flag para graceful shutdown
running = True


def signal_handler(signum, frame):
    """Maneja señales para apagado graceful."""
    global running
    print(f"\n⏹  Señal {signum} recibida. Cerrando scheduler...")
    running = False


def obtener_tweets_para_colectar() -> list[dict]:
    """Obtiene tweets que necesitan colecta según las ventanas de tiempo.

    Returns:
        Lista de tweets pendientes con su ventana correspondiente.
    """
    init_db()
    conn = _get_connection()
    cursor = conn.cursor()

    # Obtener tweets que no son legacy y tienen tweet_id real
    cursor.execute("""
        SELECT * FROM tweets
        WHERE tweet_id NOT LIKE 'legacy_%'
        AND tweet_id NOT LIKE 'pending_%'
        ORDER BY published_at DESC
    """)

    tweets = [dict(row) for row in cursor.fetchall()]
    conn.close()

    ahora = datetime.now()
    pendientes = []

    for tweet in tweets:
        published_at = datetime.fromisoformat(tweet["published_at"])
        minutos_desde_publicacion = (ahora - published_at).total_seconds() / 60

        last_collected = tweet.get("last_collected_at")
        if last_collected:
            ultima_colecta = datetime.fromisoformat(last_collected)
            minutos_desde_ultima_colecta = (ahora - ultima_colecta).total_seconds() / 60
        else:
            minutos_desde_ultima_colecta = float("inf")

        # Verificar cada ventana
        for ventana in VENTANAS_COLECTA:
            minutos_objetivo = ventana["minutos"]

            # Ya pasó el tiempo objetivo
            if minutos_desde_publicacion >= minutos_objetivo:
                # No se ha colectado en esta ventana (o hace más de 1 hora)
                if minutos_desde_ultima_colecta >= 60:
                    pendientes.append({
                        **tweet,
                        "ventana": ventana["label"],
                    })
                    break  # Solo la ventana más reciente

    return pendientes


def ejecutar_colecta() -> dict:
    """Ejecuta una ronda de colección de métricas.

    Returns:
        Estadísticas de la colecta.
    """
    import tweepy

    tweets_pendientes = obtener_tweets_para_colectar()

    if not tweets_pendientes:
        return {"colectados": 0, "errores": 0, "pendientes": 0}

    print(f"\n{'━' * 50}")
    print(f"  📊 Colectando métricas para {len(tweets_pendientes)} tweets...")
    print(f"  ⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'━' * 50}")

    try:
        client = crear_cliente()
    except Exception as e:
        print(f"  ❌ Error creando cliente Twitter: {e}")
        return {"colectados": 0, "errores": 1, "pendientes": len(tweets_pendientes)}

    colectados = 0
    errores = 0

    for tweet in tweets_pendientes:
        tweet_id = tweet["tweet_id"]
        ventana = tweet["ventana"]

        try:
            metricas = obtener_metricas_tweet(client, tweet_id)

            # Actualizar métricas actuales
            actualizar_metricas(
                tweet_id=tweet_id,
                likes=metricas["likes"],
                retweets=metricas["retweets"],
                replies=metricas["replies"],
                impressions=metricas["impressions"],
                bookmarks=metricas["bookmarks"],
            )

            # Guardar en historial
            guardar_historial(
                tweet_id=tweet_id,
                likes=metricas["likes"],
                retweets=metricas["retweets"],
                replies=metricas["replies"],
                impressions=metricas["impressions"],
                bookmarks=metricas["bookmarks"],
            )

            print(f"  ✅ [{ventana}] {tweet_id}: "
                  f"❤️ {metricas['likes']} "
                  f"🔁 {metricas['retweets']} "
                  f"💬 {metricas['replies']}")

            colectados += 1

            # Rate limit: esperar entre requests
            time.sleep(2)

        except tweepy.TooManyRequests:
            print(f"  ⚠️ Rate limit. Esperando 15 minutos...")
            time.sleep(900)

        except Exception as e:
            print(f"  ❌ Error {tweet_id}: {e}")
            errores += 1

    print(f"{'━' * 50}")
    print(f"  ✅ Colectados: {colectados} | ❌ Errores: {errores}")
    print(f"{'━' * 50}")

    return {"colectados": colectados, "errores": errores, "pendientes": len(tweets_pendientes)}


def main() -> None:
    """Ejecuta el scheduler en loop continuo."""
    global running

    # Registrar handlers de señales
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    print("━" * 50)
    print("  🔄 Metrics Scheduler iniciado")
    print(f"  ⏰ Revisando cada {CHECK_INTERVAL // 60} minutos")
    print(f"  📊 Ventanas: {', '.join(v['label'] for v in VENTANAS_COLECTA)}")
    print("━" * 50)

    init_db()

    while running:
        try:
            resultado = ejecutar_colecta()

            if resultado["pendientes"] == 0:
                print(f"  💤 Sin tweets pendientes. "
                      f"Próxima revisión en {CHECK_INTERVAL // 60} min...")

        except Exception as e:
            print(f"  ❌ Error en scheduler: {e}")

        # Esperar hasta la próxima revisión
        for _ in range(CHECK_INTERVAL):
            if not running:
                break
            time.sleep(1)

    print("  👋 Scheduler detenido.")


if __name__ == "__main__":
    main()
