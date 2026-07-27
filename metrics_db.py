"""Módulo de base de datos SQLite para métricas de tweets."""

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

import config

DB_PATH = Path(config.METRICS_DB_PATH)


def _get_connection() -> sqlite3.Connection:
    """Obtiene una conexión a la base de datos.

    Returns:
        Conexión SQLite con row_factory configurado.
    """
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
            prompt_file TEXT,
            template_estilo TEXT,
            source TEXT NOT NULL,
            item_id TEXT,
            published_at TEXT NOT NULL,
            likes_latest INTEGER DEFAULT 0,
            retweets_latest INTEGER DEFAULT 0,
            replies_latest INTEGER DEFAULT 0,
            impressions_latest INTEGER DEFAULT 0,
            bookmarks_latest INTEGER DEFAULT 0,
            engagement_score REAL DEFAULT 0.0,
            last_collected_at TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS metrics_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tweet_id TEXT NOT NULL,
            collected_at TEXT NOT NULL,
            likes INTEGER DEFAULT 0,
            retweets INTEGER DEFAULT 0,
            replies INTEGER DEFAULT 0,
            impressions INTEGER DEFAULT 0,
            bookmarks INTEGER DEFAULT 0,
            FOREIGN KEY (tweet_id) REFERENCES tweets(tweet_id)
        )
    """)

    # Índices para consultas frecuentes
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_tweets_source ON tweets(source)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_tweets_published ON tweets(published_at)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_history_tweet ON metrics_history(tweet_id)
    """)

    conn.commit()
    conn.close()


def registrar_tweet(
    tweet_id: str,
    texto: str,
    source: str,
    item_id: str = None,
    prompt_file: str = None,
    template_estilo: str = None,
) -> None:
    """Registra un nuevo tweet publicado en la base de datos.

    Args:
        tweet_id: ID del tweet en Twitter.
        texto: Contenido del tweet.
        source: Fuente (github, github_manual, news).
        item_id: ID del item procesado (gh_123, nw_456).
        prompt_file: Ruta del prompt usado.
        template_estilo: Estilo de gancho usado (si aplica).
    """
    init_db()
    conn = _get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT OR REPLACE INTO tweets
            (tweet_id, texto, prompt_file, template_estilo, source, item_id, published_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            tweet_id,
            texto,
            prompt_file,
            template_estilo,
            source,
            item_id,
            datetime.now().isoformat(),
        ),
    )

    conn.commit()
    conn.close()


def actualizar_metricas(
    tweet_id: str,
    likes: int,
    retweets: int,
    replies: int,
    impressions: int = 0,
    bookmarks: int = 0,
) -> None:
    """Actualiza las métricas más recientes de un tweet.

    Args:
        tweet_id: ID del tweet.
        likes: Cantidad de likes.
        retweets: Cantidad de retweets.
        replies: Cantidad de replies.
        impressions: Cantidad de impresiones.
        bookmarks: Cantidad de bookmarks.
    """
    conn = _get_connection()
    cursor = conn.cursor()

    # Calcular engagement score ponderado
    engagement_score = (
        likes * config.ENGAGEMENT_WEIGHTS.get("likes", 1.0)
        + retweets * config.ENGAGEMENT_WEIGHTS.get("retweets", 2.0)
        + replies * config.ENGAGEMENT_WEIGHTS.get("replies", 3.0)
        + bookmarks * config.ENGAGEMENT_WEIGHTS.get("bookmarks", 2.5)
    )

    cursor.execute(
        """
        UPDATE tweets SET
            likes_latest = ?,
            retweets_latest = ?,
            replies_latest = ?,
            impressions_latest = ?,
            bookmarks_latest = ?,
            engagement_score = ?,
            last_collected_at = ?
        WHERE tweet_id = ?
        """,
        (likes, retweets, replies, impressions, bookmarks, engagement_score,
         datetime.now().isoformat(), tweet_id),
    )

    conn.commit()
    conn.close()


def guardar_historial(
    tweet_id: str,
    likes: int,
    retweets: int,
    replies: int,
    impressions: int = 0,
    bookmarks: int = 0,
) -> None:
    """Guarda un snapshot de métricas en el historial.

    Args:
        tweet_id: ID del tweet.
        likes: Cantidad de likes.
        retweets: Cantidad de retweets.
        replies: Cantidad de replies.
        impressions: Cantidad de impresiones.
        bookmarks: Cantidad de bookmarks.
    """
    conn = _get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO metrics_history
            (tweet_id, collected_at, likes, retweets, replies, impressions, bookmarks)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (tweet_id, datetime.now().isoformat(), likes, retweets, replies, impressions, bookmarks),
    )

    conn.commit()
    conn.close()


def obtener_tweets_pendientes_colecta(minutos_minimo: int = 30) -> list[dict]:
    """Obtiene tweets que necesitan actualización de métricas.

    Args:
        minutos_minimo: Minutos mínimos desde publicación para considerar.

    Returns:
        Lista de diccionarios con datos de tweets pendientes.
    """
    init_db()
    conn = _get_connection()
    cursor = conn.cursor()

    # Tweets publicados hace más de X minutos y no colectados recientemente
    cursor.execute("""
        SELECT * FROM tweets
        WHERE datetime(published_at) <= datetime('now', ?)
        AND (
            last_collected_at IS NULL
            OR datetime(last_collected_at) <= datetime('now', '-1 hour')
        )
        ORDER BY published_at DESC
    """, (f'-{minutos_minimo} minutes',))

    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


def obtener_todos_tweets(order_by: str = "published_at", limit: int = 100) -> list[dict]:
    """Obtiene todos los tweets ordenados por un campo.

    Args:
        order_by: Campo para ordenar (published_at, engagement_score).
        limit: Cantidad máxima de resultados.

    Returns:
        Lista de diccionarios con datos de tweets.
    """
    init_db()
    conn = _get_connection()
    cursor = conn.cursor()

    # Validar campo de ordenamiento
    campos_validos = {"published_at", "engagement_score", "likes_latest", "retweets_latest"}
    if order_by not in campos_validos:
        order_by = "published_at"

    cursor.execute(f"""
        SELECT * FROM tweets
        ORDER BY {order_by} DESC
        LIMIT ?
    """, (limit,))

    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


def obtener_historial_tweet(tweet_id: str) -> list[dict]:
    """Obtiene el historial de métricas de un tweet.

    Args:
        tweet_id: ID del tweet.

    Returns:
        Lista de snapshots de métricas ordenados por fecha.
    """
    conn = _get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM metrics_history
        WHERE tweet_id = ?
        ORDER BY collected_at ASC
    """, (tweet_id,))

    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


def obtener_estadisticas_por_fuente() -> list[dict]:
    """Obtiene estadísticas agrupadas por fuente.

    Returns:
        Lista con estadísticas por source.
    """
    init_db()
    conn = _get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            source,
            COUNT(*) as total_tweets,
            ROUND(AVG(engagement_score), 2) as avg_engagement,
            ROUND(AVG(likes_latest), 1) as avg_likes,
            ROUND(AVG(retweets_latest), 1) as avg_retweets,
            ROUND(AVG(replies_latest), 1) as avg_replies,
            MAX(engagement_score) as max_engagement
        FROM tweets
        GROUP BY source
    """)

    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


def obtener_estadisticas_por_prompt() -> list[dict]:
    """Obtiene estadísticas agrupadas por prompt usado.

    Returns:
        Lista con estadísticas por prompt_file.
    """
    init_db()
    conn = _get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            prompt_file,
            COUNT(*) as total_tweets,
            ROUND(AVG(engagement_score), 2) as avg_engagement,
            ROUND(AVG(likes_latest), 1) as avg_likes,
            ROUND(AVG(retweets_latest), 1) as avg_retweets,
            ROUND(AVG(replies_latest), 1) as avg_replies,
            MAX(engagement_score) as max_engagement
        FROM tweets
        GROUP BY prompt_file
    """)

    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


def obtener_estadisticas_por_estilo() -> list[dict]:
    """Obtiene estadísticas agrupadas por estilo de gancho.

    Returns:
        Lista con estadísticas por template_estilo.
    """
    init_db()
    conn = _get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            template_estilo,
            COUNT(*) as total_tweets,
            ROUND(AVG(engagement_score), 2) as avg_engagement,
            ROUND(AVG(likes_latest), 1) as avg_likes,
            ROUND(AVG(retweets_latest), 1) as avg_retweets,
            ROUND(AVG(replies_latest), 1) as avg_replies,
            MAX(engagement_score) as max_engagement
        FROM tweets
        WHERE template_estilo IS NOT NULL
        GROUP BY template_estilo
    """)

    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


def obtener_tweets_para_few_shot(cantidad: int = 5) -> list[dict]:
    """Obtiene los tweets con mayor engagement para usar como ejemplos.

    Args:
        cantidad: Número de ejemplos a retornar.

    Returns:
        Lista de tweets ordenados por engagement.
    """
    init_db()
    conn = _get_connection()
    cursor = conn.cursor()

    # Solo tweets con métricas ya colectadas
    cursor.execute("""
        SELECT texto, engagement_score, likes_latest, retweets_latest
        FROM tweets
        WHERE last_collected_at IS NOT NULL
        AND engagement_score > 0
        ORDER BY engagement_score DESC
        LIMIT ?
    """, (cantidad,))

    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]
