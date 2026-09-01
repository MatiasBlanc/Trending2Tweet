"""Bot de Código y Programación: obtiene historias técnicas y guarda borradores en Obsidian.

Uso:
    python -m bots.codigo [cantidad]
"""

import sys

from sources.hacker_news_client import get_best_stories, get_top_stories
from src import config
from src.engine import run_pipeline

PROMPT_FILE = "prompts/prompt_codigo.txt"

KEYWORDS = (
    "code", "coding", "programming", "programming language", "software",
    "developer", "developers", "compiler", "interpreter", "open source",
    "github", "git", "python", "javascript", "typescript", "rust",
    "golang", "java", "react", "linux", "terminal", "cli", "api",
    "database", "docker", "kubernetes", "vscode", "neovim", "vim", "emacs",
)

ESTILO_GANCHO = (
    "Enfócate en la consecuencia práctica para quien escribe y mantiene software. "
    "Contrasta la promesa de la noticia con el trabajo real de un desarrollador."
)


def _fetch_code_news() -> list[dict]:
    limit_pool = max(config.NEWS_LIMIT * 20, 100)
    stories = get_best_stories(limit_pool) if config.NEWS_SOURCE == "best" else get_top_stories(limit_pool)
    return [
        s for s in stories
        if s.get("score", 0) >= config.NEWS_MIN_SCORE
        and any(k in s.get("title", "").lower() for k in KEYWORDS)
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
        bot_name="codigo",
        display_name="💻 Code News Bot (Obsidian)",
        category="codigo",
        prompt_file=PROMPT_FILE,
        fetch_items=_fetch_code_news,
        format_user_message=_format_message,
        get_item_id=lambda s: str(s["id"]),
        get_title=lambda s: s["title"],
        get_url=lambda s: s.get("url") or f"https://news.ycombinator.com/item?id={s['id']}",
        get_variables=lambda s: {"estilo_gancho": ESTILO_GANCHO},
        limit=limit,
    )


if __name__ == "__main__":
    main()
