"""Bot de Teclados y Periféricos: obtiene posts de Reddit y guarda borradores en Obsidian.

Uso:
    python -m bots.teclados [cantidad]
"""

import sys

from sources.reddit_client import obtener_posts_teclados
from src import config
from src.engine import run_pipeline

PROMPT_FILE = "prompts/prompt_teclados.txt"

ESTILO_GANCHO = (
    "Enfócate en cómo el post cambia la experiencia de escribir, la ergonomía "
    "o la personalización. Evita tratar el teclado como un simple accesorio."
)

_MIN_LARGO_TITULO = 40
_MIN_LARGO_TEXTO = 80
_TITULOS_INFORMATIVOS = (
    "build", "keyboard", "keycap", "switch", "firmware", "layout",
    "ergo", "split", "colemak", "dvorak", "qmk", "via", "corne",
    "alice", "tofu", "mtnu", "susuwatari", "review", "guide", "compare", "typing",
)


def _tiene_sustancia(post: dict) -> bool:
    if len(post.get("texto", "")) >= _MIN_LARGO_TEXTO:
        return True
    t = post.get("title", "").lower()
    return len(t) >= _MIN_LARGO_TITULO and any(p in t for p in _TITULOS_INFORMATIVOS)


def _fetch_posts() -> list[dict]:
    posts = obtener_posts_teclados(limite_por_sub=10)
    return [p for p in posts if _tiene_sustancia(p)]


def _format_message(post: dict) -> str:
    msg = (
        f"Publicación de r/{post['subreddit']}\n"
        f"Título: {post['title']}\n"
        f"Autor: {post['author']}"
    )
    if post.get("texto"):
        msg += f"\n\nTexto de la publicación:\n{post['texto']}"
    return msg


def main() -> None:
    limit = (
        min(int(sys.argv[1]), config.MAX_GENERATION_LIMIT)
        if len(sys.argv) > 1 and sys.argv[1].isdigit()
        else 1
    )
    run_pipeline(
        bot_name="teclados",
        display_name="⌨️  Teclados Bot (Reddit - Obsidian)",
        category="teclado",
        prompt_file=PROMPT_FILE,
        fetch_items=_fetch_posts,
        format_user_message=_format_message,
        get_item_id=lambda p: p["id"],
        get_title=lambda p: p["title"],
        get_url=lambda p: p.get("url") or "",
        get_variables=lambda p: {"estilo_gancho": ESTILO_GANCHO},
        limit=limit,
    )


if __name__ == "__main__":
    main()
