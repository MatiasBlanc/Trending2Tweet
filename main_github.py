"""Bot de GitHub: descubre repos trending, genera y publica tweets.

Ejecución automatizada sin interacción del usuario.
La URL del repo se guarda en archivo aparte para agregar como comentario.
"""

import sys
from datetime import datetime
from pathlib import Path

import config
from sources.github_client import get_trending_repos, get_readme_content
from llm_client import generate_tweet
from twitter_client import publicar_tweet
from metrics_db import load_processed, is_processed

PROMPT_FILE = "prompts/prompt_github.txt"


def guardar_tweet_con_url(tweet_text: str, repo_id: str, repo_name: str, repo_url: str) -> str:
    """Guarda el tweet y la URL en un archivo .txt con timestamp.

    Args:
        tweet_text: Texto del tweet generado (sin URL).
        repo_id: ID del repositorio (ej: gh_123456).
        repo_name: Nombre del repositorio.
        repo_url: URL del repositorio (para agregar como comentario).

    Returns:
        Ruta del archivo creado.
    """
    tweets_dir = Path("tweets")
    tweets_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = repo_name.replace("/", "_").replace(" ", "_")[:30]
    filename = tweets_dir / f"gh_{safe_name}_{timestamp}.txt"

    contenido = (
        f"ID: {repo_id}\n"
        f"Repo: {repo_name}\n"
        f"URL: {repo_url}\n"
        f"{'─' * 40}\n"
        f"{tweet_text}\n"
    )

    filename.write_text(contenido, encoding="utf-8")
    return str(filename)


def construir_mensaje_usuario(repo: dict) -> str:
    """Construye el mensaje del usuario para el LLM (sin URL).

    Args:
        repo: Diccionario con datos del repositorio.

    Returns:
        Mensaje formateado para el LLM.
    """
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

    # 1. Cargar estado previo
    processed = load_processed()
    print(f"  Items en historial: {len(processed)}")
    print(f"  Source: metrics.db")

    # 2. Buscar repos trending
    try:
        repos = get_trending_repos(limit=10)
    except Exception as e:
        print(f"Error consultando GitHub: {e}")
        sys.exit(1)

    if not repos:
        print("No se encontraron repositorios nuevos.")
        return

    print(f"  Repos encontrados: {len(repos)}")

    # 3. Buscar el primer repo nuevo y publicarlo
    for repo in repos:
        # Verificar si ya fue publicado
        if is_processed(repo["id"]):
            print(f"\n  ⏭  Ya publicado: {repo['name']}")
            continue

        print(f"\n  📦 Nuevo repo: {repo['name']}")
        print(f"     {repo['description'][:80]}...")

        # Descargar README
        readme = get_readme_content(repo["name"])
        if readme:
            repo["readme_content"] = readme

        # Generar tweet (sin URL)
        try:
            mensaje = construir_mensaje_usuario(repo)
            tweet_text = generate_tweet(PROMPT_FILE, mensaje)
        except Exception as e:
            print(f"  ❌ Error generando tweet: {e}")
            sys.exit(1)

        # Truncar si excede 280 chars
        if config.FORCE_280_CHAR_TWEET and len(tweet_text) > 280:
            tweet_text = tweet_text[:277] + "..."

        # Publicar en Twitter
        try:
            resultado = publicar_tweet(
                texto=tweet_text,
                source="github",
                item_id=repo["id"],
                prompt_file=PROMPT_FILE,
            )
            print(f"  🐦 Publicado en Twitter (ID: {resultado['id']})")
        except Exception as e:
            print(f"  ❌ Error publicando en Twitter: {e}")
            sys.exit(1)

        # Guardar tweet + URL en archivo
        filename = guardar_tweet_con_url(tweet_text, repo["id"], repo["name"], repo["html_url"])
        print(f"  💾 Guardado: {filename}")
        print(f"  📎 URL para comentario: {repo['html_url']}")

        # Persistir estado (ya se hace automáticamente en twitter_client)
        # processed.add(repo["id"])
        # save_processed(processed)

        print(f"\n{'━' * 50}")
        print(f"  ✅ Completado: 1 tweet publicado")
        print(f"{'━' * 50}")
        return

    print("\n  ⚠️  No hay repos nuevos para publicar.")


if __name__ == "__main__":
    main()
