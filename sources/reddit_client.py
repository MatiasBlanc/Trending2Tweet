"""Cliente para obtener publicaciones de subreddits de teclados vía RSS.

La API JSON pública de Reddit devuelve 403 desde IPs de datacenter (Railway),
pero el feed RSS funciona y respeta los límites de uso. El RSS no expone el
score numérico, pero el orden del feed ``top?t=day`` ya prioriza por votos.
"""

import html as html_lib
import re
import time
from typing import Sequence
from xml.etree import ElementTree as ET

import requests

REDDIT_USER_AGENT = "linux:trending2tweet:v1.0 (by /u/trending2tweet)"
ATOM = "{http://www.w3.org/2005/Atom}"
_RETRIES = 3
_BACKOFF_SEGUNDOS = 10

# Subreddits relevantes para el bot de teclados, en orden de prioridad.
SUBREDDITS_TECLADOS: tuple[str, ...] = (
    "MechanicalKeyboards",
    "ErgoMechKeyboards",
    "olkb",
)

# Patrón para separar el texto del pie de página que añade Reddit al HTML.
_PIE_MARCAS = ("submitted by", "[link]", "[comments]")


def _limpiar_html(texto: str) -> str:
    """Convierte el HTML del content del RSS a texto plano legible.

    Args:
        texto: HTML que envuelve el selftext del post.

    Returns:
        Texto plano sin la imagen de cabecera ni marcas de Reddit.
    """
    # Elimina la tabla con la imagen (el contenido visual del post).
    texto = re.sub(r"<table>.*?</table>", "", texto, flags=re.DOTALL)
    texto = re.sub(r"<[^>]+>", " ", texto)
    texto = html_lib.unescape(texto)
    for marca in _PIE_MARCAS:
        texto = texto.replace(marca, "")
    return re.sub(r"\s+", " ", texto).strip()


def _obtener_feed(subreddit: str, limite: int) -> list[dict]:
    """Obtiene los posts top del día de un subreddit vía RSS.

    Args:
        subreddit: Nombre del subreddit sin prefijo ``r/``.
        limite: Cantidad máxima de posts a pedir.

    Returns:
        Posts normalizados con título, id, autor, texto y url.

    Raises:
        requests.RequestException: Si Reddit no responde después de reintentos.
    """
    url = (
        f"https://www.reddit.com/r/{subreddit}/top/.rss"
        f"?t=day&limit={limite}"
    )
    for intento in range(_RETRIES):
        try:
            resp = requests.get(
                url,
                headers={"User-Agent": REDDIT_USER_AGENT},
                timeout=20,
            )
            if resp.status_code == 429:
                raise requests.HTTPError(
                    f"Rate limit de Reddit (429), intento {intento + 1}"
                )
            resp.raise_for_status()
            return _parsear_feed(resp.content)
        except requests.RequestException:
            if intento == _RETRIES - 1:
                raise
            time.sleep(_BACKOFF_SEGUNDOS * (intento + 1))
    return []


def _parsear_feed(contenido: bytes) -> list[dict]:
    """Convierte el XML Atom del feed en una lista de posts normalizados.

    Args:
        contenido: XML crudo devuelto por Reddit.

    Returns:
        Posts con las claves que espera el resto del bot.
    """
    root = ET.fromstring(contenido)
    posts = []
    for entry in root.findall(f"{ATOM}entry"):
        id_elem = entry.find(f"{ATOM}id")
        title_elem = entry.find(f"{ATOM}title")
        author_elem = entry.find(f"{ATOM}author/{ATOM}name")
        link_elem = entry.find(f"{ATOM}link")
        content_elem = entry.find(f"{ATOM}content")

        post_id = id_elem.text if id_elem is not None else ""
        # El id llega como t3_1vqn3ah; se usa completo para evitar colisiones.
        if not post_id:
            continue

        posts.append({
            "id": f"rd_{post_id}",
            "title": (title_elem.text or "").strip(),
            "author": (author_elem.text or "anónimo").replace("/u/", ""),
            "url": link_elem.get("href") if link_elem is not None else "",
            "texto": _limpiar_html(content_elem.text or ""),
            "subreddit": "",
        })
    return posts


def obtener_posts_teclados(
    subreddits: Sequence[str] | None = None,
    limite_por_sub: int = 10,
) -> list[dict]:
    """Obtiene posts de teclados combinando varios subreddits.

    Args:
        subreddits: Subreddits a consultar; por defecto usa los configurados.
        limite_por_sub: Cantidad de posts por subreddit.

    Returns:
        Posts combinados conservando el orden de prioridad de los subreddits.

    Raises:
        requests.RequestException: Si ningún subreddit responde.
    """
    seleccion = tuple(subreddits) if subreddits else SUBREDDITS_TECLADOS
    posts: list[dict] = []
    errores = 0

    for subreddit in seleccion:
        try:
            feed = _obtener_feed(subreddit, limite_por_sub)
            for post in feed:
                post["subreddit"] = subreddit
            posts.extend(feed)
            # Espaciado entre peticiones para no disparar el rate limit.
            time.sleep(2)
        except requests.RequestException as error:
            errores += 1
            print(f"  ⚠️  r/{subreddit} no disponible: {error}")

    if not posts and errores == len(seleccion):
        raise requests.RequestException(
            "Reddit no respondió en ningún subreddit"
        )
    return posts
