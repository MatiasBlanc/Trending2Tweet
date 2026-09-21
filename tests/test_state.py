"""Pruebas de transiciones del estado central."""

import pytest

from src.core.models import Candidate, GenerationResult, PipelineEvent
from src.tui.state import AppState


def _candidate() -> Candidate:
    return Candidate(
        item_id="gh_1",
        title="owner/project",
        description="Una herramienta para developers",
        url="https://github.com/owner/project",
        metadata="1.2k stars · Python",
        data={"id": "gh_1"},
    )


def test_state_moves_from_prompt_to_generated_post() -> None:
    state = AppState()
    state.start("Busca herramientas de Python")
    assert state.stage == "running"
    assert list(state.pipeline) == ["search", "rank", "analyze", "write"]

    candidate = _candidate()
    state.apply_event(
        PipelineEvent("rank", "Seleccionado: owner/project", "success", candidate)
    )
    assert state.selected_candidate == candidate

    result = GenerationResult("github", state.query, candidate, "Post listo", None, ["Post listo"])
    state.complete(result)
    assert state.stage == "complete"
    assert state.current_post == "Post listo"


def test_state_rejects_empty_prompt_and_invalid_variant() -> None:
    state = AppState()
    with pytest.raises(ValueError, match="Escribe"):
        state.start("   ")

    state.generated_posts = ["Original"]
    with pytest.raises(IndexError):
        state.select_variant(2)


def test_variants_are_unique() -> None:
    state = AppState(generated_posts=["Original"])
    state.add_variants(["Breve", "Original", "Con postura"])
    assert state.generated_posts == ["Original", "Breve", "Con postura"]
    assert state.select_variant(2) == "Con postura"


def test_state_fail_stores_title_and_message_and_resets_on_start() -> None:
    state = AppState()
    state.fail("Error de conexión", title="× Error en IA")
    assert state.stage == "error"
    assert state.error == "Error de conexión"
    assert state.error_title == "× Error en IA"

    state.start("Nueva búsqueda")
    assert state.stage == "running"
    assert state.error is None
    assert state.error_title is None


def test_candidate_confirmation_and_cycling() -> None:
    c1 = Candidate(item_id="1", title="Repo One", description="Desc 1", url="", metadata="1k", data={})
    c2 = Candidate(item_id="2", title="Repo Two", description="Desc 2", url="", metadata="2k", data={})
    c3 = Candidate(item_id="3", title="Repo Three", description="Desc 3", url="", metadata="3k", data={})

    state = AppState()
    state.start("Python")
    assert state.stage == "running"

    state.set_candidates([c1, c2, c3])
    assert state.stage == "confirm"
    assert state.candidate_index == 0
    assert state.selected_candidate == c1
    assert "Seleccionado: Repo One" in state.pipeline["rank"].label

    # Next candidate
    next_c = state.next_candidate()
    assert next_c == c2
    assert state.candidate_index == 1
    assert state.selected_candidate == c2
    assert "Seleccionado: Repo Two" in state.pipeline["rank"].label

    # Next candidate again
    state.next_candidate()
    assert state.candidate_index == 2
    assert state.selected_candidate == c3

    # Wraps around
    state.next_candidate()
    assert state.candidate_index == 0
    assert state.selected_candidate == c1

    # Previous candidate wraps around backwards
    state.previous_candidate()
    assert state.candidate_index == 2
    assert state.selected_candidate == c3

    # Confirm candidate
    confirmed = state.confirm_candidate()
    assert confirmed == c3
    assert state.stage == "running"
