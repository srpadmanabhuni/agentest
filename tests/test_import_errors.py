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


def test_refill_string_steps_import_on_the_cli(tmp_path):
    """The refill log's trace is a list of strings. file: adapters must still import it."""
    demo = Path(__file__).resolve().parents[1] / "examples" / "agnostic_demo"
    out = tmp_path / "refill.otlp.jsonl"
    rc = main(["std", "import", str(demo / "native" / "refill_bot.jsonl"),
               "--map", str(demo / "import" / "map.json"),
               "--tools", str(demo / "agents" / "refill_bot" / "tools.json"),
               "--service", "refill_bot", "--out", str(out)])
    assert rc == 0
    assert "verify_identity" in out.read_text(encoding="utf-8")


def test_file_adapter_is_executed_not_sandboxed():
    """A file: adapter is imported and run in this process. The contract does not claim a sandbox."""
    import inspect

    from agentest.standards.importers import _plugin

    doc = inspect.getdoc(_plugin)
    assert "imported and executed" in doc
    assert "not a sandbox" in doc


def test_file_adapter_errors_on_the_cli(tmp_path, capsys):
    """file: modules are loaded and executed here; a missing module or a missing to_trace exits 2."""
    log = _log(tmp_path, json.dumps({"probe": "p", "input": "hi", "trace": []}) + "\n")
    missing = tmp_path / "map_missing.json"
    missing.write_text(json.dumps({"dialect": "file:missing_map.py"}), encoding="utf-8")
    assert main(["std", "import", str(log), "--map", str(missing)]) == 2
    assert "not found" in capsys.readouterr().out
    (tmp_path / "empty_map.py").write_text("x = 1\n", encoding="utf-8")
    empty = tmp_path / "map_empty.json"
    empty.write_text(json.dumps({"dialect": "file:empty_map.py"}), encoding="utf-8")
    assert main(["std", "import", str(log), "--map", str(empty)]) == 2
    assert "to_trace" in capsys.readouterr().out


def test_file_adapter_runtime_error_is_not_masked(tmp_path):
    (tmp_path / "boom.py").write_text("def to_trace(raw, ep):\n    raise RuntimeError('adapter blew up')\n", encoding="utf-8")
    mapping = tmp_path / "map_boom.json"
    mapping.write_text(json.dumps({"dialect": "file:boom.py"}), encoding="utf-8")
    log = _log(tmp_path, json.dumps({"probe": "p", "input": "hi", "trace": []}) + "\n", "boom.jsonl")
    try:
        main(["std", "import", str(log), "--map", str(mapping)])
    except RuntimeError as e:
        assert "adapter blew up" in str(e)
    else:
        raise AssertionError("adapter RuntimeError was masked")


def test_tools_file_errors_on_the_cli(tmp_path, capsys):
    log = _log(tmp_path, json.dumps({"probe": "p", "input": "hi", "trace": []}) + "\n", "tools-log.jsonl")
    missing = tmp_path / "no-tools.json"
    assert main(["std", "import", str(log), "--dialect", "events", "--tools", str(missing)]) == 2
    assert "not found" in capsys.readouterr().out
    bad = tmp_path / "bad-tools.json"
    bad.write_text("{no\n", encoding="utf-8")
    assert main(["std", "import", str(log), "--dialect", "events", "--tools", str(bad)]) == 2
    assert "not valid JSON" in capsys.readouterr().out
    listed = tmp_path / "list-tools.json"
    listed.write_text("[]", encoding="utf-8")
    assert main(["std", "import", str(log), "--dialect", "events", "--tools", str(listed)]) == 2
    assert "tools array" in capsys.readouterr().out
    unnamed = tmp_path / "unnamed-tools.json"
    unnamed.write_text(json.dumps({"tools": ["lookup"]}), encoding="utf-8")
    assert main(["std", "import", str(log), "--dialect", "events", "--tools", str(unnamed)]) == 2
    assert "object with a name" in capsys.readouterr().out


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
