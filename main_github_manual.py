"""Bot de GitHub Manual: genera borrador de tweet para un repo específico.

Genera un borrador en Obsidian para que el usuario revise y publique
manualmente cuando quiera.

Uso: python main_github_manual.py user/repo

Ejemplo: python main_github_manual.py facebook/react
"""

import sys
from pathlib import Path

import requests

import config
from sources.github_client import get_readme_content, GITHUB_API
from llm_client import generate_tweet
from obsidian_vault import guardar_borrador

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


def construir_mensaje_usuario(repo: dict) -> str:
    """Construye el mensaje para el LLM.

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
    print("  GitHub Manual Bot - Generador de Borradores")
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

    # 2. Descargar README
    print("\n  📥 Descargando README...")
    readme = get_readme_content(repo["name"])
    if readme:
        repo["readme_content"] = readme
        print(f"  ✅ README descargado ({len(readme)} caracteres)")
    else:
        print("  ⚠️  No se pudo descargar el README")

    # 3. Generar tweet
    print("\n  ✍️  Generando tweet...")
    try:
        mensaje = construir_mensaje_usuario(repo)
        tweet_text = generate_tweet(PROMPT_FILE, mensaje)
    except Exception as e:
        print(f"  ❌ Error generando tweet: {e}")
        sys.exit(1)

    # 4. Mostrar tweet generado
    print(f"\n{'━' * 50}")
    print("  Tweet generado:")
    print(f"{'━' * 50}")
    print(tweet_text)
    print(f"{'━' * 50}")

    # 5. Guardar como borrador en Obsidian
    print("\n  💾 Guardando borrador en Obsidian...")
    filepath = guardar_borrador(
        texto=tweet_text,
        source="github_manual",
        titulo=repo["name"],
        url=repo["html_url"],
        repo_name=repo["name"],
        repo_stars=repo["stars"],
        item_id=repo["id"],
        prompt_file=PROMPT_FILE,
    )

    if filepath:
        print(f"\n{'━' * 50}")
        print(f"  ✅ Borrador guardado en Obsidian")
        print(f"  📂 Archivo: {Path(filepath).name}")
        print(f"\n  Próximos pasos:")
        print(f"  1. Abre Obsidian y revisa el borrador")
        print(f"  2. Edita el tweet si quieres")
        print(f"  3. Mueve a 'listos' cuando esté listo")
        print(f"  4. Copia y publica en Twitter manualmente")
        print(f"{'━' * 50}")
    else:
        print("\n  ⚠️ No se pudo guardar en Obsidian")
        print("  Verifica que OBSIDIAN_VAULT_PATH esté configurado en .env")
        sys.exit(1)


if __name__ == "__main__":
    main()
