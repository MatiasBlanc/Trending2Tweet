"""Configuración centralizada del bot."""

import math
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

_ROOT = Path(__file__).parent.parent
load_dotenv(_ROOT / ".env")


def _leer_entero(nombre: str, defecto: int, minimo: int, maximo: int) -> int:
    """Lee un entero de entorno y lo mantiene dentro de límites seguros."""
    try:
        valor = int(os.getenv(nombre, str(defecto)))
    except ValueError:
        return defecto
    return min(max(valor, minimo), maximo)


def _leer_decimal(nombre: str, defecto: float, minimo: float, maximo: float) -> float:
    """Lee un decimal de entorno y lo mantiene dentro de límites seguros."""
    try:
        valor = float(os.getenv(nombre, str(defecto)))
    except ValueError:
        return defecto
    if not math.isfinite(valor):
        return defecto
    return min(max(valor, minimo), maximo)


# Límite para evitar costes inesperados al lanzar varios borradores.
MAX_GENERATION_LIMIT: int = 20

# GitHub
GITHUB_TOKEN: str = os.getenv("GITHUB_TOKEN", "").strip()

# LLM
LLM_API_KEY: str = os.getenv("LLM_API_KEY", "").strip()
LLM_BASE_URL: str = (
    os.getenv("LLM_BASE_URL", "https://api.openai.com/v1").strip()
    or "https://api.openai.com/v1"
)
LLM_MODEL: str = os.getenv("LLM_MODEL", "gpt-4o-mini").strip() or "gpt-4o-mini"
LLM_MAX_TOKENS: int = _leer_entero("LLM_MAX_TOKENS", 1024, 1, 8192)
LLM_TEMPERATURE: float = _leer_decimal("LLM_TEMPERATURE", 0.2, 0.0, 2.0)
# Versión de API obligatoria en Azure OpenAI (solo endpoints estilo *.openai.azure.com).
# Vacío = no aplica. El endpoint /openai/v1 de AI Foundry NO acepta este parámetro.
LLM_API_VERSION: str = os.getenv("LLM_API_VERSION", "")
# true = usar max_completion_tokens en lugar de max_tokens (modelos gpt-5.x)
LLM_USE_MAX_COMPLETION_TOKENS: bool = os.getenv(
    "LLM_USE_MAX_COMPLETION_TOKENS", "false"
).lower() == "true"


@dataclass(frozen=True)
class LLMSettings:
    """Configuración de un proveedor compatible con la API de OpenAI."""

    api_key: str
    base_url: str
    model: str
    max_tokens: int
    temperature: float
    api_version: str = ""
    use_max_completion_tokens: bool = False


OUTPUT_LLM_SETTINGS = LLMSettings(
    api_key=LLM_API_KEY,
    base_url=LLM_BASE_URL,
    model=LLM_MODEL,
    max_tokens=LLM_MAX_TOKENS,
    temperature=LLM_TEMPERATURE,
    api_version=LLM_API_VERSION,
    use_max_completion_tokens=LLM_USE_MAX_COMPLETION_TOKENS,
)

# El modelo de entrada puede ser más económico, por ejemplo DeepSeek en
# OpenRouter. Si no hay una clave separada, se reutiliza el modelo de salida.
_INPUT_LLM_API_KEY = os.getenv("INPUT_LLM_API_KEY", "").strip()
if _INPUT_LLM_API_KEY:
    INPUT_LLM_SETTINGS = LLMSettings(
        api_key=_INPUT_LLM_API_KEY,
        base_url=(
            os.getenv("INPUT_LLM_BASE_URL", LLM_BASE_URL).strip()
            or LLM_BASE_URL
        ),
        model=os.getenv("INPUT_LLM_MODEL", LLM_MODEL).strip() or LLM_MODEL,
        max_tokens=_leer_entero(
            "INPUT_LLM_MAX_TOKENS", LLM_MAX_TOKENS, 1, 8192
        ),
        temperature=_leer_decimal(
            "INPUT_LLM_TEMPERATURE", LLM_TEMPERATURE, 0.0, 2.0
        ),
        api_version=os.getenv("INPUT_LLM_API_VERSION", ""),
        use_max_completion_tokens=os.getenv(
            "INPUT_LLM_USE_MAX_COMPLETION_TOKENS", "false"
        ).lower()
        == "true",
    )
else:
    INPUT_LLM_SETTINGS = OUTPUT_LLM_SETTINGS

# Alias de compatibilidad para código externo que usaba el nombre anterior.
LLM_SETTINGS = OUTPUT_LLM_SETTINGS

# Control de longitud de tweets
# false = sin límite de 280 caracteres (X Premium permite tweets más largos)
FORCE_280_CHAR_TWEET: bool = os.getenv("FORCE_280_CHAR_TWEET", "false").lower() == "true"

# Noticias
NEWS_SOURCE: str = os.getenv("NEWS_SOURCE", "hacker_news").strip().lower()
NEWS_LIMIT: int = _leer_entero("NEWS_LIMIT", 5, 1, MAX_GENERATION_LIMIT)
NEWS_FETCH_LIMIT: int = _leer_entero(
    "NEWS_FETCH_LIMIT", max(NEWS_LIMIT, 20), 1, 100
)
NEWS_MIN_SCORE: int = _leer_entero("NEWS_MIN_SCORE", 50, 0, 1_000_000)

# Obsidian Vault
# Por defecto se usa ~/Obsidian/Twitter/bot/
_DEFAULT_VAULT_PATH = str(Path.home() / "Obsidian/Twitter/bot")
OBSIDIAN_VAULT_PATH: str = os.path.expanduser(
    os.getenv("OBSIDIAN_VAULT_PATH", _DEFAULT_VAULT_PATH)
)

# Raíz de la bóveda completa de Twitter (ej. ~/Obsidian/Twitter)
_obs_path = Path(OBSIDIAN_VAULT_PATH)
if _obs_path.name.lower() == "bot":
    _DEFAULT_TWITTER_VAULT = str(_obs_path.parent)
else:
    _DEFAULT_TWITTER_VAULT = OBSIDIAN_VAULT_PATH

TWITTER_VAULT_PATH: str = os.path.expanduser(
    os.getenv("TWITTER_VAULT_PATH", _DEFAULT_TWITTER_VAULT)
)

# Base de datos local
METRICS_DB_PATH: str = os.path.expanduser(
    os.getenv("METRICS_DB_PATH", "metrics.db").strip() or "metrics.db"
)

# Twitter API
TWITTER_API_KEY: str = os.getenv("TWITTER_API_KEY", "")
TWITTER_API_SECRET: str = os.getenv("TWITTER_API_SECRET", "")
TWITTER_ACCESS_TOKEN: str = os.getenv("TWITTER_ACCESS_TOKEN", "")
TWITTER_ACCESS_SECRET: str = os.getenv("TWITTER_ACCESS_SECRET", "")
