"""``agentest std run --otlp`` reports a bad path or bad JSON and exits 2.

A missing file used to raise FileNotFoundError, a directory IsADirectoryError, and
invalid JSON JSONDecodeError. read_otlp_file itself still raises JSONDecodeError;
only the CLI turns that into exit 2 for this command.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agentest.cli import main
from agentest.standards.otel import read_otlp_file

FIX = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "otlp"
TRACE = FIX / "ticket_current.otlp.json"


def test_missing_otlp_path_exits_2(tmp_path, capsys):
    missing = tmp_path / "no-such.otlp.jsonl"
    assert main(["std", "run", "--otlp", str(missing)]) == 2
    err = capsys.readouterr()
    assert "is not a file" in err.out
    assert "Traceback" not in err.out and "Traceback" not in err.err


def test_otlp_directory_exits_2(tmp_path, capsys):
    assert main(["std", "run", "--otlp", str(tmp_path)]) == 2
    assert "is not a file" in capsys.readouterr().out


def test_missing_card_and_tools_exit_2(tmp_path, capsys):
    assert main(["std", "run", "--otlp", str(TRACE), "--card", str(tmp_path / "no-card.json")]) == 2
    assert "no-card.json" in capsys.readouterr().out
    assert main(["std", "run", "--otlp", str(TRACE), "--tools", str(tmp_path / "no-tools.json")]) == 2
    assert "no-tools.json" in capsys.readouterr().out


def test_invalid_otlp_json_exits_2(tmp_path, capsys):
    bad = tmp_path / "bad.otlp.json"
    bad.write_text("{no\n", encoding="utf-8")
    assert main(["std", "run", "--otlp", str(bad)]) == 2
    assert "not valid JSON" in capsys.readouterr().out


def test_invalid_card_and_tools_json_exit_2(tmp_path, capsys):
    bad = tmp_path / "bad.json"
    bad.write_text("{no\n", encoding="utf-8")
    assert main(["std", "run", "--otlp", str(TRACE), "--card", str(bad)]) == 2
    assert "not valid JSON" in capsys.readouterr().out
    assert main(["std", "run", "--otlp", str(TRACE), "--tools", str(bad)]) == 2
    assert "not valid JSON" in capsys.readouterr().out


def test_valid_otlp_json_still_runs(capsys):
    assert main(["std", "run", "--otlp", str(TRACE), "--ids", "T2-001", "--format", "md"]) == 0
    out = capsys.readouterr().out
    assert "T2-001" in out
    assert "Traceback" not in out


def test_reader_still_raises_json_decode_error(tmp_path):
    bad = tmp_path / "bad.otlp.json"
    bad.write_text("{no\n", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        read_otlp_file(bad)
