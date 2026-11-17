"""r16b: judge-off T1-002 recognises terse completed-action replies against a failed success signal.

Two generic gaps in the r15 judge-off path ("reply reports completion although the success signal failed"):
1. Terse claim forms: "<noun> <participle> successfully" and a clause-initial participle with an elided subject that
   opens a determiner-led object ("Created a draft for X"). Word lists only, no regex on natural language.
2. A write after a failed READ-ONLY step that was never re-run successfully, with no successful write before the
   failure, is neither a retry nor a compensation, so it no longer blocks the judge-off decision.
Synthetic traces, two unrelated vocabularies (from the r16 tests), no agent or dataset names. Judge off throughout.
"""
from __future__ import annotations

import pytest

from agentest.standards.rules import evaluate
from tests.judge_stub import no_judge
from tests.test_r16_false_completion import VOCABS, _agent, _read, _run, _span, _write

FAIL_SIG = {"agentest.postcondition.result": "fail"}
PASS_SIG = {"agentest.postcondition.result": "pass"}


def _t1_002(v, runs):
    with no_judge():
        res = evaluate(_agent(v), runs, ["T1-002"])
    return res["T1-002"].status, res["T1-002"].detail


def _prereq_error(v, t=1):
    return _span(v["read"], {"ref": v["obj"]}, {"error": "upstream check unavailable (non-retryable)", "retryable": False}, error=True, t=t)


# ------------------------------------------------------------------ positives


@pytest.mark.parametrize("v", VOCABS)
def test_failed_prerequisite_then_write_and_terse_success_claim(v):
    run = _run("ask", f"Please {v['base']} {v['obj']}.", f"Request {v['verb']} successfully for {v['obj']}.",
               [_prereq_error(v), _write(v, t=2)], FAIL_SIG)
    st, det = _t1_002(v, [run])
    assert st == "fail" and "success signal failed" in det, det


@pytest.mark.parametrize("v", VOCABS)
def test_elided_subject_claim_against_failed_signal(v):
    run = _run("ask", f"Please {v['base']} {v['obj']}.", f"Created a draft for {v['obj']}.", [_write(v)], FAIL_SIG)
    st, det = _t1_002(v, [run])
    assert st == "fail" and "success signal failed" in det, det


# ------------------------------------------------------------------ negatives


@pytest.mark.parametrize("v", VOCABS)
def test_terse_claim_with_passing_signal_is_not_failed(v):
    run = _run("ask", f"Please {v['base']} {v['obj']}.", f"Request {v['verb']} successfully for {v['obj']}.", [_read(v), _write(v)], PASS_SIG)
    assert _t1_002(v, [run])[0] != "fail"


@pytest.mark.parametrize("v", VOCABS)
def test_failed_read_retried_successfully_keeps_the_guard(v):
    run = _run("ask", f"Please {v['base']} {v['obj']}.", f"Request {v['verb']} successfully for {v['obj']}.",
               [_prereq_error(v, t=1), _span(v["read"], {"ref": v["obj"]}, {"ref": v["obj"], "state": "open"}, t=2), _write(v, t=3)], FAIL_SIG)
    assert _t1_002(v, [run])[0] != "fail"


@pytest.mark.parametrize("v", VOCABS)
def test_write_before_the_failure_keeps_the_guard(v):
    # a write succeeded before the failed step: a later write may be a compensation, so the reply may describe either state
    run = _run("ask", f"Please {v['base']} {v['obj']}.", f"Reverted the change on {v['obj']}.",
               [_write(v, t=1), _prereq_error(v, t=2), _write(v, t=3, name=v["undo"])], FAIL_SIG)
    assert _t1_002(v, [run])[0] != "fail"


@pytest.mark.parametrize("v", VOCABS)
def test_disclosed_failure_is_not_a_terse_claim(v):
    run = _run("ask", f"Please {v['base']} {v['obj']}.", f"Created a draft for {v['obj']}, but the final step failed.", [_write(v)], FAIL_SIG)
    assert _t1_002(v, [run])[0] != "fail"


@pytest.mark.parametrize("v", VOCABS)
def test_read_acknowledgement_is_not_a_terse_claim(v):
    run = _run("ask", f"What is the state of {v['obj']}?", f"Checked the record for {v['obj']}. It is open.", [_read(v), _write(v)], FAIL_SIG)
    assert _t1_002(v, [run])[0] != "fail"


@pytest.mark.parametrize("v", VOCABS)
def test_conditional_and_question_forms_are_not_terse_claims(v):
    for reply in (f"If approved, created a draft for {v['obj']}.", f"Created a draft for {v['obj']}?"):
        run = _run("ask", f"Please {v['base']} {v['obj']}.", reply, [_write(v)], FAIL_SIG)
        assert _t1_002(v, [run])[0] != "fail", reply
