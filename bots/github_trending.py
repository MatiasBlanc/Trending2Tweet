"""Bot de GitHub Trending: descubre repos trending y genera borradores en Obsidian.

Uso: python -m bots.github_trending
"""

import sys
from pathlib import Path

from src import config
from sources.github_client import get_trending_repos, get_readme_content
from src.llm_client import generate_tweet
from db.metrics_db import is_processed, mark_as_processed
from src.obsidian_vault import guardar_borrador, guardar_imagen_vault
from src.card_generator import generate_github_card
from src.railway_sync import registrar_en_railway

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


def main() -> None:
    """Ejecución principal del bot de GitHub."""
    print("━" * 50)
    print("  GitHub Trending Bot")
    print("━" * 50)

    try:
        repos = get_trending_repos(limit=10)
    except Exception as e:
        print(f"Error consultando GitHub: {e}")
        sys.exit(1)

    if not repos:
        print("No se encontraron repositorios nuevos.")
        return

    print(f"  Repos encontrados: {len(repos)}")

    borradores_creados = 0
    MAX_BORRADORES = 2
    
    for repo in repos:
        if borradores_creados >= MAX_BORRADORES:
            print(f"\n  ⏸  Límite de {MAX_BORRADORES} borradores alcanzado")
            break
        
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

        imagen_path = None
        try:
            image_bytes = generate_github_card(
                repo_name=repo["name"],
                description=repo["description"],
                language=repo["language"],
                stars=repo["stars"],
            )
            if image_bytes:
                imagen_path = guardar_imagen_vault(
                    image_bytes=image_bytes,
                    nombre_archivo=repo["name"].split("/")[-1],
                    source="github",
                )
                if imagen_path:
                    print(f"  🖼️  Tarjeta visual generada")
        except Exception as e:
            print(f"  ⚠️  No se pudo generar tarjeta: {e}")

        filepath = guardar_borrador(
            texto=tweet_text,
            source="github",
            titulo=repo["name"],
            url=repo["html_url"],
            repo_name=repo["name"],
            repo_stars=repo["stars"],
            item_id=repo["id"],
            prompt_file=PROMPT_FILE,
            imagen_path=imagen_path,
        )

        if filepath:
            print(f"  ✅ Borrador guardado: {Path(filepath).name}")
            mark_as_processed(repo["id"], "github", texto=tweet_text[:100])
            registrar_en_railway(repo["id"], "github")
            borradores_creados += 1
        else:
            print(f"  ⚠️ No se pudo guardar borrador")

    print(f"\n{'━' * 50}")
    print(f"  ✅ Completado: {borradores_creados} borradores creados")
    print(f"\n  Próximos pasos:")
    print(f"  1. Abre Obsidian y revisa los borradores en T2T/borradores/")
    print(f"  2. Edita los que te gusten")
    print(f"  3. Mueve a T2T/listos/ cuando estén listos")
    print(f"  4. Publica manualmente en Twitter")
    print(f"{'━' * 50}")


if __name__ == "__main__":
    main()
