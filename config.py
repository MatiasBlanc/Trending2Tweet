"""Configuración centralizada del bot."""

import os
from dotenv import load_dotenv

load_dotenv()

# GitHub
GITHUB_TOKEN: str = os.getenv("GITHUB_TOKEN", "")

# LLM
LLM_API_KEY: str = os.getenv("LLM_API_KEY", "")
LLM_BASE_URL: str = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
LLM_MODEL: str = os.getenv("LLM_MODEL", "gpt-4o-mini")
LLM_MAX_TOKENS: int = int(os.getenv("LLM_MAX_TOKENS", "1024"))
LLM_TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "0.2"))

# Estado
STATE_FILE: str = os.getenv("STATE_FILE", "state.json")

# Control de longitud de tweets
# true  = tweets limitados a 280 caracteres (modo estándar)
# false = tweets de cualquier largo (X Premium)
FORCE_280_CHAR_TWEET: bool = os.getenv("FORCE_280_CHAR_TWEET", "true").lower() == "true"
