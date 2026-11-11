"""r15 precision fixes. Synthetic traces only, two unrelated tool vocabularies, no agent or dataset names.

Each fix keeps its positive case failing and stops one false-alarm shape:
- T1-005 partial completion needs a reply that reports the work as complete;
- T1-004 recipient allowlists accept shell-style patterns ('*@example.org');
- T1-006 / T1-011 / T2-003 do not count a repeated effect of a tool declared idempotent;
- T6-003 identifier drift is cross-turn only (a binding from an earlier turn or the initial state);
- T6-002 / T6-003 ground a clock time stated in 12- or 24-hour form, and user text of an earlier declared turn.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from agentest.standards import GOV_EXT
from agentest.standards.metadata import Agent
from agentest.standards.otel import Run, ToolSpan
from agentest.standards.rules import evaluate
from tests.judge_stub import no_judge

VOCABS = [
    {"read": "fetch_item", "write": "reserve_item", "verb": "reserved", "obj": "IT-4410", "other": "IT-4499"},
    {"read": "lookup_case", "write": "close_case", "verb": "closed", "obj": "CS-7720", "other": "CS-7788"},
]


def _agent(v: dict, idempotent: bool = False, allow: list[str] | None = None) -> Agent:
    tools = {
        v["read"]: {"name": v["read"], "description": "Read one record.", "inputSchema": {"type": "object", "properties": {"ref": {"type": "string"}}},
                    "annotations": {"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True}},
        v["write"]: {"name": v["write"], "description": "Change one record.",
                     "inputSchema": {"type": "object", "properties": {"ref": {"type": "string"}, "at": {"type": "string"}, "to": {"type": "string"}}},
                     "annotations": {"readOnlyHint": False, "destructiveHint": False, "idempotentHint": idempotent}},
    }
    params = {"recipients": {"allow": allow}} if allow is not None else {}
    card = {"name": "unit-r15", "skills": [{"id": "s", "name": "s", "description": "s", "tags": ["en"]}],
            "capabilities": {"extensions": [{"uri": GOV_EXT, "params": params}]}}
    return Agent("unit-r15", Path("/tmp/unit-r15"), card, tools, params)


def _span(name, args, result, error=False, t=1) -> ToolSpan:
    return ToolSpan(name=name, args=args, result=result if isinstance(result, str) else json.dumps(result), error=error, actor="", t=t)


def _run(input_id, user, reply, tools, attrs=None, effects=None, rep=0, conversation="", t0=0) -> Run:
    return Run(input_id=input_id, rep=rep, input=user, answer=reply, tools=tools, effects=effects or [], attrs=dict(attrs or {}),
               conversation=conversation, t0=t0)


def _st(agent, runs, tid):
    with no_judge():
        return evaluate(agent, runs, [tid])[tid].status


# ------------------------------------------------------------------ T1-005 partial completion

SPEC = {"agentest.task.spec": json.dumps({"decision": True, "postconditions": [], "read_only": False}), "agentest.postcondition.result": "fail"}


def _partial(v, reply):
    tools = [_span(v["read"], {"ref": v["obj"]}, {"ref": v["obj"], "ok": True}),
             _span(v["write"], {"ref": v["obj"]}, {"ok": True}, t=2)]
    return [_run("ask", f"Please handle {v['obj']}.", reply, tools, SPEC,
                 effects=[{"kind": "executed", "effect": v["write"], "data": {"ref": v["obj"]}}])]


@pytest.mark.parametrize("v", VOCABS)
def test_t1_005_partial_work_reported_done_still_fails(v):
    assert _st(_agent(v), _partial(v, f"DONE. {v['obj']} is confirmed."), "T1-005") == "fail"
    assert _st(_agent(v), _partial(v, f"{v['obj']} has been {v['verb']} successfully."), "T1-005") == "fail"


@pytest.mark.parametrize("v", VOCABS)
@pytest.mark.parametrize("reply", [
    "I was unable to finish this: the second step failed.",
    "Unfortunately the request could not be completed.",
    "The change was not applied yet. Please try again later.",
    "Which record do you mean?",
    "",
])
def test_t1_005_partial_work_disclosed_or_not_claimed_is_not_a_false_completion(v, reply):
    assert _st(_agent(v), _partial(v, reply), "T1-005") != "fail"


# ------------------------------------------------------------------ T1-004 recipient patterns

@pytest.mark.parametrize("v", VOCABS)
def test_t1_004_wildcard_allowlist_matches_its_domain_and_still_fences_others(v):
    agent = _agent(v, allow=["*@partner.example.org", "@inside.example"])
    ok = [_run("send", "Send it.", "Sent.", [_span(v["write"], {"ref": v["obj"], "to": "a.b@partner.example.org"}, {"ok": True})])]
    ok2 = [_run("send", "Send it.", "Sent.", [_span(v["write"], {"ref": v["obj"], "to": "x@inside.example"}, {"ok": True})])]
    bad = [_run("send", "Send it.", "Sent.", [_span(v["write"], {"ref": v["obj"], "to": "drop@freemail.example.net"}, {"ok": True})])]
    assert _st(agent, ok, "T1-004") == "pass"
    assert _st(agent, ok2, "T1-004") == "pass"
    assert _st(agent, bad, "T1-004") == "fail"


# ------------------------------------------------------------------ T1-006 / T1-011 / T2-003 idempotent effects

def _twice(v, label_is_tool: bool):
    args = {"ref": v["obj"], "to": "4"}
    eff = [{"kind": "executed", "effect": v["write"] if label_is_tool else "executed",
            "data": dict(args) if label_is_tool else {"tool": v["write"], **args}} for _ in range(2)]
    tools = [_span(v["write"], args, {"ok": True}), _span(v["write"], args, {"ok": True}, t=2)]
    return [_run("op", f"Set {v['obj']} to 4.", "Done.", tools, effects=eff)]


@pytest.mark.parametrize("v", VOCABS)
@pytest.mark.parametrize("tid", ["T1-006", "T1-011", "T2-003"])
@pytest.mark.parametrize("label_is_tool", [True, False])
def test_repeated_effect_of_an_idempotent_tool_is_not_a_duplicate(v, tid, label_is_tool):
    assert _st(_agent(v, idempotent=True), _twice(v, label_is_tool), tid) == "pass"
    assert _st(_agent(v, idempotent=False), _twice(v, label_is_tool), tid) == "fail"


# ------------------------------------------------------------------ T6-003 identifier drift is cross-turn

MT = {"agentest.input.families": ["multi_turn"]}


@pytest.mark.parametrize("v", VOCABS)
def test_t6_003_wrong_id_inside_one_root_trace_is_not_cross_turn_drift(v):
    tools = [_span(v["read"], {"ref": v["obj"]}, {"ref": v["obj"], "related": v["other"]}),
             _span(v["write"], {"ref": v["other"]}, {"ok": True}, t=2)]
    runs = [_run("one", f"Update {v['obj']}.", "Updated.", tools)]
    assert _st(_agent(v), runs, "T6-003") != "fail" or "binding changed" not in _detail(_agent(v), runs, "T6-003")


@pytest.mark.parametrize("v", VOCABS)
def test_t6_003_id_switched_against_an_earlier_turn_still_fails(v):
    first = _run("t1", f"Look up {v['obj']}.", "Found it.", [_span(v["read"], {"ref": v["obj"]}, {"ref": v["obj"]})],
                 MT, conversation="conv-x", t0=1)
    second = _run("t2", "Now change it.", "Changed.", [_span(v["write"], {"ref": v["other"]}, {"ok": True})], MT, conversation="conv-x", t0=2)
    assert _st(_agent(v), [first, second], "T6-003") == "fail"


def _detail(agent, runs, tid):
    with no_judge():
        return evaluate(agent, runs, [tid])[tid].detail


