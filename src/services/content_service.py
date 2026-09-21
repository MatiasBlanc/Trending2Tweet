"""Orquestación observable del pipeline de búsqueda y generación."""

import logging
import re
import unicodedata
from collections.abc import Callable
from pathlib import Path

from src.core.models import Candidate, GenerationResult, PipelineEvent
from src.db import is_processed, mark_as_processed
from src.llm_client import generate_tweet
from src.obsidian_vault import actualizar_texto_borrador, guardar_borrador
from src.services.providers import SourceProvider

EventCallback = Callable[[PipelineEvent], None]
CancelCallback = Callable[[], bool]

logger = logging.getLogger(__name__)

_STOP_WORDS = {
    "about", "algo", "busca", "buscar", "convert", "convierte", "de", "del",
    "encuentra", "find", "github", "hacker", "interesting", "interesante", "la",
    "las", "los", "news", "para", "post", "publicar", "que", "reddit", "sobre",
    "something", "tech", "tweet", "today", "una", "un", "hoy",
}

_VARIANT_INSTRUCTIONS = {
    "short": (
        "Crea una versión especialmente breve: conserva el dato y el ángulo central, "
        "elimina cualquier frase prescindible y evita superar 280 caracteres."
    ),
    "opinionated": (
        "Crea una versión con una postura técnica más marcada, sin inventar hechos ni "
        "caer en provocación vacía."
    ),
}


class PipelineCancelled(RuntimeError):
    """Indica que el usuario canceló el pipeline entre dos operaciones."""


class NoCandidatesError(RuntimeError):
    """Indica que una fuente no produjo elementos nuevos utilizables."""


class ContentService:
    """Ejecuta búsqueda, selección, redacción y persistencia sin conocer la UI."""

    def generate(
        self,
        provider: SourceProvider,
        query: str,
        on_event: EventCallback | None = None,
        should_cancel: CancelCallback | None = None,
    ) -> GenerationResult:
        """Ejecuta una generación completa con eventos de progreso reales.

        Args:
            provider: Fuente que se consultará.
            query: Intención editorial escrita por el usuario.
            on_event: Receptor opcional de cambios de etapa.
            should_cancel: Comprobación cooperativa de cancelación.

        find_candidates: Localiza y clasifica candidatos sin generar el post.
        generate_from_item: Redacta y guarda el post para un candidato específico.
        generate: Ejecuta todo el flujo de forma secuencial.

        Returns:
            Resultado generado y guardado como borrador.

        Raises:
            PipelineCancelled: Si se solicita cancelar entre etapas.
            NoCandidatesError: Si no existen elementos nuevos utilizables.
            RuntimeError: Si el borrador no se puede persistir.
            Exception: Si falla la fuente o el proveedor LLM.
        """
        candidates = self.find_candidates(
            provider,
            query,
            on_event=on_event,
            should_cancel=should_cancel,
        )
        top_candidate = candidates[0]
        return self.generate_from_item(
            provider,
            top_candidate,
            query=query,
            on_event=on_event,
            should_cancel=should_cancel,
        )

    def find_candidates(
        self,
        provider: SourceProvider,
        query: str,
        on_event: EventCallback | None = None,
        should_cancel: CancelCallback | None = None,
    ) -> list[Candidate]:
        """Busca y ordena candidatos según la intención editorial.

        Args:
            provider: Adaptador de la fuente elegida.
            query: Intención editorial del usuario.
            on_event: Notificación opcional de eventos del pipeline.
            should_cancel: Verificación opcional de cancelación interactiva.

        Returns:
            Lista de candidatos ordenados por relevancia.

        Raises:
            PipelineCancelled: Si se solicita cancelar.
            NoCandidatesError: Si no hay elementos o ya fueron procesados.
        """
        emit = on_event or (lambda event: None)
        cancelled = should_cancel or (lambda: False)

        self._check_cancelled(cancelled)
        emit(PipelineEvent("search", f"Buscando en {provider.name}", "running"))
        items = provider.search(query)
        emit(
            PipelineEvent(
                "search",
                self._found_label(provider, len(items)),
                "success" if items else "warning",
            )
        )
        if not items:
            raise NoCandidatesError(f"{provider.name} no devolvió resultados.")

        self._check_cancelled(cancelled)
        emit(PipelineEvent("rank", "Seleccionando el mejor hallazgo", "running"))
        available = [item for item in items if not is_processed(provider.get_item_id(item))]
        ranked = self.rank_items(provider, available, query)
        if not ranked:
            emit(PipelineEvent("rank", "No hay hallazgos nuevos", "warning"))
            raise NoCandidatesError(
                f"Los resultados de {provider.name} ya fueron procesados."
            )

        candidates = [provider.to_candidate(item) for item in ranked]
        top_candidate = candidates[0]
        emit(
            PipelineEvent(
                "rank",
                f"Seleccionado: {top_candidate.title}",
                "success",
                candidate=top_candidate,
            )
        )
        return candidates

    def generate_from_item(
        self,
        provider: SourceProvider,
        candidate: Candidate,
        item: dict | None = None,
        query: str = "",
        on_event: EventCallback | None = None,
        should_cancel: CancelCallback | None = None,
    ) -> GenerationResult:
        """Redacta y guarda el post para un candidato confirmado.

        Args:
            provider: Adaptador de la fuente elegida.
            candidate: Hallazgo seleccionado y confirmado por el usuario.
            item: Datos crudos opcionales (por defecto se usa candidate.data).
            query: Intención editorial del usuario.
            on_event: Notificación opcional de eventos del pipeline.
            should_cancel: Verificación opcional de cancelación interactiva.

        Returns:
            Resultado generado y guardado en la bóveda.

        Raises:
            PipelineCancelled: Si se solicita cancelar.
            RuntimeError: Si no se puede guardar el borrador.
        """
        emit = on_event or (lambda event: None)
        cancelled = should_cancel or (lambda: False)

        selected_item = item if item is not None else candidate.data

        self._check_cancelled(cancelled)
        emit(PipelineEvent("analyze", "Preparando contexto", "running"))
        if provider.prepare_item is not None:
            selected_item = provider.prepare_item(selected_item)
            candidate = provider.to_candidate(selected_item)
        user_message = self._build_user_message(provider, selected_item, query)
        emit(PipelineEvent("analyze", "Contexto preparado", "success"))

        self._check_cancelled(cancelled)
        emit(PipelineEvent("write", "Escribiendo el post", "running"))
        variables = provider.get_variables(selected_item) if provider.get_variables else None
        post = generate_tweet(
            provider.prompt_file,
            user_message,
            variables=variables,
        )
        emit(PipelineEvent("write", "Post listo", "success"))

        self._check_cancelled(cancelled)
        filepath = self._save(provider, candidate, post)
        return GenerationResult(
            provider_key=provider.key,
            query=query,
            candidate=candidate,
            post=post,
            filepath=filepath,
            variants=[post],
        )

    def regenerate(
        self,
        provider: SourceProvider,
        result: GenerationResult,
        variant: str = "original",
        on_event: EventCallback | None = None,
    ) -> str:
        """Vuelve a redactar el candidato actual sin repetir la búsqueda.

        Args:
            provider: Fuente original del candidato.
            result: Resultado del que se reutilizarán datos e intención.
            variant: Estilo ``original``, ``short`` u ``opinionated``.
            on_event: Receptor opcional del progreso de redacción.

        Returns:
            Nueva versión del post.

        Raises:
            ValueError: Si el estilo solicitado no existe.
            Exception: Si falla el proveedor LLM.
        """
        if variant not in ("original", *_VARIANT_INSTRUCTIONS):
            raise ValueError(f"Variante desconocida: {variant}")

        emit = on_event or (lambda event: None)
        emit(PipelineEvent("write", "Escribiendo una nueva versión", "running"))
        item = result.candidate.data
        variables = provider.get_variables(item) if provider.get_variables else None
        post = generate_tweet(
            provider.prompt_file,
            self._build_user_message(provider, item, result.query),
            variables=variables,
            additional_instructions=_VARIANT_INSTRUCTIONS.get(variant),
        )
        emit(PipelineEvent("write", "Nueva versión lista", "success"))
        return post

    def save_post(self, result: GenerationResult, post: str) -> None:
        """Actualiza el borrador persistido con el texto elegido o editado.

        Args:
            result: Resultado que contiene la ruta del borrador.
            post: Texto que reemplazará el contenido actual.

        Raises:
            ValueError: Si el texto está vacío o no existe un borrador asociado.
            RuntimeError: Si el archivo no se puede actualizar de forma segura.
        """
        if not post.strip():
            raise ValueError("El post no puede quedar vacío.")
        if result.filepath is None:
            raise ValueError("No existe un borrador asociado al resultado.")
        if not actualizar_texto_borrador(str(result.filepath), post.strip()):
            raise RuntimeError("No se pudo actualizar el borrador en Obsidian.")
        result.post = post.strip()

    @staticmethod
    def rank_items(
        provider: SourceProvider,
        items: list[dict],
        query: str,
    ) -> list[dict]:
        """Ordena candidatos por afinidad textual sin alterar el ranking original.

        Las palabras genéricas del prompt inicial se ignoran. Si no hay términos
        temáticos, se conserva exactamente el orden entregado por la fuente.

        Args:
            provider: Proveedor capaz de extraer título y descripción.
            items: Resultados utilizables de la fuente.
            query: Intención del usuario.

        Returns:
            Nueva lista ordenada por coincidencias y posición original.
        """
        terms = _query_terms(query)
        if not terms:
            return list(items)

        def relevance(indexed_item: tuple[int, dict]) -> tuple[int, int]:
            index, item = indexed_item
            searchable = _normalize(
                f"{provider.get_title(item)} {provider.get_description(item)}"
            )
            score = sum(1 for term in terms if term in searchable)
            return (-score, index)

        return [item for _, item in sorted(enumerate(items), key=relevance)]

    @staticmethod
    def _check_cancelled(should_cancel: CancelCallback) -> None:
        if should_cancel():
            raise PipelineCancelled("Operación cancelada.")

    @staticmethod
    def _build_user_message(
        provider: SourceProvider,
        item: dict,
        query: str,
    ) -> str:
        message = provider.format_user_message(item)
        if query.strip():
            message += f"\n\nIntención editorial del usuario: {query.strip()}"
        return message

    @staticmethod
    def _found_label(provider: SourceProvider, count: int) -> str:
        noun = {
            "github": "repositorios",
            "reddit": "publicaciones",
            "hacker_news": "historias",
            "code": "historias",
        }.get(provider.key, "resultados")
        return f"{count} {noun} encontrados"

    @staticmethod
    def _save(
        provider: SourceProvider,
        candidate: Candidate,
        post: str,
    ) -> Path:
        metadata = (
            provider.get_draft_metadata(candidate.data)
            if provider.get_draft_metadata
            else {}
        )
        filepath = guardar_borrador(
            texto=post,
            categoria=provider.category,
            source=provider.draft_source,
            titulo=candidate.title,
            url=candidate.url,
            repo_name=metadata.get("repo_name"),
            repo_stars=metadata.get("repo_stars"),
            item_id=candidate.item_id,
            prompt_file=provider.prompt_file,
            template_estilo=metadata.get("template_estilo"),
            notas=metadata.get("notas"),
        )
        if not filepath:
            raise RuntimeError("No se pudo guardar el borrador en Obsidian.")
        mark_as_processed(
            candidate.item_id,
            provider.draft_source,
            texto=post[:100],
        )
        logger.info("Borrador generado: %s", filepath)
        return Path(filepath)


def character_count(text: str) -> int:
    """Cuenta caracteres de un post tal como se muestran al usuario.

    Args:
        text: Contenido completo del post.

    Returns:
        Número de puntos de código de Python, incluyendo saltos de línea.
    """
    return len(text)


def _query_terms(query: str) -> tuple[str, ...]:
    words = re.findall(r"[a-z0-9]+", _normalize(query))
    terms = [
        word
        for word in words
        if (len(word) > 2 or word in {"ai", "ia", "go", "ml"})
        and word not in _STOP_WORDS
    ]
    if "ia" in terms and "ai" not in terms:
        terms.append("ai")
    if "ai" in terms and "ia" not in terms:
        terms.append("ia")
    return tuple(terms)


def _normalize(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text.lower())
    return "".join(char for char in decomposed if not unicodedata.combining(char))
