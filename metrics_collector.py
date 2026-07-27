"""Recolector automático de métricas de tweets usando Twitter API v2."""

import sys
import time
from datetime import datetime

import tweepy

import config
from metrics_db import (
    init_db,
    obtener_tweets_pendientes_colecta,
    actualizar_metricas,
    guardar_historial,
)

# Ventanas de tiempo para colectar métricas (en minutos)
VENTANAS_COLECTA = [
    30,    # 30 minutos después de publicado
    120,   # 2 horas
    1440,  # 24 horas
    10080, # 7 días
]


def crear_cliente() -> tweepy.Client:
    """Crea un cliente autenticado de Twitter API v2.

    Returns:
        Cliente de tweepy configurado.
    """
    return tweepy.Client(
        consumer_key=config.TWITTER_API_KEY,
        consumer_secret=config.TWITTER_API_SECRET,
        access_token=config.TWITTER_ACCESS_TOKEN,
        access_token_secret=config.TWITTER_ACCESS_SECRET,
    )


def obtener_metricas_tweet(client: tweepy.Client, tweet_id: str) -> dict:
    """Obtiene las métricas actuales de un tweet.

    Args:
        client: Cliente de tweepy.
        tweet_id: ID del tweet.

    Returns:
        Diccionario con las métricas del tweet.

    Raises:
        Exception: Si no se puede obtener el tweet.
    """
    response = client.get_tweet(
        tweet_id,
        tweet_fields=["public_metrics", "created_at"],
    )

    if not response.data:
        raise Exception(f"Tweet {tweet_id} no encontrado")

    metrics = response.data.public_metrics

    return {
        "likes": metrics.get("like_count", 0),
        "retweets": metrics.get("retweet_count", 0),
        "replies": metrics.get("reply_count", 0),
        "impressions": metrics.get("impression_count", 0),
        "bookmarks": metrics.get("bookmark_count", 0),
    }


def colectar_metricas() -> dict:
    """Ejecuta la recolección de métricas para tweets pendientes.

    Returns:
        Diccionario con estadísticas de la recolección.
    """
    init_db()

    # Verificar credenciales
    if not all([
        config.TWITTER_API_KEY,
        config.TWITTER_API_SECRET,
        config.TWITTER_ACCESS_TOKEN,
        config.TWITTER_ACCESS_SECRET,
    ]):
        print("❌ Faltan credenciales de Twitter en .env")
        sys.exit(1)

    # Obtener tweets pendientes
    tweets_pendientes = obtener_tweets_pendientes_colecta(minutos_minimo=30)

    if not tweets_pendientes:
        print("✅ No hay tweets pendientes de colectar métricas")
        return {"colectados": 0, "errores": 0}

    print(f"📊 Colectando métricas para {len(tweets_pendientes)} tweets...")
    print("━" * 50)

    client = crear_cliente()
    colectados = 0
    errores = 0

    for tweet in tweets_pendientes:
        tweet_id = tweet["tweet_id"]
        published_at = tweet["published_at"]

        try:
            # Obtener métricas de la API
            metricas = obtener_metricas_tweet(client, tweet_id)

            # Actualizar métricas actuales
            actualizar_metricas(
                tweet_id=tweet_id,
                likes=metricas["likes"],
                retweets=metricas["retweets"],
                replies=metricas["replies"],
                impressions=metricas["impressions"],
                bookmarks=metricas["bookmarks"],
            )

            # Guardar en historial
            guardar_historial(
                tweet_id=tweet_id,
                likes=metricas["likes"],
                retweets=metricas["retweets"],
                replies=metricas["replies"],
                impressions=metricas["impressions"],
                bookmarks=metricas["bookmarks"],
            )

            total_engagement = (
                metricas["likes"] + metricas["retweets"] + metricas["replies"]
            )

            print(f"  ✅ {tweet_id}: "
                  f"❤️ {metricas['likes']} "
                  f"🔁 {metricas['retweets']} "
                  f"💬 {metricas['replies']} "
                  f"👁 {metricas['impressions']}")

            colectados += 1

            # Rate limit: esperar entre requests
            time.sleep(2)

        except tweepy.TooManyRequests:
            print(f"  ⚠️ Rate limit alcanzado. Esperando 15 minutos...")
            time.sleep(900)
            # Reintentar este tweet
            try:
                metricas = obtener_metricas_tweet(client, tweet_id)
                actualizar_metricas(
                    tweet_id=tweet_id,
                    likes=metricas["likes"],
                    retweets=metricas["retweets"],
                    replies=metricas["replies"],
                    impressions=metricas["impressions"],
                    bookmarks=metricas["bookmarks"],
                )
                guardar_historial(
                    tweet_id=tweet_id,
                    likes=metricas["likes"],
                    retweets=metricas["retweets"],
                    replies=metricas["replies"],
                    impressions=metricas["impressions"],
                    bookmarks=metricas["bookmarks"],
                )
                colectados += 1
            except Exception as e:
                print(f"  ❌ Error en reintento para {tweet_id}: {e}")
                errores += 1

        except Exception as e:
            print(f"  ❌ Error para {tweet_id}: {e}")
            errores += 1

    print("━" * 50)
    print(f"  ✅ Colectados: {colectados}")
    if errores:
        print(f"  ❌ Errores: {errores}")

    return {"colectados": colectados, "errores": errores}


def main() -> None:
    """Punto de entrada principal."""
    print("━" * 50)
    print("  📊 Metrics Collector")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("━" * 50)

    resultado = colectar_metricas()

    if resultado["colectados"] == 0 and resultado["errores"] == 0:
        print("\n  ℹ️  No había nada que colectar.")


if __name__ == "__main__":
    main()
