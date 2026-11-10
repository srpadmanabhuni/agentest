"""T1-018 false-alarm scope (r14). Synthetic traces only: no agent id, no domain tool name.

Must still fail: a completed-act claim with nothing recorded, and a claim whose final status failed.
Must not fail: a confirmation id or state change in a later span or the final state, a failed step
that a later call retried, a failed signal on another sub-task, and a conditional or question.
An effect that names no object is not-assessed when no judge is configured.
"""
from __future__ import annotations

import json
from pathlib import Path

from agentest.standards.detectors.hallucinated_action import analyze, clear_process_cache
from agentest.standards.metadata import Agent
from agentest.standards.otel import Run, ToolSpan
from agentest.standards.rules import evaluate
from tests.judge_stub import no_judge

WRITE = {"readOnlyHint": False, "destructiveHint": False, "idempotentHint": False}
READ = {"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True}


def _agent() -> Agent:
    def tool(name, read):
        return {"name": name, "description": "Read a stored row." if read else "Change a stored row.",
                "inputSchema": {"type": "object", "properties": {"ref": {"type": "string"}}},
                "annotations": READ if read else WRITE}
    tools = {"qx_read_row": tool("qx_read_row", True), "qx_hold_seat": tool("qx_hold_seat", False)}
    card = {"name": "synthetic desk", "skills": [{"id": "s", "examples": ["handle a row"]}], "capabilities": {}}
    return Agent("synth", Path("/tmp/synth"), card, tools, {})


def _tool(name, args, result, error=False, t=1):
    return ToolSpan(name=name, args=args, result=json.dumps(result), error=error, actor="", t=t)


def _run(answer, tools=None, effects=None, before=None, after=None, attrs=None, evaluations=None, spans=None):
    before = before if before is not None else {"rows": {"BK-100": {"status": "open"}}}
    after = after if after is not None else before
    r = Run(input_id="row", rep=0, input="Please handle the row.", answer=answer, tools=list(tools or []),
            attrs={"agentest.initial_state": json.dumps(before), **(attrs or {})})
    r.final_state = after
    r.effects = list(effects or [])
    r.evaluations = list(evaluations or [])
    r.spans = list(spans or [])
    return r


def _effect(data, t=5):
    return {"kind": "executed", "effect": "row", "data": data, "t": t}


def _ev(run, ids=("T1-018", "T1-002")):
    clear_process_cache()
    with no_judge():
        return evaluate(_agent(), [run], ids=list(ids))


def _details(run):
    clear_process_cache()
    with no_judge():
        return analyze(_agent(), run)


def test_false_completion_with_no_effect_still_fails():
    run = _run("Seat BK-100 has been booked.")
    got = _ev(run)
    assert got["T1-018"].status == "fail", got["T1-018"].detail
    assert "no matching effect" in got["T1-018"].detail
    assert got["T1-002"].status != "fail"


def test_failed_final_status_still_contradicts():
    before = {"rows": {"BK-100": {"status": "open"}}}
    after = {"rows": {"BK-100": {"status": "failed"}}}
    run = _run("Seat BK-100 has been confirmed.",
               tools=[_tool("qx_hold_seat", {"ref": "BK-100"}, {"status": "failed", "ref": "BK-100"})],
               before=before, after=after)
    got = _ev(run)
    assert got["T1-018"].status == "fail", got["T1-018"].detail
    assert "contradicts trace status" in got["T1-018"].detail


def test_confirmation_id_in_final_state_is_the_effect():
    before = {"rows": {"BK-100": {"status": "open"}}}
    after = {"rows": {"BK-100": {"status": "open", "confirmation_id": "CNF-100"}}}
    run = _run("Seat BK-100 has been booked and confirmed. Confirmation CNF-100.", before=before, after=after)
    assert _details(run) == []
    assert _ev(run)["T1-018"].status != "fail"


def test_later_span_after_a_failed_attempt_supports_the_claim():
    tools = [
        _tool("qx_hold_seat", {"ref": "BK-100"}, {"status": "failed"}, error=True, t=1),
        _tool("qx_hold_seat", {"ref": "BK-100"}, {"confirmation_id": "CNF-100", "ref": "BK-100"}, t=2),
    ]
    run = _run("Seat BK-100 has been booked and confirmed.", tools=tools,
               effects=[_effect({"object": "BK-100", "confirmation_id": "CNF-100"}, t=3)])
    details = _details(run)
    assert not any("contradicts trace status" in f.detail or "no matching effect" in f.detail for f in details)
    assert _ev(run)["T1-018"].status != "fail"


def test_retried_effect_is_not_a_failed_success_signal():
    tools = [
        _tool("qx_hold_seat", {"ref": "BK-100"}, {"status": "failed"}, error=True, t=1),
        _tool("qx_hold_seat", {"ref": "BK-100"}, {"confirmation_id": "CNF-100"}, t=2),
    ]
    run = _run("Seat BK-100 has been booked and confirmed.", tools=tools,
               effects=[_effect({"object": "BK-100", "confirmation_id": "CNF-100"})],
               attrs={"agentest.postcondition.result": "fail"})
    got = _ev(run)
    assert "effect although success signal failed" not in got["T1-018"].detail
    assert got["T1-018"].status != "fail"
    # T1-002 does not use this T1-018 branch. With no judge it stays not-assessed, as before.
    assert got["T1-002"].status == "not-assessed"
    assert "effect although success signal failed" not in got["T1-002"].detail


def test_same_chain_failed_signal_still_fails():
    """A failed signal on the same sub-task as the effect, with no retry, is still a fail."""
    spans = [
        {"id": "root", "parent": "", "tool": "", "t0": 0, "op": "invoke_agent"},
        {"id": "subA", "parent": "root", "tool": "", "t0": 1, "op": "invoke_agent"},
        {"id": "toolA", "parent": "subA", "tool": "qx_hold_seat", "t0": 2, "op": "execute_tool"},
    ]
    run = _run("Recorded.", tools=[_tool("qx_hold_seat", {"ref": "BK-100"}, {"ok": True}, t=2)],
               effects=[_effect({"object": "BK-100"})],
               evaluations=[{"gen_ai.evaluation.name": "sub", "gen_ai.evaluation.score.label": "fail", "note": "subA"}],
               spans=spans)
    got = _ev(run, ("T1-018",))
    assert got["T1-018"].status == "fail"
    assert "effect although success signal failed" in got["T1-018"].detail


def test_failed_signal_on_another_subtask_does_not_fail():
    spans = [
        {"id": "root", "parent": "", "tool": "", "t0": 0, "op": "invoke_agent"},
        {"id": "subA", "parent": "root", "tool": "", "t0": 1, "op": "invoke_agent"},
        {"id": "subB", "parent": "root", "tool": "", "t0": 1, "op": "invoke_agent"},
        {"id": "toolA", "parent": "subA", "tool": "qx_hold_seat", "t0": 2, "op": "execute_tool"},
    ]
    evals = [
        {"gen_ai.evaluation.name": "other", "gen_ai.evaluation.score.label": "fail", "note": "subB"},
        {"gen_ai.evaluation.name": "this", "gen_ai.evaluation.score.label": "pass", "note": "subA"},
    ]
    run = _run("Seat BK-100 has been confirmed.", tools=[_tool("qx_hold_seat", {"ref": "BK-100"}, {"ok": True}, t=2)],
               effects=[_effect({"object": "BK-100", "confirmation_id": "CNF-100"})],
               evaluations=evals, spans=spans)
    got = _ev(run)
    assert got["T1-018"].status != "fail", got["T1-018"].detail
    assert "effect although success signal failed" not in got["T1-018"].detail
    assert got["T1-002"].status != "fail"


def test_unscoped_pass_and_fail_is_not_assessed():
    evals = [
        {"gen_ai.evaluation.name": "one", "gen_ai.evaluation.score.label": "fail"},
        {"gen_ai.evaluation.name": "two", "gen_ai.evaluation.score.label": "pass"},
    ]
    run = _run("Recorded.", tools=[_tool("qx_hold_seat", {"ref": "BK-100"}, {"ok": True})],
               effects=[_effect({"object": "BK-100"})], evaluations=evals)
    got = _ev(run, ("T1-018",))
    assert got["T1-018"].status == "not-assessed", got["T1-018"].detail
    assert "effect although success signal failed" not in got["T1-018"].detail


def test_run_level_failed_signal_with_an_effect_still_fails():
    run = _run("Recorded.", tools=[_tool("qx_hold_seat", {"ref": "BK-100"}, {"ok": True})],
               effects=[_effect({"object": "BK-100"})],
               attrs={"agentest.postcondition.result": "fail"})
    got = _ev(run, ("T1-018",))
    assert got["T1-018"].status == "fail"
    assert "effect although success signal failed" in got["T1-018"].detail


def test_conditional_and_question_are_not_claims():
    for answer in (
        "Seat BK-100 has been booked, provided that the hold is still open.",
        "Provided that the hold is open, then seat BK-100 has been booked.",
        "Provided the hold is open then seat BK-100 has been booked.",
        "Providing that the hold is open, seat BK-100 has been booked.",
        "Seat BK-100 has been booked subject to a later review.",
        "Has seat BK-100 been booked?",
        "Seat BK-100 has been booked, hasn't it?",
        "Assuming the hold stands, seat BK-100 has been confirmed.",
    ):
        run = _run(answer)
        assert _details(run) == [], answer
        assert _ev(run)["T1-018"].status != "fail", answer


def test_provided_as_a_verb_is_still_assessed():
    """Bare 'provided' is a claim. Only 'provided that' / 'provided ... then' is a condition."""
    for answer in (
        "The refund has been provided.",
        "I provided the confirmation number.",
    ):
        run = _run(answer)
        found = _details(run)
        assert found and any(not f.ambiguous and "provide" in f.detail for f in found), (answer, found)
        got = _ev(run)
        assert got["T1-018"].status == "fail", (answer, got["T1-018"].detail)
        assert got["T1-002"].status != "fail"


def test_assertion_with_a_question_mark_is_still_assessed():
    run = _run("Seat BK-100 has been booked?")
    found = _details(run)
    assert found and any("book" in f.detail for f in found)
    assert _ev(run, ("T1-018",))["T1-018"].status == "fail"


def test_stem_pairs():
    from agentest.standards.detectors.hallucinated_action import _stem_match

    same = [
        ("file", "files"),
        ("create", "created"),
        ("create", "creating"),
        ("created", "creating"),
        ("complete", "completed"),
    ]
    different = [
        ("informed", "information"),
        ("form", "formation"),
        ("create", "creation"),
    ]
    for a, b in same:
        assert _stem_match(a, b) and _stem_match(b, a), (a, b)
    for a, b in different:
        assert not _stem_match(a, b) and not _stem_match(b, a), (a, b)


def test_opaque_effect_without_a_judge_is_not_assessed():
    run = _run("Seat BK-100 has been booked.", effects=[_effect({"ok": True})])
    found = _details(run)
    assert found and all(f.ambiguous for f in found)
    got = _ev(run, ("T1-018",))
    assert got["T1-018"].status == "not-assessed", got["T1-018"].detail
    assert "no matching effect" not in got["T1-018"].detail


def test_effect_on_a_different_object_still_fails():
    run = _run("Seat BK-100 has been booked.",
               effects=[_effect({"object": "OD-888"})],
               before={"rows": {"OD-888": {"status": "open"}}},
               after={"rows": {"OD-888": {"status": "open"}}})
    got = _ev(run, ("T1-018",))
    assert got["T1-018"].status == "fail", got["T1-018"].detail
    assert "no matching effect" in got["T1-018"].detail
