"""Bot de Noticias Tech: obtiene noticias diarias y genera borradores en Obsidian.

Uso: python -m bots.news
"""

import random
import sys
from pathlib import Path

from src import config
from sources.hacker_news_client import get_top_stories, get_best_stories
from src.llm_client import generate_tweet
from db.metrics_db import is_processed, mark_as_processed
from src.card_generator import generate_news_card
from src.obsidian_vault import guardar_borrador, guardar_imagen_vault

PROMPT_FILE = "prompts/prompt_news.txt"

TECH_KEYWORDS = [
    "python", "javascript", "typescript", "rust", "go", "golang", "java",
    "react", "vue", "angular", "svelte", "nextjs", "next.js",
    "django", "flask", "fastapi", "express", "nestjs", "spring",
    "ai", "ml", "machine learning", "deep learning", "llm", "gpt",
    "openai", "anthropic", "claude", "gemini", "mistral", "llama",
    "transformer", "neural", "model", "training", "inference", "rag",
    "docker", "kubernetes", "k8s", "terraform", "aws", "gcp", "azure",
    "postgres", "mysql", "sqlite", "mongodb", "redis", "supabase",
    "blockchain", "ethereum", "solana", "web3", "bitcoin",
    "api", "rest", "graphql", "grpc", "microservice", "monorepo",
    "linux", "git", "terminal", "shell", "bash", "npm", "cargo",
    "apple", "google", "microsoft", "meta", "amazon", "nvidia",
    "browser", "chrome", "firefox", "wasm", "webassembly",
]

EXCLUDE_KEYWORDS = [
    "earthquake", "terremoto", "tsunami", "hurricane", "tornado",
    "war", "guerra", "conflict", "politics", "political", "election",
    "celebrity", "movie", "film", "music", "album", "sport", "football",
    "soccer", "basketball", "tennis", "nba", "nfl", "fifa", "olympics",
    "recipe", "cooking", "food", "restaurant", "diet", "fashion",
    "travel", "tourism", "hotel", "vacation", "flight", "real estate",
]

ESTILOS_GANCHO = [
    "Abre con la consecuencia más incómoda o inesperada de esta noticia para los developers. No la noticia en sí, sino lo que implica en la práctica.",
    "Usa el formato 'Todo lo que sabíamos sobre [X] acaba de cambiar' adaptado al contexto exacto de la noticia. Sé específico.",
    "Abre revelando el dato más sorprendente o contraintuitivo de la noticia — el que la mayoría pasaría por alto pero que cambia cómo se lee todo lo demás.",
    "Plantea la tensión central que esta noticia crea en el ecosistema: ¿quién gana, quién pierde, qué stack queda en duda?",
    "Abre con la pregunta que los seniors de tu empresa estarían haciendo en Slack ahora mismo si vieran esta noticia.",
    "Usa el contraste: muestra cómo era antes vs. cómo cambia ahora con esta noticia. Una sola línea, sin relleno.",
    "Abre con una afirmación que divida a la comunidad en dos posiciones claras. El objetivo es que quien lee sienta la necesidad de posicionarse.",
    "Comienza con el dato de tracción de Hacker News (puntos + comentarios) como prueba social de por qué esta noticia merece atención ahora.",
]


def es_noticia_tech(titulo: str) -> bool:
    """Verifica si una noticia es relevante para el público tech/developer."""
    titulo_lower = titulo.lower()
    
    for keyword in EXCLUDE_KEYWORDS:
        if keyword in titulo_lower:
            return False
    
    for keyword in TECH_KEYWORDS:
        if keyword in titulo_lower:
            return True
    
    return False


def construir_mensaje_usuario(story: dict) -> str:
    """Construye el mensaje del usuario para el LLM."""
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

    for story in stories:
        if is_processed(story["id"]):
            print(f"\n  ⏭  Ya publicada: {story['title'][:60]}...")
            continue

        if story["score"] < config.NEWS_MIN_SCORE:
            print(f"\n  ⏭  Score bajo ({story['score']}): {story['title'][:60]}...")
            continue

        if not es_noticia_tech(story["title"]):
            print(f"\n  ⏭  No es tech: {story['title'][:60]}...")
            continue

        print(f"\n  📰 Nueva noticia: {story['title'][:60]}...")
        print(f"     Puntuación: {story['score']} | Comentarios: {story['comments']}")

        estilo_gancho = random.choice(ESTILOS_GANCHO)
        try:
            mensaje = construir_mensaje_usuario(story)
            variables = {"estilo_gancho": estilo_gancho}
            tweet_text = generate_tweet(PROMPT_FILE, mensaje, variables)
        except Exception as e:
            print(f"  ❌ Error generando tweet: {e}")
            continue

        if config.FORCE_280_CHAR_TWEET and len(tweet_text) > 280:
            tweet_text = tweet_text[:277] + "..."

        imagen_path = None
        try:
            image_bytes = generate_news_card(
                title=story["title"],
                score=story["score"],
                comments=story["comments"],
                author=story.get("author", ""),
            )
            if image_bytes:
                print(f"  🖼️  Tarjeta visual generada")
                imagen_path = guardar_imagen_vault(
                    image_bytes=image_bytes,
                    nombre_archivo=story["title"][:50],
                    source="news",
                )
        except Exception as e:
            print(f"  ⚠️  No se pudo generar tarjeta: {e}")

        try:
            filepath = guardar_borrador(
                texto=tweet_text,
                source="news",
                titulo=story["title"],
                url=story["url"],
                item_id=story["id"],
                prompt_file=PROMPT_FILE,
                template_estilo=estilo_gancho[:100],
                imagen_path=imagen_path,
                notas=f"Puntuación HN: {story['score']} | Comentarios: {story['comments']}",
            )
            if filepath:
                print(f"  📝 Borrador guardado: {Path(filepath).name}")
                mark_as_processed(story["id"], "news", texto=tweet_text[:100])
        except Exception as e:
            print(f"  ⚠️  No se pudo guardar borrador: {e}")

        print(f"\n{'━' * 50}")
        print(f"  ✅ Completado: 1 borrador creado")
        print(f"{'━' * 50}")
        return

    print("\n  ⚠️  No hay noticias nuevas para procesar.")


if __name__ == "__main__":
    main()
