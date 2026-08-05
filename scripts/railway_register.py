"""Registra items como procesados en la DB de Railway (volume /data).

Este script corre dentro del container de Railway y se invoca desde la
máquina local vía `railway ssh`. Su propósito es que el scheduler de Railway
conozca los items que el usuario ya procesó localmente (borradores o
publicaciones manuales) y no los vuelva a publicar.

Uso (dentro del container de Railway):
    /opt/venv/bin/python3 scripts/railway_register.py <item_id> <source> [<item_id> <source> ...]

También acepta líneas "item_id source" por stdin.
"""

import os
import sys
from pathlib import Path

# La DB del volume de Railway siempre vive en /data/metrics.db.
os.environ["METRICS_DB_PATH"] = "/data/metrics.db"

# Asegurar que el directorio raíz del proyecto (/app) esté en el path.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from db.metrics_db import init_db, is_processed, mark_as_processed  # noqa: E402


def _registrar(item_id: str, source: str) -> str:
    """Registra un item como procesado en la DB de Railway.

    Args:
        item_id: ID del item (ej: gh_123456, nw_123456).
        source: Fuente del item (github, news, github_manual...).

    Returns:
        Mensaje con el resultado de la operación.
    """
    init_db()
    if is_processed(item_id):
        return f"  ⏭  Ya existe en Railway: {item_id}"
    mark_as_processed(item_id, source, texto="[Registrado desde local]")
    return f"  ✅ Registrado en Railway: {item_id} (source={source})"


def main() -> None:
    """Punto de entrada: procesa pares item_id/source desde args o stdin."""
    pares: list[tuple[str, str]] = []

    if len(sys.argv) >= 3:
        args = sys.argv[1:]
        for i in range(0, len(args) - 1, 2):
            pares.append((args[i], args[i + 1]))
    elif not sys.stdin.isatty():
        for linea in sys.stdin:
            partes = linea.strip().split()
            if len(partes) >= 2:
                pares.append((partes[0], partes[1]))

    if not pares:
        print("Uso: railway_register.py <item_id> <source> [<item_id> <source> ...]")
        print("  o por stdin: 'item_id source' por línea")
        sys.exit(2)

    for item_id, source in pares:
        print(_registrar(item_id, source))


if __name__ == "__main__":
    main()
