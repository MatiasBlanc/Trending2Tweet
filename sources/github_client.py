"""Cliente resiliente para interactuar con la API de GitHub."""

import base64
import logging
import math
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import requests

from src import config

GITHUB_API = "https://api.github.com"
_REPO_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    """Obtiene la hora UTC sin depender de un datetime ingenuo obsoleto."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _get_headers(use_auth: bool = True) -> dict[str, str]:
    """Genera las cabeceras estándar para la API de GitHub."""
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = config.GITHUB_TOKEN.strip() if config.GITHUB_TOKEN else ""
    if use_auth and token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _github_request(url: str, params: Optional[dict] = None, timeout: int = 25) -> requests.Response:
    """Realiza una petición a la API de GitHub con fallback si el token es inválido."""
    headers = _get_headers(use_auth=True)
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=timeout)
        if resp.status_code == 401 and "Authorization" in headers:
            logger.warning(
                "GITHUB_TOKEN inválido o expirado; se reintenta sin autenticación"
            )
            anon_headers = _get_headers(use_auth=False)
            resp = requests.get(url, params=params, headers=anon_headers, timeout=timeout)
        resp.raise_for_status()
        return resp
    except requests.RequestException:
        raise


def _parse_github_date(value: Any) -> datetime | None:
    """Convierte una fecha ISO de GitHub sin hacer fallar el filtrado."""
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        return None


def _is_technical_repo(item: dict[str, Any]) -> bool:
    """Descarta señales obvias de contenido no técnico en el buscador general."""
    language = str(item.get("language") or "").strip()
    text = " ".join(
        str(item.get(key) or "")
        for key in ("full_name", "description", "name")
    ).lower()
    topics = " ".join(str(topic) for topic in item.get("topics", [])).lower()
    technical_terms = (
        "api", "app", "cli", "cloud", "code", "compiler", "database", "dev",
        "docker", "framework", "github", "golang", "javascript", "kubernetes",
        "library", "linux", "llm", "machine learning", "model", "python", "rust",
        "sdk", "server", "software", "terminal", "typescript", "web", "workflow",
    )
    noise_terms = (
        "wallpaper", "wallpapers", "awesome-list", "awesome list", "portfolio",
        "resume", "icons", "icon pack", "course", "tutorial collection",
    )
    if any(term in text or term in topics for term in noise_terms):
        return False
    return bool(language) or any(term in text or term in topics for term in technical_terms)


def _signal_score(item: dict[str, Any], now: datetime | None = None) -> tuple[float, list[str]]:
    """Calcula una señal ordenable usando actividad y adopción pública."""
    current = now or _utcnow()
    stars = max(int(item.get("stargazers_count", 0) or 0), 0)
    forks = max(int(item.get("forks_count", 0) or 0), 0)
    issues = max(int(item.get("open_issues_count", 0) or 0), 0)
    pushed_at = _parse_github_date(item.get("pushed_at"))
    age_days = max((current - pushed_at).total_seconds() / 86_400, 0) if pushed_at else 999
    activity_bonus = max(0.0, 20.0 - min(age_days, 20.0))
    # Las forks pesan más que las stars: son una señal de uso técnico, no solo
    # de visibilidad. El ratio se filtra aparte para no penalizar proyectos pequeños.
    score = (
        math.log1p(stars) * 3.0
        + math.log1p(forks) * 5.0
        + min(issues, 100) * 0.05
        + activity_bonus
    )
    reasons = [f"{stars} stars", f"{forks} forks"]
    if pushed_at and age_days <= config.GITHUB_ACTIVITY_DAYS:
        reasons.append("actividad reciente")
    return round(score, 2), reasons


def is_signal_repo(item: dict[str, Any], now: datetime | None = None) -> bool:
    """Indica si un repositorio supera los filtros de señal configurados.

    Es una heurística conservadora: no puede demostrar que una estrella sea
    orgánica, pero elimina forks, repos abandonados y patrones inflados muy
    evidentes antes de enviarlos al modelo.
    """
    if item.get("fork") or item.get("archived") or item.get("disabled"):
        return False
    description = str(item.get("description") or "").strip()
    stars = int(item.get("stargazers_count", item.get("stars", 0)) or 0)
    forks = int(item.get("forks_count", item.get("forks", 0)) or 0)
    if not description or stars < config.GITHUB_MIN_STARS or not _is_technical_repo(item):
        return False

    pushed_at = _parse_github_date(item.get("pushed_at"))
    if pushed_at:
        current = now or _utcnow()
        age_days = (current - pushed_at).total_seconds() / 86_400
        if age_days > config.GITHUB_ACTIVITY_DAYS:
            return False

    if stars >= config.GITHUB_HIGH_STAR_THRESHOLD:
        ratio = stars / max(forks, 1)
        if ratio > config.GITHUB_MAX_STAR_FORK_RATIO:
            return False
    return True


def _normalize_repo(item: dict[str, Any]) -> dict[str, Any]:
    """Normaliza la respuesta de GitHub y conserva señales para revisión."""
    stars = int(item.get("stargazers_count", item.get("stars", 0)) or 0)
    forks = int(item.get("forks_count", item.get("forks", 0)) or 0)
    score, reasons = _signal_score(item)
    return {
        "id": f"gh_{item['id']}",
        "name": item["full_name"],
        "description": item.get("description") or "Sin descripción",
        "language": item.get("language") or "Desconocido",
        "stars": stars,
        "forks": forks,
        "open_issues": int(item.get("open_issues_count", 0) or 0),
        "topics": item.get("topics") or [],
        "created_at": item.get("created_at"),
        "pushed_at": item.get("pushed_at"),
        "signal_score": score,
        "signal_reasons": reasons,
        "url": item["html_url"],
    }


def get_trending_repos(limit: int = 10) -> list[dict]:
    """Busca repositorios recientes y los ordena por señales técnicas públicas."""
    since = (_utcnow() - timedelta(days=config.GITHUB_TRENDING_DAYS)).strftime("%Y-%m-%d")
    params = {
        "q": f"created:>{since} archived:false fork:false is:public",
        "sort": "stars",
        "order": "desc",
        "per_page": min(max(limit, 1), 100),
    }

    resp = _github_request(f"{GITHUB_API}/search/repositories", params=params, timeout=30)
    items = resp.json().get("items", [])
    candidates = [item for item in items if is_signal_repo(item)]
    candidates.sort(key=lambda item: _signal_score(item)[0], reverse=True)
    return [_normalize_repo(item) for item in candidates[: max(limit, 1)]]


def get_repo_info(repo_name: str) -> dict:
    """Obtiene los detalles de un repositorio específico (owner/repo).

    Args:
        repo_name: Nombre con formato ``propietario/repositorio``.

    Returns:
        Datos normalizados del repositorio.

    Raises:
        ValueError: Si el nombre no tiene un formato seguro de GitHub.
        requests.RequestException: Si GitHub no responde correctamente.
    """
    repo_name = repo_name.strip()
    partes = repo_name.split("/")
    if (
        len(partes) != 2
        or any(parte in (".", "..") for parte in partes)
        or not _REPO_PATTERN.fullmatch(repo_name)
    ):
        raise ValueError(
            "El repositorio debe tener el formato propietario/repositorio "
            "y solo puede contener letras, números, puntos, guiones o guiones bajos."
        )

    resp = _github_request(f"{GITHUB_API}/repos/{repo_name}", timeout=15)
    data = resp.json()
    return {
        "id": f"gh_{data['id']}",
        "name": data["full_name"],
        "description": data.get("description") or "Sin descripción",
        "language": data.get("language") or "Desconocido",
        "stars": data["stargazers_count"],
        "url": data["html_url"],
    }


def get_readme_content(repo_name: str, max_chars: int = 4000) -> Optional[str]:
    """Descarga el contenido del README.md de un repositorio.

    Args:
        repo_name: Nombre con formato ``propietario/repositorio``.
        max_chars: Máximo de caracteres que se incorporan al prompt.

    Returns:
        Contenido del README truncado o ``None`` si no está disponible.

    Raises:
        ValueError: Si el nombre no tiene un formato seguro de GitHub.
    """
    repo_name = repo_name.strip()
    partes = repo_name.split("/")
    if (
        len(partes) != 2
        or any(parte in (".", "..") for parte in partes)
        or not _REPO_PATTERN.fullmatch(repo_name)
    ):
        raise ValueError("El repositorio no tiene un formato válido de GitHub.")

    readme_names = ["README.md", "readme.md", "README.MD", "Readme.md"]

    for filename in readme_names:
        try:
            resp = _github_request(f"{GITHUB_API}/repos/{repo_name}/contents/{filename}", timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                content = base64.b64decode(data.get("content", "")).decode("utf-8", errors="replace")
                if len(content) > max_chars:
                    content = content[:max_chars] + "\n\n[... contenido truncado]"
                return content
        except Exception:
            continue

    return None
