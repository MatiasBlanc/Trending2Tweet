"""Migración: sube todos los items de la DB local a la DB de Railway.

Uso: python scripts/sync_local_to_railway.py

Registra en el volume de Railway todos los items que ya están procesados en
la DB local, para que el scheduler no vuelva a publicar contenido que el
usuario ya generó o publicó desde su máquina.
"""

import sys
from pathlib import Path

# Asegurar que los módulos del proyecto se importen desde la raíz.
sys.path.insert(0, str(Path(__file__).parent.parent))

from db.metrics_db import obtener_todos_tweets  # noqa: E402
from src import config  # noqa: E402
from src.railway_sync import sincronizar_items  # noqa: E402


def main() -> None:
    """Ejecuta la migración de items locales hacia Railway."""
    print("━" * 50)
    print("  Sincronización local → Railway")
    print("━" * 50)

    if not config.RAILWAY_SYNC_ENABLED:
        print("  ⚠️  RAILWAY_SYNC_ENABLED=false, abortando.")
        sys.exit(1)

    tweets = obtener_todos_tweets(limit=10000)
    items = [
        (t["item_id"], t["source"])
        for t in tweets
        if t.get("item_id")
    ]

    if not items:
        print("  ℹ️  No hay items en la DB local.")
        return

    print(f"  📦 Subiendo {len(items)} items a Railway...")
    registrados = sincronizar_items(items)
    print(f"\n  ✅ Sincronización completada: {registrados} registrados.")


if __name__ == "__main__":
    main()
