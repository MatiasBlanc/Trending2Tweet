"""Menú interactivo y gestión de historial."""

from pathlib import Path

from state_manager import load_processed, remove_from_history, clear_history


def show_main_menu() -> str:
    """Muestra el menú principal y retorna la opción seleccionada.

    Returns:
        '1' para twittear, '2' para gestionar historial, '0' para salir.
    """
    print("\n" + "=" * 50)
    print("         Trending2Tweet")
    print("=" * 50)
    print("  1. Iniciar a twittear")
    print("  2. Ver historial")
    print("  0. Salir")
    print("=" * 50)

    while True:
        opcion = input("Selecciona una opción: ").strip()
        if opcion in ("0", "1", "2"):
            return opcion
        print("Opción no válida. Intenta de nuevo.")


def manage_history() -> None:
    """Gestiona el historial: ver y eliminar repos procesados."""
    while True:
        processed = load_processed()

        print("\n" + "=" * 50)
        print("         Historial de Tweets")
        print("=" * 50)

        if not processed:
            print("  No hay repos en el historial.")
            print("=" * 50)
            input("\nPresiona Enter para volver...")
            return

        print(f"  Repos procesados: {len(processed)}")
        print("=" * 50)
        print("  1. Ver historial")
        print("  2. Eliminar un repo")
        print("  3. Limpiar todo")
        print("  0. Volver al menú principal")
        print("=" * 50)

        opcion = input("Selecciona una opción: ").strip()

        if opcion == "0":
            return

        elif opcion == "1":
            _show_history(processed)

        elif opcion == "2":
            _delete_repo(processed)

        elif opcion == "3":
            _clear_all()

        else:
            print("Opción no válida.")


def _show_history(processed: set) -> None:
    """Muestra el historial de repos procesados."""
    repos_ordenados = sorted(processed)
    print(f"\nHistorial ({len(processed)} repos):")
    print("-" * 50)
    for i, repo_name in enumerate(repos_ordenados, 1):
        print(f"  {i}. {repo_name}")
    print("-" * 50)
    input("\nPresiona Enter para continuar...")


def _delete_repo(processed: set) -> None:
    """Elimina un repo del historial y su tweet asociado."""
    repos_ordenados = sorted(processed)
    print("\nSelecciona el repo a eliminar:")
    print("-" * 50)
    for i, repo_name in enumerate(repos_ordenados, 1):
        print(f"  {i}. {repo_name}")
    print("-" * 50)

    try:
        seleccion = input("\nNúmero del repo (0 para cancelar): ").strip()
        if seleccion == "0":
            return

        idx = int(seleccion) - 1
        if 0 <= idx < len(repos_ordenados):
            repo_name = repos_ordenados[idx]
            confirmacion = input(
                f"\n¿Eliminar '{repo_name}' del historial Y su tweet? (s/n): "
            ).strip().lower()
            
            if confirmacion in ("s", "si", "sí"):
                # Eliminar del state.json
                remove_from_history(repo_name)
                
                # Eliminar archivo del tweet si existe
                _eliminar_tweet_de_repo(repo_name)
                
                print(f"Repo '{repo_name}' eliminado del historial.")
            else:
                print("Operación cancelada.")
        else:
            print("Número fuera de rango.")
    except ValueError:
        print("Entrada no válida.")


def _eliminar_tweet_de_repo(repo_name: str) -> None:
    """Busca y elimina el archivo de tweet asociado a un repo.

    Args:
        repo_name: Nombre del repositorio (ej: "owner/repo").
    """
    tweets_dir = Path("tweets")
    if not tweets_dir.exists():
        return
    
    safe_name = repo_name.replace("/", "_").replace(" ", "_")
    for archivo in tweets_dir.glob(f"*tweet_{safe_name}*.txt"):
        archivo.unlink()
        print(f"Tweet '{archivo.name}' eliminado.")


def _clear_all() -> None:
    """Limpia todo el historial (state.json y carpeta tweets/)."""
    confirmacion = input("\n¿Eliminar todo el historial y tweets? (s/n): ").strip().lower()
    if confirmacion not in ("s", "si", "sí"):
        print("Operación cancelada.")
        return

    # Limpiar state.json
    count = clear_history()
    print(f"{count} repo(s) eliminado(s) del historial.")

    # Eliminar archivos de tweets
    tweets_dir = Path("tweets")
    if tweets_dir.exists():
        archivos = list(tweets_dir.glob("tweet_*.txt"))
        for archivo in archivos:
            archivo.unlink()
        print(f"{len(archivos)} archivo(s) de tweets eliminado(s).")
    else:
        print("La carpeta tweets/ no existe.")
