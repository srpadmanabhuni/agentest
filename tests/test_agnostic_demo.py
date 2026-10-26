"""Agnosticism proof (next version, v2.0.0-dev): a plain-Python agent with its own log format is onboarded
with one YAML profile + a 24-line adapter, without touching any check code; the buggy build is caught."""

import json
from pathlib import Path

from agentest.model import generic
from agentest.model.profile import load_all
from agentest.model.runner import run_all
from agentest.model.trace import validate

DEMO = Path(__file__).resolve().parents[1] / "examples" / "agnostic_demo"


def _fresh_runs(tmp_path):
    import importlib.util

    spec = importlib.util.spec_from_file_location("refill_agent", DEMO / "refill_agent.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_recorded_runs_match_agent():
    m = _fresh_runs(None)
    for buggy, name in ((False, "refill_bot"), (True, "refill_bot_buggy")):
        rec = [json.loads(ln) for ln in (DEMO / f"{name}.jsonl").read_text().splitlines()]
        assert rec == json.loads(json.dumps(m.record(buggy, name)))


def test_good_build_passes_buggy_build_caught():
    res = run_all(load_all(DEMO))
    good, bad = res["refill_bot"], res["refill_bot_buggy"]
    assert {k for k, r in good.items() if r.status == "fail"} == set()
    assert sum(r.status == "pass" for r in good.values()) >= 14
    caught = {k for k, r in bad.items() if r.status == "fail"}
    assert {"T1-004", "T2-001", "T2-004", "T2-005", "T3-001", "T4-009", "T7-014"} <= caught


def test_traces_are_schema_valid():
    from agentest.model.runner import traces

    for p in load_all(DEMO).values():
        for e in traces(p):
            assert validate(e.to_dict()) == []


def test_no_agent_specific_check_code():
    src = Path(generic.__file__).read_text()
    for name in ("refill", "RX-501", "a05", "expense_bot", "eager"):
        assert name not in src
