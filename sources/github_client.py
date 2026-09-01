"""Cliente resiliente para interactuar con la API de GitHub."""

import base64
import re
from datetime import datetime, timedelta
from typing import Optional

import requests

from src import config

GITHUB_API = "https://api.github.com"
_REPO_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")


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
            print("  ⚠️ GITHUB_TOKEN en .env es inválido o expiró. Reintentando de forma pública...")
            anon_headers = _get_headers(use_auth=False)
            resp = requests.get(url, params=params, headers=anon_headers, timeout=timeout)
        resp.raise_for_status()
        return resp
    except requests.RequestException:
        raise


def get_trending_repos(limit: int = 10) -> list[dict]:
    """Busca repositorios con más stars creados en los últimos 30 días."""
    since = (datetime.utcnow() - timedelta(days=30)).strftime("%Y-%m-%d")
    params = {
        "q": f"created:>{since}",
        "sort": "stars",
        "order": "desc",
        "per_page": min(limit, 100),
    }

    resp = _github_request(f"{GITHUB_API}/search/repositories", params=params, timeout=30)
    items = resp.json().get("items", [])

    repos = []
    for item in items:
        repos.append({
            "id": f"gh_{item['id']}",
            "name": item["full_name"],
            "description": item.get("description") or "Sin descripción",
            "language": item.get("language") or "Desconocido",
            "stars": item["stargazers_count"],
            "url": item["html_url"],
        })
    return repos


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
