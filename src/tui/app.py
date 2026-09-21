"""Aplicación Textual principal de Trending2Tweet."""

import logging
from pathlib import Path
from typing import ClassVar

from textual import events, on
from textual.app import App, ComposeResult
from textual.binding import Binding, BindingType
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Input, Label, Static, TextArea
from textual.worker import Worker, get_current_worker

from src import config
from src.core.models import Candidate, GenerationResult, PipelineEvent
from src.services.content_service import (
    ContentService,
    NoCandidatesError,
    PipelineCancelled,
)
from src.services.logging_config import configure_file_logging
from src.services.providers import SourceProvider, get_source_providers
from src.tui.state import AppState
from src.tui.widgets import (
    ActiveSourceBadge,
    CandidateWidget,
    PipelineWidget,
    PostWidget,
    PromptWidget,
    SourcesWidget,
)

logger = logging.getLogger(__name__)


class DebugScreen(ModalScreen[None]):
    """Panel secundario que muestra las últimas líneas del log técnico."""

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("escape", "dismiss", "Cerrar", show=False)
    ]

    def __init__(self, log_path: Path) -> None:
        super().__init__()
        self.log_path = log_path

    def compose(self) -> ComposeResult:
        """Compone un visor acotado para no cargar logs completos."""
        try:
            lines = self.log_path.read_text(encoding="utf-8").splitlines()[-200:]
            content = "\n".join(lines) or "Todavía no hay eventos técnicos."
        except OSError as error:
            content = f"No se pudo leer el log: {error}"
        with Vertical(id="debug-dialog"):
            yield Label(f"Debug  ·  {self.log_path}", id="debug-title")
            with VerticalScroll():
                yield Static(content, markup=False, id="debug-content")
            yield Label("Esc  Cerrar", id="debug-close")

    async def action_dismiss(self, result: None = None) -> None:
        """Cierra el panel de depuración.

        Args:
            result: Resultado vacío requerido por el contrato de Textual.
        """
        await self.dismiss(result)


class TrendingToTweetApp(App[None]):
    """TUI reactiva y ligera montada sobre los servicios existentes."""

    CSS_PATH = "styles/app.tcss"
    TITLE = "Trending 2 Tweet"
    ENABLE_COMMAND_PALETTE = False

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("ctrl+c", "quit", "Salir", priority=True, show=False),
        Binding("escape", "escape", "Volver", priority=True, show=False),
        Binding("enter", "confirm_candidate", "Confirmar", show=False),
        Binding("n", "next_candidate", "Siguiente hallazgo", show=False),
        Binding("p", "previous_candidate", "Hallazgo anterior", show=False),
        Binding("c", "copy_post", "Copiar", show=False),
        Binding("r", "regenerate", "Otra vez", show=False),
        Binding("v", "variants", "Variantes", show=False),
        Binding("e", "edit", "Editar", show=False),
        Binding("ctrl+s", "save_edit", "Guardar", priority=True, show=False),
        Binding("up", "previous_source", "Fuente anterior", show=False),
        Binding("down", "next_source", "Fuente siguiente", show=False),
        Binding("tab", "next_source", "Fuente siguiente", priority=True, show=False),
        Binding("shift+tab", "previous_source", "Fuente anterior", priority=True, show=False),
        Binding("left", "previous_variant", "Anterior", show=False),
        Binding("right", "next_variant", "Siguiente", show=False),
        Binding("1", "select_variant(0)", "Original", show=False),
        Binding("2", "select_variant(1)", "Breve", show=False),
        Binding("3", "select_variant(2)", "Con postura", show=False),
        Binding("d", "debug", "Debug", show=False),
    ]

    def __init__(self, presentation: bool = False) -> None:
        super().__init__()
        self.presentation = presentation
        self.providers = get_source_providers()
        self.provider_by_key = {provider.key: provider for provider in self.providers}
        self.app_state = AppState(current_source=self.providers[0].key)
        self.content_service = ContentService()
        self.log_path = configure_file_logging()
        self._active_worker: Worker[object] | None = None
        self._operation_busy = False
        self._operation_id = 0
        self._activity = "Listo"

    def compose(self) -> ComposeResult:
        """Compone vistas simples cuya jerarquía cambia con el estado."""
        with Vertical(id="workspace"):
            with Horizontal(id="topbar"):
                yield Label("Trending2Tweet", id="brand")
                yield Label("Listo", id="status")

            with Vertical(id="idle-view"):
                yield PromptWidget(id="prompt-section")
                with Vertical(id="sources-container"):
                    yield ActiveSourceBadge(id="source-badge")
                    yield SourcesWidget(self.providers, id="sources")
                    yield Label("Enter generar   Tab / ↑ ↓ cambiar fuente   Ctrl+C salir", classes="quiet-hint")

            with Vertical(id="running-view"):
                yield Label("", id="active-source")
                yield PipelineWidget(id="pipeline")
                yield CandidateWidget(id="candidate")
                yield Label("Esc  Cancelar", classes="quiet-hint", id="running-hint")

            with Vertical(id="complete-view"):
                yield Label("", id="result-summary")
                yield PostWidget(id="post")

            with Vertical(id="error-view"):
                yield Label("× No se pudo completar", id="error-title")
                yield Static("", id="error-message")
                yield Label("[R] Reintentar    [Esc] Volver", id="error-actions")

            yield Label("D  Debug", id="debug-hint")

    def on_mount(self) -> None:
        """Aplica el modo visual y entrega el foco al prompt."""
        if self.presentation:
            self.screen.add_class("presentation")
        self._set_compact(self.size.width < 90 or self.size.height < 28)
        provider = self.provider_by_key[self.app_state.current_source]
        self.query_one("#source-badge", ActiveSourceBadge).show_source(provider, animate=False)
        self._render_state()
        self.query_one("#query-input", Input).focus()
        logger.info("TUI iniciada (presentation=%s)", self.presentation)

    def on_resize(self, event: events.Resize) -> None:
        """Simplifica metadata cuando la terminal es pequeña."""
        self._set_compact(event.size.width < 90 or event.size.height < 28)

    @on(SourcesWidget.Changed)
    def _source_changed(self, event: SourcesWidget.Changed) -> None:
        self.app_state.current_source = event.source_key
        provider = self.provider_by_key[event.source_key]
        self.query_one("#source-badge", ActiveSourceBadge).show_source(provider, animate=True)
        self._render_state()

    @on(Input.Submitted, "#query-input")
    def _prompt_submitted(self, event: Input.Submitted) -> None:
        self._start_generation(event.value)

    def _start_generation(self, query: str | None = None) -> None:
        if self._operation_busy:
            return
        prompt = self.query_one("#query-input", Input)
        requested_query = query if query is not None else prompt.value
        try:
            self.app_state.start(requested_query)
        except ValueError as error:
            self.notify(str(error), severity="warning", timeout=2)
            prompt.focus()
            return

        self._operation_busy = True
        self._operation_id += 1
        operation_id = self._operation_id
        self._render_state()
        provider = self.provider_by_key[self.app_state.current_source]
        self._active_worker = self.run_worker(
            lambda: self._run_search(
                provider, self.app_state.query, operation_id
            ),
            thread=True,
            group="pipeline",
            exclusive=True,
            name="buscar-candidatos",
        )

    def _run_search(
        self,
        provider: SourceProvider,
        query: str,
        operation_id: int,
    ) -> None:
        worker = get_current_worker()
        try:
            candidates = self.content_service.find_candidates(
                provider,
                query,
                on_event=lambda event: self.call_from_thread(
                    self._apply_pipeline_event, event, operation_id
                ),
                should_cancel=lambda: worker.is_cancelled,
            )
        except PipelineCancelled:
            self.call_from_thread(self._finish_cancelled, operation_id)
        except Exception as error:
            logger.exception("Falló la búsqueda en %s", provider.key)
            self.call_from_thread(self._finish_error, error, operation_id)
        else:
            self.call_from_thread(self._finish_search, candidates, operation_id)

    def _finish_search(
        self,
        candidates: list[Candidate],
        operation_id: int,
    ) -> None:
        if operation_id != self._operation_id:
            return
        self._operation_busy = False
        self._active_worker = None
        self.app_state.set_candidates(candidates)
        self._render_state()

    def action_confirm_candidate(self) -> None:
        """Confirma el candidato seleccionado y procede a generar el post."""
        if self.app_state.stage != "confirm" or self._operation_busy:
            return
        candidate = self.app_state.selected_candidate
        if candidate is None:
            return
        self.app_state.confirm_candidate()
        self._operation_busy = True
        self._operation_id += 1
        operation_id = self._operation_id
        self._render_state()
        provider = self.provider_by_key[self.app_state.current_source]
        self._active_worker = self.run_worker(
            lambda: self._run_generation_from_candidate(
                provider, candidate, self.app_state.query, operation_id
            ),
            thread=True,
            group="pipeline",
            exclusive=True,
            name="generar-post",
        )

    def _run_generation_from_candidate(
        self,
        provider: SourceProvider,
        candidate: Candidate,
        query: str,
        operation_id: int,
    ) -> None:
        worker = get_current_worker()
        try:
            result = self.content_service.generate_from_item(
                provider,
                candidate,
                query=query,
                on_event=lambda event: self.call_from_thread(
                    self._apply_pipeline_event, event, operation_id
                ),
                should_cancel=lambda: worker.is_cancelled,
            )
        except PipelineCancelled:
            self.call_from_thread(self._finish_cancelled, operation_id)
        except Exception as error:
            logger.exception("Falló la redacción para %s", candidate.title)
            self.call_from_thread(self._finish_error, error, operation_id)
        else:
            self.call_from_thread(self._finish_generation, result, operation_id)

    def action_next_candidate(self) -> None:
        """Avanza al siguiente candidato durante la confirmación."""
        if self.app_state.stage == "confirm" and not self._operation_busy:
            self.app_state.next_candidate()
            self._render_state()

    def action_previous_candidate(self) -> None:
        """Vuelve al candidato anterior durante la confirmación."""
        if self.app_state.stage == "confirm" and not self._operation_busy:
            self.app_state.previous_candidate()
            self._render_state()

    def _run_generation(
        self,
        provider: SourceProvider,
        query: str,
        operation_id: int,
    ) -> None:
        worker = get_current_worker()
        try:
            result = self.content_service.generate(
                provider,
                query,
                on_event=lambda event: self.call_from_thread(
                    self._apply_pipeline_event, event, operation_id
                ),
                should_cancel=lambda: worker.is_cancelled,
            )
        except PipelineCancelled:
            self.call_from_thread(self._finish_cancelled, operation_id)
        except Exception as error:
            logger.exception("Falló el pipeline de %s", provider.key)
            self.call_from_thread(self._finish_error, error, operation_id)
        else:
            self.call_from_thread(self._finish_generation, result, operation_id)

    def _apply_pipeline_event(
        self,
        event: PipelineEvent,
        operation_id: int,
    ) -> None:
        if operation_id != self._operation_id:
            return
        if self.app_state.stage in ("running", "confirm"):
            self.app_state.apply_event(event)
            self._render_state()

    def _finish_generation(
        self,
        result: GenerationResult,
        operation_id: int | None = None,
    ) -> None:
        if operation_id is not None and operation_id != self._operation_id:
            return
        self._operation_busy = False
        self._active_worker = None
        self.app_state.complete(result)
        self._render_state()

    def _finish_cancelled(self, operation_id: int) -> None:
        if operation_id != self._operation_id:
            return
        self._operation_busy = False
        self._active_worker = None
        self._reset_to_idle()
        self.notify("Operación cancelada", timeout=1.5)

    def _finish_error(self, error: Exception, operation_id: int) -> None:
        if operation_id != self._operation_id:
            return
        self._operation_busy = False
        self._active_worker = None
        error_name = type(error).__name__
        error_str = str(error)
        provider = self.provider_by_key[self.app_state.current_source]

        if isinstance(error, NoCandidatesError):
            title = f"× Sin resultados en {provider.name}"
            message = error_str
        elif isinstance(error, ValueError) and "clave API" in error_str:
            title = "× Falta clave de API"
            message = (
                "No hay una clave API configurada. "
                "Configura AZURE_API_KEY o LLM_API_KEY en tu .env o dotfiles."
            )
        elif "AuthenticationError" in error_name or "invalid_api_key" in error_str or "Incorrect API key" in error_str:
            title = "× Error de autenticación en IA"
            message = (
                "La clave de API (AZURE_API_KEY / LLM_API_KEY) fue rechazada (401). "
                "Verifica tus credenciales en el archivo .env o en dotfiles."
            )
        elif "RateLimitError" in error_name or "insufficient_quota" in error_str:
            title = "× Límite o cuota excedida en IA"
            message = (
                "Se excedió la cuota o el límite de peticiones del proveedor de IA. "
                "Espera unos momentos o revisa tu plan."
            )
        elif "APIConnectionError" in error_name or "ConnectError" in error_name:
            title = "× Error de conexión con la IA"
            message = (
                f"No se pudo conectar con el endpoint del LLM ({config.LLM_BASE_URL}). "
                "Revisa tu conexión o la URL configurada."
            )
        elif "APIStatusError" in error_name or "BadRequestError" in error_name:
            title = "× Error en el servicio de IA"
            message = f"El proveedor de IA devolvió un error: {error_str}"
        elif isinstance(error, (OSError, PermissionError)):
            title = "× Error al guardar borrador"
            message = f"No se pudo escribir en la bóveda: {error_str}"
        else:
            current_step = None
            for step_key in ("write", "analyze", "rank", "search"):
                event = self.app_state.pipeline.get(step_key)
                if event and event.status == "running":
                    current_step = step_key
                    break

            if current_step == "search":
                title = f"× Error al consultar {provider.name}"
                message = f"Fallo al conectar con {provider.name}: {error_str or 'Error de red o servicio.'}"
            elif current_step in ("write", "analyze"):
                title = "× Error en el servicio de IA"
                message = f"Fallo durante la redacción con el LLM: {error_str or 'Error desconocido.'}"
            else:
                title = f"× Error en {provider.name}"
                message = error_str or f"No se pudo completar la operación con {provider.name}."

        self.app_state.fail(message, title=title)
        self._render_state()

    def _render_state(self) -> None:
        stage = self.app_state.stage
        visible_stage = (
            "idle"
            if stage in ("idle", "cancelled")
            else ("running" if stage in ("running", "confirm") else stage)
        )
        for name in ("idle", "running", "complete", "error"):
            self.query_one(f"#{name}-view").display = name == visible_stage

        provider = self.provider_by_key[self.app_state.current_source]
        if visible_stage == "idle":
            self.query_one("#sources", SourcesWidget).select(provider.key)
            badge = self.query_one("#source-badge", ActiveSourceBadge)
            if badge._current_key != provider.key:
                badge.show_source(provider, animate=True)
        elif visible_stage == "running":
            self.query_one("#active-source", Label).update(
                f"{provider.icon}  {provider.name}"
            )
            pipeline = self.query_one("#pipeline", PipelineWidget)
            pipeline.show_steps(list(self.app_state.pipeline.values()))
            candidate_widget = self.query_one("#candidate", CandidateWidget)
            candidate_widget.display = self.app_state.selected_candidate is not None
            if self.app_state.selected_candidate:
                is_confirming = self.app_state.stage == "confirm"
                candidate_widget.set_class(is_confirming, "confirming")
                candidate_widget.show_candidate(
                    self.app_state.selected_candidate,
                    current_index=self.app_state.candidate_index,
                    total_count=len(self.app_state.candidates) or 1,
                    is_confirming=is_confirming,
                    source_key=provider.key,
                )
            hint = self.query_one("#running-hint", Label)
            if self.app_state.stage == "confirm":
                total = len(self.app_state.candidates)
                if total > 1:
                    hint.update("Enter Usar y redactar post   ·   N / → Siguiente   ·   P / ← Anterior   ·   Esc Cancelar")
                else:
                    hint.update("Enter Usar y redactar post   ·   Esc Cancelar")
            else:
                hint.update("Esc  Cancelar")
        elif visible_stage == "complete":
            candidate = self.app_state.selected_candidate
            summary = f"✓  {provider.name}"
            if candidate:
                summary += f"  →  {candidate.title}"
            self.query_one("#result-summary", Label).update(summary)
            self.query_one("#post", PostWidget).show_post(
                self.app_state.current_post,
                self.app_state.selected_variant,
                len(self.app_state.generated_posts),
            )
        else:
            title = self.app_state.error_title or f"× Error en {provider.name}"
            self.query_one("#error-title", Label).update(title)
            self.query_one("#error-message", Static).update(
                self.app_state.error or "Error desconocido."
            )

    def action_escape(self) -> None:
        """Cancela edición, operación o resultado según el contexto."""
        if self.app_state.stage == "complete":
            post_widget = self.query_one("#post", PostWidget)
            if post_widget.is_editing:
                post_widget.cancel_edit()
                return
            self._reset_to_idle()
            return
        if self.app_state.stage in ("running", "confirm"):
            self._cancel_active_operation()
            self._reset_to_idle()
            self.notify("Operación cancelada", timeout=1.5)
            return
        if self.app_state.stage == "error":
            self._reset_to_idle()

    def action_copy_post(self) -> None:
        """Copia el post visible usando el soporte de portapapeles de Textual."""
        if self.app_state.stage != "complete" or not self.app_state.current_post:
            return
        try:
            self.copy_to_clipboard(self.app_state.current_post)
            self.notify("✓ Copiado", timeout=1.5)
        except Exception:
            logger.exception("No se pudo copiar al portapapeles")
            self.notify("Portapapeles no disponible", severity="warning", timeout=2)

    def action_regenerate(self) -> None:
        """Regenera únicamente la variante visible y conserva el hallazgo."""
        if self.app_state.stage == "error":
            self._start_generation(self.app_state.query)
            return
        if self.app_state.stage != "complete" or self._operation_busy:
            return
        result = self.app_state.result
        if result is None:
            return
        style = ("original", "short", "opinionated")[
            min(self.app_state.selected_variant, 2)
        ]
        self._run_post_worker([style], replace_current=True)

    def action_variants(self) -> None:
        """Genera las dos alternativas editoriales sin repetir la búsqueda."""
        if (
            self.app_state.stage != "complete"
            or self._operation_busy
            or self.app_state.result is None
        ):
            return
        if len(self.app_state.generated_posts) >= 3:
            self._select_variant((self.app_state.selected_variant + 1) % 3)
            return
        self._run_post_worker(["short", "opinionated"], replace_current=False)

    def _run_post_worker(self, styles: list[str], replace_current: bool) -> None:
        self._operation_busy = True
        self._operation_id += 1
        operation_id = self._operation_id
        self._active_worker = self.run_worker(
            lambda: self._generate_posts(
                styles, replace_current, operation_id
            ),
            thread=True,
            group="pipeline",
            exclusive=True,
            name="generar-variantes",
        )

    def _generate_posts(
        self,
        styles: list[str],
        replace_current: bool,
        operation_id: int,
    ) -> None:
        result = self.app_state.result
        if result is None:
            return
        provider = self.provider_by_key[result.provider_key]
        posts: list[str] = []
        worker = get_current_worker()
        try:
            for style in styles:
                if worker.is_cancelled:
                    return
                posts.append(
                    self.content_service.regenerate(
                        provider,
                        result,
                        variant=style,
                        on_event=lambda event: self.call_from_thread(
                            self._apply_pipeline_event, event, operation_id
                        ),
                    )
                )
        except Exception as error:
            logger.exception("Falló la generación de variantes")
            self.call_from_thread(self._variant_error, error, operation_id)
        else:
            self.call_from_thread(
                self._finish_posts,
                posts,
                replace_current,
                operation_id,
            )

    def _finish_posts(
        self,
        posts: list[str],
        replace_current: bool,
        operation_id: int,
    ) -> None:
        if operation_id != self._operation_id:
            return
        self._operation_busy = False
        self._active_worker = None
        if not posts or self.app_state.result is None:
            return
        if replace_current:
            index = self.app_state.selected_variant
            self.app_state.generated_posts[index] = posts[0]
        else:
            self.app_state.add_variants(posts)
            if len(self.app_state.generated_posts) > 1:
                self.app_state.selected_variant = 1
        try:
            self.content_service.save_post(
                self.app_state.result,
                self.app_state.current_post,
            )
        except Exception:
            logger.exception("No se pudo guardar la nueva versión")
            self.notify("La versión se generó, pero no pudo guardarse", severity="warning")
        self._render_state()

    def _variant_error(self, error: Exception, operation_id: int) -> None:
        if operation_id != self._operation_id:
            return
        self._operation_busy = False
        self._active_worker = None
        error_name = type(error).__name__
        error_str = str(error)
        if "AuthenticationError" in error_name or "invalid_api_key" in error_str:
            msg = "Error 401 en IA: verifica AZURE_API_KEY / LLM_API_KEY"
        elif "RateLimitError" in error_name:
            msg = "Cuota o límite de peticiones de IA excedido"
        elif "APIConnectionError" in error_name:
            msg = "Error de conexión con el proveedor de IA"
        else:
            msg = f"Error al generar versión: {error_str[:60]}"
        self.notify(msg, severity="error", timeout=4)

    def action_edit(self) -> None:
        """Convierte la tarjeta final en editor de texto."""
        if self.app_state.stage == "complete" and not self._operation_busy:
            self.query_one("#post", PostWidget).begin_edit()

    def action_save_edit(self) -> None:
        """Guarda la edición en estado y en el borrador de Obsidian."""
        if self.app_state.stage != "complete" or self.app_state.result is None:
            return
        post_widget = self.query_one("#post", PostWidget)
        if not post_widget.is_editing:
            return
        try:
            post = post_widget.save_edit()
            self.content_service.save_post(self.app_state.result, post)
        except ValueError as error:
            self.notify(str(error), severity="warning", timeout=2)
            return
        except Exception:
            logger.exception("No se pudo guardar la edición")
            self.notify("No se pudo guardar la edición", severity="error", timeout=2)
            return
        self.app_state.generated_posts[self.app_state.selected_variant] = post
        self.notify("✓ Guardado", timeout=1.5)
        self._render_state()

    def action_previous_source(self) -> None:
        """Cambia a la fuente anterior en reposo o candidato anterior en confirmación."""
        if self.app_state.stage == "idle":
            self.query_one("#sources", SourcesWidget).action_previous_source()
        elif self.app_state.stage == "confirm":
            self.action_previous_candidate()

    def action_next_source(self) -> None:
        """Cambia a la fuente siguiente en reposo o candidato siguiente en confirmación."""
        if self.app_state.stage == "idle":
            self.query_one("#sources", SourcesWidget).action_next_source()
        elif self.app_state.stage == "confirm":
            self.action_next_candidate()

    def action_previous_variant(self) -> None:
        """Cambia a la fuente anterior en reposo, candidato en confirmación o variante en completado."""
        if self.app_state.stage == "idle":
            self.action_previous_source()
        elif self.app_state.stage == "confirm":
            self.action_previous_candidate()
        elif self.app_state.stage == "complete" and not self._is_editing():
            count = len(self.app_state.generated_posts)
            if count > 1:
                self._select_variant((self.app_state.selected_variant - 1) % count)

    def action_next_variant(self) -> None:
        """Cambia a la fuente siguiente en reposo, candidato en confirmación o variante en completado."""
        if self.app_state.stage == "idle":
            self.action_next_source()
        elif self.app_state.stage == "confirm":
            self.action_next_candidate()
        elif self.app_state.stage == "complete" and not self._is_editing():
            count = len(self.app_state.generated_posts)
            if count > 1:
                self._select_variant((self.app_state.selected_variant + 1) % count)

    def action_select_variant(self, index: int) -> None:
        """Selecciona directamente una variante mediante 1, 2 o 3."""
        if (
            self.app_state.stage == "complete"
            and not self._is_editing()
            and index < len(self.app_state.generated_posts)
        ):
            self._select_variant(index)

    def _select_variant(self, index: int) -> None:
        post = self.app_state.select_variant(index)
        if self.app_state.result is not None:
            try:
                self.content_service.save_post(self.app_state.result, post)
            except Exception:
                logger.exception("No se pudo persistir la variante elegida")
                self.notify("No se pudo guardar la variante", severity="warning")
        self._render_state()

    def action_debug(self) -> None:
        """Abre los detalles técnicos bajo demanda."""
        if not isinstance(self.focused, (Input, TextArea)):
            self.push_screen(DebugScreen(self.log_path))

    def _is_editing(self) -> bool:
        return self.query_one("#post", PostWidget).is_editing

    def _cancel_active_operation(self) -> None:
        self._operation_id += 1
        if self._active_worker is not None:
            self._active_worker.cancel()
        self._active_worker = None
        self._operation_busy = False

    def _reset_to_idle(self) -> None:
        if self._operation_busy:
            self._cancel_active_operation()
        current_source = self.app_state.current_source
        query = self.app_state.query
        self.app_state = AppState(current_source=current_source, query=query)
        self._operation_busy = False
        self._active_worker = None
        self._render_state()
        prompt = self.query_one("#query-input", Input)
        prompt.value = query
        prompt.focus()

    def _set_compact(self, is_compact: bool) -> None:
        self.screen.set_class(is_compact, "compact")
