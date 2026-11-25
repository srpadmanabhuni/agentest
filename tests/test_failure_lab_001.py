"""Failure Lab 001: a refund retried after a tool timeout must create one refund, not two.

The recorded-trace tests need agentest only. The end-to-end tests run the OpenAI Agents SDK example's
refund workflow with a scripted model; they need ``pip install openai-agents==0.26.0`` and skip without it.
``--runxfail`` shows the original (unfixed) tool contract failing.
"""

from __future__ import annotations

import json
import sys
from importlib import metadata
from pathlib import Path

import pytest

import agentest

LAB = Path(__file__).resolve().parents[1] / "examples" / "failure-lab" / "001-refund-timeout-retry"
CHECKS = "T2-003,T1-006,T1-011"


def _verdicts(variant: str) -> dict[str, str]:
    doc = json.loads((LAB / "traces" / f"{variant}.otlp.json").read_text(encoding="utf-8"))
    return {c.id: c.status for c in agentest.run(doc, tools=str(LAB / "tools.json"), ids=CHECKS)}


def test_recorded_original_run_shows_two_refunds_and_is_caught():
    run = json.loads((LAB / "traces" / "original.run.json").read_text(encoding="utf-8"))
    assert [r["refund_ticket"] for r in run["refunds"]] == ["RF-1001", "RF-1002"]
    assert _verdicts("original") == {"T2-003": "fail", "T1-006": "fail", "T1-011": "fail"}


def test_recorded_fixed_run_shows_one_refund_and_passes():
    run = json.loads((LAB / "traces" / "fixed.run.json").read_text(encoding="utf-8"))
    assert [r["refund_ticket"] for r in run["refunds"]] == ["RF-1001"]
    assert _verdicts("fixed") == {"T2-003": "pass", "T1-006": "pass", "T1-011": "pass"}


def _sdk():
    try:
        version = metadata.version("openai-agents")
    except metadata.PackageNotFoundError:
        pytest.skip("pip install openai-agents==0.26.0 to run the workflow end to end")
    if version != "0.26.0":
        pytest.skip(f"Failure Lab 001 is pinned to openai-agents 0.26.0, found {version}")
    sys.path.insert(0, str(LAB))
    import refund_agent
    from to_trace import TOOLS, build_trace

    return refund_agent, TOOLS, build_trace


@pytest.mark.parametrize("variant", [
    "fixed",
    pytest.param("original", marks=pytest.mark.xfail(strict=True, reason="Failure Lab 001: the retried refund is created twice")),
])
def test_timeout_retry_creates_one_refund(variant, monkeypatch):
    monkeypatch.setenv("OPENAI_AGENTS_DISABLE_TRACING", "1")
    refund_agent, tools, build_trace = _sdk()
    run = refund_agent.run_scenario(variant)
    calls = [i for i in run["items"] if i.get("type") == "function_call" and i["name"] == "submit_refund"]
    assert len(calls) == 2, "the scenario must time out once and retry once"
    assert len(run["refunds"]) == 1, f"refunds created: {[r['refund_ticket'] for r in run['refunds']]}"
    agentest.assert_passes(agentest.run(build_trace(run), tools=str(tools), ids=CHECKS), ids=CHECKS)
