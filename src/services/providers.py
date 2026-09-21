"""Adaptadores comunes para las fuentes que ya utiliza Trending2Tweet."""

import random
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from bots import codigo, github_trending, news, teclados
from src.core.models import Candidate

Item = dict[str, Any]


@dataclass(frozen=True)
class SourceProvider:
    """Describe una fuente sin acoplarla a una interfaz de usuario.

    Attributes:
        key: Identificador utilizado por CLI y estado.
        name: Nombre legible de la fuente.
        icon: Monograma de la fuente, seguro para terminales sin emojis.
        category: Carpeta de destino en Obsidian.
        draft_source: Identificador histórico guardado por la CLI original.
        prompt_file: Prompt existente para redactar el contenido.
        fetch_items: Función síncrona que consulta la integración real.
        format_user_message: Convierte un elemento en entrada para el LLM.
        get_item_id: Extrae el identificador estable.
        get_title: Extrae el título visible.
        get_url: Extrae la URL original.
        get_description: Extrae un resumen breve.
        get_metadata_label: Construye la métrica visible.
        prepare_item: Enriquece el elemento antes de redactar.
        get_variables: Variables que requiere el prompt existente.
        get_draft_metadata: Metadatos específicos para Obsidian.
    """

    key: str
    name: str
    icon: str
    category: str
    draft_source: str
    prompt_file: str
    fetch_items: Callable[[], list[Item]]
    format_user_message: Callable[[Item], str]
    get_item_id: Callable[[Item], str]
    get_title: Callable[[Item], str]
    get_url: Callable[[Item], str]
    get_description: Callable[[Item], str]
    get_metadata_label: Callable[[Item], str]
    prepare_item: Callable[[Item], Item] | None = None
    get_variables: Callable[[Item], dict[str, str]] | None = None
    get_draft_metadata: Callable[[Item], dict[str, Any]] | None = None

    def search(self, query: str) -> list[Item]:
        """Consulta la integración real del proveedor.

        El texto se conserva en la firma para permitir búsquedas específicas en
        futuros adaptadores; las fuentes actuales ya entregan su ranking propio.

        Args:
            query: Intención editorial del usuario.

        Returns:
            Elementos normalizados por el cliente existente.
        """
        return self.fetch_items()

    def to_candidate(self, item: Item) -> Candidate:
        """Normaliza un elemento externo para presentarlo y seleccionarlo.

        Args:
            item: Elemento devuelto por la integración del proveedor.

        Returns:
            Candidato independiente de la fuente concreta.
        """
        return Candidate(
            item_id=self.get_item_id(item),
            title=self.get_title(item),
            description=self.get_description(item),
            url=self.get_url(item),
            metadata=self.get_metadata_label(item),
            data=item,
        )


def _compact_number(value: int) -> str:
    """Formatea una métrica entera para ocupar poco espacio.

    Args:
        value: Métrica no negativa.

    Returns:
        Número compacto con sufijo ``k`` o ``M`` cuando corresponde.
    """
    if value >= 1_000_000:
        return f"{value / 1_000_000:.1f}M"
    if value >= 1_000:
        return f"{value / 1_000:.1f}k"
    return str(value)


def _github_provider() -> SourceProvider:
    return SourceProvider(
        key="github",
        name="GitHub",
        icon="GH",
        category="github",
        draft_source="github_trending",
        prompt_file=github_trending.PROMPT_FILE,
        fetch_items=github_trending._fetch_repos,
        format_user_message=github_trending._format_message,
        get_item_id=lambda item: str(item["id"]),
        get_title=lambda item: str(item["name"]),
        get_url=lambda item: str(item.get("url") or ""),
        get_description=lambda item: str(item.get("description") or "Sin descripción"),
        get_metadata_label=lambda item: (
            f"{_compact_number(int(item.get('stars', 0)))} stars"
            f" · {item.get('language') or 'Desconocido'}"
        ),
        prepare_item=github_trending._prepare_repo,
        get_draft_metadata=lambda item: {
            "repo_name": item["name"],
            "repo_stars": item["stars"],
        },
    )


def _hacker_news_provider() -> SourceProvider:
    return SourceProvider(
        key="hacker_news",
        name="Hacker News",
        icon="Y",
        category="news",
        draft_source="news",
        prompt_file=news.PROMPT_FILE,
        fetch_items=news._fetch_news,
        format_user_message=news._format_message,
        get_item_id=lambda item: str(item["id"]),
        get_title=lambda item: str(item["title"]),
        get_url=lambda item: str(item.get("url") or ""),
        get_description=lambda item: (
            f"Por {item.get('author', 'anónimo')} · "
            f"{item.get('comments', 0)} comentarios"
        ),
        get_metadata_label=lambda item: f"{_compact_number(int(item.get('score', 0)))} puntos",
        get_variables=lambda item: {"estilo_gancho": random.choice(news.ESTILOS_GANCHO)},
    )


def _code_news_provider() -> SourceProvider:
    return SourceProvider(
        key="code",
        name="Code News",
        icon="</>",
        category="codigo",
        draft_source="codigo",
        prompt_file=codigo.PROMPT_FILE,
        fetch_items=codigo._fetch_code_news,
        format_user_message=codigo._format_message,
        get_item_id=lambda item: str(item["id"]),
        get_title=lambda item: str(item["title"]),
        get_url=lambda item: str(item.get("url") or ""),
        get_description=lambda item: (
            f"Por {item.get('author', 'anónimo')} · "
            f"{item.get('comments', 0)} comentarios"
        ),
        get_metadata_label=lambda item: f"{_compact_number(int(item.get('score', 0)))} puntos",
        get_variables=lambda item: {"estilo_gancho": codigo.ESTILO_GANCHO},
    )


def _reddit_provider() -> SourceProvider:
    return SourceProvider(
        key="reddit",
        name="Reddit",
        icon="R",
        category="teclado",
        draft_source="teclados",
        prompt_file=teclados.PROMPT_FILE,
        fetch_items=teclados._fetch_posts,
        format_user_message=teclados._format_message,
        get_item_id=lambda item: str(item["id"]),
        get_title=lambda item: str(item["title"]),
        get_url=lambda item: str(item.get("url") or ""),
        get_description=lambda item: str(item.get("texto") or "Publicación de la comunidad"),
        get_metadata_label=lambda item: f"r/{item.get('subreddit', 'Reddit')}",
        get_variables=lambda item: {"estilo_gancho": teclados.ESTILO_GANCHO},
    )


def get_source_providers() -> tuple[SourceProvider, ...]:
    """Construye el registro ordenado de fuentes disponibles.

    Returns:
        Proveedores reales compartidos por CLI y TUI.
    """
    return (
        _github_provider(),
        _reddit_provider(),
        _hacker_news_provider(),
        _code_news_provider(),
    )
