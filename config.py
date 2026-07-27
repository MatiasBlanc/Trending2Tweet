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

# ── Twitter/X API ─────────────────────────────────────────────
TWITTER_API_KEY: str = os.getenv("TWITTER_API_KEY", "")
TWITTER_API_SECRET: str = os.getenv("TWITTER_API_SECRET", "")
TWITTER_ACCESS_TOKEN: str = os.getenv("TWITTER_ACCESS_TOKEN", "")
TWITTER_ACCESS_SECRET: str = os.getenv("TWITTER_ACCESS_SECRET", "")

# ── Noticias ──────────────────────────────────────────────────
NEWS_SOURCE: str = os.getenv("NEWS_SOURCE", "hacker_news")
NEWS_LIMIT: int = int(os.getenv("NEWS_LIMIT", "5"))
NEWS_MIN_SCORE: int = int(os.getenv("NEWS_MIN_SCORE", "50"))

# ── Métricas y Analytics ──────────────────────────────────────
METRICS_DB_PATH: str = os.getenv("METRICS_DB_PATH", "metrics.db")
METRICS_COLLECT_INTERVAL: int = int(os.getenv("METRICS_COLLECT_INTERVAL", "60"))  # minutos

# Pesos para calcular engagement score
# Ajustar según qué métrica consideras más valiosa
ENGAGEMENT_WEIGHTS: dict = {
    "likes": float(os.getenv("ENG_WEIGHT_LIKES", "1.0")),
    "retweets": float(os.getenv("ENG_WEIGHT_RTS", "2.0")),
    "replies": float(os.getenv("ENG_WEIGHT_REPLIES", "3.0")),
    "bookmarks": float(os.getenv("ENG_WEIGHT_BOOKMARKS", "2.5")),
}

# Few-shot: cantidad de ejemplos a inyectar en el prompt
FEW_SHOT_EXAMPLES: int = int(os.getenv("FEW_SHOT_EXAMPLES", "3"))
