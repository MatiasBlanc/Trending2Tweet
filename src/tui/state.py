"""Estado central y transiciones de la experiencia interactiva."""

from dataclasses import dataclass, field
from typing import Literal

from src.core.models import Candidate, GenerationResult, PipelineEvent

AppStage = Literal["idle", "running", "confirm", "complete", "error", "cancelled"]

_DEFAULT_STEPS = (
    PipelineEvent("search", "Buscar en la fuente", "pending"),
    PipelineEvent("rank", "Seleccionar un hallazgo", "pending"),
    PipelineEvent("analyze", "Preparar contexto", "pending"),
    PipelineEvent("write", "Escribir el post", "pending"),
)


@dataclass
class AppState:
    """Fuente única de verdad para la pantalla principal.

    Attributes:
        current_source: Clave de la fuente seleccionada.
        query: Intención editorial del usuario.
        stage: Momento actual de la experiencia.
        candidates: Candidatos visibles, limitados por la UI.
        candidate_index: Posición del candidato protagonista actual.
        selected_candidate: Hallazgo protagonista.
        generated_posts: Original y variantes generadas.
        selected_variant: Índice de la versión visible.
        error: Mensaje recuperable para el usuario.
        pipeline: Estado actual de cada etapa.
        result: Resultado persistido asociado a la sesión.
    """

    current_source: str = "github"
    query: str = ""
    stage: AppStage = "idle"
    candidates: list[Candidate] = field(default_factory=list)
    candidate_index: int = 0
    selected_candidate: Candidate | None = None
    generated_posts: list[str] = field(default_factory=list)
    selected_variant: int = 0
    error: str | None = None
    error_title: str | None = None
    pipeline: dict[str, PipelineEvent] = field(default_factory=dict)
    result: GenerationResult | None = None

    def start(self, query: str) -> None:
        """Inicia una ejecución y limpia los datos de la anterior.

        Args:
            query: Intención editorial no vacía.

        Raises:
            ValueError: Si no se escribió una intención.
        """
        if not query.strip():
            raise ValueError("Escribe qué quieres publicar.")
        self.query = query.strip()
        self.stage = "running"
        self.candidates = []
        self.candidate_index = 0
        self.selected_candidate = None
        self.generated_posts = []
        self.selected_variant = 0
        self.error = None
        self.error_title = None
        self.result = None
        self.pipeline = {event.step: event for event in _DEFAULT_STEPS}

    def set_candidates(self, candidates: list[Candidate]) -> None:
        """Establece los candidatos encontrados y pasa a etapa de confirmación.

        Args:
            candidates: Lista no vacía de candidatos ordenados.

        Raises:
            ValueError: Si la lista está vacía.
        """
        if not candidates:
            raise ValueError("La lista de candidatos no puede estar vacía.")
        self.candidates = candidates
        self.candidate_index = 0
        self.selected_candidate = candidates[0]
        self.stage = "confirm"
        if "rank" in self.pipeline:
            self.pipeline["rank"] = PipelineEvent(
                "rank",
                f"Seleccionado: {self.selected_candidate.title}",
                "success",
                candidate=self.selected_candidate,
            )

    def next_candidate(self) -> Candidate:
        """Avanza al siguiente candidato disponible de forma cíclica.

        Returns:
            El candidato recién seleccionado.

        Raises:
            IndexError: Si no hay candidatos disponibles.
        """
        if not self.candidates:
            raise IndexError("No hay candidatos disponibles.")
        self.candidate_index = (self.candidate_index + 1) % len(self.candidates)
        self.selected_candidate = self.candidates[self.candidate_index]
        if "rank" in self.pipeline:
            self.pipeline["rank"] = PipelineEvent(
                "rank",
                f"Seleccionado: {self.selected_candidate.title}",
                "success",
                candidate=self.selected_candidate,
            )
        return self.selected_candidate

    def previous_candidate(self) -> Candidate:
        """Retrocede al candidato anterior de forma cíclica.

        Returns:
            El candidato recién seleccionado.

        Raises:
            IndexError: Si no hay candidatos disponibles.
        """
        if not self.candidates:
            raise IndexError("No hay candidatos disponibles.")
        self.candidate_index = (self.candidate_index - 1) % len(self.candidates)
        self.selected_candidate = self.candidates[self.candidate_index]
        if "rank" in self.pipeline:
            self.pipeline["rank"] = PipelineEvent(
                "rank",
                f"Seleccionado: {self.selected_candidate.title}",
                "success",
                candidate=self.selected_candidate,
            )
        return self.selected_candidate

    def confirm_candidate(self) -> Candidate:
        """Confirma el candidato actual y avanza a la redacción.

        Returns:
            El candidato confirmado.

        Raises:
            ValueError: Si no hay candidato seleccionado.
        """
        if self.selected_candidate is None:
            raise ValueError("No hay un candidato seleccionado para confirmar.")
        self.stage = "running"
        return self.selected_candidate

    def apply_event(self, event: PipelineEvent) -> None:
        """Aplica una transición semántica emitida por el servicio.

        Args:
            event: Nuevo estado de una etapa conocida o nueva.
        """
        self.pipeline[event.step] = event
        if event.candidate is not None:
            self.selected_candidate = event.candidate
            if not self.candidates:
                self.candidates = [event.candidate]
                self.candidate_index = 0

    def complete(self, result: GenerationResult) -> None:
        """Convierte el post generado en protagonista de la interfaz.

        Args:
            result: Resultado generado y persistido.
        """
        self.stage = "complete"
        self.result = result
        self.selected_candidate = result.candidate
        self.candidates = [result.candidate]
        self.candidate_index = 0
        self.generated_posts = list(result.variants or [result.post])
        self.selected_variant = 0
        self.error = None
        self.error_title = None

    def fail(self, message: str, title: str | None = None) -> None:
        """Muestra un error recuperable con título descriptivo.

        Args:
            message: Explicación breve orientada al usuario.
            title: Título de la tarjeta de error.
        """
        self.stage = "error"
        self.error = message
        self.error_title = title

    def cancel(self) -> None:
        """Vuelve al inicio después de cancelar una operación."""
        self.stage = "cancelled"
        self.error = None
        self.error_title = None

    def add_variants(self, posts: list[str]) -> None:
        """Agrega alternativas no vacías evitando duplicados.

        Args:
            posts: Nuevas versiones generadas.
        """
        for post in posts:
            clean = post.strip()
            if clean and clean not in self.generated_posts:
                self.generated_posts.append(clean)

    def select_variant(self, index: int) -> str:
        """Selecciona una variante disponible.

        Args:
            index: Posición basada en cero.

        Returns:
            Texto de la variante seleccionada.

        Raises:
            IndexError: Si la posición no existe.
        """
        if not 0 <= index < len(self.generated_posts):
            raise IndexError("La variante solicitada no existe.")
        self.selected_variant = index
        return self.generated_posts[index]

    @property
    def current_post(self) -> str:
        """Devuelve el post visible o texto vacío si todavía no existe."""
        if not self.generated_posts:
            return ""
        return self.generated_posts[self.selected_variant]
