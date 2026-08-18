"""Bot de Noticias Tech: obtiene noticias diarias y publica tweets.

Uso: python -m bots.news
"""

import random
import sys

from src import config
from sources.hacker_news_client import get_top_stories, get_best_stories
from src.llm_client import generate_tweet
from db.metrics_db import is_processed
from src.publishing import publicar_y_registrar

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
    "Destruye el mito que la mayoría asocia con esta noticia. No resumas; cuestiona lo que el lector cree saber.",
    "Revela la consecuencia más incómoda para los developers que usan esto a diario. La que nadie quiere escuchar.",
    "Señala el error de lectura más común que provocaría esta noticia. ¿Qué entiende mal la mayoría?",
    "Contrasta lo que la noticia parece decir vs. lo que realmente dice. Una línea para cada uno.",
    "Plantea la pregunta que un senior haría en Slack al ver esto: corta, directa, sin contexto previo.",
    "Afirmación divisiva: toma un lado que obligue al lector a posicionarse. Sin tibieza.",
    "El mecanismo concreto detrás de la noticia que cambia cómo se interpreta todo lo demás. Sé técnico.",
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


def main() -> bool:
    """Ejecuta el bot de noticias y devuelve si publicó un tweet.

    Returns:
        True cuando se publica y registra una noticia; False cuando no hay
        una historia válida o ninguna publicación termina correctamente.
    """
    print("━" * 50)
    print("  Tech News Bot")
    print("━" * 50)

    try:
        if config.NEWS_SOURCE == "best":
            stories = get_best_stories(limit=config.NEWS_FETCH_LIMIT)
        else:
            stories = get_top_stories(limit=config.NEWS_FETCH_LIMIT)
    except Exception as e:
        print(f"Error consultando noticias: {e}")
        sys.exit(1)

    if not stories:
        print("No se encontraron noticias nuevas.")
        return False

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

        if publicar_y_registrar(story["id"], "news", tweet_text):
            return True

    print("\n  ⚠️  No hay noticias nuevas para procesar.")
    return False


if __name__ == "__main__":
    raise SystemExit(0 if main() else 1)
