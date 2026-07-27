"""Persistencia ligera de items ya procesados (repos y noticias)."""

import json
from pathlib import Path
from typing import Set

import config


def load_processed() -> Set[str]:
    """Carga los IDs ya publicados.

    Returns:
        Conjunto de IDs procesados (ej: "gh_12345", "hn_67890").
    """
    path = Path(config.STATE_FILE)
    if not path.exists():
        return set()
    data = json.loads(path.read_text(encoding="utf-8"))
    return set(data.get("processed_ids", []))


def save_processed(processed: Set[str]) -> None:
    """Guarda el conjunto actualizado de IDs procesados.

    Args:
        processed: Conjunto de IDs procesados.
    """
    path = Path(config.STATE_FILE)
    path.write_text(
        json.dumps({"processed_ids": sorted(processed)}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def remove_from_history(item_id: str) -> bool:
    """Elimina un item del historial por su ID.

    Args:
        item_id: ID del item a eliminar.

    Returns:
        True si se eliminó correctamente, False si no se encontró.
    """
    processed = load_processed()
    if item_id not in processed:
        return False
    processed.remove(item_id)
    save_processed(processed)
    return True


def clear_history() -> int:
    """Limpia todo el historial de items procesados.

    Returns:
        Cantidad de items eliminados del historial.
    """
    processed = load_processed()
    count = len(processed)
    save_processed(set())
    return count
