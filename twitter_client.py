"""Cliente para publicar tweets en X/Twitter usando tweepy (API v2 + v1.1).

Media upload: usa la API v1.1 (tweepy.API) para subir imágenes,
luego la API v2 (tweepy.Client) para publicar el tweet con media_ids.
"""

from datetime import datetime

import tweepy

from src import config


def _crear_cliente_v2() -> tweepy.Client:
    """Crea un cliente autenticado de Twitter API v2."""
    if not all([
        config.TWITTER_API_KEY,
        config.TWITTER_API_SECRET,
        config.TWITTER_ACCESS_TOKEN,
        config.TWITTER_ACCESS_SECRET,
    ]):
        raise ValueError(
            "Faltan credenciales de Twitter. "
            "Configura TWITTER_API_KEY, TWITTER_API_SECRET, "
            "TWITTER_ACCESS_TOKEN y TWITTER_ACCESS_SECRET en .env"
        )
    return tweepy.Client(
        consumer_key=config.TWITTER_API_KEY,
        consumer_secret=config.TWITTER_API_SECRET,
        access_token=config.TWITTER_ACCESS_TOKEN,
        access_token_secret=config.TWITTER_ACCESS_SECRET,
    )


def publicar_tweet(texto: str) -> dict:
    """Publica un tweet de texto en Twitter.

    Args:
        texto: Contenido del tweet.

    Returns:
        Diccionario con el ID del tweet y datos adicionales.

    Raises:
        Exception: Si hay error en la publicación.
    """
    cliente_v2 = _crear_cliente_v2()

    try:
        respuesta = cliente_v2.create_tweet(text=texto)
        tweet_id = respuesta.data["id"]
        print(f"  ✅ Tweet publicado: {tweet_id}")
        
        return {
            "tweet_id": tweet_id,
            "texto": texto,
            "fecha": datetime.now().isoformat(),
        }
    except Exception as e:
        print(f"  ❌ Error publicando tweet: {e}")
        raise