"""Bot de posts sobre teclados y periféricos usando Reddit.

Uso: python -m bots.teclados
"""

import sys

from src import config
from sources.reddit_client import obtener_posts_teclados
from src.llm_client import generate_tweet
from db.metrics_db import is_processed
from src.publishing import publicar_y_registrar

PROMPT_FILE = "prompts/prompt_teclados.txt"

ESTILO_GANCHO = (
    "Enfócate en cómo el post cambia la experiencia de escribir, la ergonomía "
    "o la personalización. Evita tratar el teclado como un simple accesorio."
)

# Posts de fotos pura (builds sin texto) dan menos material. Un selftext largo
# es ideal; un título largo y descriptivo suele bastar para un build con nombre.
_MIN_LARGO_TITULO = 40
_MIN_LARGO_TEXTO = 80

# Títulos genéricos de showcase que no aportan material para un tweet.
_TITULOS_INFORMATIVOS = (
    "build",
    "keyboard",
    "keycap",
    "switch",
    "firmware",
    "layout",
    "ergo",
    "split",
    "colemak",
    "dvorak",
    "qmk",
    "via",
    "corne",
    "alice",
    "tofu",
    "mtnu",
    "susuwatari",
    "review",
    "guide",
    "compare",
    "first build",
    "typing",
)


def _post_con_sustancia(post: dict) -> bool:
    """Determina si un post tiene material suficiente para un tweet.

    Args:
        post: Publicación normalizada de Reddit.

    Returns:
        True si el post tiene texto descriptivo o un título informativo.
    """
    if len(post["texto"]) >= _MIN_LARGO_TEXTO:
        return True
    titulo = post["title"].lower()
    return len(post["title"]) >= _MIN_LARGO_TITULO and any(
        palabra in titulo for palabra in _TITULOS_INFORMATIVOS
    )


def construir_mensaje_usuario(post: dict) -> str:
    """Construye el contexto que recibirá el modelo para un post de Reddit.

    Args:
        post: Publicación con título, autor, texto y subreddit.

    Returns:
        Texto con los datos relevantes del post.
    """
    msg = (
        f"Publicación de r/{post['subreddit']}\n"
        f"Título: {post['title']}\n"
        f"Autor: {post['author']}"
    )
    if post["texto"]:
        msg += f"\n\nTexto de la publicación:\n{post['texto']}"
    return msg


def main() -> bool:
    """Ejecuta el bot de teclados y devuelve si publicó un tweet.

    Returns:
        True cuando se publica y registra un post; False si no hay posts
        válidos o ninguna publicación termina correctamente.
    """
    print("━" * 50)
    print("  ⌨️  Teclados Bot (Reddit)")
    print("━" * 50)

    try:
        posts = obtener_posts_teclados(limite_por_sub=10)
    except Exception as error:
        print(f"  ❌ Error consultando Reddit: {error}")
        sys.exit(1)

    if not posts:
        print("  ⚠️  No se encontraron publicaciones.")
        return False

    print(f"  Posts encontrados: {len(posts)}")

    for post in posts:
        if is_processed(post["id"]):
            print(f"\n  ⏭  Ya publicada: {post['title'][:60]}...")
            continue

        if not _post_con_sustancia(post):
            print(f"\n  ⏭  Sin material: {post['title'][:60]}...")
            continue

        print(f"\n  📰 Post: {post['title'][:60]}...")
        try:
            tweet_text = generate_tweet(
                PROMPT_FILE,
                construir_mensaje_usuario(post),
                variables={"estilo_gancho": ESTILO_GANCHO},
            )
        except Exception as error:
            print(f"  ❌ Error generando tweet: {error}")
            continue

        if config.FORCE_280_CHAR_TWEET and len(tweet_text) > 280:
            tweet_text = tweet_text[:277] + "..."

        if publicar_y_registrar(post["id"], "teclados", tweet_text):
            return True

    print("\n  ⚠️  No se pudo publicar ninguna publicación.")
    return False


if __name__ == "__main__":
    raise SystemExit(0 if main() else 1)
