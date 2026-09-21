"""Contratos de dominio para el pipeline de generación de contenido."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

PipelineStatus = Literal["pending", "running", "success", "warning", "error"]


@dataclass(frozen=True)
class Candidate:
    """Elemento normalizado encontrado por un proveedor.

    Attributes:
        item_id: Identificador estable de la fuente.
        title: Nombre o titular visible.
        description: Resumen breve del elemento.
        url: URL original, cuando existe.
        metadata: Métricas secundarias listas para presentar.
        data: Respuesta normalizada que consume el generador existente.
    """

    item_id: str
    title: str
    description: str
    url: str
    metadata: str
    data: dict[str, Any] = field(compare=False, repr=False)


@dataclass(frozen=True)
class PipelineEvent:
    """Cambio semántico de una etapa del pipeline.

    Attributes:
        step: Identificador estable de la etapa.
        label: Texto breve orientado al usuario.
        status: Estado visual de la etapa.
        candidate: Hallazgo seleccionado cuando la etapa lo produce.
    """

    step: str
    label: str
    status: PipelineStatus
    candidate: Candidate | None = None


@dataclass
class GenerationResult:
    """Resultado reutilizable de una ejecución completa.

    Attributes:
        provider_key: Proveedor que originó el resultado.
        query: Intención escrita por el usuario.
        candidate: Elemento seleccionado para redactar.
        post: Texto principal generado.
        filepath: Borrador persistido en Obsidian.
        variants: Versiones alternativas disponibles.
    """

    provider_key: str
    query: str
    candidate: Candidate
    post: str
    filepath: Path | None
    variants: list[str] = field(default_factory=list)
