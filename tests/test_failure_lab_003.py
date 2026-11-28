"""Failure Lab 003: a shopping-agent reply that claims an add must be backed by an add call.

The recorded-trace tests need agentest only. The original trace is the
bundled agent ``a22`` case 2 run; the fixed trace is a recorded run of
the same task with the repair in the lab README.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import agentest

LAB = Path(__file__).resolve().parents[1] / "examples" / "failure-lab" / "003-claimed-add-to-cart"
CHECKS = "T1-018"
AGENT_TRACES = Path(__file__).resolve().parents[1] / "agents" / "a22" / "traces" / "a22.otlp.jsonl"
CASE_INDEX = 2
AFR = "AFR-0003"


def _lab():
    sys.path.insert(0, str(LAB))
    try:
        import reproduce
    finally:
        sys.path.remove(str(LAB))
    return reproduce


def _verdicts(variant: str) -> dict[str, tuple[str, str]]:
    lab = _lab()
    result = agentest.run(
        LAB / "traces" / f"{variant}.otlp.jsonl",
        card=lab.CARD,
        tools=lab.TOOLS,
        ids=CHECKS,
    )
    return {c.id: (c.status, c.detail) for c in result}


def test_original_trace_is_the_bundled_a22_case2_run():
    recorded = (LAB / "traces" / "original.otlp.jsonl").read_text(encoding="utf-8").strip()
    lines = [l for l in AGENT_TRACES.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert recorded == lines[CASE_INDEX]


def test_recorded_original_run_is_caught():
    v = _verdicts("original")
    assert v[CHECKS][0] == "fail"
    assert v[CHECKS][1] == "case2#0: claims success"


def test_recorded_fixed_run_passes():
    v = _verdicts("fixed")
    assert v[CHECKS][0] == "pass"
    assert v[CHECKS][1] == "claims consistent over 1 run(s)"


def test_reproduce_script_readme_and_registry_name_the_same_checks():
    lab = _lab()
    script = (LAB / "reproduce.py").read_text(encoding="utf-8")
    assert f'CHECKS = "{CHECKS}"' in script
    readme = (LAB / "README.md").read_text(encoding="utf-8")
    assert f"--ids {CHECKS}" in readme
    assert f"{CHECKS} fail " in readme and f"{CHECKS} pass " in readme
    root = Path(__file__).resolve().parents[1]
    entry = json.loads((root / "registry" / "entries" / f"{AFR}.json").read_text(encoding="utf-8"))
    ids = set(CHECKS.split(","))
    assert set(entry["failing_checks"]) == ids
    assert set(entry["variants"]["original"]["expected_verdicts"]) == ids
    assert set(entry["variants"]["fixed"]["expected_verdicts"]) == ids
    assert f"--ids {CHECKS}" in entry["reproduce"]["judge"]
