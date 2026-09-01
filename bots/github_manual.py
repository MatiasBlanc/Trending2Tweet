"""Bot de GitHub Manual: genera borrador de tweet para un repo específico.

Uso:
    python -m bots.github_manual user/repo
Ejemplo:
    python -m bots.github_manual facebook/react
"""

import sys
from pathlib import Path

from sources.github_client import get_repo_info, get_readme_content
from src.db import mark_as_processed, is_processed, remove_from_history
from src.llm_client import generate_tweet
from src.obsidian_vault import guardar_borrador

PROMPT_FILE = "prompts/prompt_github.txt"


def _format_message(repo: dict) -> str:
    msg = (
        f"Repo: {repo['name']}\n"
        f"Descripción: {repo['description']}\n"
        f"Lenguaje: {repo['language']}\n"
        f"Stars: {repo['stars']}"
    )
    if repo.get("readme_content"):
        msg += f"\n\n--- README del repositorio ---\n{repo['readme_content']}\n--- Fin del README ---"
    return msg


def main() -> None:
    if len(sys.argv) < 2:
        print("Uso: python -m bots.github_manual user/repo")
        print("Ejemplo: python -m bots.github_manual facebook/react")
        sys.exit(1)

    repo_name = sys.argv[1].strip()
    if "/" not in repo_name:
        print(f"Error: '{repo_name}' debe tener el formato user/repo")
        sys.exit(1)

    print("━" * 50)
    print("  🐙 GitHub Manual Bot")
    print("━" * 50)
    print(f"  Repo: {repo_name}")

    try:
        repo = get_repo_info(repo_name)
    except Exception as e:
        print(f"  ❌ Error: {e}")
        sys.exit(1)

    if is_processed(repo["id"]):
        print(f"\n  ⚠️  Este repo ya fue procesado anteriormente.")
        respuesta = input("  ¿Deseas regenerarlo? (s/n): ").strip().lower()
        if respuesta not in ("s", "si", "sí", "y", "yes"):
            print("  ℹ️  Operación cancelada.")
            sys.exit(0)
        remove_from_history(repo["id"])
        print("  🔄 Regenerando tweet...")

    print(f"  ⭐ Stars: {repo['stars']}")
    print(f"  📝 {repo['description'][:80]}...")

    print("\n  📥 Descargando README...")
    readme = get_readme_content(repo["name"])
    if readme:
        repo["readme_content"] = readme
        print(f"  ✅ README descargado ({len(readme)} caracteres)")

    print("\n  ✍️  Generando tweet...")
    try:
        tweet_text = generate_tweet(PROMPT_FILE, _format_message(repo))
    except Exception as e:
        print(f"  ❌ Error generando tweet: {e}")
        sys.exit(1)

    print(f"\n{'━' * 50}")
    print("  Tweet generado:")
    print(f"{'━' * 50}")
    print(tweet_text)
    print(f"{'━' * 50}")

    print("\n  💾 Guardando borrador en Obsidian (categoría: github)...")
    filepath = guardar_borrador(
        texto=tweet_text,
        categoria="github",
        source="github_manual",
        titulo=repo["name"],
        url=repo.get("url") or f"https://github.com/{repo['name']}",
        repo_name=repo["name"],
        repo_stars=repo["stars"],
        item_id=repo["id"],
        prompt_file=PROMPT_FILE,
    )

    if filepath:
        mark_as_processed(repo["id"], "github_manual", texto=tweet_text[:100])
        print(f"\n{'━' * 50}")
        print(f"  ✅ Borrador guardado en Obsidian: {Path(filepath).name}")
        print(f"  📂 Carpeta: github/")
        print(f"{'━' * 50}")


if __name__ == "__main__":
    main()
