"""Base de datos SQLite para métricas de tweets."""

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

from src import config

DB_PATH = Path(config.METRICS_DB_PATH)


def _get_connection() -> sqlite3.Connection:
    """Obtiene una conexión a la base de datos."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Inicializa la base de datos y crea las tablas si no existen."""
    conn = _get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tweets (
            tweet_id TEXT PRIMARY KEY,
            texto TEXT NOT NULL,
            source TEXT NOT NULL,
            item_id TEXT,
            published_at TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_tweets_source ON tweets(source)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_tweets_item ON tweets(item_id)
    """)

    conn.commit()
    conn.close()


def registrar_tweet(
    tweet_id: str,
    texto: str,
    source: str,
    item_id: str = None,
) -> None:
    """Registra un nuevo tweet en la base de datos."""
    init_db()
    conn = _get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT OR REPLACE INTO tweets
            (tweet_id, texto, source, item_id, published_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (tweet_id, texto, source, item_id, datetime.now().isoformat()),
    )

    conn.commit()
    conn.close()


def is_processed(item_id: str) -> bool:
    """Verifica si un item ya fue procesado."""
    init_db()
    conn = _get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT 1 FROM tweets WHERE item_id = ? LIMIT 1",
        (item_id,),
    )
    result = cursor.fetchone()
    conn.close()

    return result is not None


def mark_as_processed(item_id: str, source: str, tweet_id: str = None, texto: str = None) -> None:
    """Marca un item como procesado."""
    init_db()
    conn = _get_connection()
    cursor = conn.cursor()

    real_tweet_id = tweet_id or f"pending_{item_id}"
    real_texto = texto or "[Tweet pendiente de publicar]"

    cursor.execute(
        """
        INSERT OR REPLACE INTO tweets
            (tweet_id, texto, source, item_id, published_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (real_tweet_id, real_texto, source, item_id, datetime.now().isoformat()),
    )

    conn.commit()
    conn.close()


def load_processed() -> set[str]:
    """Carga los IDs de items ya procesados."""
    init_db()
    conn = _get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT item_id FROM tweets WHERE item_id IS NOT NULL")
    rows = cursor.fetchall()
    conn.close()

    return {row["item_id"] for row in rows}


def obtener_todos_tweets(limit: int = 100) -> list[dict]:
    """Obtiene todos los tweets ordenados por fecha."""
    init_db()
    conn = _get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM tweets
        ORDER BY published_at DESC
        LIMIT ?
    """, (limit,))

    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


def obtener_tweet(tweet_id: str) -> Optional[dict]:
    """Obtiene un tweet por su ID."""
    init_db()
    conn = _get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM tweets WHERE tweet_id = ?", (tweet_id,))
    row = cursor.fetchone()
    conn.close()

    return dict(row) if row else None


def remove_from_history(item_id: str) -> bool:
    """Elimina un item del historial."""
    init_db()
    conn = _get_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM tweets WHERE item_id = ?", (item_id,))
    eliminado = cursor.rowcount > 0

    conn.commit()
    conn.close()

    return eliminado


def clear_history() -> int:
    """Limpia todo el historial."""
    init_db()
    conn = _get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM tweets")
    count = cursor.fetchone()[0]

    cursor.execute("DELETE FROM tweets")

    conn.commit()
    conn.close()

    return count
