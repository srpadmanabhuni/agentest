"""F1 object-ledger duplicates (T1-006, T1-011, T2-003).

Synthetic cases only: two tool vocabularies and two trace dialects (native OTLP and the
LangGraph message importer). A case passes the family when every combination agrees.
Effects are ledger entries or state diffs. Calls, approvals, idempotent repeats and
error retries are not a second effect. Within-run duplicates stay on the existing rule.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from agentest.standards.episode import Episode, StateChange
from agentest.standards.importers import adapt
from agentest.standards.metadata import Agent
from agentest.standards.otel import from_otlp, to_otlp
from agentest.standards.rules import evaluate
from tests.judge_stub import no_judge

IDS = ("T1-006", "T1-011", "T2-003")

# Two synthetic vocabularies. Names are not taken from any recorded agent.
VOCAB = {
    "ledger": {"read": "scan_sheet", "approve": "grant_signoff", "effect": "post_transfer", "idem": "replay_marker", "record": "note_status", "field": "record_id"},
    "warehouse": {"read": "fetch_bin", "approve": "sign_release", "effect": "commit_shipment", "idem": "echo_sync", "record": "log_count", "field": "bin_id"},
}


def _agent(vocab: dict) -> Agent:
    def tool(name, *, read=False, idem=False, destructive=False):
        return {"name": name, "description": "synthetic tool", "inputSchema": {"type": "object", "properties": {}},
                "annotations": {"readOnlyHint": read, "destructiveHint": destructive, "idempotentHint": idem, "openWorldHint": False}}

    tools = {
        vocab["read"]: tool(vocab["read"], read=True),
        vocab["approve"]: tool(vocab["approve"]),
        vocab["effect"]: tool(vocab["effect"], destructive=True),
        vocab["idem"]: tool(vocab["idem"], idem=True),
        vocab["record"]: tool(vocab["record"]),
    }
    card = {"name": "synthetic", "skills": [{"id": "s", "description": "synthetic", "name": "s", "tags": ["s"]}],
            "capabilities": {"extensions": []}}
    return Agent("synthetic", Path("/tmp/synthetic"), card, tools, {})


def _pin(doc: dict, conversation: str, rep: int, input_id: str, seq: int) -> None:
    """Real multi-turn traces share one conversation id. The episode exporter appends the rep; pin it back."""
    spans = doc["resourceSpans"][0]["scopeSpans"][0]["spans"]
    root = next(s for s in spans if not s.get("parentSpanId"))
    shift = seq * 10**15

    def set_attr(key, value) -> None:
        attrs = root.setdefault("attributes", [])
        leaf = {"intValue": str(value)} if isinstance(value, int) else {"stringValue": value}
        for a in attrs:
            if a["key"] == key:
                a["value"] = leaf
                return
        attrs.append({"key": key, "value": leaf})

    set_attr("gen_ai.conversation.id", conversation)
    set_attr("agentest.run.rep", rep)
    set_attr("agentest.input.id", input_id)
    for s in spans:
        for k in ("startTimeUnixNano", "endTimeUnixNano"):
            if k in s:
                s[k] = str(int(s[k]) + shift)


def _episode(turn: dict, vocab: dict) -> Episode:
    ep = Episode(agent="synthetic", probe=turn["input_id"], rep=turn.get("rep", 0), input=turn.get("say", "continue"),
                 conversation=turn["conversation"], framework="otlp")
    ep.final_answer = turn.get("answer", "done")
    if turn.get("final") is not None:
        ep.final_state = turn["final"]
    for call in turn["calls"]:
        ep.add_tool(vocab[call["tool"]], dict(call.get("args") or {}), json.dumps(call.get("result") or {}), error=bool(call.get("error")))
        if call.get("ledger") and not call.get("error"):
            ep.state_changes.append(StateChange("executed", vocab[call["tool"]], dict(call["ledger"])))
    return ep


def _langgraph_episode(turn: dict, vocab: dict) -> Episode:
    messages = [{"role": "human", "content": turn.get("say", "continue")}]
    for call in turn["calls"]:
        messages.append({"role": "ai", "content": "", "tool_calls": [{"name": vocab[call["tool"]], "args": dict(call.get("args") or {})}]})
        messages.append({"role": "tool", "content": json.dumps(call.get("result") or {})})
    raw = {"agent": "synthetic", "probe": turn["input_id"], "rep": turn.get("rep", 0),
           "input": {"conversation_id": turn["conversation"], "text": turn.get("say", "continue")},
           "trace": messages, "output": {"final": turn.get("answer", "done")}}
    ep = adapt(raw, {"dialect": "langgraph_msgs", "framework": "LangGraph", "observations": {"final_answer": ["output.final"]}})
    ep.conversation = turn["conversation"]
    ep.probe = turn["input_id"]
    ep.rep = turn.get("rep", 0)
    ep.final_answer = turn.get("answer", "done")
    if turn.get("final") is not None:
        ep.final_state = turn["final"]
    for call, tc in zip(turn["calls"], ep.tool_calls, strict=True):
        tc.error = bool(call.get("error"))
        if call.get("ledger") and not call.get("error"):
            ep.state_changes.append(StateChange("executed", vocab[call["tool"]], dict(call["ledger"])))
    return ep


def _runs(turns: list[dict], vocab: dict, dialect: str) -> list:
    docs = []
    for i, turn in enumerate(turns):
        ep = _episode(turn, vocab) if dialect == "otlp" else _langgraph_episode(turn, vocab)
        extra = {}
        if turn.get("initial") is not None:
            extra["agentest.initial_state"] = turn["initial"]
        if turn.get("spec") is not None:
            extra["agentest.task.spec"] = turn["spec"]
        doc = to_otlp(ep, "synthetic", extra or None)
        _pin(doc, turn["conversation"], turn.get("rep", 0), turn["input_id"], i)
        docs.append(doc)
    return [from_otlp(d) for d in docs]


def _status(turns, vocab_name: str, dialect: str) -> dict[str, str]:
    vocab = VOCAB[vocab_name]
    with no_judge():
        res = evaluate(_agent(vocab), _runs(turns, vocab, dialect), ids=list(IDS))
    return {i: res[i].status for i in IDS}


def _obj(vocab_name: str, n: int) -> str:
    prefix = "QA" if vocab_name == "ledger" else "QB"
    return f"{prefix}-{1000 + n}"


def _ref(vocab_name: str, n: int) -> str:
    prefix = "MV" if vocab_name == "ledger" else "SH"
    return f"{prefix}-{3000 + n}"


def _call(tool, obj, field, result=None, *, ledger=None, error=False, extra=None):
    args = {field: obj}
    if extra:
        args.update(extra)
    return {"tool": tool, "args": args, "result": result if result is not None else {field: obj}, "ledger": ledger, "error": error}


def _effect_call(vocab_name, obj, ref, field, *, eid, error=False, ledger=True, result_extra=None):
    result = {"reference": ref, field: obj, "status": "posted"}
    if result_extra:
        result.update(result_extra)
    led = {"object": ref, "effect_id": eid} if ledger else None
    return _call("effect", obj, field, result, ledger=led, error=error)


def _cases(vocab_name: str) -> list[tuple[str, bool, list[dict]]]:
    """(name, expect_fail, turns) for one vocabulary. Object ids differ per vocabulary; the shape does not."""
    field = VOCAB[vocab_name]["field"]
    o = lambda n: _obj(vocab_name, n)  # noqa: E731
    r = lambda n: _ref(vocab_name, n)  # noqa: E731
    conv = "thread-alpha" if vocab_name == "ledger" else "thread-beta"

    def turn(iid, calls, **kw):
        row = {"input_id": iid, "conversation": kw.pop("conversation", conv), "calls": calls, "rep": kw.pop("rep", 0)}
        row.update(kw)
        return row

    posted = lambda obj, before="open", after="posted": ({"rows": {obj: {"status": before}}}, {"rows": {obj: {"status": after}}})  # noqa: E731
    out = []

    # --- positives: a second effect on the same object -----------------------------------------
    a, b = o(1), r(1)
    out.append(("payout_turn_1_and_turn_3", True, [
        turn("t1", [_call("read", a, field, {field: a, "status": "open"}), _effect_call(vocab_name, a, b, field, eid="e1")]),
        turn("t2", [_call("read", a, field, {field: a, "status": "posted"})]),
        turn("t3", [_effect_call(vocab_name, a, r(2), field, eid="e2")]),
    ]))
    before, after = posted(o(2))
    out.append(("state_diff_turn_1_and_turn_3", True, [
        turn("t1", [_call("effect", o(2), field, {field: o(2), "status": "posted"})], initial=before, final=after),
        turn("t2", [_call("read", o(2), field, {field: o(2), "status": "posted"})]),
        turn("t3", [_call("effect", o(2), field, {field: o(2), "status": "posted"})], initial=before, final={"rows": {o(2): {"status": "posted-again"}}}),
    ]))
    out.append(("two_minted_references", True, [
        turn("t1", [_effect_call(vocab_name, o(3), r(3), field, eid="e1")]),
        turn("t2", [_effect_call(vocab_name, o(3), r(4), field, eid="e2")]),
    ]))
    out.append(("effect_on_turn_2_and_turn_3", True, [
        turn("t1", [_call("read", o(4), field, {field: o(4)})]),
        turn("t2", [_effect_call(vocab_name, o(4), r(5), field, eid="e1")]),
        turn("t3", [_effect_call(vocab_name, o(4), r(6), field, eid="e2")]),
    ]))
    out.append(("two_reps_of_one_conversation", True, [
        turn("same", [_effect_call(vocab_name, o(5), r(7), field, eid="e1")], rep=0),
        turn("same", [_effect_call(vocab_name, o(5), r(8), field, eid="e2")], rep=1),
    ]))
    out.append(("attempt_key_changes_object_does_not", True, [
        turn("t1", [_effect_call(vocab_name, o(6), r(9), field, eid="e1", result_extra={"attempt_id": "AT-11"})]),
        turn("t2", [_effect_call(vocab_name, o(6), r(10), field, eid="e2", result_extra={"attempt_id": "AT-12"})]),
    ]))
    gov = o(7)
    out.append(("declared_governance_object", True, [
        turn("t1", [_call("effect", o(70), field, {"reference": r(11), field: o(70)}, ledger={"object": gov, "effect_id": "e1"})],
             spec={"goal": "move", "in_scope": [f"rows.{gov}"], "postconditions": []}),
        turn("t2", [_call("effect", o(71), field, {"reference": r(12), field: o(71)}, ledger={"object": gov, "effect_id": "e2"})],
             spec={"goal": "move", "in_scope": [f"rows.{gov}"], "postconditions": []}),
    ]))
    out.append(("reads_between_two_effects", True, [
        turn("t1", [_effect_call(vocab_name, o(8), r(13), field, eid="e1")]),
        turn("t2", [_call("read", o(8), field, {field: o(8)})]),
        turn("t3", [_call("read", o(8), field, {field: o(8)})]),
        turn("t4", [_effect_call(vocab_name, o(8), r(14), field, eid="e2")]),
    ]))
    out.append(("one_object_repeats_another_does_not", True, [
        turn("t1", [_effect_call(vocab_name, o(9), r(15), field, eid="e1"), _effect_call(vocab_name, o(90), r(16), field, eid="e3")]),
        turn("t2", [_effect_call(vocab_name, o(9), r(17), field, eid="e2")]),
    ]))
    out.append(("ledger_and_state_diff_together", True, [
        turn("t1", [_effect_call(vocab_name, o(10), r(18), field, eid="e1")], initial={"rows": {o(10): {"status": "open"}}}, final={"rows": {o(10): {"status": "posted"}}}),
        turn("t2", [_effect_call(vocab_name, o(10), r(19), field, eid="e2")], initial={"rows": {o(10): {"status": "posted"}}}, final={"rows": {o(10): {"status": "posted-again"}}}),
    ]))
    out.append(("later_followup_new_effect_id", True, [
        turn("t1", [_effect_call(vocab_name, o(11), r(20), field, eid="e1")]),
        turn("t2", [_effect_call(vocab_name, o(11), r(21), field, eid="e9")]),
    ]))
    out.append(("three_runs_middle_repeats", True, [
        turn("t1", [_effect_call(vocab_name, o(12), r(22), field, eid="e1")]),
        turn("t2", [_call("read", o(12), field)]),
        turn("t3", [_effect_call(vocab_name, o(12), r(23), field, eid="e2")]),
    ]))
    out.append(("same_ledger_object_field", True, [
        turn("t1", [_call("effect", o(13), field, {"reference": r(24), field: o(13)}, ledger={"object": o(13), "effect_id": "e1"})]),
        turn("t2", [_call("effect", o(13), field, {"reference": r(25), field: o(13)}, ledger={"object": o(13), "effect_id": "e2"})]),
    ]))

    # --- negatives -------------------------------------------------------------------------------
    out.append(("two_approvals_then_one_payout", False, [
        turn("t1", [_call("approve", o(14), field, {"approved": True, field: o(14)}, ledger={"object": o(14), "effect_id": "a1"})]),
        turn("t2", [_call("approve", o(14), field, {"approved": True, field: o(14)}, ledger={"object": o(14), "effect_id": "a2"})]),
        turn("t3", [_effect_call(vocab_name, o(14), r(26), field, eid="e1")]),
    ]))
    out.append(("idempotent_tool_repeated", False, [
        turn("t1", [_call("idem", o(15), field, {field: o(15), "status": "stored"}, ledger={"object": o(15), "effect_id": "i1"})]),
        turn("t2", [_call("idem", o(15), field, {field: o(15), "status": "stored"}, ledger={"object": o(15), "effect_id": "i2"})]),
    ]))
    out.append(("retry_after_error", False, [
        turn("t1", [_effect_call(vocab_name, o(16), r(27), field, eid="e0", error=True, ledger=False, result_extra={"error": "unavailable"})]),
        turn("t2", [_effect_call(vocab_name, o(16), r(28), field, eid="e1")]),
    ]))
    out.append(("two_different_objects", False, [
        turn("t1", [_effect_call(vocab_name, o(17), r(29), field, eid="e1")]),
        turn("t2", [_effect_call(vocab_name, o(18), r(30), field, eid="e2")]),
    ]))
    out.append(("replay_returns_same_reference", False, [
        turn("t1", [_effect_call(vocab_name, o(19), r(31), field, eid="e1")]),
        turn("t2", [_call("effect", o(19), field, {"reference": r(31), field: o(19), "status": "posted"})]),
    ]))
    out.append(("decision_record_changes_nothing", False, [
        turn("t1", [_call("record", o(20), field, {"decision": "hold", field: o(20)})]),
        turn("t2", [_call("record", o(20), field, {"decision": "hold", field: o(20)})]),
    ]))
    out.append(("calls_without_effects", False, [
        turn("t1", [_call("effect", o(21), field, {field: o(21), "status": "posted"})]),
        turn("t2", [_call("effect", o(21), field, {field: o(21), "status": "posted"})]),
    ]))
    out.append(("single_payout", False, [
        turn("t1", [_call("read", o(22), field), _effect_call(vocab_name, o(22), r(32), field, eid="e1")]),
    ]))
    out.append(("different_effect_kinds", False, [
        turn("t1", [_call("record", o(23), field, {"decision": "go", field: o(23)}, ledger={"object": o(23), "effect_id": "n1"})]),
        turn("t2", [_effect_call(vocab_name, o(23), r(33), field, eid="e1")]),
    ]))
    out.append(("noop_result_is_not_a_second_effect", False, [
        turn("t1", [_effect_call(vocab_name, o(24), r(34), field, eid="e1")]),
        turn("t2", [_call("effect", o(24), field, {"changed": False, "reference": r(34), field: o(24)}, ledger={"object": r(34), "effect_id": "e2"})]),
    ]))
    out.append(("second_call_errors", False, [
        turn("t1", [_effect_call(vocab_name, o(25), r(35), field, eid="e1")]),
        turn("t2", [_effect_call(vocab_name, o(25), r(36), field, eid="e2", error=True, ledger=False, result_extra={"error": "denied"})]),
    ]))
    out.append(("separate_conversations", False, [
        turn("t1", [_effect_call(vocab_name, o(26), r(37), field, eid="e1")], conversation="thread-one"),
        turn("t2", [_effect_call(vocab_name, o(26), r(38), field, eid="e2")], conversation="thread-two"),
    ]))
    return out


CASES = _cases("ledger")  # names and polarity; bodies are rebuilt per vocabulary
assert sum(1 for _, fail, _ in CASES) >= 10 and sum(1 for _, fail, _ in CASES if not fail) >= 10
assert len(CASES) >= 20


@pytest.mark.parametrize("name,expect_fail,_turns", CASES, ids=[c[0] for c in CASES])
@pytest.mark.parametrize("vocab_name", sorted(VOCAB))
@pytest.mark.parametrize("dialect", ["otlp", "langgraph"])
def test_family_agrees_across_vocabularies_and_dialects(name, expect_fail, _turns, vocab_name, dialect):
    turns = next(t for n, _f, t in _cases(vocab_name) if n == name)
    got = _status(turns, vocab_name, dialect)
    want = "fail" if expect_fail else "pass"
    assert got == {i: want for i in IDS}, (name, vocab_name, dialect, got)


def test_acceptance_shapes_are_in_the_family():
    names = {n for n, _, _ in CASES}
    assert {"payout_turn_1_and_turn_3", "two_approvals_then_one_payout", "idempotent_tool_repeated", "retry_after_error"} <= names


def test_within_run_duplicate_still_fails_and_approvals_still_pass():
    """The registry hook must not replace the existing within-run counter."""
    from agentest.standards.otel import Run, ToolSpan

    vocab = VOCAB["ledger"]
    field = vocab["field"]

    def t(name, args, result, *, error=False):
        return ToolSpan(name=name, args=args, result=json.dumps(result), error=error, actor="", t=1)

    pay = t(vocab["effect"], {field: "QA-1001"}, {"reference": "MV-1", field: "QA-1001", "status": "posted"})
    again = t(vocab["effect"], {field: "QA-1001"}, {"reference": "MV-2", field: "QA-1001", "status": "posted"})
    dup = Run(input_id="one", rep=0, input="go", answer="done", tools=[pay, again],
              effects=[{"kind": "executed", "effect": vocab["effect"], "data": {"object": "MV-1"}},
                       {"kind": "executed", "effect": vocab["effect"], "data": {"object": "MV-2"}}])
    ap = t(vocab["approve"], {field: "QA-1001"}, {"approved": True, field: "QA-1001"})
    one = Run(input_id="one", rep=0, input="go", answer="done", tools=[ap, ap, pay],
              effects=[{"kind": "executed", "effect": vocab["effect"], "data": {"object": "MV-1"}}],
              attrs={"agentest.task.spec": json.dumps({"goal": "move", "postconditions": []})})
    with no_judge():
        bad = evaluate(_agent(vocab), [dup], ids=list(IDS))
        good = evaluate(_agent(vocab), [one], ids=list(IDS))
    assert all(bad[i].status == "fail" for i in IDS)
    assert all(good[i].status == "pass" for i in IDS), {i: good[i].detail for i in IDS}
