"""Sincronización local → Railway de items procesados.

Cuando el usuario procesa tweets desde su máquina (genera borradores o
publica manualmente), los bots locales marcan los items como procesados solo
en la DB local. Para que el scheduler de Railway no vuelva a publicar esos
items, esta utilidad los registra también en la DB del volume de Railway
(/data/metrics.db) usando la CLI de Railway (`railway ssh`).
"""

import subprocess

from src import config

# Python del venv dentro del container de Railway (nixpacks).
_RAILWAY_PYTHON = "/opt/venv/bin/python3"
_RAILWAY_APP_DIR = "/app"


def registrar_en_railway(item_id: str, source: str) -> bool:
    """Registra un item como procesado en la DB de Railway.

    Args:
        item_id: ID del item (ej: gh_123456, nw_123456).
        source: Fuente del item (github, news, github_manual...).

    Returns:
        True si el item quedó registrado (o ya existía), False si falló.
    """
    if not config.RAILWAY_SYNC_ENABLED:
        print("  ⚠️  Sincronización con Railway desactivada (RAILWAY_SYNC_ENABLED=false)")
        return False

    comando = (
        f"cd {_RAILWAY_APP_DIR} && "
        f"METRICS_DB_PATH=/data/metrics.db {_RAILWAY_PYTHON} "
        f"scripts/railway_register.py {item_id} {source}"
    )

    try:
        resultado = subprocess.run(
            ["railway", "ssh", comando],
            capture_output=True,
            text=True,
            timeout=config.RAILWAY_SSH_TIMEOUT,
        )
    except Exception as e:
        print(f"  ⚠️  Railway no disponible: {e}")
        return False

    if resultado.returncode != 0:
        print(f"  ⚠️  Error registrando en Railway: {resultado.stderr.strip()[:200]}")
        return False

    for linea in resultado.stdout.splitlines():
        if "Registrado" in linea or "Ya existe" in linea:
            print(f"  🚂 {linea.strip()}")
    return True


def sincronizar_items(items: list[tuple[str, str]]) -> int:
    """Registra una lista de items (item_id, source) en la DB de Railway.

    Args:
        items: Lista de tuplas (item_id, source).

    Returns:
        Cantidad de items registrados con éxito.
    """
    if not items:
        return 0

    # Agrupar en lotes para evitar comandos demasiado largos.
    lote: list[str] = []
    for item_id, source in items:
        lote.extend([item_id, source])

    comando = (
        f"cd {_RAILWAY_APP_DIR} && "
        f"METRICS_DB_PATH=/data/metrics.db {_RAILWAY_PYTHON} "
        f"scripts/railway_register.py {' '.join(lote)}"
    )

    try:
        resultado = subprocess.run(
            ["railway", "ssh", comando],
            capture_output=True,
            text=True,
            timeout=config.RAILWAY_SSH_TIMEOUT,
        )
    except Exception as e:
        print(f"  ⚠️  Railway no disponible: {e}")
        return 0

    if resultado.returncode != 0:
        print(f"  ⚠️  Error sincronizando con Railway: {resultado.stderr.strip()[:200]}")
        return 0

    for linea in resultado.stdout.splitlines():
        if "Registrado" in linea or "Ya existe" in linea:
            print(f"  🚂 {linea.strip()}")

    exitos = sum(1 for linea in resultado.stdout.splitlines() if "✅" in linea)
    return exitos
