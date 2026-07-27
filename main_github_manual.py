"""Bot de GitHub Manual: genera tweet para un repo específico.

Uso: python main_github_manual.py user/repo

Ejemplo: python main_github_manual.py facebook/react
"""

import subprocess
import sys
from datetime import datetime
from pathlib import Path

import requests

import config
from sources.github_client import get_readme_content, GITHUB_API
from llm_client import generate_tweet
from twitter_client import publicar_tweet
from state_manager import load_processed, save_processed

PROMPT_FILE = "prompts/prompt_github.txt"


def obtener_info_repo(repo_name: str) -> dict:
    """Obtiene información de un repositorio de GitHub.

    Args:
        repo_name: Nombre del repositorio (ej: "facebook/react").

    Returns:
        Diccionario con datos del repositorio.

    Raises:
        Exception: Si no se puede obtener la información.
    """
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {config.GITHUB_TOKEN}",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    resp = requests.get(
        f"{GITHUB_API}/repos/{repo_name}",
        headers=headers,
        timeout=15,
    )

    if resp.status_code == 404:
        raise Exception(f"Repositorio '{repo_name}' no encontrado")
    
    resp.raise_for_status()
    data = resp.json()

    return {
        "id": f"gh_{data['id']}",
        "name": data["full_name"],
        "description": data.get("description") or "Sin descripción",
        "language": data.get("language") or "Desconocido",
        "stars": data["stargazers_count"],
        "html_url": data["html_url"],
    }


def guardar_tweet_con_url(tweet_text: str, repo_id: str, repo_name: str, repo_url: str) -> str:
    """Guarda el tweet y la URL en un archivo .txt.

    Args:
        tweet_text: Texto del tweet generado (sin URL).
        repo_id: ID del repositorio.
        repo_name: Nombre del repositorio.
        repo_url: URL del repositorio.

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
    """Construye el mensaje para el LLM (sin URL).

    Args:
        repo: Diccionario con datos del repositorio.

    Returns:
        Mensaje formateado.
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
    """Ejecución principal del bot manual."""
    # Verificar argumento
    if len(sys.argv) < 2:
        print("Uso: python main_github_manual.py user/repo")
        print("Ejemplo: python main_github_manual.py facebook/react")
        sys.exit(1)

    repo_name = sys.argv[1]

    # Validar formato
    if "/" not in repo_name:
        print(f"Error: '{repo_name}' no tiene formato user/repo")
        sys.exit(1)

    print("━" * 50)
    print("  GitHub Manual Bot")
    print("━" * 50)
    print(f"  Repo: {repo_name}")

    # 1. Obtener información del repo
    try:
        repo = obtener_info_repo(repo_name)
    except Exception as e:
        print(f"  ❌ Error: {e}")
        sys.exit(1)

    print(f"  ⭐ Stars: {repo['stars']}")
    print(f"  📝 {repo['description'][:80]}...")

    # 2. Verificar si ya fue publicado
    processed = load_processed()
    if repo["id"] in processed:
        print(f"\n  ⚠️  Este repo ya fue publicado anteriormente (ID: {repo['id']})")
        respuesta = input("  ¿Continuar de todos modos? (s/n): ").strip().lower()
        if respuesta not in ("s", "si", "sí"):
            print("  Cancelado.")
            sys.exit(0)

    # 3. Descargar README
    print("\n  📥 Descargando README...")
    readme = get_readme_content(repo["name"])
    if readme:
        repo["readme_content"] = readme
        print(f"  ✅ README descargado ({len(readme)} caracteres)")
    else:
        print("  ⚠️  No se pudo descargar el README")

    # 4. Generar tweet
    print("\n  ✍️  Generando tweet...")
    try:
        mensaje = construir_mensaje_usuario(repo)
        tweet_text = generate_tweet(PROMPT_FILE, mensaje)
    except Exception as e:
        print(f"  ❌ Error generando tweet: {e}")
        sys.exit(1)

    # 5. Truncar si es necesario
    if config.FORCE_280_CHAR_TWEET and len(tweet_text) > 280:
        tweet_text = tweet_text[:277] + "..."

    # 6. Mostrar tweet y preguntar si publicar
    print(f"\n{'━' * 50}")
    print("  Tweet generado:")
    print(f"{'━' * 50}")
    print(tweet_text)
    print(f"{'━' * 50}")

    respuesta = input("\n  ¿Publicar en Twitter? (s/n): ").strip().lower()
    if respuesta not in ("s", "si", "sí"):
        print("  Cancelado.")
        # Guardar archivo sin publicar
        filename = guardar_tweet_con_url(tweet_text, repo["id"], repo["name"], repo["html_url"])
        print(f"  💾 Tweet guardado sin publicar: {filename}")
        sys.exit(0)

    # 7. Publicar en Twitter
    try:
        resultado = publicar_tweet(
            texto=tweet_text,
            source="github_manual",
            item_id=repo["id"],
            prompt_file=PROMPT_FILE,
        )
        print(f"  🐦 Publicado en Twitter (ID: {resultado['id']})")
    except Exception as e:
        print(f"  ❌ Error publicando en Twitter: {e}")
        sys.exit(1)

    # 8. Guardar archivo y copiar URL al portapapeles
    filename = guardar_tweet_con_url(tweet_text, repo["id"], repo["name"], repo["html_url"])
    print(f"  💾 Guardado: {filename}")
    
    # Copiar URL al portapapeles automáticamente
    try:
        subprocess.run(
            ["xclip", "-selection", "clipboard"],
            input=repo["html_url"].encode(),
            check=True,
            capture_output=True,
        )
        print(f"  📎 URL copiada al portapapeles: {repo['html_url']}")
    except FileNotFoundError:
        print(f"  📎 URL para comentario (copia manual): {repo['html_url']}")
    except Exception as e:
        print(f"  📎 URL para comentario (copia manual): {repo['html_url']} [{e}]")

    # 9. Actualizar state
    processed.add(repo["id"])
    save_processed(processed)

    print(f"\n{'━' * 50}")
    print(f"  ✅ Completado")
    print(f"{'━' * 50}")


if __name__ == "__main__":
    main()
