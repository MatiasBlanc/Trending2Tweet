"""Scheduler automático para publicación de tweets.

Se ejecuta como worker, publica tweets en horarios configurados.
Diseñado para correr en Railway con persistencia en Volume.
"""

import os
import time
import signal
import sys
import subprocess
from datetime import datetime, timezone
from pathlib import Path

# Ruta base del proyecto
BASE_DIR = Path(__file__).parent

# ── Horarios de publicación ────────────────────────────────────
# Usa UTC. Railway corre en UTC por defecto.
# Chile: UTC-4 (horario estándar) o UTC-3 (horario de verano)
# Configura con la variable de entorno PUBLISH_TIMEZONE_OFFSET (ej: "-4")
_TZ_OFFSET = int(os.getenv("PUBLISH_TIMEZONE_OFFSET", "-4"))

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
        print(f"  ⏰ Hora actual UTC: {_now_utc().strftime('%Y-%m-%d %H:%M:%S')}")
        print("━" * 60)

    except Exception as e:
        print(f"  ❌ Error fatal en inicialización: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    print("  ✅ Scheduler listo para procesar")

    while running:
        try:
            # Cada minuto verificar si es hora de publicar
            verificar_y_publicar()

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

    print("  👋 Scheduler detenido.")


if __name__ == "__main__":
    main()