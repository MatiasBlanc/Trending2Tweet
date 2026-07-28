"""Scheduler automático para publicación y recolección de métricas.

Se ejecuta como worker, publica tweets en horarios configurados
y colecta métricas periódicamente.
Diseñado para correr en Railway con persistencia en Volume.
"""

import os
import time
import signal
import sys
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from metrics_db import (
    init_db,
    actualizar_metricas,
    guardar_historial,
    _get_connection,
)
from metrics_collector import crear_cliente, obtener_metricas_tweet

# Ruta base del proyecto
BASE_DIR = Path(__file__).parent

# ── Horarios de publicación ────────────────────────────────────
# Usa UTC. Railway corre en UTC por defecto.
# Si tu zona es UTC-4 y quieres publicar a las 9:00 AM local → hora=13 (UTC)
# Si quieres publicar a las 12:00 PM local → hora=16 (UTC)
# Configura con la variable de entorno PUBLISH_TIMEZONE_OFFSET (ej: "-4")
_TZ_OFFSET = int(os.getenv("PUBLISH_TIMEZONE_OFFSET", "0"))

def _local_to_utc(hora: int, minuto: int) -> tuple[int, int]:
    """Convierte hora local a UTC según el offset configurado."""
    total_minutos = hora * 60 + minuto - _TZ_OFFSET * 60
    total_minutos = total_minutos % (24 * 60)
    return total_minutos // 60, total_minutos % 60

_RAW_SCHEDULES = [
    {"hora": 9,  "minuto": 0, "script": "main_news.py",   "label": "📰 News"},
    {"hora": 12, "minuto": 0, "script": "main_github.py", "label": "🐙 GitHub"},
]

HORARIOS_PUBLICACION = [
    {
        **s,
        "hora_utc": _local_to_utc(s["hora"], s["minuto"])[0],
        "minuto_utc": _local_to_utc(s["hora"], s["minuto"])[1],
    }
    for s in _RAW_SCHEDULES
]

# Registro de publicaciones del día (para no duplicar)
_publicaciones_hoy: dict[str, bool] = {}

# Ventanas de colecta de métricas (en minutos después de publicación)
# Solo T+30min y T+24h para ahorrar costos de API
VENTANAS_COLECTA = [
    {"minutos": 30,    "label": "T+30min"},
    {"minutos": 1440,  "label": "T+24h"},
]

# Cada cuánto revisar si hay tweets pendientes de métricas (en segundos)
CHECK_INTERVAL = 300  # 5 minutos

# Flag para graceful shutdown
running = True


def signal_handler(signum, frame):
    """Maneja señales para apagado graceful."""
    global running
    print(f"\n⏹  Señal {signum} recibida. Cerrando scheduler...")
    running = False


def _now_utc() -> datetime:
    """Retorna el datetime actual en UTC."""
    return datetime.now(timezone.utc)


def obtener_tweets_para_colectar() -> list[dict]:
    """Obtiene tweets que necesitan colecta según las ventanas de tiempo.

    Returns:
        Lista de tweets pendientes con su ventana correspondiente.
    """
    init_db()
    conn = _get_connection()
    cursor = conn.cursor()

    # Obtener tweets con tweet_id real (no legacy ni pending)
    cursor.execute("""
        SELECT * FROM tweets
        WHERE tweet_id NOT LIKE 'legacy_%'
        AND tweet_id NOT LIKE 'pending_%'
        ORDER BY published_at DESC
        LIMIT 200
    """)

    tweets = [dict(row) for row in cursor.fetchall()]
    conn.close()

    ahora = _now_utc()
    pendientes = []

    for tweet in tweets:
        try:
            published_at_str = tweet["published_at"]
            # Manejar timestamps con o sin timezone
            if published_at_str.endswith("Z"):
                published_at = datetime.fromisoformat(published_at_str.replace("Z", "+00:00"))
            elif "+" in published_at_str or (published_at_str.count("-") > 2):
                published_at = datetime.fromisoformat(published_at_str)
            else:
                # Sin timezone → asumir UTC
                published_at = datetime.fromisoformat(published_at_str).replace(tzinfo=timezone.utc)
        except (ValueError, TypeError) as e:
            print(f"  ⚠️ Error parseando fecha para {tweet.get('tweet_id')}: {e}")
            continue

        # Asegurar que published_at sea aware
        if published_at.tzinfo is None:
            published_at = published_at.replace(tzinfo=timezone.utc)

        minutos_desde_publicacion = (ahora - published_at).total_seconds() / 60

        # No colectar tweets con más de 8 días (ventana superada)
        if minutos_desde_publicacion > 10080 + 60:
            continue

        last_collected = tweet.get("last_collected_at")
        if last_collected:
            try:
                ultima_colecta = datetime.fromisoformat(last_collected)
                if ultima_colecta.tzinfo is None:
                    ultima_colecta = ultima_colecta.replace(tzinfo=timezone.utc)
                minutos_desde_ultima_colecta = (ahora - ultima_colecta).total_seconds() / 60
            except (ValueError, TypeError):
                minutos_desde_ultima_colecta = float("inf")
        else:
            minutos_desde_ultima_colecta = float("inf")

        # Verificar cada ventana
        for ventana in VENTANAS_COLECTA:
            minutos_objetivo = ventana["minutos"]

            # Ya pasó el tiempo objetivo y no se ha colectado recientemente
            if minutos_desde_publicacion >= minutos_objetivo:
                if minutos_desde_ultima_colecta >= 60:
                    pendientes.append({
                        **tweet,
                        "ventana": ventana["label"],
                    })
                    break  # Solo la ventana más reciente pendiente

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
    print(f"  ⏰ {_now_utc().strftime('%Y-%m-%d %H:%M:%S')} UTC")
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

            actualizar_metricas(
                tweet_id=tweet_id,
                likes=metricas["likes"],
                retweets=metricas["retweets"],
                replies=metricas["replies"],
                impressions=metricas["impressions"],
                bookmarks=metricas["bookmarks"],
            )

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
                  f"💬 {metricas['replies']} "
                  f"👁 {metricas['impressions']}")

            colectados += 1
            time.sleep(2)  # Rate limit: esperar entre requests

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
    print(f"  ⏰ {_now_utc().strftime('%Y-%m-%d %H:%M:%S')} UTC")
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

    ahora = _now_utc()
    fecha_hoy = ahora.strftime("%Y-%m-%d")

    # Resetear registro si cambió el día (en UTC)
    if _publicaciones_hoy.get("fecha") != fecha_hoy:
        _publicaciones_hoy = {"fecha": fecha_hoy}

    for horario in HORARIOS_PUBLICACION:
        clave = f"{fecha_hoy}_{horario['script']}"

        # Ya se publicó hoy
        if _publicaciones_hoy.get(clave):
            continue

        # Verificar si es la hora UTC configurada (ventana de 1 minuto)
        if ahora.hour == horario["hora_utc"] and ahora.minute == horario["minuto_utc"]:
            print(f"\n🕐 ¡Es hora de {horario['label']}! (UTC {ahora.strftime('%H:%M')})")
            exito = ejecutar_publicacion(horario["script"], horario["label"])
            _publicaciones_hoy[clave] = True

            if exito:
                print(f"  📝 Registrado como publicado hoy")


def main() -> None:
    """Ejecuta el scheduler en loop continuo."""
    global running

    try:
        # Registrar handlers de señales
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        # Info de timezone
        tz_info = f"UTC{_TZ_OFFSET:+d}" if _TZ_OFFSET != 0 else "UTC"

        # Mostrar horarios configurados
        horarios_str = ", ".join(
            f"{h['label']} a las {h['hora']:02d}:{h['minuto']:02d} ({tz_info}) "
            f"→ {h['hora_utc']:02d}:{h['minuto_utc']:02d} UTC"
            for h in HORARIOS_PUBLICACION
        )

        print("━" * 60)
        print("  🔄 Scheduler iniciado")
        print(f"  🌍 Timezone: {tz_info} (offset={_TZ_OFFSET:+d}h)")
        print(f"  📰 Publicación: {horarios_str}")
        print(f"  📊 Métricas: cada {CHECK_INTERVAL // 60} minutos")
        print(f"  📊 Ventanas: {', '.join(v['label'] for v in VENTANAS_COLECTA)}")
        print(f"  ⏰ Hora actual UTC: {_now_utc().strftime('%Y-%m-%d %H:%M:%S')}")
        print("━" * 60)

        init_db()
        print("  ✅ Base de datos inicializada")

    except Exception as e:
        print(f"  ❌ Error fatal en inicialización: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    # Contador para alternar entre chequear publicación y métricas
    ciclo = 0

    print("  ✅ Scheduler listo para procesar")

    while running:
        try:
            # Cada minuto verificar si es hora de publicar
            verificar_y_publicar()

            # Cada CHECK_INTERVAL segundos (5 min) colectar métricas
            if ciclo % (CHECK_INTERVAL // 60) == 0:
                resultado = ejecutar_colecta()

                if resultado["pendientes"] == 0:
                    print(f"  💤 Sin tweets pendientes de métricas.")

        except KeyboardInterrupt:
            print("\n  ⚠️  Interrumpido por usuario")
            running = False
        except Exception as e:
            print(f"  ❌ Error en scheduler: {e}")
            import traceback
            traceback.print_exc()
            # No salir del loop, intentar continuar

        # Esperar 1 minuto
        try:
            time.sleep(60)
        except KeyboardInterrupt:
            print("\n  ⚠️  Interrumpido durante espera")
            running = False

        ciclo += 1

    print("  👋 Scheduler detenido.")


if __name__ == "__main__":
    main()
