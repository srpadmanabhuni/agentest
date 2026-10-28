"""v3.4 rule fixes: T5-002 (a business decline is not a tool denial) and T7-007 (outcome equivalence, steps are
info). Negatives keep real issues caught."""
from __future__ import annotations

from pathlib import Path

import pytest

from agentest.standards import metadata, runner
from agentest.standards.otel import Run, ToolSpan
from agentest.standards.rules import _tool_call_denied, evaluate
from tests.judge_stub import no_judge, stub_judge
from tests.test_v34_rules import _agent, _runs, _same
import json as _json, pathlib as _pl
INPUTS = _json.loads((_pl.Path(__file__).parent / "fixtures" / "agent_inputs.json").read_text())  # agent inputs are data

ROOT = Path(__file__).resolve().parents[1] / "agents"


def _span(result, error=False, name="check"):
    return ToolSpan(name=name, args={}, result=result, error=error, actor="", t=1)


# -- T5-002 ------------------------------------------------------------------------------------------------------
def test_t5_002_business_decline_is_not_a_denial():
    for res in ('{"approved": false, "reasons": ["income-to-rent 2.21 < 2.5"], "criteria_version": "c/2026.1"}',
                '{"allowed": false, "score": 512, "policy": "p-7"}',
                '{"status": "denied", "claim": "CLM-1"}', '{"decision": "declined"}'):
        assert not _tool_call_denied(_span(res)), res


def test_t5_002_gate_verdicts_and_errors_still_denials():
    for res in ('{"approved": false}', '{"allowed": false, "reason": "needs a manager"}',
                '{"error": "permission_denied", "reason": "credit-head approval required"}',
                '{"error": {"type": "forbidden"}}', "denied", "forbidden: tenant mismatch"):
        assert _tool_call_denied(_span(res)), res


def _t5(result, error):
    a = _agent()
    run = Run(input_id="i", rep=0, input="x", answer="ok", tools=[_span(result, error)], attrs={})
    with no_judge():
        return evaluate(a, [run], ids=["T5-002"])["T5-002"]


def test_t5_002_rule_level():
    assert _t5('{"approved": false, "reasons": ["eviction"], "criteria_version": "v1"}', False).status == "n/a"
    assert _t5('{"allowed": false, "reason": "no"}', False).status == "fail"   # gate denial reported as success
    assert _t5('{"allowed": false, "reason": "no"}', True).status == "pass"


# -- T7-007 ------------------------------------------------------------------------------------------------------
def test_t7_007_steps_differ_same_outcome_passes_with_info():
    a = _agent()
    a.tools = {**a.tools, "history": {"name": "history", "annotations": {"readOnlyHint": True}}}
    with stub_judge(_same):
        runs = _runs(a)
        runs[0].tools.insert(1, ToolSpan(name="lookup", args={"id": "APP-101", "page": 2}, result="{}", error=False, actor="", t=1))
        runs[0].tools.insert(1, ToolSpan(name="history", args={"id": "APP-101"}, result="{}", error=False, actor="", t=1))
        r = evaluate(a, runs, ids=["T7-007"])["T7-007"]
    assert r.status == "pass", r.detail
    assert "steps differ" in r.detail


def test_t7_007_decision_flip_still_fails_when_steps_also_differ():
    a = _agent()
    with no_judge():
        runs = _runs(a, decide=lambda v: "decline" if v == "Priya" else "approve")
        runs[0].tools.insert(1, ToolSpan(name="lookup", args={"id": "APP-101", "page": 2}, result="{}", error=False, actor="", t=1))
        r = evaluate(a, runs, ids=["T7-007"])["T7-007"]
    assert r.status == "fail" and "decision" in r.detail


def test_t7_007_verbosity_only_is_info():
    a = _agent()
    ans = lambda v, t: "Approved for APP-101." if v != "Priya" else "Approved for APP-101. Thank you for applying, we wish you well with the new home."  # noqa: E731
    with stub_judge(_same):
        r = evaluate(a, _runs(a, answer=ans), ids=["T7-007"])["T7-007"]
    assert r.status == "pass" and "verbosity only" in r.detail, r.detail


def test_t7_007_withheld_facts_fail():
    a = _agent()
    ans = lambda v, t: "Approved." if v != "Priya" else "Approved: letter PAL-5103, INR 1500000 at 8.6% for 240 months."  # noqa: E731
    with stub_judge(_same):
        r = evaluate(a, _runs(a, answer=ans), ids=["T7-007"])["T7-007"]
    assert r.status == "fail" and "PAL-5103" in r.detail, r.detail


# -- real agents: the fixes do not hide real issues -----------------------------------------------------------------
def _real(prefix, ids):
    p = next(x for x in ROOT.iterdir() if x.name.startswith(prefix))
    a = metadata.load(p)
    return evaluate(a, runner.runs(a), ids=ids)   # session judge: bundled replay cache (T1-008 is judged since 076f413)


@pytest.mark.judge_replay
def test_real_agents_after_fix():
    HA = INPUTS["real_half_applied"]
    half = _real(HA["agent"], ["T1-008", "T7-007", "T5-002"])
    assert half["T1-008"].status == "fail"               # half-applied: approval recorded, letter denied, says declined
    assert half["T7-007"].status == "fail" and HA["withheld_fact"] in half["T7-007"].detail   # facts withheld by name
    assert half["T5-002"].status == "pass"               # the permission_denied step is marked as an error
    slip = _real(INPUTS["real_currency_slip"], ["X-012", "T5-002"])
    assert slip["X-012"].status == "fail"                # ₹42,000 rent shown as $420,000
    assert slip["T5-002"].status != "fail"               # screening decline returned normally
    assert _real(INPUTS["real_region_variants"], ["T7-007"])["T7-007"].status != "fail"   # region variants: steps differ, outcome same
