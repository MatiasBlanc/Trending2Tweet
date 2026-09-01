"""Bot de Noticias Tech: obtiene historias de Hacker News y guarda borradores en Obsidian.

Uso:
    python -m bots.news [cantidad]
"""

import random
import sys

from sources.hacker_news_client import get_best_stories, get_top_stories
from src import config
from src.engine import run_pipeline

PROMPT_FILE = "prompts/prompt_news.txt"

TECH_KEYWORDS = (
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
)

EXCLUDE_KEYWORDS = (
    "earthquake", "terremoto", "tsunami", "hurricane", "tornado",
    "war", "guerra", "conflict", "politics", "political", "election",
    "celebrity", "movie", "film", "music", "album", "sport", "football",
    "soccer", "basketball", "tennis", "nba", "nfl", "fifa", "olympics",
    "recipe", "cooking", "food", "restaurant", "diet", "fashion",
    "travel", "tourism", "hotel", "vacation", "flight", "real estate",
)

ESTILOS_GANCHO = (
    "Destruye el mito que la mayoría asocia con esta noticia. No resumas; cuestiona lo que el lector cree saber.",
    "Revela la consecuencia más incómoda para los developers que usan esto a diario. La que nadie quiere escuchar.",
    "Señala el error de lectura más común que provocaría esta noticia. ¿Qué entiende mal la mayoría?",
    "Contrasta lo que la noticia parece decir vs. lo que realmente dice. Una línea para cada uno.",
    "Plantea la pregunta que un senior haría en Slack al ver esto: corta, directa, sin contexto previo.",
    "Afirmación divisiva: toma un lado que obligue al lector a posicionarse. Sin tibieza.",
    "El mecanismo concreto detrás de la noticia que cambia cómo se interpreta todo lo demás. Sé técnico.",
)


def _es_noticia_tech(titulo: str) -> bool:
    t = titulo.lower()
    if any(k in t for k in EXCLUDE_KEYWORDS):
        return False
    return any(k in t for k in TECH_KEYWORDS)


def _fetch_news() -> list[dict]:
    stories = get_best_stories(config.NEWS_FETCH_LIMIT) if config.NEWS_SOURCE == "best" else get_top_stories(config.NEWS_FETCH_LIMIT)
    return [
        s for s in stories
        if s.get("score", 0) >= config.NEWS_MIN_SCORE and _es_noticia_tech(s.get("title", ""))
    ]


def _format_message(story: dict) -> str:
    return (
        f"Título: {story['title']}\n"
        f"Puntuación: {story['score']} puntos\n"
        f"Autor: {story['author']}\n"
        f"Comentarios: {story['comments']}"
    )


def main() -> None:
    limit = (
        min(int(sys.argv[1]), config.MAX_GENERATION_LIMIT)
        if len(sys.argv) > 1 and sys.argv[1].isdigit()
        else 1
    )
    run_pipeline(
        bot_name="news",
        display_name="📰 Tech News Bot (Obsidian)",
        category="news",
        prompt_file=PROMPT_FILE,
        fetch_items=_fetch_news,
        format_user_message=_format_message,
        get_item_id=lambda s: str(s["id"]),
        get_title=lambda s: s["title"],
        get_url=lambda s: s.get("url") or f"https://news.ycombinator.com/item?id={s['id']}",
        get_variables=lambda s: {"estilo_gancho": random.choice(ESTILOS_GANCHO)},
        limit=limit,
    )


if __name__ == "__main__":
    main()
