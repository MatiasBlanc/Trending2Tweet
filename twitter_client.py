"""Cliente para publicar tweets en X/Twitter usando tweepy (API v2)."""

import tweepy

import config
from metrics_db import registrar_tweet


def crear_cliente() -> tweepy.Client:
    """Crea y retorna un cliente autenticado de Twitter API v2.

    Returns:
        Cliente de tweepy configurado.

    Raises:
        ValueError: Si faltan credenciales de Twitter.
    """
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


def publicar_tweet(
    texto: str,
    source: str = "unknown",
    item_id: str = None,
    prompt_file: str = None,
    template_estilo: str = None,
) -> dict:
    """Publica un tweet en X/Twitter y lo registra en la base de métricas.

    Args:
        texto: Contenido del tweet (sin URLs).
        source: Fuente del tweet (github, github_manual, news).
        item_id: ID del item procesado (gh_123, nw_456).
        prompt_file: Ruta del prompt usado para generar el tweet.
        template_estilo: Estilo de gancho usado (si aplica).

    Returns:
        Diccionario con 'id' y 'text' del tweet publicado.

    Raises:
        Exception: Error de la API de Twitter.
    """
    client = crear_cliente()
    respuesta = client.create_tweet(text=texto)

    tweet_id = respuesta.data["id"]

    # Registrar en la base de datos de métricas
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
        # No fallar la publicación si falla el registro
        print(f"  ⚠️ No se pudo registrar en metrics DB: {e}")

    return {
        "id": tweet_id,
        "text": texto,
    }


def publicar_respuesta(tweet_id: str, texto: str) -> dict:
    """Publica una respuesta a un tweet existente.

    Args:
        tweet_id: ID del tweet al que responder.
        texto: Contenido de la respuesta.

    Returns:
        Diccionario con 'id' y 'text' de la respuesta.

    Raises:
        Exception: Error de la API de Twitter.
    """
    client = crear_cliente()
    respuesta = client.create_tweet(text=texto, in_reply_to_tweet_id=tweet_id)

    return {
        "id": respuesta.data["id"],
        "text": texto,
    }
