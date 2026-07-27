"""Migración de state.json a metrics.db.

Ejecutar una sola vez para migrar los IDs existentes.
"""

import json
from pathlib import Path
from datetime import datetime

from metrics_db import init_db, _get_connection


def migrar_state_json() -> None:
    """Migra los IDs de state.json a metrics.db como tweets legacy."""
    state_file = Path("state.json")

    if not state_file.exists():
        print("No se encontró state.json, nada que migrar.")
        return

    data = json.loads(state_file.read_text(encoding="utf-8"))
    processed_ids = data.get("processed_ids", [])

    if not processed_ids:
        print("state.json está vacío, nada que migrar.")
        return

    print(f"Migrando {len(processed_ids)} IDs de state.json a metrics.db...")

    init_db()
    conn = _get_connection()
    cursor = conn.cursor()

    migrados = 0
    ya_existian = 0

    for item_id in processed_ids:
        # Determinar source según el prefijo
        if item_id.startswith("gh_"):
            source = "github"
        elif item_id.startswith("nw_"):
            source = "news"
        else:
            source = "unknown"

        # Insertar como tweet legacy (sin tweet_id real de Twitter)
        # Usamos el item_id como tweet_id temporal
        try:
            cursor.execute(
                """
                INSERT OR IGNORE INTO tweets
                    (tweet_id, texto, source, item_id, published_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    f"legacy_{item_id}",  # ID temporal
                    f"[Tweet migrado de state.json - {item_id}]",
                    source,
                    item_id,
                    datetime.now().isoformat(),
                ),
            )
            if cursor.rowcount > 0:
                migrados += 1
            else:
                ya_existian += 1
        except Exception as e:
            print(f"  Error migrando {item_id}: {e}")

    conn.commit()
    conn.close()

    print(f"✅ Migración completada:")
    print(f"   - Migrados: {migrados}")
    print(f"   - Ya existían: {ya_existian}")

    # Renombrar state.json como backup
    backup_path = state_file.with_suffix(".json.backup")
    state_file.rename(backup_path)
    print(f"   - state.json renombrado a {backup_path.name}")


if __name__ == "__main__":
    migrar_state_json()
