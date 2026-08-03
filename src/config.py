"""Configuración centralizada del bot."""

import os
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

# Control de longitud de tweets
FORCE_280_CHAR_TWEET: bool = os.getenv("FORCE_280_CHAR_TWEET", "true").lower() == "true"

# Noticias
NEWS_SOURCE: str = os.getenv("NEWS_SOURCE", "hacker_news")
NEWS_LIMIT: int = int(os.getenv("NEWS_LIMIT", "5"))
NEWS_MIN_SCORE: int = int(os.getenv("NEWS_MIN_SCORE", "50"))

# Obsidian
OBSIDIAN_VAULT_PATH: str = os.getenv("OBSIDIAN_VAULT_PATH", "")

# Base de datos
METRICS_DB_PATH: str = os.getenv("METRICS_DB_PATH", "metrics.db")

# Branding para tarjetas
CARD_BRAND_NAME: str = os.getenv("CARD_BRAND_NAME", "matiasblnc")
ENABLE_TWEET_IMAGES: bool = os.getenv("ENABLE_TWEET_IMAGES", "true").lower() == "true"

# Twitter API
TWITTER_API_KEY: str = os.getenv("TWITTER_API_KEY", "")
TWITTER_API_SECRET: str = os.getenv("TWITTER_API_SECRET", "")
TWITTER_ACCESS_TOKEN: str = os.getenv("TWITTER_ACCESS_TOKEN", "")
TWITTER_ACCESS_SECRET: str = os.getenv("TWITTER_ACCESS_SECRET", "")
