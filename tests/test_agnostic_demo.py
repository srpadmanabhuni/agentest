"""Agnosticism proof: a plain-Python agent with its own log format is onboarded with standard artefacts only
(A2A AgentCard + MCP tools/list + OTLP traces, converted once from its ad-hoc log with ``agentest std import`` and a
small mapping function), with zero test changes; the buggy build is caught by the same universal rules."""

import json
from pathlib import Path

from agentest.standards import metadata, runner

DEMO = Path(__file__).resolve().parents[1] / "examples" / "agnostic_demo"


def _agent_module():
    import importlib.util

    spec = importlib.util.spec_from_file_location("refill_agent", DEMO / "refill_agent.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_recorded_runs_match_agent():
    m = _agent_module()
    for buggy, name in ((False, "refill_bot"), (True, "refill_bot_buggy")):
        rec = [json.loads(ln) for ln in (DEMO / "native" / f"{name}.jsonl").read_text().splitlines()]
        assert rec == json.loads(json.dumps(m.record(buggy, name)))


def test_checked_in_traces_match_import(tmp_path):
    """The OTLP traces in agents/ are exactly what ``agentest std import`` makes from the native log."""
    from agentest.cli import main

    for name in ("refill_bot", "refill_bot_buggy"):
        out = tmp_path / f"{name}.otlp.jsonl"
        assert main(["std", "import", str(DEMO / "native" / f"{name}.jsonl"), "--map", str(DEMO / "import" / "map.json"),
                     "--tools", str(DEMO / "agents" / name / "tools.json"), "--service", name, "--out", str(out)]) == 0
        assert out.read_text() == (DEMO / "agents" / name / "traces" / f"{name}.otlp.jsonl").read_text()


def test_agent_folders_hold_standard_files_only():
    for d in (DEMO / "agents").iterdir():
        assert {p.name for p in d.iterdir() if p.name != "__pycache__"} == {"agent-card.json", "tools.json", "traces"}


def test_metadata_is_valid():
    for a in metadata.load_all(DEMO / "agents").values():
        assert metadata.validate(a) == []


def test_good_build_passes_buggy_build_caught():
    res = runner.run_all(metadata.load_all(DEMO / "agents"))
    good, bad = res["refill_bot"], res["refill_bot_buggy"]
    assert {k for k, r in good.items() if r.status == "fail"} == set()
    assert sum(r.status == "pass" for r in good.values()) >= 50
    caught = {k for k, r in bad.items() if r.status == "fail"}
    assert {"T1-004", "T2-001", "T2-005", "T4-009", "T7-014"} <= caught  # T2-004/T3-001 need gated effects; v3.3 scopes approval to approval.required
