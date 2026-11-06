"""Importer contracts: malformed logs exit 2 with a message. Missing optional fields still import.

These are not coverage fillers. Before this file, unknown dialects, bad JSON, a missing file,
a non-object trace item, a non-integer rep, and a missing file: module raised KeyError,
JSONDecodeError, FileNotFoundError, AttributeError, or ValueError.
"""

from __future__ import annotations

import json
from pathlib import Path

from agentest.cli import main
from agentest.standards import importers

EVENTS = {"dialect": "events"}


def _log(tmp_path: Path, text: str, name: str = "log.jsonl") -> Path:
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return p


def test_import_cli_requires_a_file_and_a_dialect(capsys):
    assert main(["std", "import"]) == 2
    assert "native log files" in capsys.readouterr().out
    assert main(["std", "import", "missing.jsonl"]) == 2
    assert "dialect" in capsys.readouterr().out


def test_import_cli_rejects_malformed_inputs(tmp_path, capsys):
    bad = _log(tmp_path, "{not json\n")
    assert main(["std", "import", str(bad), "--dialect", "events", "--out", str(tmp_path / "o.jsonl")]) == 2
    assert "not valid JSON" in capsys.readouterr().out

    missing = tmp_path / "no-such.jsonl"
    assert main(["std", "import", str(missing), "--dialect", "events"]) == 2
    assert "not found" in capsys.readouterr().out

    weird = _log(tmp_path, json.dumps({"probe": "p", "trace": ["nope"]}) + "\n", "item.jsonl")
    assert main(["std", "import", str(weird), "--dialect", "events"]) == 2
    assert "trace items must be JSON objects" in capsys.readouterr().out

    rep = _log(tmp_path, json.dumps({"probe": "p", "rep": "nope", "trace": []}) + "\n", "rep.jsonl")
    assert main(["std", "import", str(rep), "--dialect", "events"]) == 2
    assert "rep must be an integer" in capsys.readouterr().out

    ok = _log(tmp_path, json.dumps({"probe": "p", "input": "hi", "trace": []}) + "\n", "ok.jsonl")
    assert main(["std", "import", str(ok), "--dialect", "nope"]) == 2
    err = capsys.readouterr().out
    assert "unknown dialect" in err and "nope" in err

    gone = tmp_path / "map.json"
    assert main(["std", "import", str(bad), "--map", str(gone)]) == 2
    assert "not found" in capsys.readouterr().out


def test_missing_optional_fields_still_import():
    bare = importers.adapt({"probe": "p", "input": "hi"}, EVENTS)
    assert [m.role for m in bare.messages] == ["user"] and bare.tool_calls == []
    call = importers.adapt(
        {"probe": "p", "trace": [{"kind": "tool", "name": "lookup", "data": {"args": {"id": "R-1"}}}]},
        EVENTS,
    )
    assert call.tool_calls[0].name == "lookup"
    assert call.tool_calls[0].result is None and call.tool_calls[0].error is False
    failed = importers.adapt(
        {"probe": "p", "trace": [{"kind": "tool", "name": "lookup", "data": {"result": {"error": "missing"}}}]},
        EVENTS,
    )
    assert failed.tool_calls[0].error is True


def test_mapping_module_must_exist_and_define_to_trace(tmp_path):
    try:
        importers.adapt({"probe": "p", "trace": []}, {"dialect": "file:missing_map.py"}, base=tmp_path)
    except importers.NativeLogError as e:
        assert "not found" in str(e)
    else:
        raise AssertionError("missing mapping module did not fail")
    mod = tmp_path / "empty_map.py"
    mod.write_text("x = 1\n", encoding="utf-8")
    try:
        importers.adapt({"probe": "p", "trace": []}, {"dialect": "file:empty_map.py"}, base=tmp_path)
    except importers.NativeLogError as e:
        assert "to_trace" in str(e)
    else:
        raise AssertionError("mapping module without to_trace did not fail")
