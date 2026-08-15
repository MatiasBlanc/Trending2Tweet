"""Utilidades compartidas para publicar y registrar contenido."""

from db.metrics_db import mark_as_processed
from twitter_client import publicar_tweet


def publicar_y_registrar(item_id: str, source: str, texto: str) -> bool:
    """Publica un tweet y registra el elemento solo después del éxito.

    Args:
        item_id: Identificador único del contenido procesado.
        source: Nombre del bot que origina la publicación.
        texto: Texto final que se publicará en X.

    Returns:
        True si la publicación y el registro se completaron correctamente;
        False si ocurrió un error durante la publicación.
    """
    try:
        resultado = publicar_tweet(texto=texto)
        mark_as_processed(
            item_id,
            source,
            tweet_id=resultado["tweet_id"],
            texto=texto[:100],
        )
        print(f"\n{'━' * 50}")
        print(f"  ✅ Tweet publicado: {resultado['tweet_id']}")
        print(f"{'━' * 50}")
        return True
    except Exception as error:
        print(f"  ❌ Error publicando tweet: {error}")
        return False
