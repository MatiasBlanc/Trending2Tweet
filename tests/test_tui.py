"""Pruebas de humo para la jerarquía visual de Textual."""

from pathlib import Path

import pytest
from textual.widgets import Input

from src.core.models import Candidate, GenerationResult
from src.tui.app import TrendingToTweetApp
from src.tui.widgets import PostWidget


@pytest.mark.asyncio
async def test_initial_screen_focuses_prompt_and_supports_compact_mode() -> None:
    app = TrendingToTweetApp(presentation=True)
    async with app.run_test(size=(80, 24)) as pilot:
        await pilot.pause()
        assert app.app_state.stage == "idle"
        assert isinstance(app.focused, Input)
        assert app.screen.has_class("presentation")
        assert app.screen.has_class("compact")
        assert app.query_one("#idle-view").display
        assert not app.query_one("#complete-view").display


@pytest.mark.asyncio
async def test_completed_flow_makes_post_the_main_view(tmp_path: Path) -> None:
    candidate = Candidate(
        item_id="1",
        title="owner/project",
        description="Descripción",
        url="https://example.com",
        metadata="10 stars",
        data={"id": "1"},
    )
    result = GenerationResult(
        provider_key="github",
        query="Python",
        candidate=candidate,
        post="Post generado",
        filepath=tmp_path / "post.md",
        variants=["Post generado"],
    )
    app = TrendingToTweetApp()
    async with app.run_test(size=(100, 30)) as pilot:
        app._finish_generation(result)
        await pilot.pause()
        assert not app.query_one("#idle-view").display
        assert app.query_one("#complete-view").display
        post_widget = app.query_one("#post", PostWidget)
        assert post_widget._post == "Post generado"

        await pilot.press("e")
        assert post_widget.is_editing
        await pilot.press("escape")
        assert not post_widget.is_editing


@pytest.mark.asyncio
async def test_error_flow_displays_contextual_title_and_message() -> None:
    app = TrendingToTweetApp()
    async with app.run_test(size=(100, 30)) as pilot:
        app.app_state.current_source = "github"
        app._operation_id = 1
        app._finish_error(Exception("Incorrect API key provided"), 1)
        await pilot.pause()
        assert not app.query_one("#idle-view").display
        assert app.query_one("#error-view").display
        assert "autenticación" in str(app.query_one("#error-title").render())
        assert "AZURE_API_KEY" in str(app.query_one("#error-message").render())


@pytest.mark.asyncio
async def test_source_navigation_with_keys_in_idle() -> None:
    app = TrendingToTweetApp()
    async with app.run_test(size=(100, 30)) as pilot:
        assert app.app_state.current_source == "github"
        await pilot.press("down")
        assert app.app_state.current_source != "github"
        second_source = app.app_state.current_source
        badge = app.query_one("#source-badge")
        assert badge._current_key == second_source
        await pilot.press("up")
        assert app.app_state.current_source == "github"
        assert badge._current_key == "github"
        await pilot.press("tab")
        assert app.app_state.current_source == second_source
        assert badge._current_key == second_source


@pytest.mark.asyncio
async def test_confirmation_stage_and_candidate_cycling() -> None:
    c1 = Candidate(item_id="1", title="pallets/flask", description="Web framework", url="", metadata="60k stars", data={})
    c2 = Candidate(item_id="2", title="tiangolo/fastapi", description="FastAPI framework", url="", metadata="70k stars", data={})

    app = TrendingToTweetApp()
    async with app.run_test(size=(100, 30)) as pilot:
        app.app_state.start("python")
        app._finish_search([c1, c2], app._operation_id)
        await pilot.pause()

        assert app.app_state.stage == "confirm"
        assert app.query_one("#running-view").display
        candidate_widget = app.query_one("#candidate")
        assert "¿Quieres usar este repositorio para redactar el post?" in str(candidate_widget.render())
        assert "pallets/flask" in str(candidate_widget.render())

        # Press N to cycle candidate
        await pilot.press("n")
        assert app.app_state.candidate_index == 1
        assert app.app_state.selected_candidate == c2
        assert "tiangolo/fastapi" in str(candidate_widget.render())

        # Press P to go back
        await pilot.press("p")
        assert app.app_state.candidate_index == 0
        assert app.app_state.selected_candidate == c1

        # Press Esc to cancel
        await pilot.press("escape")
        assert app.app_state.stage == "idle"
        assert app.query_one("#idle-view").display


@pytest.mark.asyncio
async def test_confirm_candidate_action_starts_generation(monkeypatch: pytest.MonkeyPatch) -> None:
    c1 = Candidate(item_id="1", title="pallets/flask", description="Web framework", url="", metadata="60k stars", data={})
    app = TrendingToTweetApp()
    called = []
    monkeypatch.setattr(app, "run_worker", lambda *args, **kwargs: called.append(kwargs.get("name")))

    async with app.run_test(size=(100, 30)) as pilot:
        app.app_state.start("python")
        app._finish_search([c1], app._operation_id)
        await pilot.pause()
        assert app.app_state.stage == "confirm"

        await pilot.press("enter")
        assert app.app_state.stage == "running"
        assert "generar-post" in called


def test_app_callbacks_signature_validity() -> None:
    import inspect
    sig = inspect.signature(TrendingToTweetApp._finish_search)
    assert "candidates" in sig.parameters
