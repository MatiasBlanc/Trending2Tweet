"""Configuración centralizada del bot."""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

_ROOT = Path(__file__).parent.parent
load_dotenv(_ROOT / ".env")

# GitHub
GITHUB_TOKEN: str = os.getenv("GITHUB_TOKEN", "")

# LLM
LLM_API_KEY: str = os.getenv("LLM_API_KEY", "")
LLM_BASE_URL: str = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
LLM_MODEL: str = os.getenv("LLM_MODEL", "gpt-4o-mini")
LLM_MAX_TOKENS: int = int(os.getenv("LLM_MAX_TOKENS", "1024"))
LLM_TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "0.2"))
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
        base_url=os.getenv("INPUT_LLM_BASE_URL", LLM_BASE_URL),
        model=os.getenv("INPUT_LLM_MODEL", LLM_MODEL),
        max_tokens=int(
            os.getenv("INPUT_LLM_MAX_TOKENS", str(LLM_MAX_TOKENS))
        ),
        temperature=float(
            os.getenv("INPUT_LLM_TEMPERATURE", str(LLM_TEMPERATURE))
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
# true = 280 caracteres (X estándar, evita rechazos y fuerza tweets concisos)
FORCE_280_CHAR_TWEET: bool = os.getenv("FORCE_280_CHAR_TWEET", "true").lower() == "true"

# Scheduler
PUBLISH_TIMEZONE_OFFSET: int = int(os.getenv("PUBLISH_TIMEZONE_OFFSET", "-4"))

# Noticias
NEWS_SOURCE: str = os.getenv("NEWS_SOURCE", "hacker_news")
NEWS_LIMIT: int = int(os.getenv("NEWS_LIMIT", "5"))
NEWS_FETCH_LIMIT: int = int(
    os.getenv("NEWS_FETCH_LIMIT", str(max(NEWS_LIMIT, 20)))
)
NEWS_MIN_SCORE: int = int(os.getenv("NEWS_MIN_SCORE", "50"))

# Obsidian
OBSIDIAN_VAULT_PATH: str = os.getenv("OBSIDIAN_VAULT_PATH", "")

# Base de datos
METRICS_DB_PATH: str = os.getenv("METRICS_DB_PATH", "metrics.db")

# Sincronización con Railway
# true = los items procesados localmente se registran también en la DB de
# Railway (volume /data) para que el scheduler no los vuelva a publicar.
RAILWAY_SYNC_ENABLED: bool = os.getenv("RAILWAY_SYNC_ENABLED", "true").lower() == "true"
RAILWAY_SSH_TIMEOUT: int = int(os.getenv("RAILWAY_SSH_TIMEOUT", "45"))

# Twitter API
TWITTER_API_KEY: str = os.getenv("TWITTER_API_KEY", "")
TWITTER_API_SECRET: str = os.getenv("TWITTER_API_SECRET", "")
TWITTER_ACCESS_TOKEN: str = os.getenv("TWITTER_ACCESS_TOKEN", "")
TWITTER_ACCESS_SECRET: str = os.getenv("TWITTER_ACCESS_SECRET", "")
