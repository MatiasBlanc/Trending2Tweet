"""Persistencia ligera de repos ya procesados."""

import json
from pathlib import Path
from typing import List, Set

import config


def load_processed() -> Set[str]:
    """Carga los nombres de repos ya publicados.

    Returns:
        Conjunto de nombres de repos procesados (ej: "owner/repo").
    """
    path = Path(config.STATE_FILE)
    if not path.exists():
        return set()
    data = json.loads(path.read_text(encoding="utf-8"))
    return set(data.get("processed_repos", []))


def save_processed(processed: Set[str]) -> None:
    """Guarda el conjunto actualizado de repos procesados.

    Args:
        processed: Conjunto de nombres de repos procesados.
    """
    path = Path(config.STATE_FILE)
    path.write_text(
        json.dumps({"processed_repos": sorted(processed)}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def remove_from_history(repo_name: str) -> bool:
    """Elimina un repo del historial por su nombre.

    Args:
        repo_name: Nombre del repositorio a eliminar.

    Returns:
        True si se eliminó correctamente, False si no se encontró.
    """
    processed = load_processed()
    if repo_name not in processed:
        return False
    processed.remove(repo_name)
    save_processed(processed)
    return True


def clear_history() -> int:
    """Limpia todo el historial de repos procesados.

    Returns:
        Cantidad de repos eliminados del historial.
    """
    processed = load_processed()
    count = len(processed)
    save_processed(set())
    return count
