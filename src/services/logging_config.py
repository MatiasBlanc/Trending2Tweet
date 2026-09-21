"""Configuración de observabilidad fuera de la interfaz principal."""

import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path


def get_log_path() -> Path:
    """Obtiene la ruta de log respetando el estándar XDG.

    Returns:
        Ruta ``app.log`` dentro del directorio de estado del usuario.
    """
    state_home = Path(
        os.getenv("XDG_STATE_HOME", str(Path.home() / ".local" / "state"))
    ).expanduser()
    return state_home / "trending-to-tweet" / "app.log"


def configure_file_logging() -> Path:
    """Envía logs técnicos a archivo sin contaminar la pantalla Textual.

    Returns:
        Ruta absoluta del archivo configurado.

    Raises:
        OSError: Si el directorio de estado no se puede crear.
    """
    path = get_log_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    root = logging.getLogger()

    if not any(
        isinstance(handler, logging.FileHandler)
        and Path(handler.baseFilename) == path.resolve()
        for handler in root.handlers
    ):
        handler = RotatingFileHandler(
            path,
            maxBytes=1_000_000,
            backupCount=3,
            encoding="utf-8",
        )
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s %(levelname)s %(name)s: %(message)s"
            )
        )
        root.addHandler(handler)
    root.setLevel(logging.INFO)
    return path
