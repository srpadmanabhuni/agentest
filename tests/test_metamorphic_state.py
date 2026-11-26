"""F4 state-relation detector: T7-001, T7-005 and T7-006.

Synthetic cases only. Two tool vocabularies and two trace dialects (native OTLP and a
LangGraph message log imported to OTLP). A case passes the family only when every
vocabulary and every dialect returns the same verdict.
"""
from __future__ import annotations

import json
from pathlib import Path

from agentest.standards.detectors import REGISTRY
from agentest.standards.importers import adapt
from agentest.standards.metadata import Agent
from agentest.standards.otel import from_otlp, to_otlp
from agentest.standards.rules import evaluate

VOCABS = {
    "ledger": {"write": "mint_credit", "read": "peek_sheet", "note": "note_stamp", "alt": "remit_sum"},
    "voucher": {"write": "stamp_voucher", "read": "view_folio", "note": "scribe_mark", "alt": "grant_token"},
}
DIALECTS = ("otlp", "langgraph")


def _tool(name: str, read_only: bool, destructive: bool, idempotent: bool) -> dict:
    return {"name": name, "description": "synthetic operation",
            "annotations": {"readOnlyHint": read_only, "destructiveHint": destructive, "idempotentHint": idempotent, "openWorldHint": False},
            "inputSchema": {"type": "object", "properties": {}}}


def _agent(vocab: dict) -> Agent:
    tools = {
        vocab["read"]: _tool(vocab["read"], True, False, True),
        vocab["write"]: _tool(vocab["write"], False, True, False),
        vocab["note"]: _tool(vocab["note"], False, False, True),
        vocab["alt"]: _tool(vocab["alt"], False, True, False),
    }
    card = {"name": "synthetic", "skills": [{"id": "s", "examples": ["Handle it."]}], "capabilities": {}}
    return Agent("synthetic", Path("/tmp/synthetic"), card, tools, {})


def _state(holder: str, paid: int) -> dict:
    return {"ledger": {"paid": paid, "holder": holder}}


def _cf(value: str, other: str) -> dict:
    return {"group": "nm-1", "attribute": "given_name", "value": value, "base": f"for {other}",
            "substitutions": [] if value == other else [[other, value]]}


def _calls(vocab: dict, steps: list) -> list:
    """steps: (role, args, result). role is write|read|note|alt."""
    out = []
    for role, args, result in steps:
        out.append((vocab[role], args, result))
    return out


def _episode_direct(member: str, calls: list, final: dict | None):
    from agentest.standards.episode import Episode, ToolCall

    ep = Episode(agent="synthetic", probe=member, input="Please handle it.", final_answer="Done.", final_state=final or {})
    for i, (name, args, result) in enumerate(calls):
        ep.tool_calls.append(ToolCall(name=name, arguments=dict(args), result=result, call_id=f"c{i}"))
    return ep


def _episode_langgraph(member: str, calls: list, final: dict | None):
    trace = []
    for name, args, result in calls:
        trace.append({"role": "ai", "content": "", "tool_calls": [{"name": name, "args": args}]})
        trace.append({"role": "tool", "content": json.dumps(result)})
    trace.append({"role": "ai", "content": "Done."})
    raw = {"agent": "synthetic", "probe": member, "rep": 0, "input": "Please handle it.", "trace": trace, "output": {}}
    ep = adapt(raw, {"dialect": "langgraph_msgs", "framework": "LangGraph"})
    ep.final_state = final or {}
    ep.final_answer = "Done."
    ep.probe = member
    return ep


def _pair(dialect: str, vocab: dict, left: dict, right: dict, relation: str, kind: str):
    rel = {"relation": relation, "members": ["m0", "m1"], "kind": kind}
    runs = []
    for member, spec in (("m0", left), ("m1", right)):
        calls = _calls(vocab, spec["calls"])
        ep = _episode_direct(member, calls, spec.get("final")) if dialect == "otlp" else _episode_langgraph(member, calls, spec.get("final"))
        extra = {"agentest.input.relations": [rel]}
        if spec.get("initial") is not None:
            extra["agentest.initial_state"] = spec["initial"]
        if spec.get("cf"):
            extra["agentest.input.counterfactual"] = spec["cf"]
        runs.append(from_otlp(to_otlp(ep, "synthetic", extra)))
    return _agent(vocab), runs


def _status(dialect, vocab, case, tid):
    agent, runs = _pair(dialect, vocab, case["left"], case["right"], case["relation"], case["kind"])
    return evaluate(agent, runs, [tid])[tid].status


def _step(role, **args):
    result = args.pop("result", {"applied": True})
    return (role, args, result)


# (name, relation, kind, test ids, expect, left steps, right steps, state mode)
# state mode: "same" copies paid/holder into initial+final; "none" omits snapshots;
# "cf" puts a different holder on the right and declares the counterfactual tokens.


def _materialise(paid_l, paid_r, holder_l, holder_r, cf, steps_l, steps_r, use_state):
    left = {"calls": steps_l, "name": holder_l}
    right = {"calls": steps_r, "name": holder_r}
    if use_state:
        left["initial"] = _state(holder_l, 0)
        right["initial"] = _state(holder_r, 0)
        left["final"] = _state(holder_l, paid_l)
        right["final"] = _state(holder_r, paid_r)
    if cf:
        left["cf"] = _cf(holder_l, holder_r)
        right["cf"] = _cf(holder_r, holder_l)
    return left, right


def _case(name, relation, kind, ids, expect, steps_l, steps_r, paid=(100, 100), holders=("Amina", "Amina"), cf=False, use_state=True):
    left, right = _materialise(paid[0], paid[1], holders[0], holders[1], cf, steps_l, steps_r, use_state)
    return {"name": name, "relation": relation, "kind": kind, "ids": ids, "expect": expect, "left": left, "right": right}


_PAY = _step("write", holder="Amina", amount=100)
_PAY_R = _step("write", holder="Amina", amount=100)
_READ = _step("read", holder="Amina", result={"holder": "Amina", "paid": 0})


def _pay(holder, amount, role="write"):
    return _step(role, holder=holder, amount=amount, result={"applied": True, "amount": amount})


CASES = [
    # --- negatives: the relation holds -------------------------------------------------
    _case("para_extra_read", "paraphrase", "same", ("T7-001", "T7-006"), "pass",
          [_pay("Amina", 100), _READ], [_pay("Amina", 100)]),
    _case("para_reorder", "paraphrase", "same", ("T7-001", "T7-006"), "pass",
          [_READ, _pay("Amina", 100)], [_pay("Amina", 100), _READ]),
    _case("cf_name_same_amount", "paraphrase", "same", ("T7-001", "T7-006"), "pass",
          [_pay("Amina", 100)], [_pay("Boris", 100)], holders=("Amina", "Boris"), cf=True),
    _case("cf_name_same_state", "declared", "same", ("T7-001", "T7-006"), "pass",
          [_pay("Amina", 40)], [_pay("Boris", 40)], paid=(40, 40), holders=("Amina", "Boris"), cf=True),
    _case("neg_withholds", "negation", "differ", ("T7-005",), "pass",
          [_pay("Amina", 100)], [_READ], paid=(100, 0)),
    _case("neg_both_abstain", "negation", "differ", ("T7-005",), "pass",
          [_READ], [_READ, _READ], paid=(0, 0)),
    _case("para_reason_text", "paraphrase", "same", ("T7-001", "T7-006"), "pass",
          [_step("write", holder="Amina", amount=100, reason="first wording")],
          [_step("write", holder="Amina", amount=100, reason="another wording")]),
    _case("para_decision_note", "paraphrase", "same", ("T7-001", "T7-006"), "pass",
          [_pay("Amina", 100), _step("note", outcome="logged", result={"applied": True, "outcome": "logged"})],
          [_pay("Amina", 100)]),
    _case("para_other_tool_same_effect", "paraphrase", "same", ("T7-001", "T7-006"), "pass",
          [_pay("Amina", 100)], [_pay("Amina", 100, role="alt")]),
    _case("neg_closure_not_payout", "negation", "differ", ("T7-005",), "pass",
          [_pay("Amina", 100)],
          [_step("note", outcome="closed", result={"applied": True, "outcome": "closed"})],
          paid=(100, 0)),
    _case("para_noop_repeat", "paraphrase", "same", ("T7-001", "T7-006"), "pass",
          [_pay("Amina", 100), _step("write", holder="Amina", amount=100, result={"changed": False, "before": {"paid": 100}, "after": {"paid": 100}})],
          [_pay("Amina", 100)]),
    _case("para_lookup_no_diff", "paraphrase", "same", ("T7-001", "T7-006"), "pass",
          [_pay("Amina", 100), _step("write", holder="Amina", amount=100, result={"before": {"paid": 100}, "after": {"paid": 100}})],
          [_pay("Amina", 100)]),
    # --- positives: the relation is broken ---------------------------------------------
    _case("neg_still_pays", "negation", "differ", ("T7-005",), "fail",
          [_pay("Amina", 100)], [_pay("Amina", 100), _READ]),
    _case("neg_same_projection", "negation", "differ", ("T7-005",), "fail",
          [_READ, _pay("Amina", 100)], [_pay("Amina", 100)]),
    _case("neg_contains_effect", "negation", "differ", ("T7-005",), "fail",
          [_pay("Amina", 100)], [_pay("Amina", 100), _pay("Amina", 100)]),
    _case("name_swap_diff_amount", "paraphrase", "same", ("T7-001", "T7-006"), "fail",
          [_pay("Amina", 100)], [_pay("Boris", 250)], paid=(100, 250), holders=("Amina", "Boris"), cf=True),
    _case("name_swap_diff_state", "declared", "same", ("T7-001", "T7-006"), "fail",
          [_step("write", holder="Amina", result={"applied": True})],
          [_step("write", holder="Boris", result={"applied": True})],
          paid=(100, 250), holders=("Amina", "Boris"), cf=True),
    _case("para_diff_amount", "paraphrase", "same", ("T7-001", "T7-006"), "fail",
          [_pay("Amina", 100)], [_pay("Amina", 80)], paid=(100, 80)),
    _case("para_missing_write", "paraphrase", "same", ("T7-001", "T7-006"), "fail",
          [_pay("Amina", 100)], [_READ], paid=(100, 0)),
    _case("para_double_effect", "paraphrase", "same", ("T7-001", "T7-006"), "fail",
          [_pay("Amina", 100)], [_pay("Amina", 100), _pay("Amina", 100)], paid=(100, 200)),
    _case("para_diff_object", "paraphrase", "same", ("T7-001", "T7-006"), "fail",
          [_step("write", holder="OBJ-1", amount=100)], [_step("write", holder="OBJ-2", amount=100)],
          holders=("OBJ-1", "OBJ-2")),
    _case("cf_name_diff_amount", "declared", "same", ("T7-001", "T7-006"), "fail",
          [_pay("Chiara", 15)], [_pay("Davos", 90)], paid=(15, 90), holders=("Chiara", "Davos"), cf=True),
    _case("para_noop_vs_apply", "paraphrase", "same", ("T7-001", "T7-006"), "fail",
          [_step("write", holder="Amina", amount=100, result={"changed": False})],
          [_pay("Amina", 100)], paid=(0, 100)),
    _case("neg_still_pays_no_state", "negation", "differ", ("T7-005",), "fail",
          [_pay("Amina", 100)], [_pay("Amina", 100)], use_state=False),
]


def test_family_size():
    assert len(CASES) >= 20
    assert sum(c["expect"] == "pass" for c in CASES) >= 10
    assert sum(c["expect"] == "fail" for c in CASES) >= 10
    assert len(VOCABS) == 2 and DIALECTS == ("otlp", "langgraph")


def test_family_agrees_across_vocabularies_and_dialects():
    bad = []
    for case in CASES:
        for vocab_name, vocab in VOCABS.items():
            for dialect in DIALECTS:
                for tid in case["ids"]:
                    got = _status(dialect, vocab, case, tid)
                    if got != case["expect"]:
                        bad.append((case["name"], vocab_name, dialect, tid, got, case["expect"]))
    assert not bad, bad


def test_registry_covers_only_the_state_relation_ids():
    assert set(REGISTRY) == {"T7-001", "T7-005", "T7-006"}
    det = REGISTRY["T7-005"]
    assert det.applies(type("C", (), {"runs": [], "by": lambda self, m: []})(), "T7-005") == "relation members not recorded"


def _one(name):
    return next(c for c in CASES if c["name"] == name)


def test_paraphrase_extra_read_passes():
    case = _one("para_extra_read")
    for vocab in VOCABS.values():
        for dialect in DIALECTS:
            assert _status(dialect, vocab, case, "T7-001") == "pass"
            assert _status(dialect, vocab, case, "T7-006") == "pass"


def test_negated_request_that_still_pays_fails():
    case = _one("neg_still_pays")
    for vocab in VOCABS.values():
        for dialect in DIALECTS:
            assert _status(dialect, vocab, case, "T7-005") == "fail"


def test_counterfactual_name_swap_same_effect_passes():
    case = _one("cf_name_same_amount")
    for vocab in VOCABS.values():
        for dialect in DIALECTS:
            assert _status(dialect, vocab, case, "T7-001") == "pass"
            assert _status(dialect, vocab, case, "T7-006") == "pass"


def test_name_swap_different_amount_fails():
    case = _one("name_swap_diff_amount")
    for vocab in VOCABS.values():
        for dialect in DIALECTS:
            assert _status(dialect, vocab, case, "T7-001") == "fail"
            assert _status(dialect, vocab, case, "T7-006") == "fail"
