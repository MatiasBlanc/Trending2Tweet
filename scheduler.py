"""Scheduler automático para publicación de tweets.

Se ejecuta como worker, publica tweets en horarios configurados y tolera
reinicios o pequeños retrasos del proceso. Diseñado para correr en Railway
con persistencia en Volume.
"""

import signal
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from src import config


# Ruta base del proyecto
BASE_DIR = Path(__file__).parent

# ── Horarios de publicación ────────────────────────────────────
# Railway usa UTC. El offset permite definir los horarios en la hora local.
_TZ_OFFSET = config.PUBLISH_TIMEZONE_OFFSET
_ZONA_HORARIA = timezone(timedelta(hours=_TZ_OFFSET))


def _local_to_utc(hora: int, minuto: int) -> tuple[int, int]:
    """Convierte una hora local a UTC según el offset configurado.

    Args:
        hora: Hora local en formato de 24 horas.
        minuto: Minuto local.

    Returns:
        Tupla con la hora y el minuto equivalentes en UTC.
    """
    total_minutos = hora * 60 + minuto - _TZ_OFFSET * 60
    total_minutos = total_minutos % (24 * 60)
    return total_minutos // 60, total_minutos % 60


_RAW_SCHEDULES = [
    {"hora": 9, "minuto": 0, "modulo": "bots.news", "label": "📰 News"},
    {"hora": 12, "minuto": 0, "modulo": "bots.github_trending", "label": "🐙 GitHub"},
    {"hora": 15, "minuto": 0, "modulo": "bots.codigo", "label": "💻 Código"},
    {"hora": 18, "minuto": 0, "modulo": "bots.teclados", "label": "⌨️ Teclados"},
]

HORARIOS_PUBLICACION = [
    {
        **horario,
        "hora_utc": _local_to_utc(horario["hora"], horario["minuto"])[0],
        "minuto_utc": _local_to_utc(horario["hora"], horario["minuto"])[1],
    }
    for horario in _RAW_SCHEDULES
]

# Estado del día actual. Solo se marca como completado tras una publicación real.
_estado_horarios: dict[str, dict[str, object]] = {}

# Se permite recuperar una ejecución perdida por un reinicio cercano al horario.
_VENTANA_RECUPERACION_MINUTOS = 60
_INTERVALO_REINTENTO_MINUTOS = 5
_MAX_INTENTOS_POR_HORARIO = 3
_INTERVALO_REVISION_SEGUNDOS = 15

# Flag para graceful shutdown
running = True


def signal_handler(signum: int, frame: object) -> None:
    """Maneja señales para un apagado ordenado del scheduler.

    Args:
        signum: Número de la señal recibida.
        frame: Marco de ejecución entregado por el sistema.
    """
    del frame
    global running
    print(f"\n⏹  Señal {signum} recibida. Cerrando scheduler...")
    running = False


def _now_utc() -> datetime:
    """Devuelve el datetime actual en UTC."""
    return datetime.now(timezone.utc)


def _now_local() -> datetime:
    """Devuelve el datetime actual en la zona horaria configurada."""
    return _now_utc().astimezone(_ZONA_HORARIA)


def ejecutar_publicacion(modulo: str, label: str) -> bool:
    """Ejecuta un módulo de publicación.

    Args:
        modulo: Módulo Python a ejecutar, por ejemplo ``bots.news``.
        label: Etiqueta descriptiva para los logs.

    Returns:
        True si el módulo terminó con código cero, False en caso contrario.
    """
    print(f"\n{'━' * 50}")
    print(f"  {label} - Publicando...")
    print(f"  ⏰ {_now_utc().strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print(f"{'━' * 50}")

    try:
        resultado = subprocess.run(
            [sys.executable, "-m", modulo],
            capture_output=True,
            text=True,
            timeout=300,
            cwd=str(BASE_DIR),
        )

        if resultado.stdout:
            print(resultado.stdout)
        if resultado.stderr:
            print(f"  ⚠️ Stderr: {resultado.stderr}")

        if resultado.returncode == 0:
            print(f"  ✅ {label} completado")
            return True

        print(f"  ❌ {label} falló (código {resultado.returncode})")
        return False

    except subprocess.TimeoutExpired:
        print(f"  ❌ {label} timeout después de 5 minutos")
        return False
    except Exception as error:
        print(f"  ❌ Error ejecutando {label}: {error}")
        return False


def _clave_horario(horario: dict[str, object], fecha_local: str) -> str:
    """Construye una clave única para un horario y fecha local.

    Args:
        horario: Configuración del horario de publicación.
        fecha_local: Fecha local en formato ISO.

    Returns:
        Clave usada para mantener el estado del horario.
    """
    return f"{fecha_local}_{horario['modulo']}"


def _hora_programada(
    horario: dict[str, object], ahora_local: datetime
) -> datetime:
    """Construye la hora programada usando la fecha local actual.

    Args:
        horario: Configuración del horario de publicación.
        ahora_local: Fecha y hora local actuales.

    Returns:
        Datetime consciente de zona horaria correspondiente al horario.
    """
    return ahora_local.replace(
        hour=int(horario["hora"]),
        minute=int(horario["minuto"]),
        second=0,
        microsecond=0,
    )


def _debe_ejecutarse(
    horario: dict[str, object], clave: str, ahora_local: datetime
) -> bool:
    """Determina si un horario está listo para ejecutarse o reintentarse.

    Args:
        horario: Configuración del horario de publicación.
        clave: Clave única del horario para el día actual.
        ahora_local: Fecha y hora local actuales.

    Returns:
        True si la ejecución está dentro de la ventana permitida.
    """
    estado = _estado_horarios.get(clave, {})
    if estado.get("completado") or estado.get("agotado"):
        return False

    programada = _hora_programada(horario, ahora_local)
    limite = programada + timedelta(minutes=_VENTANA_RECUPERACION_MINUTOS)
    if ahora_local < programada or ahora_local > limite:
        return False

    intentos = int(estado.get("intentos", 0))
    if intentos >= _MAX_INTENTOS_POR_HORARIO:
        return False

    ultima_ejecucion = estado.get("ultima_ejecucion")
    if isinstance(ultima_ejecucion, datetime):
        espera = timedelta(minutes=_INTERVALO_REINTENTO_MINUTOS)
        if ahora_local - ultima_ejecucion < espera:
            return False

    return True


def _limpiar_estado_antiguo(fecha_local: str) -> None:
    """Elimina del estado los horarios de fechas locales anteriores.

    Args:
        fecha_local: Fecha local que se está procesando en este ciclo.
    """
    prefijo_actual = f"{fecha_local}_"
    for clave in list(_estado_horarios):
        if not clave.startswith(prefijo_actual):
            del _estado_horarios[clave]


def verificar_y_publicar() -> None:
    """Verifica los horarios locales y ejecuta las publicaciones pendientes."""
    ahora_local = _now_local()
    fecha_local = ahora_local.strftime("%Y-%m-%d")
    _limpiar_estado_antiguo(fecha_local)

    for horario in HORARIOS_PUBLICACION:
        clave = _clave_horario(horario, fecha_local)
        if not _debe_ejecutarse(horario, clave, ahora_local):
            continue

        estado = _estado_horarios.setdefault(clave, {"intentos": 0})
        estado["intentos"] = int(estado.get("intentos", 0)) + 1
        estado["ultima_ejecucion"] = ahora_local
        intento = int(estado["intentos"])

        hora_programada = _hora_programada(horario, ahora_local)
        print(
            f"\n🕐 ¡Es hora de {horario['label']}! "
            f"(local {hora_programada.strftime('%H:%M')}, "
            f"ejecución {ahora_local.strftime('%H:%M:%S %Z')}, "
            f"intento {intento}/{_MAX_INTENTOS_POR_HORARIO})"
        )

        exito = ejecutar_publicacion(
            str(horario["modulo"]),
            str(horario["label"]),
        )
        if exito:
            estado["completado"] = True
            print("  📝 Registrado como publicado hoy")
        elif intento >= _MAX_INTENTOS_POR_HORARIO:
            estado["agotado"] = True
            print("  ⚠️  Horario agotado después de varios intentos")
        else:
            print(
                f"  🔁 Se reintentará en {_INTERVALO_REINTENTO_MINUTOS} minutos"
            )


def main() -> None:
    """Ejecuta el scheduler en un loop continuo."""
    global running

    try:
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        tz_info = f"UTC{_TZ_OFFSET:+d}" if _TZ_OFFSET != 0 else "UTC"
        horarios_str = ", ".join(
            f"{horario['label']} a las {horario['hora']:02d}:{horario['minuto']:02d} "
            f"({tz_info}) → {horario['hora_utc']:02d}:{horario['minuto_utc']:02d} UTC"
            for horario in HORARIOS_PUBLICACION
        )

        print("━" * 60)
        print("  🔄 Scheduler iniciado")
        print(f"  🌍 Timezone: {tz_info} (offset={_TZ_OFFSET:+d}h)")
        print(f"  📰 Publicación: {horarios_str}")
        print(f"  ⏰ Hora actual UTC: {_now_utc().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"  ⏰ Hora local: {_now_local().strftime('%Y-%m-%d %H:%M:%S %Z')}")
        print("━" * 60)

    except Exception as error:
        print(f"  ❌ Error fatal en inicialización: {error}")
        import traceback

        traceback.print_exc()
        sys.exit(1)

    print("  ✅ Scheduler listo para procesar")

    while running:
        try:
            verificar_y_publicar()
        except KeyboardInterrupt:
            print("\n  ⚠️  Interrumpido por usuario")
            running = False
        except Exception as error:
            print(f"  ❌ Error en scheduler: {error}")
            import traceback

            traceback.print_exc()

        try:
            time.sleep(_INTERVALO_REVISION_SEGUNDOS)
        except KeyboardInterrupt:
            print("\n  ⚠️  Interrumpido durante espera")
            running = False

    print("  👋 Scheduler detenido.")


if __name__ == "__main__":
    main()
