"""Selector horizontal y reutilizable de fuentes."""

from typing import ClassVar

from rich.text import Text
from textual import events
from textual.binding import Binding, BindingType
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import Static

from src.services.providers import SourceProvider

_SOURCE_COLORS = {
    "github": "#38bdf8",
    "reddit": "#f97316",
    "hacker_news": "#f59e0b",
    "code": "#22c55e",
}

_SOURCE_ICONS = {
    "github": "🐙",
    "reddit": "⌨️",
    "hacker_news": "📰",
    "code": "💻",
}


class SourcesWidget(Static):
    """Permite recorrer proveedores con las flechas horizontales."""

    can_focus = True

    class Changed(Message):
        """Notifica que el usuario eligió una fuente distinta."""

        def __init__(self, source_key: str) -> None:
            super().__init__()
            self.source_key = source_key

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("left", "previous_source", "Fuente anterior", show=False),
        Binding("right", "next_source", "Fuente siguiente", show=False),
    ]

    selected_index = reactive(0)

    def __init__(
        self,
        providers: tuple[SourceProvider, ...],
        *,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
        disabled: bool = False,
    ) -> None:
        super().__init__(name=name, id=id, classes=classes, disabled=disabled)
        self.providers = providers

    def render(self) -> Text:
        """Dibuja las fuentes con estilo de pastilla destacada para la opción activa."""
        line = Text()
        for index, provider in enumerate(self.providers):
            if index:
                line.append("  ")
            is_selected = index == self.selected_index
            icon = _SOURCE_ICONS.get(provider.key, provider.icon or "●")
            color = _SOURCE_COLORS.get(provider.key, "#f4f4f5")
            if is_selected:
                line.append(f" ▸ {icon} {provider.name} ", style=f"bold {color} on #1f2937")
            else:
                line.append(f"   {icon} {provider.name} ", style="#71717a")
        return line

    def watch_selected_index(self) -> None:
        """Actualiza la línea cuando cambia la selección."""
        self.refresh()

    def action_previous_source(self) -> None:
        """Selecciona el proveedor anterior de forma circular."""
        self.selected_index = (self.selected_index - 1) % len(self.providers)
        self.post_message(self.Changed(self.providers[self.selected_index].key))

    def action_next_source(self) -> None:
        """Selecciona el proveedor siguiente de forma circular."""
        self.selected_index = (self.selected_index + 1) % len(self.providers)
        self.post_message(self.Changed(self.providers[self.selected_index].key))

    def on_click(self, event: events.Click) -> None:
        """Permite seleccionar la fuente directamente al hacer click con el mouse."""
        total_width = self.size.width
        if total_width > 0 and len(self.providers) > 0:
            segment_width = total_width / len(self.providers)
            idx = int(event.x / segment_width)
            idx = max(0, min(idx, len(self.providers) - 1))
            self.selected_index = idx
            self.post_message(self.Changed(self.providers[idx].key))
        else:
            self.action_next_source()

    def select(self, source_key: str) -> None:
        """Sincroniza la selección a partir de una clave externa.

        Args:
            source_key: Clave de uno de los proveedores registrados.
        """
        for index, provider in enumerate(self.providers):
            if provider.key == source_key:
                self.selected_index = index
                return
        raise ValueError(f"Fuente desconocida: {source_key}")
