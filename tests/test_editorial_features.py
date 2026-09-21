"""Pruebas de las heurísticas editoriales sin llamadas externas."""

from datetime import datetime, timezone
from pathlib import Path

from src.few_shot import build_few_shot_block, load_examples
from sources.github_client import is_signal_repo


def test_few_shot_catalog_is_selected_by_prompt_category() -> None:
    block = build_few_shot_block("prompts/prompt_github.txt")
    assert "EJEMPLOS CURADOS DE ESTILO" in block
    assert "github_dolor_arquitectura" in block
    assert "news_contraste" not in block


def test_few_shot_catalog_accepts_a_local_override(tmp_path: Path) -> None:
    catalog = tmp_path / "examples.json"
    catalog.write_text(
        '[{"id":"local","category":"github","context":"dolor",'
        '"output":"gancho"}]',
        encoding="utf-8",
    )
    examples = load_examples(category="github", path=catalog, limit=1)
    assert [example.identifier for example in examples] == ["local"]


def test_github_signal_filter_rejects_noise_and_inflated_ratio() -> None:
    base = {
        "description": "CLI para equipos de desarrollo",
        "language": "Python",
        "pushed_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }
    assert is_signal_repo({**base, "stars": 100, "forks": 10})
    assert not is_signal_repo({**base, "description": "wallpaper collection", "stars": 100, "forks": 10})
    assert not is_signal_repo({**base, "stars": 5_000, "forks": 1})
