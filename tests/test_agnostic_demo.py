"""Agnosticism proof (v3.0.0): a plain-Python agent with its own log format is onboarded with
standard metadata only (A2A AgentCard + MCP tools/list + a field-mapping adapter), with zero test
changes; the buggy build is caught by the same universal rules."""

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
        rec = [json.loads(ln) for ln in (DEMO / "agents" / name / f"{name}.jsonl").read_text().splitlines()]
        assert rec == json.loads(json.dumps(m.record(buggy, name)))


def test_metadata_is_valid():
    for a in metadata.load_all(DEMO / "agents").values():
        assert metadata.validate(a) == []


def test_good_build_passes_buggy_build_caught():
    res = runner.run_all(metadata.load_all(DEMO / "agents"))
    good, bad = res["refill_bot"], res["refill_bot_buggy"]
    assert {k for k, r in good.items() if r.status == "fail"} == set()
    assert sum(r.status == "pass" for r in good.values()) >= 50
    caught = {k for k, r in bad.items() if r.status == "fail"}
    assert {"T1-004", "T2-001", "T2-004", "T2-005", "T3-001", "T4-009", "T7-014"} <= caught
