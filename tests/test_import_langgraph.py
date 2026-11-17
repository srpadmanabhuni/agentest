"""Connector group: LangChain / LangGraph message lists (``langgraph_msgs``), imported in the trace format 1.0.0.

The bundled example log is imported with the run-level attributes. The output validates against the schema, keeps
every span unchanged, and gets the same verdicts on all default checks as the committed example traces."""

from __future__ import annotations

import json
import subprocess
import sys

from agentest.standards import metadata
from agentest.standards.importers import _unix_nano, is_write_from_tools, read_native, source_attrs, to_docs
from tests.connector_roundtrip import ROOT, check, resource, verdicts

EX = ROOT / "examples" / "langgraph_import"
NATIVE, MAP = EX / "native" / "expense_bot.jsonl", EX / "import" / "map.json"
AGENT_DIR = EX / "agents" / "expense_bot"
GOLDEN = AGENT_DIR / "traces" / "expense_bot.otlp.jsonl"


def _mapping() -> dict:
    return json.loads(MAP.read_text(encoding="utf-8"))


def _stamped(raws: list[dict]) -> list[dict]:
    """The example records with the native ids and clock a LangGraph run log carries (thread, run, user, start)."""
    out = []
    for i, r in enumerate(raws):
        r = json.loads(json.dumps(r))
        r["run_id"], r["user_id"], r["started_at"] = f"run-{i}", "user-7", f"2026-11-18T01:{i % 60:02d}:00+05:30"
        if isinstance(r.get("input"), str):
            r["input"] = {"text": r["input"], "thread_id": f"thread-{r['probe']}"} if i % 2 else r["input"]
        out.append(r)
    return out


def test_default_import_is_unchanged():
    raws = read_native(NATIVE)
    docs = to_docs(raws, _mapping(), "expense_bot", is_write_from_tools(AGENT_DIR / "tools.json"))
    golden = [json.loads(x) for x in GOLDEN.read_text(encoding="utf-8").splitlines() if x.strip()]
    assert docs == golden


def test_trace_format_import_keeps_verdicts():
    agent = metadata.load(AGENT_DIR)
    raws = read_native(NATIVE)
    is_write = is_write_from_tools(AGENT_DIR / "tools.json")
    docs, got = check(raws, _mapping(), "expense_bot", agent, is_write)
    golden = [json.loads(x) for x in GOLDEN.read_text(encoding="utf-8").splitlines() if x.strip()]
    assert got == verdicts(agent, golden)
    assert all(resource(d) == {"service.name": "expense_bot", "gen_ai.framework": _mapping()["framework"],
                               "agentest.trace_format.version": "1.0.0"} for d in docs)


def test_native_ids_and_clock_go_to_the_resource():
    agent = metadata.load(AGENT_DIR)
    raws = _stamped(read_native(NATIVE))
    docs, _ = check(raws, _mapping(), "expense_bot", agent, is_write_from_tools(AGENT_DIR / "tools.json"))
    r = resource(docs[1])
    assert r["agentest.run.id"] == "run-1" and r["user.id"] == "user-7"
    assert int(r["agentest.source.start_time_unix_nano"]) == _unix_nano("2026-11-17T19:31:00Z")
    spans = docs[1]["resourceSpans"][0]["scopeSpans"][0]["spans"]
    assert int(spans[0]["startTimeUnixNano"]) < 2 * 10**18  # imported clock unchanged (replay clock, D9)


def test_source_attrs_reads_common_native_fields():
    assert source_attrs({}) == {"agentest.trace_format.version": "1.0.0"}
    a = source_attrs({"execution_id": 42, "input": {"user_id": "u1"}, "start_time_unix_nano": 1763400000123456789})
    assert a == {"agentest.trace_format.version": "1.0.0", "agentest.run.id": "42", "user.id": "u1",
                 "agentest.source.start_time_unix_nano": 1763400000123456789}
    assert _unix_nano(1763400000) == 1763400000 * 10**9 and _unix_nano(1763400000123) == 1763400000123 * 10**6
    assert _unix_nano("not a time") is None and _unix_nano(True) is None and _unix_nano(5) is None


def test_cli_flag(tmp_path):
    out = tmp_path / "t.otlp.jsonl"
    p = subprocess.run([sys.executable, "-m", "agentest", "std", "import", str(NATIVE), "--map", str(MAP), "--trace-format",
                        "--tools", str(AGENT_DIR / "tools.json"), "--out", str(out)],
                       cwd=ROOT, capture_output=True, text=True, env={"PYTHONPATH": str(ROOT / "src"), "PATH": "/usr/bin:/bin"})
    assert p.returncode == 0, p.stderr
    docs = [json.loads(x) for x in out.read_text(encoding="utf-8").splitlines()]
    assert docs and all(resource(d)["agentest.trace_format.version"] == "1.0.0" for d in docs)


def test_source_paths_in_the_mapping():
    raw = {"trace_id": "trace_1", "metadata": {"user": "u9"}, "trace": [{"ts": "2026-11-18T01:17:00+05:30"}], "run_id": "ignored"}
    a = source_attrs(raw, {"run_id": "trace_id", "user_id": "metadata.user", "start_time": "trace.0.ts"})
    assert a["agentest.run.id"] == "trace_1" and a["user.id"] == "u9"
    assert a["agentest.source.start_time_unix_nano"] == _unix_nano("2026-11-17T19:47:00Z")
