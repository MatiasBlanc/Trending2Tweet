"""Punto de entrada: menú principal, descubre, filtra, genera y guarda el tweet."""

import sys
from datetime import datetime
from pathlib import Path

import config
from github_client import get_trending_repos, get_readme_content
from llm_client import generate_tweet
from menu import show_main_menu, manage_history
from state_manager import load_processed, save_processed


def save_tweet_to_file(tweet_text: str, repo_name: str) -> str:
    """Guarda el tweet en un archivo .txt con timestamp dentro de la carpeta tweets/.

    Args:
        tweet_text: Texto del tweet generado.
        repo_name: Nombre del repositorio (para el nombre del archivo).

    Returns:
        Ruta del archivo creado.
    """
    tweets_dir = Path("tweets")
    tweets_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = repo_name.replace("/", "_").replace(" ", "_")
    filename = tweets_dir / f"{timestamp}_tweet-{safe_name}.txt"

    filename.write_text(tweet_text, encoding="utf-8")

    return str(filename)


def ask_continue() -> bool:
    """Pregunta al usuario si quiere buscar el siguiente repo.

    Returns:
        True si el usuario quiere continuar, False en caso contrario.
    """
    while True:
        respuesta = input("\n¿Buscar siguiente repositorio? (s/n): ").strip().lower()
        if respuesta in ("s", "si", "sí"):
            return True
        if respuesta in ("n", "no"):
            return False
        print("Respuesta no válida. Escribe 's' o 'n'.")


def start_tweeting() -> None:
    """Ejecución principal del bot de tweets."""
    # 1. Cargar estado previo
    processed = load_processed()

    # 2. Buscar repos trending
    try:
        repos = get_trending_repos(limit=10)
    except Exception as e:
        print(f"Error consultando GitHub: {e}")
        sys.exit(1)

    if not repos:
        print("No se encontraron repositorios nuevos.")
        return

    # 3. Iterar sobre los repos y preguntar al usuario
    for i, repo in enumerate(repos):
        # Verificar si ya fue publicado
        if repo["name"] in processed:
            print(f"\n[{i + 1}/{len(repos)}] Ya publicado: {repo['name']} ({repo['stars']} ⭐)")
            if not ask_continue():
                return
            continue

        # Mostrar información del repo
        print(f"\n[{i + 1}/{len(repos)}] Nuevo repo encontrado:")
        print(f"  Nombre: {repo['name']}")
        print(f"  Descripción: {repo['description']}")
        print(f"  Lenguaje: {repo['language']}")
        print(f"  Estrellas: {repo['stars']}")
        print(f"  URL: {repo['html_url']}")

        # Preguntar si quiere generar el tweet para este repo
        while True:
            respuesta = input("\n¿Generar tweet para este repo? (s/n): ").strip().lower()
            if respuesta in ("s", "si", "sí"):
                break
            if respuesta in ("n", "no"):
                break
            print("Respuesta no válida. Escribe 's' o 'n'.")

        if respuesta in ("n", "no"):
            if not ask_continue():
                return
            continue

        # Descargar README para dar contexto al LLM
        print("  Descargando README...")
        readme = get_readme_content(repo["name"])
        if readme:
            repo["readme_content"] = readme
            print(f"  README descargado ({len(readme)} caracteres)")
        else:
            repo["readme_content"] = None
            print("  No se pudo descargar el README")

        # Generar tweet con IA
        try:
            tweet_text = generate_tweet(repo)
        except Exception as e:
            print(f"Error generando tweet con LLM: {e}")
            if not ask_continue():
                return
            continue

        # Truncar si excede 280 chars (fallback por si la IA no respeta el límite)
        if config.FORCE_280_CHAR_TWEET and len(tweet_text) > 280:
            tweet_text = tweet_text[:277] + "..."

        # Guardar tweet en archivo
        filename = save_tweet_to_file(tweet_text, repo["name"])
        print(f"\nTweet guardado en: {filename}")
        print(f"\n--- Tweet para publicar manualmente ---\n")
        print(tweet_text)
        print(f"\n----------------------------------------\n")

        # Persistir estado
        processed.add(repo["name"])
        save_processed(processed)

        # Preguntar si quiere continuar con el siguiente
        if not ask_continue():
            return

    print("\nNo hay más repositorios en la lista.")


def main() -> None:
    """Punto de entrada principal con menú interactivo."""
    while True:
        opcion = show_main_menu()

        if opcion == "0":
            print("¡Hasta luego!")
            sys.exit(0)

        elif opcion == "1":
            start_tweeting()

        elif opcion == "2":
            manage_history()


if __name__ == "__main__":
    main()
