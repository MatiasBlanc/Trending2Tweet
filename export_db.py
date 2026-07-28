"""Exporta la base de datos de métricas como SQL dump.

Se ejecuta como tarea temporal en Railway para exportar la DB.
Uso: railway run python export_db.py
"""

import sqlite3
import sys
from pathlib import Path

DB_PATH = "/data/metrics.db"


def main() -> None:
    """Exporta la DB como SQL dump a stdout."""
    db_path = Path(DB_PATH)

    if not db_path.exists():
        print("EMPTY")
        sys.exit(0)

    try:
        conn = sqlite3.connect(DB_PATH)
        for line in conn.iterdump():
            print(line)
        conn.close()
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
