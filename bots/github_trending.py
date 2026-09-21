"""Bot de GitHub Trending: descubre repos trending y guarda borradores en Obsidian.

Uso:
    python -m bots.github_trending [cantidad]
"""

import sys

from sources.github_client import (
    get_readme_content,
    get_trending_repos,
    is_signal_repo,
)
from src import config
from src.engine import run_pipeline

PROMPT_FILE = "prompts/prompt_github.txt"


def _fetch_repos() -> list[dict]:
    """Obtiene repos recientes y elimina señales obvias de ruido.

    El cliente ya aplica el filtro antes de normalizar, pero repetirlo aquí
    mantiene este bot seguro si se reemplaza el cliente por un adaptador propio.
    """
    repos = get_trending_repos(limit=config.GITHUB_FETCH_LIMIT)
    return [repo for repo in repos if is_signal_repo(repo)]


def _prepare_repo(repo: dict) -> dict:
    readme = get_readme_content(repo["name"])
    if readme:
        repo["readme_content"] = readme
    return repo


def _format_message(repo: dict) -> str:
    msg = (
        f"Repo: {repo['name']}\n"
        f"Descripción: {repo['description']}\n"
        f"Lenguaje: {repo['language']}\n"
        f"Stars: {repo['stars']}\n"
        f"Forks: {repo.get('forks', 0)}\n"
        f"Señal pública: {repo.get('signal_score', 'n/d')} "
        f"({', '.join(repo.get('signal_reasons', []))})"
    )
    if repo.get("readme_content"):
        msg += f"\n\n--- README del repositorio ---\n{repo['readme_content']}\n--- Fin del README ---"
    return msg


def main() -> None:
    limit = (
        min(int(sys.argv[1]), config.MAX_GENERATION_LIMIT)
        if len(sys.argv) > 1 and sys.argv[1].isdigit()
        else 1
    )
    run_pipeline(
        bot_name="github_trending",
        display_name="🐙 GitHub Trending Bot (Obsidian)",
        category="github",
        prompt_file=PROMPT_FILE,
        fetch_items=_fetch_repos,
        format_user_message=_format_message,
        get_item_id=lambda r: r["id"],
        get_title=lambda r: r["name"],
        get_url=lambda r: r.get("url") or f"https://github.com/{r['name']}",
        prepare_item=_prepare_repo,
        get_metadata=lambda r: {
            "repo_name": r["name"],
            "repo_stars": r["stars"],
            "notas": (
                "Filtro de señal aplicado: "
                + ", ".join(r.get("signal_reasons", []))
            ),
        },
        limit=limit,
    )


if __name__ == "__main__":
    main()
