"""The CLI must not crash on a console whose codec cannot encode catalogue text (default Windows cp1252)."""
import io
import sys

from agentest import cli


def test_list_survives_a_cp1252_console(monkeypatch):
    raw = io.BytesIO()
    console = io.TextIOWrapper(raw, encoding="cp1252", errors="strict")
    monkeypatch.setattr(sys, "stdout", console)
    assert cli.main(["list"]) == 0
    console.flush()
    assert raw.getvalue()


def test_unencodable_character_is_replaced_not_raised(monkeypatch):
    raw = io.BytesIO()
    console = io.TextIOWrapper(raw, encoding="cp1252", errors="strict")
    monkeypatch.setattr(sys, "stdout", console)
    cli._tolerate_unencodable_output()
    print("goal \u2192 same state")
    console.flush()
    assert raw.getvalue().startswith(b"goal ")
