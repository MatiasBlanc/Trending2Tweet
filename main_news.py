"""Bot de Noticias Tech: obtiene noticias diarias, genera y publica tweets.

Ejecución automatizada sin interacción del usuario.
La URL de la noticia se guarda en archivo aparte para agregar como comentario.
"""

import random
import sys
from datetime import datetime
from pathlib import Path

import config
from sources.hacker_news_client import get_top_stories, get_best_stories
from llm_client import generate_tweet
from twitter_client import publicar_tweet
from metrics_db import load_processed, is_processed

PROMPT_FILE = "prompts/prompt_news.txt"

# Estilos de gancho para variar el tono de los tweets
# Optimizados para maximizar reply velocity en los primeros 30 minutos
ESTILOS_GANCHO = [
    "Abre con la consecuencia más incómoda o inesperada de esta noticia para los developers. No la noticia en sí, sino lo que implica en la práctica para quien escribe código hoy.",
    "Usa el formato 'Todo lo que sabíamos sobre [X] acaba de cambiar' adaptado al contexto exacto de la noticia. Sé específico con qué es lo que cambió.",
    "Abre revelando el dato más sorprendente o contraintuitivo de la noticia — el que la mayoría pasaría por alto pero que cambia cómo se lee todo lo demás.",
    "Plantea la tensión central que esta noticia crea en el ecosistema: ¿quién gana, quién pierde, qué stack queda en duda? Empieza con esa fricción.",
    "Abre con la pregunta que los seniors de tu empresa estarían haciendo en Slack ahora mismo si vieran esta noticia. Concreta, técnica, sin respuesta obvia.",
    "Usa el contraste: muestra cómo era antes vs. cómo cambia ahora con esta noticia. Una sola línea, sin relleno.",
    "Abre con una afirmación que divida a la comunidad en dos posiciones claras. El objetivo es que quien lee sienta la necesidad de posicionarse.",
    "Comienza con el dato de tracción de Hacker News (puntos + comentarios) como prueba social de por qué esta noticia merece atención ahora, luego revela el tema.",
]


def guardar_tweet_con_url(tweet_text: str, story_id: str, story_title: str, story_url: str) -> str:
    """Guarda el tweet y la URL en un archivo .txt con timestamp.

    Args:
        tweet_text: Texto del tweet generado (sin URL).
        story_id: ID de la noticia (ej: nw_123456).
        story_title: Título de la noticia.
        story_url: URL de la noticia (para agregar como comentario).

    Returns:
        Ruta del archivo creado.
    """
    tweets_dir = Path("tweets")
    tweets_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_title = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in story_title[:30])
    filename = tweets_dir / f"nw_{safe_title}_{timestamp}.txt"

    contenido = (
        f"ID: {story_id}\n"
        f"Título: {story_title}\n"
        f"URL: {story_url}\n"
        f"{'─' * 40}\n"
        f"{tweet_text}\n"
    )

    filename.write_text(contenido, encoding="utf-8")
    return str(filename)


def construir_mensaje_usuario(story: dict) -> str:
    """Construye el mensaje del usuario para el LLM (sin URL).

    Args:
        story: Diccionario con datos de la noticia.

    Returns:
        Mensaje formateado para el LLM.
    """
    return (
        f"Título: {story['title']}\n"
        f"Puntuación: {story['score']} puntos\n"
        f"Autor: {story['author']}\n"
        f"Comentarios: {story['comments']}"
    )


def main() -> None:
    """Ejecución principal del bot de noticias."""
    print("━" * 50)
    print("  Tech News Bot")
    print("━" * 50)

    # 1. Cargar estado previo
    processed = load_processed()
    print(f"  Items en historial: {len(processed)}")
    print(f"  Source: metrics.db")

    # 2. Obtener noticias según fuente configurada
    try:
        if config.NEWS_SOURCE == "best":
            stories = get_best_stories(limit=config.NEWS_LIMIT)
        else:
            stories = get_top_stories(limit=config.NEWS_LIMIT)
    except Exception as e:
        print(f"Error consultando noticias: {e}")
        sys.exit(1)

    if not stories:
        print("No se encontraron noticias nuevas.")
        return

    print(f"  Noticias encontradas: {len(stories)}")

    # 3. Buscar la primera noticia nueva y publicarla
    for story in stories:
        # Verificar si ya fue publicado
        if is_processed(story["id"]):
            print(f"\n  ⏭  Ya publicada: {story['title'][:60]}...")
            continue

        # Filtrar por puntuación mínima
        if story["score"] < config.NEWS_MIN_SCORE:
            print(f"\n  ⏭  Score bajo ({story['score']}): {story['title'][:60]}...")
            continue

        print(f"\n  📰 Nueva noticia: {story['title'][:60]}...")
        print(f"     Puntuación: {story['score']} | Comentarios: {story['comments']}")

        # Generar tweet (sin URL) con estilo aleatorio
        estilo_gancho = random.choice(ESTILOS_GANCHO)
        try:
            mensaje = construir_mensaje_usuario(story)
            variables = {"estilo_gancho": estilo_gancho}
            tweet_text = generate_tweet(PROMPT_FILE, mensaje, variables)
        except Exception as e:
            print(f"  ❌ Error generando tweet: {e}")
            sys.exit(1)

        # Truncar si excede 280 chars
        if config.FORCE_280_CHAR_TWEET and len(tweet_text) > 280:
            tweet_text = tweet_text[:277] + "..."

        # Publicar en Twitter
        try:
            resultado = publicar_tweet(
                texto=tweet_text,
                source="news",
                item_id=story["id"],
                prompt_file=PROMPT_FILE,
                template_estilo=estilo_gancho[:100],  # Truncar para que quepa en DB
            )
            print(f"  🐦 Publicado en Twitter (ID: {resultado['id']})")
        except Exception as e:
            print(f"  ❌ Error publicando en Twitter: {e}")
            sys.exit(1)

        # Guardar tweet + URL en archivo
        filename = guardar_tweet_con_url(tweet_text, story["id"], story["title"], story["url"])
        print(f"  💾 Guardado: {filename}")
        print(f"  📎 URL para comentario: {story['url']}")

        # Persistir estado (ya se hace automáticamente en twitter_client)
        # processed.add(story["id"])
        # save_processed(processed)

        print(f"\n{'━' * 50}")
        print(f"  ✅ Completado: 1 tweet publicado")
        print(f"{'━' * 50}")
        return

    print("\n  ⚠️  No hay noticias nuevas para publicar.")


if __name__ == "__main__":
    main()
