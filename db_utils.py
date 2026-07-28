"""Utilidades para consultar y administrar la base de datos.

Uso:
    python db_utils.py --list          # Listar tweets
    python db_utils.py --stats         # Estadísticas
    python db_utils.py --export        # Exportar a CSV
    python db_utils.py --register ID   # Registrar tweet ya publicado
"""

import argparse
import csv
import sys
from datetime import datetime
from pathlib import Path

from metrics_db import init_db, obtener_todos_tweets, registrar_tweet


def listar_tweets() -> None:
    """Lista todos los tweets en la base de datos."""
    init_db()
    tweets = obtener_todos_tweets(limit=50)

    if not tweets:
        print("📭 No hay tweets en la base de datos.")
        return

    print(f"\n📊 Total: {len(tweets)} tweets\n")
    print(f"{'ID':<20} {'Source':<10} {'Likes':<8} {'RTs':<8} {'Replies':<8} {'Impressions':<12} {'Fecha':<20}")
    print("─" * 96)

    for t in tweets:
        fecha = t['published_at'][:19] if t['published_at'] else 'N/A'
        print(
            f"{t['tweet_id'][:18]:<20} "
            f"{t['source']:<10} "
            f"{t['likes_latest']:<8} "
            f"{t['retweets_latest']:<8} "
            f"{t['replies_latest']:<8} "
            f"{t['impressions_latest']:<12} "
            f"{fecha:<20}"
        )


def mostrar_estadisticas() -> None:
    """Muestra estadísticas resumidas."""
    init_db()
    tweets = obtener_todos_tweets(limit=100)

    if not tweets:
        print("📭 No hay datos para mostrar estadísticas.")
        return

    total = len(tweets)
    total_likes = sum(t['likes_latest'] or 0 for t in tweets)
    total_rts = sum(t['retweets_latest'] or 0 for t in tweets)
    total_replies = sum(t['replies_latest'] or 0 for t in tweets)
    total_impressions = sum(t['impressions_latest'] or 0 for t in tweets)

    print("\n📊 Estadísticas generales")
    print("─" * 40)
    print(f"  Total tweets:      {total}")
    print(f"  Total likes:       {total_likes}")
    print(f"  Total retweets:    {total_rts}")
    print(f"  Total replies:     {total_replies}")
    print(f"  Total impressions: {total_impressions:,}")
    print(f"  Promedio likes:    {total_likes / total:.1f}")
    print(f"  Promedio RTs:      {total_rts / total:.1f}")


def exportar_csv() -> None:
    """Exporta los tweets a un archivo CSV."""
    init_db()
    tweets = obtener_todos_tweets(limit=500)

    if not tweets:
        print("📭 No hay tweets para exportar.")
        return

    filename = f"tweets_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    filepath = Path("tweets") / filename
    filepath.parent.mkdir(exist_ok=True)

    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([
            'tweet_id', 'source', 'texto', 'likes', 'retweets',
            'replies', 'impressions', 'engagement_score', 'published_at'
        ])
        for t in tweets:
            writer.writerow([
                t['tweet_id'], t['source'], t['texto'],
                t['likes_latest'], t['retweets_latest'],
                t['replies_latest'], t['impressions_latest'],
                t['engagement_score'], t['published_at']
            ])

    print(f"✅ Exportado a: {filepath}")


def registrar_tweet_manual(tweet_id: str, source: str, texto: str = "") -> None:
    """Registra un tweet que ya fue publicado.

    Args:
        tweet_id: ID del tweet en Twitter.
        source: Fuente (github, news, github_manual).
        texto: Texto del tweet (opcional).
    """
    init_db()
    registrar_tweet(
        tweet_id=tweet_id,
        texto=texto or f"[Registrado manualmente - {tweet_id}]",
        source=source,
        item_id=tweet_id,
    )
    print(f"✅ Tweet {tweet_id} registrado como {source}")


def main() -> None:
    """Punto de entrada principal."""
    parser = argparse.ArgumentParser(description="Utilidades de base de datos")
    parser.add_argument("--list", action="store_true", help="Listar tweets")
    parser.add_argument("--stats", action="store_true", help="Mostrar estadísticas")
    parser.add_argument("--export", action="store_true", help="Exportar a CSV")
    parser.add_argument("--register", nargs=2, metavar=("TWEET_ID", "SOURCE"),
                        help="Registrar tweet existente (ID source)")

    args = parser.parse_args()

    if args.list:
        listar_tweets()
    elif args.stats:
        mostrar_estadisticas()
    elif args.export:
        exportar_csv()
    elif args.register:
        tweet_id, source = args.register
        registrar_tweet_manual(tweet_id, source)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
