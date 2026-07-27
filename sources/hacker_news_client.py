"""Cliente para obtener noticias de Hacker News."""

from typing import List

import requests


HN_API = "https://hacker-news.firebaseio.com/v0"


def get_top_stories(limit: int = 5) -> List[dict]:
    """Obtiene las historias principales de Hacker News.

    Args:
        limit: Cantidad de historias a obtener.

    Returns:
        Lista de dicts con keys: id, title, url, score, author, time, comments.
    """
    # Obtener IDs de las historias principales
    resp = requests.get(f"{HN_API}/topstories.json", timeout=15)
    resp.raise_for_status()
    story_ids = resp.json()[:limit]

    stories = []
    for story_id in story_ids:
        try:
            story_resp = requests.get(f"{HN_API}/item/{story_id}.json", timeout=10)
            story_resp.raise_for_status()
            item = story_resp.json()

            if not item or item.get("type") != "story":
                continue

            stories.append({
                "id": f"nw_{item['id']}",
                "title": item.get("title", "Sin título"),
                "url": item.get("url", f"https://news.ycombinator.com/item?id={item['id']}"),
                "score": item.get("score", 0),
                "author": item.get("by", "anónimo"),
                "time": item.get("time", 0),
                "comments": item.get("descendants", 0),
            })
        except requests.RequestException:
            continue

    return stories


def get_best_stories(limit: int = 5) -> List[dict]:
    """Obtiene las mejores historias de Hacker News.

    Args:
        limit: Cantidad de historias a obtener.

    Returns:
        Lista de dicts con keys: id, title, url, score, author, time, comments.
    """
    resp = requests.get(f"{HN_API}/beststories.json", timeout=15)
    resp.raise_for_status()
    story_ids = resp.json()[:limit]

    stories = []
    for story_id in story_ids:
        try:
            story_resp = requests.get(f"{HN_API}/item/{story_id}.json", timeout=10)
            story_resp.raise_for_status()
            item = story_resp.json()

            if not item or item.get("type") != "story":
                continue

            stories.append({
                "id": f"nw_{item['id']}",
                "title": item.get("title", "Sin título"),
                "url": item.get("url", f"https://news.ycombinator.com/item?id={item['id']}"),
                "score": item.get("score", 0),
                "author": item.get("by", "anónimo"),
                "time": item.get("time", 0),
                "comments": item.get("descendants", 0),
            })
        except requests.RequestException:
            continue

    return stories
