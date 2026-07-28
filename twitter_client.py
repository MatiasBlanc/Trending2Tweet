"""Cliente para publicar tweets en X/Twitter usando tweepy (API v2 + v1.1).

Media upload: usa la API v1.1 (tweepy.API) para subir imágenes,
luego la API v2 (tweepy.Client) para publicar el tweet con media_ids.
"""

import os
import tempfile
from typing import Optional

import tweepy

import config
from metrics_db import registrar_tweet


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


# Alias público para compatibilidad con metrics_collector
def crear_cliente() -> tweepy.Client:
    return _crear_cliente_v2()


def subir_imagen(image_bytes: bytes) -> Optional[str]:
    """Sube una imagen a Twitter y devuelve el media_id.

    Args:
        image_bytes: Bytes de la imagen PNG.

    Returns:
        media_id_string si fue exitoso, None si falló.
    """
    try:
        api_v1 = _crear_api_v1()
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            tmp.write(image_bytes)
            tmp_path = tmp.name
        try:
            media = api_v1.media_upload(filename=tmp_path)
            return str(media.media_id)
        finally:
            os.unlink(tmp_path)
    except Exception as e:
        print(f"  ⚠️ Error subiendo imagen: {e}")
        return None


def publicar_tweet(
    texto: str,
    source: str = "unknown",
    item_id: str = None,
    prompt_file: str = None,
    template_estilo: str = None,
    image_bytes: bytes = None,
) -> dict:
    """Publica un tweet en X/Twitter (con imagen opcional) y lo registra.

    Args:
        texto: Contenido del tweet.
        source: Fuente (github, news, github_manual).
        item_id: ID del item procesado.
        prompt_file: Ruta del prompt usado.
        template_estilo: Estilo de gancho usado (si aplica).
        image_bytes: Bytes PNG de la imagen a adjuntar (opcional).

    Returns:
        Diccionario con 'id', 'text' y 'has_media'.
    """
    client = _crear_cliente_v2()

    # Subir imagen si se provee
    media_id = None
    if image_bytes:
        print("  🖼️  Subiendo imagen...")
        media_id = subir_imagen(image_bytes)
        if media_id:
            print(f"  ✅ Imagen subida (media_id: {media_id})")
        else:
            print("  ⚠️  Continuando sin imagen...")

    # Publicar tweet
    kwargs = {"text": texto}
    if media_id:
        kwargs["media_ids"] = [media_id]

    respuesta = client.create_tweet(**kwargs)
    tweet_id  = respuesta.data["id"]

    # Registrar en métricas
    try:
        registrar_tweet(
            tweet_id=tweet_id,
            texto=texto,
            source=source,
            item_id=item_id,
            prompt_file=prompt_file,
            template_estilo=template_estilo,
        )
    except Exception as e:
        print(f"  ⚠️ No se pudo registrar en metrics DB: {e}")

    return {"id": tweet_id, "text": texto, "has_media": media_id is not None}


def publicar_respuesta(tweet_id: str, texto: str) -> dict:
    """Publica una respuesta a un tweet existente."""
    client = _crear_cliente_v2()
    respuesta = client.create_tweet(text=texto, in_reply_to_tweet_id=tweet_id)
    return {"id": respuesta.data["id"], "text": texto}
