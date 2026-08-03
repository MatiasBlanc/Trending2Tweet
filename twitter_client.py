"""Cliente para publicar tweets en X/Twitter usando tweepy (API v2 + v1.1).

Media upload: usa la API v1.1 (tweepy.API) para subir imágenes,
luego la API v2 (tweepy.Client) para publicar el tweet con media_ids.
"""

import os
import tempfile
from datetime import datetime
from typing import Optional

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


def _crear_api_v1() -> tweepy.API:
    """Crea cliente API v1.1 (necesario para media upload)."""
    auth = tweepy.OAuth1UserHandler(
        consumer_key=config.TWITTER_API_KEY,
        consumer_secret=config.TWITTER_API_SECRET,
        access_token=config.TWITTER_ACCESS_TOKEN,
        access_token_secret=config.TWITTER_ACCESS_SECRET,
    )
    return tweepy.API(auth)


def publicar_tweet(texto: str, imagen_path: Optional[str] = None) -> dict:
    """Publica un tweet en Twitter.

    Args:
        texto: Contenido del tweet.
        imagen_path: Ruta opcional a una imagen para adjuntar.

    Returns:
        Diccionario con el ID del tweet y datos adicionales.

    Raises:
        Exception: Si hay error en la publicación.
    """
    cliente_v2 = _crear_cliente_v2()
    
    media_ids = None
    if imagen_path and os.path.exists(imagen_path):
        try:
            api_v1 = _crear_api_v1()
            media = api_v1.media_upload(filename=imagen_path)
            media_ids = [media.media_id]
            print(f"  🖼️  Imagen subida: {media.media_id}")
        except Exception as e:
            print(f"  ⚠️  Error subiendo imagen: {e}")
            # Continuar sin imagen
    
    try:
        respuesta = cliente_v2.create_tweet(
            text=texto,
            media_ids=media_ids,
        )
        tweet_id = respuesta.data["id"]
        print(f"  ✅ Tweet publicado: {tweet_id}")
        
        return {
            "tweet_id": tweet_id,
            "texto": texto,
            "fecha": datetime.now().isoformat(),
            "imagen": imagen_path,
        }
    except Exception as e:
        print(f"  ❌ Error publicando tweet: {e}")
        raise