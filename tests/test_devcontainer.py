"""The devcontainer opens a working checkout: Python 3.12, an editable install with the dev extra, no new runtime dependency."""
import json
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_devcontainer_installs_the_project_with_pytest():
    cfg = json.loads((ROOT / ".devcontainer" / "devcontainer.json").read_text(encoding="utf-8"))
    assert "python:3.12" in cfg["image"] or "python:1-3.12" in cfg["image"]
    assert 'pip install -e ".[dev]"' == cfg["postCreateCommand"]
    dev = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]["optional-dependencies"]["dev"]
    assert any(d.startswith("pytest") for d in dev)  # `pytest` works right after the editable install


def test_contributing_mentions_the_devcontainer_and_response_promise():
    text = (ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8")
    assert ".devcontainer/devcontainer.json" in text
    assert "First response within 24 hours" in text and "Review within 48 hours" in text
