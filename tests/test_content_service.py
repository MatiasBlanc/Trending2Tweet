"""Pruebas del pipeline desacoplado de red, LLM y bóveda."""

from pathlib import Path

import pytest

from src.services import content_service
from src.services.content_service import (
    ContentService,
    NoCandidatesError,
    character_count,
)
from src.services.providers import SourceProvider


def _provider(items: list[dict]) -> SourceProvider:
    return SourceProvider(
        key="test",
        name="Test",
        icon="●",
        category="news",
        draft_source="test_bot",
        prompt_file="prompts/test.txt",
        fetch_items=lambda: items,
        format_user_message=lambda item: f"Título: {item['title']}",
        get_item_id=lambda item: item["id"],
        get_title=lambda item: item["title"],
        get_url=lambda item: item.get("url", ""),
        get_description=lambda item: item["description"],
        get_metadata_label=lambda item: f"{item['score']} puntos",
    )


def test_pipeline_emits_real_transitions_and_ranks_by_query(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    items = [
        {"id": "1", "title": "Rust release", "description": "Compiler", "score": 20},
        {"id": "2", "title": "Python tool", "description": "Developer CLI", "score": 10},
    ]
    events = []
    marked = []
    draft = tmp_path / "draft.md"

    monkeypatch.setattr(content_service, "is_processed", lambda item_id: False)
    monkeypatch.setattr(content_service, "generate_tweet", lambda *args, **kwargs: "Tweet generado")
    monkeypatch.setattr(content_service, "guardar_borrador", lambda **kwargs: str(draft))
    monkeypatch.setattr(
        content_service,
        "mark_as_processed",
        lambda item_id, source, texto: marked.append((item_id, source, texto)),
    )

    result = ContentService().generate(
        _provider(items),
        "Quiero publicar sobre Python",
        on_event=events.append,
    )

    assert result.candidate.item_id == "2"
    assert result.post == "Tweet generado"
    assert result.filepath == draft
    assert marked == [("2", "test_bot", "Tweet generado")]
    assert [(event.step, event.status) for event in events] == [
        ("search", "running"),
        ("search", "success"),
        ("rank", "running"),
        ("rank", "success"),
        ("analyze", "running"),
        ("analyze", "success"),
        ("write", "running"),
        ("write", "success"),
    ]


def test_pipeline_reports_empty_source() -> None:
    events = []
    with pytest.raises(NoCandidatesError, match="no devolvió"):
        ContentService().generate(_provider([]), "tema", on_event=events.append)
    assert events[-1].status == "warning"


def test_character_counter_includes_line_breaks() -> None:
    assert character_count("Hola\nmundo") == 10


def test_find_candidates_returns_ranked_list_and_generate_from_item(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    items = [
        {"id": "1", "title": "Rust release", "description": "Compiler", "score": 20},
        {"id": "2", "title": "Python tool", "description": "Developer CLI", "score": 10},
    ]
    events = []
    draft = tmp_path / "draft2.md"

    monkeypatch.setattr(content_service, "is_processed", lambda item_id: False)
    monkeypatch.setattr(content_service, "generate_tweet", lambda *args, **kwargs: "Tweet específico")
    monkeypatch.setattr(content_service, "guardar_borrador", lambda **kwargs: str(draft))
    monkeypatch.setattr(content_service, "mark_as_processed", lambda *args, **kwargs: None)

    service = ContentService()
    candidates = service.find_candidates(_provider(items), "Python", on_event=events.append)
    assert len(candidates) == 2
    assert candidates[0].item_id == "2"
    assert candidates[1].item_id == "1"

    # User chooses candidates[1] (Rust release) instead of candidates[0]
    result = service.generate_from_item(
        _provider(items),
        candidates[1],
        query="Python",
        on_event=events.append,
    )
    assert result.candidate.item_id == "1"
    assert result.candidate.title == "Rust release"
    assert result.post == "Tweet específico"
    assert result.filepath == draft
