"""Motor de ejecución unificado y escalable para todos los bots temáticos."""

from collections.abc import Callable
from pathlib import Path
from typing import Any, Optional

from src import config
from src.db import is_processed
from src.llm_client import generate_tweet
from src.obsidian_vault import guardar_borrador


def run_pipeline(
    bot_name: str,
    display_name: str,
    category: str,
    prompt_file: str,
    fetch_items: Callable[[], list[dict[str, Any]]],
    format_user_message: Callable[[dict[str, Any]], str],
    get_item_id: Callable[[dict[str, Any]], str],
    get_title: Callable[[dict[str, Any]], Optional[str]] = lambda item: item.get("title"),
    get_url: Callable[[dict[str, Any]], Optional[str]] = lambda item: item.get("url"),
    prepare_item: Optional[Callable[[dict[str, Any]], dict[str, Any]]] = None,
    get_variables: Optional[Callable[[dict[str, Any]], dict[str, str]]] = None,
    get_metadata: Optional[Callable[[dict[str, Any]], dict[str, Any]]] = None,
    limit: int = 1,
) -> bool:
    """Ejecuta el ciclo de vida completo de un bot de contenido:
    1. Obtiene los elementos desde la fuente.
    2. Descarta los ya procesados en la base de datos local.
    3. Prepara datos adicionales si es necesario (ej. README).
    4. Genera el tweet con IA usando el prompt y variables correspondientes.
    5. Guarda el borrador en la carpeta de la categoría en Obsidian.
    6. Marca el elemento como procesado.

    Returns:
        True si generó y guardó al menos un borrador; False en caso contrario.
    """
    limite_seguro = min(max(limit, 1), config.MAX_GENERATION_LIMIT)

    print("━" * 50)
    print(f"  {display_name}")
    print("━" * 50)

    try:
        items = fetch_items()
    except Exception as error:
        print(f"  ❌ Error consultando la fuente de datos: {error}")
        return False

    if not items:
        print("  ⚠️  No se encontraron elementos nuevos.")
        return False

    print(f"  📦 Elementos consultados: {len(items)}")

    guardados = 0
    for item in items:
        item_id = get_item_id(item)
        if is_processed(item_id):
            continue

        titulo = get_title(item) or item_id
        print(f"\n  🎯 Seleccionado: {titulo[:60]}...")

        # Preparación previa (ej. README para GitHub)
        if prepare_item:
            try:
                item = prepare_item(item)
            except Exception as e:
                print(f"  ⚠️ Error en preparación previa: {e}")

        # Generar tweet con LLM
        print("  ✍️  Generando tweet con IA...")
        try:
            user_message = format_user_message(item)
            variables = get_variables(item) if get_variables else None
            tweet_text = generate_tweet(prompt_file, user_message, variables=variables)
        except Exception as error:
            print(f"  ❌ Error generando tweet: {error}")
            continue

        if config.FORCE_280_CHAR_TWEET and len(tweet_text) > 280:
            tweet_text = tweet_text[:277] + "..."

        print(f"\n{'━' * 50}")
        print("  Tweet generado:")
        print(f"{'━' * 50}")
        print(tweet_text)
        print(f"{'━' * 50}")

        meta = get_metadata(item) if get_metadata else {}
        url = get_url(item)

        filepath = guardar_borrador(
            texto=tweet_text,
            categoria=category,
            source=bot_name,
            titulo=titulo,
            url=url,
            repo_name=meta.get("repo_name"),
            repo_stars=meta.get("repo_stars"),
            item_id=item_id,
            prompt_file=prompt_file,
            template_estilo=meta.get("template_estilo"),
            notas=meta.get("notas"),
        )

        if filepath:
            from src.db import mark_as_processed
            mark_as_processed(item_id, bot_name, texto=tweet_text[:100])
            print(f"  ✅ Borrador guardado en Obsidian: {Path(filepath).name}")
            print(f"  📂 Carpeta: {category}/")
            guardados += 1

            if guardados >= limite_seguro:
                break

    if guardados > 0:
        print(f"\n✨ Completado: {guardados} borrador(es) guardado(s) en Obsidian [{category}/].")
        return True

    print("\n  ⚠️  No se pudo procesar ningún elemento nuevo.")
    return False
