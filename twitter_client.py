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


def _separar_hilo(texto: str) -> list[str]:
    """Separa un hilo usando el delimitador que utiliza la bóveda."""
    partes = [parte.strip() for parte in texto.split("\n---\n")]
    return [parte for parte in partes if parte] or [texto.strip()]


def publicar_tweet(texto: str) -> dict:
    """Publica un tweet o un hilo de texto en Twitter/X.

    Args:
        texto: Contenido del tweet; los hilos usan ``\\n---\\n`` entre partes.

    Returns:
        Diccionario con el ID del primer tweet, todos los IDs y datos adicionales.

    Raises:
        ValueError: Si el contenido está vacío.
        Exception: Si hay error durante la publicación.
    """
    if not texto.strip():
        raise ValueError("No se puede publicar un tweet vacío.")

    cliente_v2 = _crear_cliente_v2()
    partes = _separar_hilo(texto)
    ids: list[str] = []

    try:
        for parte in partes:
            parametros: dict[str, str] = {"text": parte}
            if ids:
                parametros["in_reply_to_tweet_id"] = ids[-1]
            respuesta = cliente_v2.create_tweet(**parametros)
            if not respuesta.data or "id" not in respuesta.data:
                raise RuntimeError("X no devolvió el ID del tweet publicado.")
            ids.append(respuesta.data["id"])

        etiqueta = "Hilo publicado" if len(ids) > 1 else "Tweet publicado"
        print(f"  ✅ {etiqueta}: {ids[0]}")
        return {
            "tweet_id": ids[0],
            "tweet_ids": ids,
            "texto": texto,
            "fecha": datetime.now().isoformat(),
        }
    except Exception as error:
        detalle = f" ({len(ids)} parte(s) publicada(s))" if ids else ""
        print(f"  ❌ Error publicando en X{detalle}: {error}")
        raise