"""Compatibilidad hacia atrás con db/metrics_db."""

from src.db import (
    init_db,
    is_processed,
    mark_as_processed,
    remove_from_history,
    count_processed,
)

__all__ = [
    "init_db",
    "is_processed",
    "mark_as_processed",
    "remove_from_history",
    "count_processed",
]
