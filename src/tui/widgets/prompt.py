"""Input protagonista de la pantalla inicial."""

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Input, Label


class PromptWidget(Vertical):
    """Agrupa la pregunta principal y su campo de entrada."""

    def compose(self) -> ComposeResult:
        """Compone el input principal de la aplicación."""
        yield Label("¿Qué quieres publicar?", id="prompt-title")
        yield Input(
            placeholder="Busca algo interesante y conviértelo en un post…",
            id="query-input",
        )
