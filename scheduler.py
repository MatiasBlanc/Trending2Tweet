"""Scheduler automático para publicación y recolección de métricas.

Se ejecuta como worker, publica tweets en horarios configurados
y colecta métricas periódicamente.
Diseñado para correr en Heroku, Railway, o cualquier plataforma con workers.
"""

import time
import signal
import sys
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

from metrics_db import (
    init_db,
    obtener_tweets_pendientes_colecta,
    actualizar_metricas,
    guardar_historial,
    _get_connection,
)
from metrics_collector import crear_cliente, obtener_metricas_tweet

# Ruta base del proyecto
BASE_DIR = Path(__file__).parent

# Horarios de publicación (hora del servidor UTC, formato 24h)
HORARIOS_PUBLICACION = [
    {"hora": 9, "minuto": 0, "script": "main_news.py", "label": "📰 News"},
    {"hora": 12, "minuto": 0, "script": "main_github.py", "label": "🐙 GitHub"},
]

# Registro de publicaciones del día (para no duplicar)
_publicaciones_hoy: dict[str, bool] = {}

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


def ejecutar_publicacion(script: str, label: str) -> bool:
    """Ejecuta un script de publicación.

    Args:
        script: Nombre del script a ejecutar (ej: main_news.py).
        label: Etiqueta descriptiva para los logs.

    Returns:
        True si la publicación fue exitosa, False en caso contrario.
    """
    script_path = BASE_DIR / script

    if not script_path.exists():
        print(f"  ❌ Script no encontrado: {script_path}")
        return False

    print(f"\n{'━' * 50}")
    print(f"  {label} - Publicando...")
    print(f"  ⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'━' * 50}")

    try:
        resultado = subprocess.run(
            [sys.executable, str(script_path)],
            capture_output=True,
            text=True,
            timeout=300,  # 5 minutos máximo
            cwd=str(BASE_DIR),
        )

        if resultado.stdout:
            print(resultado.stdout)
        if resultado.stderr:
            print(f"  ⚠️ Stderr: {resultado.stderr}")

        if resultado.returncode == 0:
            print(f"  ✅ {label} completado")
            return True
        else:
            print(f"  ❌ {label} falló (código {resultado.returncode})")
            return False

    except subprocess.TimeoutExpired:
        print(f"  ❌ {label} timeout después de 5 minutos")
        return False
    except Exception as e:
        print(f"  ❌ Error ejecutando {label}: {e}")
        return False


def verificar_y_publicar() -> None:
    """Verifica si es hora de publicar y ejecuta los scripts correspondientes."""
    global _publicaciones_hoy

    ahora = datetime.now()
    fecha_hoy = ahora.strftime("%Y-%m-%d")

    # Resetear registro si cambió el día
    if _publicaciones_hoy.get("fecha") != fecha_hoy:
        _publicaciones_hoy = {"fecha": fecha_hoy}

    for horario in HORARIOS_PUBLICACION:
        clave = f"{fecha_hoy}_{horario['script']}"

        # Ya se publicó hoy
        if _publicaciones_hoy.get(clave):
            continue

        # Verificar si es la hora (ventana de 1 minuto)
        if ahora.hour == horario["hora"] and ahora.minute == horario["minuto"]:
            print(f"\n🕐 ¡Es hora de {horario['label']}!")
            exito = ejecutar_publicacion(horario["script"], horario["label"])
            _publicaciones_hoy[clave] = True

            if exito:
                print(f"  📝 Registrado como publicado hoy")


def main() -> None:
    """Ejecuta el scheduler en loop continuo."""
    global running

    # Registrar handlers de señales
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Mostrar horarios configurados
    horarios_str = ", ".join(
        f"{h['label']} a las {h['hora']:02d}:{h['minuto']:02d}"
        for h in HORARIOS_PUBLICACION
    )

    print("━" * 50)
    print("  🔄 Scheduler iniciado")
    print(f"  📰 Publicación: {horarios_str}")
    print(f"  📊 Métricas: cada {CHECK_INTERVAL // 60} minutos")
    print(f"  📊 Ventanas: {', '.join(v['label'] for v in VENTANAS_COLECTA)}")
    print("━" * 50)

    init_db()

    # Contador para alternar entre chequear publicación y métricas
    ciclo = 0

    while running:
        try:
            # Cada minuto verificar si es hora de publicar
            verificar_y_publicar()

            # Cada 5 minutos colectar métricas
            if ciclo % (CHECK_INTERVAL // 60) == 0:
                resultado = ejecutar_colecta()

                if resultado["pendientes"] == 0:
                    print(f"  💤 Sin tweets pendientes de métricas.")

        except Exception as e:
            print(f"  ❌ Error en scheduler: {e}")

        # Esperar 1 minuto
        time.sleep(60)
        ciclo += 1

    print("  👋 Scheduler detenido.")


if __name__ == "__main__":
    main()
