"""Bot de GitHub Trending: descubre repos trending y publica tweets.

Uso: python -m bots.github_trending
"""

import sys

from src import config
from sources.github_client import get_trending_repos, get_readme_content
from src.llm_client import generate_tweet
from db.metrics_db import is_processed
from src.publishing import publicar_y_registrar

PROMPT_FILE = "prompts/prompt_github.txt"


def construir_mensaje_usuario(repo: dict) -> str:
    """Construye el mensaje del usuario para el LLM."""
    msg = (
        f"Repo: {repo['name']}\n"
        f"Descripción: {repo['description']}\n"
        f"Lenguaje: {repo['language']}\n"
        f"Stars: {repo['stars']}"
    )

    readme_content = repo.get("readme_content")
    if readme_content:
        msg += f"\n\n--- README del repositorio ---\n{readme_content}\n--- Fin del README ---"

    return msg


def main() -> bool:
    """Ejecuta el bot de GitHub y devuelve si publicó un tweet.

    Returns:
        True cuando se publica y registra un repositorio; False cuando no hay
        repositorios válidos o ninguna publicación termina correctamente.
    """
    print("━" * 50)
    print("  GitHub Trending Bot")
    print("━" * 50)

    # Más repos candidatos: el top-10 por stars casi no cambia entre días y el
    # bot se queda sin novedades. Con un pool mayor hay más probabilidad de
    # encontrar repos nuevos no procesados cada ejecución.
    try:
        repos = get_trending_repos(limit=30)
    except Exception as e:
        print(f"Error consultando GitHub: {e}")
        sys.exit(1)

    # Filtrar repos sin descripción real (espacios vacíos de los templates)
    # y los monstruos de IA que ya son conocidos por todos: no dan buen tweet.
    repos = [
        repo
        for repo in repos
        if repo["description"] != "Sin descripción"
        and repo["stars"] < 50_000
    ]

    if not repos:
        print("No se encontraron repositorios nuevos.")
        return False

    print(f"  Repos encontrados: {len(repos)}")

    for repo in repos:
        if is_processed(repo["id"]):
            print(f"\n  ⏭  Ya procesado: {repo['name']}")
            continue

        print(f"\n  📦 Nuevo repo: {repo['name']}")
        print(f"     {repo['description'][:80]}...")

        readme = get_readme_content(repo["name"])
        if readme:
            repo["readme_content"] = readme

        try:
            mensaje = construir_mensaje_usuario(repo)
            tweet_text = generate_tweet(PROMPT_FILE, mensaje)
        except Exception as e:
            print(f"  ❌ Error generando tweet: {e}")
            continue

        if config.FORCE_280_CHAR_TWEET and len(tweet_text) > 280:
            tweet_text = tweet_text[:277] + "..."

        if publicar_y_registrar(repo["id"], "github", tweet_text):
            return True

    print("\n  ⚠️  No se pudo publicar ningún repositorio.")
    return False


if __name__ == "__main__":
    raise SystemExit(0 if main() else 1)
