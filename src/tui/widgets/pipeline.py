"""Representación compacta y reactiva del pipeline."""

from rich.text import Text
from textual.widgets import Static

from src.core.models import PipelineEvent

_STATUS_STYLE = {
    "pending": ("·", "#52525b"),
    "running": ("→", "bold #f4f4f5"),
    "success": ("✓", "#22c55e"),
    "warning": ("!", "#f59e0b"),
    "error": ("×", "#ef4444"),
}


class PipelineWidget(Static):
    """Actualiza etapas existentes sin acumular líneas de log."""

    def show_steps(self, steps: list[PipelineEvent]) -> None:
        """Reemplaza el estado visual completo del pipeline.

        Args:
            steps: Etapas ordenadas que deben mostrarse.
        """
        content = Text()
        for index, step in enumerate(steps):
            if index:
                content.append("\n")
            symbol, style = _STATUS_STYLE[step.status]
            content.append(f"{symbol} ", style=style)
            content.append(step.label, style="#f4f4f5" if step.status == "running" else "#a1a1aa")
        self.update(content)
