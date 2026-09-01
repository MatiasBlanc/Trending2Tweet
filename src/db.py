"""Módulo de persistencia local SQLite para evitar procesamiento duplicado."""

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

from src import config

_DB_PATH = Path(config.METRICS_DB_PATH)


def _get_connection() -> sqlite3.Connection:
    """Retorna una conexión a la base de datos SQLite."""
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(_DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Inicializa la base de datos y crea la tabla si no existe."""
    with _get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tweets (
                tweet_id TEXT PRIMARY KEY,
                texto TEXT NOT NULL,
                source TEXT NOT NULL,
                item_id TEXT,
                published_at TEXT NOT NULL
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_tweets_item ON tweets(item_id)")


def is_processed(item_id: str) -> bool:
    """Verifica si un item ya fue procesado con anterioridad."""
    init_db()
    with _get_connection() as conn:
        cursor = conn.execute(
            "SELECT 1 FROM tweets WHERE item_id = ? LIMIT 1", (item_id,)
        )
        return cursor.fetchone() is not None


def mark_as_processed(
    item_id: str,
    source: str,
    tweet_id: Optional[str] = None,
    texto: Optional[str] = None,
) -> None:
    """Marca un item como procesado en la base de datos."""
    init_db()
    real_tweet_id = tweet_id or f"draft_{item_id}"
    real_texto = texto or "[Borrador en Obsidian]"

    with _get_connection() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO tweets
                (tweet_id, texto, source, item_id, published_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (real_tweet_id, real_texto, source, item_id, datetime.now().isoformat()),
        )


def remove_from_history(item_id: str) -> bool:
    """Elimina un item del historial para permitir regenerarlo."""
    init_db()
    with _get_connection() as conn:
        cursor = conn.execute("DELETE FROM tweets WHERE item_id = ?", (item_id,))
        return cursor.rowcount > 0


def count_processed() -> int:
    """Retorna el total de items procesados en la base de datos."""
    init_db()
    with _get_connection() as conn:
        cursor = conn.execute("SELECT COUNT(*) FROM tweets")
        return cursor.fetchone()[0]
