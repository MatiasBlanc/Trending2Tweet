"""Insignia animada que muestra la fuente seleccionada."""

from rich.text import Text
from textual.css.scalar import ScalarOffset
from textual.geometry import Offset
from textual.widgets import Static

from src.services.providers import SourceProvider

_SOURCE_METADATA = {
    "github": {
        "icon": "🐙",
        "title": "GitHub Trending",
        "desc": "Repositorios con mayor impacto y actividad reciente",
        "color": "#38bdf8",
        "border_color": "#0284c7",
    },
    "reddit": {
        "icon": "⌨️",
        "title": "Reddit Teclados",
        "desc": "Comunidad de teclados mecánicos, setups y hardware",
        "color": "#f97316",
        "border_color": "#ea580c",
    },
    "hacker_news": {
        "icon": "📰",
        "title": "Hacker News",
        "desc": "Noticias de tecnología, software e inteligencia artificial",
        "color": "#f59e0b",
        "border_color": "#d97706",
    },
    "code": {
        "icon": "💻",
        "title": "Code News",
        "desc": "Artículos técnicos, retos y lecciones de programación",
        "color": "#22c55e",
        "border_color": "#16a34a",
    },
}


class ActiveSourceBadge(Static):
    """Muestra la fuente activa emergiendo desde abajo con animación fluida."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._current_key: str | None = None

    def show_source(self, provider: SourceProvider, animate: bool = True) -> None:
        """Actualiza la insignia y ejecuta la animación de entrada desde abajo."""
        meta = _SOURCE_METADATA.get(
            provider.key,
            {
                "icon": provider.icon or "●",
                "title": provider.name,
                "desc": f"Contenido curado desde {provider.name}",
                "color": "#f4f4f5",
                "border_color": "#3f3f46",
            },
        )

        t = Text()
        t.append(f" {meta['icon']}  ", style=f"bold {meta['color']}")
        t.append(f"{meta['title']} ", style=f"bold {meta['color']}")
        t.append(" · ", style="#52525b")
        t.append(f" {meta['desc']} ", style="#a1a1aa")
        self.update(t)

        try:
            self.styles.border = ("round", meta["border_color"])
        except Exception:
            pass

        if animate:
            self.styles.offset = ScalarOffset.from_offset(Offset(0, 5))
            self.styles.opacity = 0.0
            self.styles.animate(
                "offset",
                value=ScalarOffset.from_offset(Offset(0, 0)),
                duration=0.32,
                easing="out_cubic",
            )
            self.styles.animate(
                "opacity",
                value=1.0,
                duration=0.32,
                easing="out_cubic",
            )
        else:
            self.styles.offset = ScalarOffset.from_offset(Offset(0, 0))
            self.styles.opacity = 1.0

        self._current_key = provider.key
