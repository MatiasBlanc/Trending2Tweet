"""Bot de GitHub Trending: descubre repos trending y publica tweets.

Ejecución automatizada sin interacción del usuario.
"""

import sys
from pathlib import Path

from src import config
from sources.github_client import get_trending_repos, get_readme_content
from src.llm_client import generate_tweet
from db.metrics_db import is_processed, mark_as_processed
from src.card_generator import generate_github_card
from twitter_client import publicar_tweet

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
    print("  GitHub Trending Bot - Publicación automática")
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

        # Generar tarjeta visual si está habilitado
        imagen_path = None
        if config.ENABLE_TWEET_IMAGES:
            try:
                image_bytes = generate_github_card(
                    repo_name=repo["name"],
                    description=repo["description"],
                    language=repo["language"],
                    stars=repo["stars"],
                )
                if image_bytes:
                    # Guardar imagen temporalmente
                    import tempfile
                    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
                        f.write(image_bytes)
                        imagen_path = f.name
                    print(f"  🖼️  Tarjeta visual generada")
            except Exception as e:
                print(f"  ⚠️  No se pudo generar tarjeta: {e}")

        # Publicar tweet
        try:
            resultado = publicar_tweet(
                texto=tweet_text,
                imagen_path=imagen_path,
            )
            
            # Marcar como procesado
            mark_as_processed(
                repo["id"],
                "github",
                tweet_id=resultado["tweet_id"],
                texto=tweet_text[:100],
            )
            
            print(f"\n{'━' * 50}")
            print(f"  ✅ Tweet publicado: {resultado['tweet_id']}")
            print(f"{'━' * 50}")
            
            # Limpiar imagen temporal
            import os
            if imagen_path and os.path.exists(imagen_path):
                os.unlink(imagen_path)
            
            return  # Publicar solo un repo por ejecución
            
        except Exception as e:
            print(f"  ❌ Error publicando tweet: {e}")
            continue

    print("\n  ⚠️  No hay repos nuevos para procesar.")


if __name__ == "__main__":
    main()