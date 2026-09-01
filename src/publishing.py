"""Utilidades compartidas para guardar borradores, publicar y archivar contenido."""

from typing import Optional
from pathlib import Path

from src.db import mark_as_processed
from twitter_client import publicar_tweet
from src.obsidian_vault import (
    guardar_borrador,
    marcar_como_publicado,
    normalizar_categoria,
)


def guardar_tweet_manual(
    texto: str,
    categoria: str,
    source: str,
    item_id: str,
    titulo: Optional[str] = None,
    url: Optional[str] = None,
    repo_name: Optional[str] = None,
    repo_stars: Optional[int] = None,
    prompt_file: Optional[str] = None,
    template_estilo: Optional[str] = None,
    notas: Optional[str] = None,
) -> Optional[str]:
    """Guarda un tweet como borrador en la carpeta de su categoría y lo registra en la DB local.

    Args:
        texto: Contenido del tweet.
        categoria: 'teclado', 'github', 'news', 'codigo'.
        source: Fuente del bot.
        item_id: ID único del elemento.
        titulo: Título opcional.
        url: URL opcional.
        repo_name: Nombre de repo.
        repo_stars: Stars del repo.
        prompt_file: Archivo de prompt.
        template_estilo: Estilo de plantilla.
        notas: Notas.

    Returns:
        Ruta del archivo guardado en Obsidian, o None si falló.
    """
    cat_norm = normalizar_categoria(categoria)
    filepath = guardar_borrador(
        texto=texto,
        categoria=cat_norm,
        source=source,
        titulo=titulo,
        url=url,
        repo_name=repo_name,
        repo_stars=repo_stars,
        item_id=item_id,
        prompt_file=prompt_file,
        template_estilo=template_estilo,
        notas=notas,
    )

    if filepath:
        mark_as_processed(
            item_id=item_id,
            source=source,
            texto=texto[:100],
        )
    return filepath


def publicar_y_archivar_borrador(filepath: str, texto: Optional[str] = None) -> bool:
    """Publica un tweet en Twitter/X y lo mueve a la carpeta de archivados.

    Args:
        filepath: Ruta al archivo Markdown en Obsidian.
        texto: Texto a publicar. Si es None, se lee del archivo.

    Returns:
        True si se publicó y archivó con éxito, False si falló.
    """
    from src.obsidian_vault import obtener_tweet_para_publicar, _parsear_frontmatter

    path = Path(filepath)
    if not path.exists():
        print(f"  ❌ Archivo no encontrado: {filepath}")
        return False

    tweet_text = texto or obtener_tweet_para_publicar(filepath)
    if not tweet_text:
        print(f"  ❌ No se pudo extraer el texto del tweet de {filepath}")
        return False

    try:
        resultado = publicar_tweet(texto=tweet_text)
        tweet_id = resultado["tweet_id"]

        info = _parsear_frontmatter(path) or {}
        item_id = info.get("item_id", f"file_{path.stem}")
        source = info.get("source", "manual")

        mark_as_processed(
            item_id=item_id,
            source=source,
            tweet_id=tweet_id,
            texto=tweet_text[:100],
        )

        marcar_como_publicado(filepath, tweet_id=tweet_id)

        print(f"\n{'━' * 50}")
        print(f"  ✅ Tweet publicado en X: {tweet_id}")
        print(f"  📦 Movido a carpeta archivados")
        print(f"{'━' * 50}")
        return True
    except Exception as error:
        print(f"  ❌ Error publicando tweet: {error}")
        return False
def publicar_y_registrar(item_id: str, source: str, texto: str) -> bool:
    """Publica directamente un tweet y lo registra en la base de datos."""
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
