"""Carga ejemplos editoriales locales para guiar la redacción del LLM.

Los ejemplos son una referencia de estilo, no una fuente factual. Se mantienen
fuera del código para que puedan reemplazarse por muestras verificadas de la
cuenta sin añadir otra dependencia o servicio.
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src import config


@dataclass(frozen=True)
class FewShotExample:
    """Ejemplo curado de entrada y salida para una categoría editorial."""

    identifier: str
    category: str
    context: str
    output: str
    editorial_note: str = ""


def _category_from_prompt(prompt_file: str) -> str | None:
    """Obtiene una categoría aproximada a partir del nombre del prompt."""
    stem = Path(prompt_file).stem.removeprefix("prompt_").lower()
    aliases = {
        "github": "github",
        "news": "news",
        "codigo": "codigo",
        "teclados": "teclado",
        "mejorar_tweet": "general",
    }
    return aliases.get(stem, stem or None)


def _parse_example(raw: Any, index: int) -> FewShotExample | None:
    """Valida una entrada externa sin permitir que un JSON mal formado detenga el bot."""
    if not isinstance(raw, dict):
        return None
    required = ("context", "output")
    if any(not isinstance(raw.get(key), str) or not raw[key].strip() for key in required):
        return None
    category = raw.get("category", "general")
    if not isinstance(category, str):
        category = "general"
    identifier = raw.get("id", f"example_{index}")
    if not isinstance(identifier, str) or not identifier.strip():
        identifier = f"example_{index}"
    note = raw.get("editorial_note", "")
    if not isinstance(note, str):
        note = ""
    return FewShotExample(
        identifier=identifier.strip(),
        category=category.strip().lower(),
        context=raw["context"].strip(),
        output=raw["output"].strip(),
        editorial_note=note.strip(),
    )


def load_examples(
    category: str | None = None,
    path: str | Path | None = None,
    limit: int | None = None,
) -> list[FewShotExample]:
    """Carga ejemplos curados compatibles con una categoría.

    Args:
        category: Categoría del prompt; ``general`` siempre es compatible.
        path: Catálogo alternativo, útil para una voz editorial propia.
        limit: Máximo de ejemplos a devolver.

    Returns:
        Ejemplos válidos. Si el catálogo no existe o no es válido, devuelve una
        lista vacía para que la generación normal siga funcionando.
    """
    examples_path = Path(path or config.FEW_SHOT_EXAMPLES_PATH).expanduser()
    try:
        raw_catalog = json.loads(examples_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []

    if isinstance(raw_catalog, dict):
        raw_catalog = raw_catalog.get("examples", [])
    if not isinstance(raw_catalog, list):
        return []

    requested = (category or "").strip().lower()
    parsed: list[FewShotExample] = []
    for index, raw in enumerate(raw_catalog, start=1):
        example = _parse_example(raw, index)
        if example is None:
            continue
        if requested and example.category not in (requested, "general"):
            continue
        parsed.append(example)

    safe_limit = config.FEW_SHOT_MAX_EXAMPLES if limit is None else max(limit, 0)
    return parsed[:safe_limit]


def build_few_shot_block(prompt_file: str) -> str:
    """Construye el bloque de demostraciones que se añade al prompt de salida."""
    if not config.FEW_SHOT_ENABLED:
        return ""

    category = _category_from_prompt(prompt_file)
    examples = load_examples(category=category)
    if not examples:
        return ""

    lines = [
        "\nEJEMPLOS CURADOS DE ESTILO (no copies sus hechos ni su texto):",
        "Usa estas muestras para mejorar el gancho, la densidad técnica y la estructura.",
    ]
    for number, example in enumerate(examples, start=1):
        lines.append(f"\nMuestra {number} — {example.identifier}")
        lines.append(f"Entrada de referencia: {example.context}")
        lines.append(f"Salida de referencia: {example.output}")
        if example.editorial_note:
            lines.append(f"Decisión editorial: {example.editorial_note}")
    lines.append(
        "No menciones estas muestras, no inventes datos para imitarlas y no las trates "
        "como información sobre el tema actual."
    )
    return "\n".join(lines)
