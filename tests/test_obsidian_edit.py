"""Pruebas de persistencia para la edición integrada."""

from pathlib import Path

import pytest

from src import config
from src.obsidian_vault import actualizar_texto_borrador


def test_update_draft_replaces_post_and_character_count(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    vault = tmp_path / "bot"
    category = vault / "github"
    category.mkdir(parents=True)
    draft = category / "draft.md"
    draft.write_text(
        "---\nstatus: draft\n---\n\n"
        "## Tweet\n\nTexto anterior\n\n"
        "## Metadata\n\n- **Caracteres**: 14\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(config, "OBSIDIAN_VAULT_PATH", str(vault))
    monkeypatch.setattr(config, "TWITTER_VAULT_PATH", str(vault))

    assert actualizar_texto_borrador(str(draft), "Nuevo\npost")
    content = draft.read_text(encoding="utf-8")
    assert "## Tweet\n\nNuevo\npost\n\n## Metadata" in content
    assert "- **Caracteres**: 10" in content


def test_update_draft_rejects_paths_outside_vault(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    vault = tmp_path / "bot"
    vault.mkdir()
    outside = tmp_path / "outside.md"
    outside.write_text("## Tweet\n\nNo tocar", encoding="utf-8")
    monkeypatch.setattr(config, "OBSIDIAN_VAULT_PATH", str(vault))
    monkeypatch.setattr(config, "TWITTER_VAULT_PATH", str(vault))

    assert not actualizar_texto_borrador(str(outside), "Cambio")
    assert "No tocar" in outside.read_text(encoding="utf-8")
