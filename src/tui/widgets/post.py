"""Resultado principal, contador y edición integrada."""

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Label, Static, TextArea

from src.services.content_service import character_count

_VARIANT_NAMES = ("Original", "Breve", "Con postura")


class PostWidget(Vertical):
    """Muestra una variante principal y la convierte en editor al solicitarlo."""

    def __init__(
        self,
        *,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
        disabled: bool = False,
    ) -> None:
        super().__init__(name=name, id=id, classes=classes, disabled=disabled)
        self._post = ""
        self._original_before_edit = ""
        self._variant_count = 1
        self._selected_variant = 0

    def compose(self) -> ComposeResult:
        """Compone el único panel con borde de la vista final."""
        yield Label("Post", id="post-title")
        yield Label("1  Original", id="variant-tabs")
        with Vertical(id="post-card"):
            yield Static("", id="post-content")
            yield TextArea("", id="post-editor")
            yield Label("0 / 280", id="character-counter")
        yield Label(
            "[C] Copiar    [R] Otra vez    [V] Variantes    [E] Editar",
            id="post-actions",
        )

    def on_mount(self) -> None:
        """Oculta el editor hasta que el usuario lo solicite."""
        self.query_one("#post-editor", TextArea).display = False

    def show_post(
        self,
        post: str,
        selected_variant: int = 0,
        variant_count: int = 1,
    ) -> None:
        """Presenta una versión y actualiza contador y pestañas.

        Args:
            post: Texto principal visible.
            selected_variant: Variante seleccionada basada en cero.
            variant_count: Cantidad total de versiones disponibles.
        """
        self._post = post
        self._selected_variant = selected_variant
        self._variant_count = variant_count
        self.query_one("#post-content", Static).update(Text(post, style="#f4f4f5"))
        self._update_counter(post)
        self._update_tabs()

    def begin_edit(self) -> None:
        """Activa el editor interno con el contenido visible."""
        self._original_before_edit = self._post
        editor = self.query_one("#post-editor", TextArea)
        editor.load_text(self._post)
        self.query_one("#post-content", Static).display = False
        editor.display = True
        self.query_one("#post-actions", Label).update(
            "[Ctrl+S] Guardar    [Esc] Cancelar"
        )
        editor.focus()

    def save_edit(self) -> str:
        """Finaliza la edición y devuelve el texto nuevo.

        Returns:
            Contenido actual del editor sin espacios exteriores.

        Raises:
            ValueError: Si el editor queda vacío.
        """
        editor = self.query_one("#post-editor", TextArea)
        post = editor.text.strip()
        if not post:
            raise ValueError("El post no puede quedar vacío.")
        self._finish_edit(post)
        return post

    def cancel_edit(self) -> None:
        """Descarta cambios y restaura el contenido previo."""
        self._finish_edit(self._original_before_edit)

    @property
    def is_editing(self) -> bool:
        """Indica si el editor ocupa actualmente la tarjeta."""
        return self.query_one("#post-editor", TextArea).display

    def on_text_area_changed(self, event: TextArea.Changed) -> None:
        """Actualiza el contador únicamente cuando cambia el editor."""
        self._update_counter(event.text_area.text)

    def _finish_edit(self, post: str) -> None:
        self._post = post
        editor = self.query_one("#post-editor", TextArea)
        editor.display = False
        content = self.query_one("#post-content", Static)
        content.display = True
        content.update(Text(post, style="#f4f4f5"))
        self.query_one("#post-actions", Label).update(
            "[C] Copiar    [R] Otra vez    [V] Variantes    [E] Editar"
        )
        self._update_counter(post)

    def _update_counter(self, post: str) -> None:
        count = character_count(post)
        counter = self.query_one("#character-counter", Label)
        counter.update(f"{count} / 280")
        counter.set_class(count > 280, "over-limit")

    def _update_tabs(self) -> None:
        tabs = []
        for index in range(self._variant_count):
            name = _VARIANT_NAMES[index] if index < len(_VARIANT_NAMES) else f"Variante {index + 1}"
            selected = "●" if index == self._selected_variant else "○"
            tabs.append(f"{selected} {index + 1} {name}")
        self.query_one("#variant-tabs", Label).update("     ".join(tabs))
