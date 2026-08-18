"""Lógica compartida para bots de noticias organizados por tema."""

from collections.abc import Sequence

from db.metrics_db import is_processed
from sources.hacker_news_client import get_best_stories, get_top_stories
from src import config
from src.llm_client import generate_tweet
from src.publishing import publicar_y_registrar


def obtener_historias_tematicas(keywords: Sequence[str]) -> list[dict]:
    """Obtiene historias de Hacker News que coinciden con un tema.

    Args:
        keywords: Palabras o expresiones que deben aparecer en el título.

    Returns:
        Historias que coinciden con el tema y superan la puntuación mínima.

    Raises:
        requests.RequestException: Si Hacker News no está disponible.
    """
    # Busca un pool amplio: los temas de nicho (teclados, código) rara vez
    # aparecen en las top 20-25 de Hacker News.
    cantidad_a_buscar = max(config.NEWS_LIMIT * 20, 100)
    if config.NEWS_SOURCE == "best":
        historias = get_best_stories(limit=cantidad_a_buscar)
    else:
        historias = get_top_stories(limit=cantidad_a_buscar)

    palabras = tuple(keyword.casefold() for keyword in keywords)
    historias_tematicas = [
        historia
        for historia in historias
        if historia["score"] >= config.NEWS_MIN_SCORE
        and any(palabra in historia["title"].casefold() for palabra in palabras)
    ]
    return historias_tematicas


def construir_mensaje_noticia(story: dict) -> str:
    """Construye el contexto que recibirá el modelo para una noticia.

    Args:
        story: Historia con título, puntuación, autor y cantidad de comentarios.

    Returns:
        Texto con los datos relevantes de la historia.
    """
    return (
        f"Título: {story['title']}\n"
        f"Puntuación: {story['score']} puntos\n"
        f"Autor: {story['author']}\n"
        f"Comentarios: {story['comments']}"
    )


def ejecutar_bot_tematico(
    nombre_bot: str,
    nombre_visible: str,
    prompt_file: str,
    keywords: Sequence[str],
    estilo_gancho: str,
) -> None:
    """Genera y publica un tweet para la primera historia disponible del tema.

    Args:
        nombre_bot: Identificador usado para registrar la publicación.
        nombre_visible: Nombre mostrado en la salida del proceso.
        prompt_file: Archivo de instrucciones específico del tema.
        keywords: Palabras o expresiones usadas para filtrar historias.
        estilo_gancho: Instrucción temática para abrir el tweet.

    Returns:
        None. La función termina después de publicar una historia o cuando no
        quedan historias válidas.
    """
    print("━" * 50)
    print(f"  {nombre_visible}")
    print("━" * 50)

    try:
        historias = obtener_historias_tematicas(keywords)
    except Exception as error:
        print(f"  ❌ Error consultando Hacker News: {error}")
        return

    if not historias:
        print("  ⚠️  No se encontraron historias nuevas para este tema.")
        return

    print(f"  Historias encontradas: {len(historias)}")

    for historia in historias:
        if is_processed(historia["id"]):
            print(f"\n  ⏭  Ya publicada: {historia['title'][:60]}...")
            continue

        print(f"\n  📰 Historia: {historia['title'][:60]}...")
        try:
            tweet_text = generate_tweet(
                prompt_file,
                construir_mensaje_noticia(historia),
                variables={"estilo_gancho": estilo_gancho},
            )
        except Exception as error:
            print(f"  ❌ Error generando tweet: {error}")
            continue

        if config.FORCE_280_CHAR_TWEET and len(tweet_text) > 280:
            tweet_text = tweet_text[:277] + "..."

        if publicar_y_registrar(historia["id"], nombre_bot, tweet_text):
            return

    print("\n  ⚠️  No se pudo publicar ninguna historia del tema.")
