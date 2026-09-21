"""Tarjeta reservada para el hallazgo seleccionado."""

from rich.text import Text
from textual.widgets import Static

from src.core.models import Candidate


class CandidateWidget(Static):
    """Presenta un solo candidato con metadata secundaria discreta."""

    def show_candidate(
        self,
        candidate: Candidate,
        current_index: int = 0,
        total_count: int = 1,
        is_confirming: bool = False,
        source_key: str = "github",
    ) -> None:
        """Actualiza la tarjeta con un candidato normalizado y pregunta de confirmación.

        Args:
            candidate: Hallazgo que se utilizará para redactar.
            current_index: Posición del candidato actual (0-indexed).
            total_count: Total de candidatos disponibles.
            is_confirming: Si estamos en etapa interactiva de confirmación.
            source_key: Clave del proveedor de la fuente.
        """
        description = candidate.description.strip().replace("\n", " ")
        if len(description) > 180:
            description = f"{description[:177].rstrip()}…"

        noun = (
            "este repositorio"
            if source_key == "github"
            else ("esta publicación" if source_key == "reddit" else "esta noticia")
        )

        content = Text()
        if is_confirming:
            content.append(f"¿Quieres usar {noun} para redactar el post?", style="bold #38bdf8")
            if total_count > 1:
                content.append(f"  [{current_index + 1}/{total_count}]\n\n", style="#71717a")
            else:
                content.append("\n\n")
        else:
            content.append("Seleccionado\n\n", style="bold #1DA1F2")

        content.append(f"{candidate.title}\n", style="bold #f4f4f5")
        if candidate.metadata:
            content.append(f"{candidate.metadata}\n", style="#a1a1aa")
        if description:
            content.append(f"{description}\n", style="#d4d4d8")

        if is_confirming:
            content.append("\n")
            content.append("Enter ", style="bold #22c55e")
            content.append("Usar y redactar   ", style="#e4e4e7")
            if total_count > 1:
                content.append("N / → ", style="bold #38bdf8")
                content.append("Siguiente   ", style="#e4e4e7")
                content.append("P / ← ", style="bold #38bdf8")
                content.append("Anterior   ", style="#e4e4e7")
            content.append("Esc ", style="bold #a1a1aa")
            content.append("Volver", style="#71717a")

        self.update(content)
