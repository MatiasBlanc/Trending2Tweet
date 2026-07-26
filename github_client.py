"""Cliente para interactuar con la API de GitHub."""

import base64
from datetime import datetime, timedelta
from typing import List, Optional

import requests

import config


GITHUB_API = "https://api.github.com"


def get_trending_repos(limit: int = 10) -> List[dict]:
    """Busca repos con más stars creados en el último mes.

    Args:
        limit: Cantidad de repos a obtener (máx 100 por la API de GitHub).

    Returns:
        Lista de dicts con keys: id, name, description, language, stars, html_url.
    """
    since = (datetime.utcnow() - timedelta(days=30)).strftime("%Y-%m-%d")
    params = {
        "q": f"created:>{since}",
        "sort": "stars",
        "order": "desc",
        "per_page": min(limit, 100),
    }
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {config.GITHUB_TOKEN}",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    resp = requests.get(
        f"{GITHUB_API}/search/repositories",
        params=params,
        headers=headers,
        timeout=30,
    )
    resp.raise_for_status()

    items = resp.json().get("items", [])
    repos = []
    for item in items:
        repos.append({
            "id": item["id"],
            "name": item["full_name"],
            "description": item.get("description") or "Sin descripción",
            "language": item.get("language") or "Desconocido",
            "stars": item["stargazers_count"],
            "html_url": item["html_url"],
        })
    return repos


def get_top_repo_last_month() -> Optional[dict]:
    """Busca el repo con más stars creado en el último mes.

    Returns:
        dict con keys: id, name, description, language, stars, html_url
        o None si no hay resultados.
    """
    repos = get_trending_repos(limit=1)
    return repos[0] if repos else None


def get_readme_content(repo_name: str, max_chars: int = 4000) -> Optional[str]:
    """Descarga el contenido del README.md de un repositorio.

    Utiliza la API de GitHub para obtener el archivo codificado en Base64
    y lo decodifica a texto plano. Trunca el contenido para evitar
    saturar la ventana de contexto del LLM.

    Args:
        repo_name: Nombre completo del repo (ej: "owner/repo").
        max_chars: Cantidad máxima de caracteres a conservar.

    Returns:
        Contenido del README como string, o None si no se pudo obtener.
    """
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {config.GITHUB_TOKEN}",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    # Intentar con nombres de archivo comunes
    readme_names = ["README.md", "readme.md", "README.MD", "Readme.md"]

    for filename in readme_names:
        try:
            resp = requests.get(
                f"{GITHUB_API}/repos/{repo_name}/contents/{filename}",
                headers=headers,
                timeout=15,
            )
            if resp.status_code == 200:
                data = resp.json()
                # Decodificar contenido Base64
                content = base64.b64decode(data["content"]).decode("utf-8", errors="replace")
                # Truncar para no saturar el contexto del LLM
                if len(content) > max_chars:
                    content = content[:max_chars] + "\n\n[... contenido truncado]"
                return content
        except (requests.RequestException, KeyError, UnicodeDecodeError):
            continue

    return None
