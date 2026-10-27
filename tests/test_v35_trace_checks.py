"""v3.5 (4): multi-span loop (X-021), thrash (X-022), recursion (X-023) and state drift (X-024), incl. negatives."""

from __future__ import annotations

import json
from pathlib import Path

from agentest.standards import rules
from agentest.standards.metadata import Agent
from agentest.standards.otel import Run, ToolSpan, from_otlp

RO = {"readOnlyHint": True}
W = {"readOnlyHint": False, "destructiveHint": False}
IDEM = {"readOnlyHint": False, "destructiveHint": False, "idempotentHint": True}


def agent(tools: dict, gov: dict | None = None) -> Agent:
    return Agent("t", Path("."), {"name": "t", "skills": []}, {n: {"name": n, "annotations": a} for n, a in tools.items()}, gov or {})


def call(name, t, error=False, result="", **args):
    return ToolSpan(name, args, result, error, "", t)


def run(*tools, spans=None, handoffs=None, final_state=None, rid="i1") -> Run:
    r = Run(rid, 0, "do it", "done", tools=list(tools), handoffs=handoffs or [], final_state=final_state or {})
    r.spans = spans or []
    return r


def verdict(i, a, *runs):
    return rules.evaluate(a, list(runs), [i])[i]


TOOLS = {"get": RO, "put": W, "set_status": IDEM, "reserve": W, "release": W, "lookup": RO}


# ------------------------------------------------------------------ X-021

def test_x021_loop_of_two_calls_three_times_fails():
    seq = [call("get", i * 2, id="A") if i % 2 == 0 else call("put", i * 2, id="A", v=1) for i in range(6)]
    v = verdict("X-021", agent(TOOLS), run(*seq))
    assert v.status == "fail" and "get→put" in v.detail


def test_x021_negatives_progress_twice_and_single_tool():
    a = agent(TOOLS)
    progress = [call("get" if i % 2 == 0 else "put", i, id=f"A{i // 2}") for i in range(6)]  # new object each cycle
    assert verdict("X-021", a, run(*progress)).status == "pass"
    twice = [call("get", 0, id="A"), call("put", 1, id="A"), call("get", 2, id="A"), call("put", 3, id="A"), call("lookup", 4), call("lookup", 5, q=1)]
    assert verdict("X-021", a, run(*twice)).status == "pass"
    same = [call("get", i, id="A") for i in range(6)]  # one tool repeated: X-004's job, not a multi-span loop
    assert verdict("X-021", a, run(*same)).status == "pass"
    assert verdict("X-021", a, run(call("get", 0))).status == "n/a"


def test_x021_threshold_from_budget(monkeypatch):
    monkeypatch.setitem(rules.BUDGET, "loop_cycles", 2)
    seq = [call("get", 0, id="A"), call("put", 1, id="A"), call("get", 2, id="A"), call("put", 3, id="A")]
    assert verdict("X-021", agent(TOOLS), run(*seq)).status == "fail"


# ------------------------------------------------------------------ X-022

def test_x022_set_change_set_back_fails():
    seq = [call("put", 0, id="A", status="open"), call("put", 1, id="A", status="closed"), call("put", 2, id="A", status="open")]
    v = verdict("X-022", agent(TOOLS), run(*seq))
    assert v.status == "fail" and "status" in v.detail


def test_x022_do_undo_redo_with_published_compensation():
    seq = [call("reserve", 0, sku="S1", qty=2), call("release", 1, sku="S1"), call("reserve", 2, sku="S1", qty=2)]
    assert verdict("X-022", agent(TOOLS, {"compensations": {"reserve": "release"}}), run(*seq)).status == "fail"
    assert verdict("X-022", agent(TOOLS), run(*seq)).status == "pass"  # without the published undo relation: no claim


def test_x022_negatives():
    a = agent(TOOLS)
    distinct = [call("put", 0, id="A", status="open"), call("put", 1, id="B", status="closed"), call("put", 2, id="A", status="open")]
    assert verdict("X-022", a, run(*distinct)).status == "pass"  # middle write is another object
    forward = [call("put", 0, id="A", status="new"), call("put", 1, id="A", status="open"), call("put", 2, id="A", status="closed")]
    assert verdict("X-022", a, run(*forward)).status == "pass"
    failed_middle = [call("put", 0, id="A", s=1), call("put", 1, error=True, id="A", s=2), call("put", 2, id="A", s=1)]
    assert verdict("X-022", a, run(*failed_middle)).status == "n/a"  # only 2 successful writes
    assert verdict("X-022", a, run(call("put", 0, id="A"))).status == "n/a"


# ------------------------------------------------------------------ X-023

def sp(i, parent, op, agent="", tool=""):
    return {"op": op, "name": f"{op} {agent or tool}", "agent": agent, "t0": i, "t1": i + 1, "id": f"s{i}", "parent": parent, "tool": tool}


def test_x023_agent_nested_in_itself_three_deep_fails():
    spans = [sp(0, "", "invoke_agent", "planner"), sp(1, "s0", "invoke_agent", "planner"), sp(2, "s1", "chat", "planner"),
             sp(3, "s2", "invoke_agent", "planner")]
    v = verdict("X-023", agent(TOOLS), run(spans=spans))
    assert v.status == "fail" and "planner nested 3x" in v.detail


def test_x023_handoff_ping_pong_fails_and_back_to_triage_passes():
    a = agent(TOOLS)
    ping = [("triage", "billing", 1), ("billing", "triage", 2), ("triage", "billing", 3), ("billing", "triage", 4), ("triage", "billing", 5)]
    assert verdict("X-023", a, run(handoffs=ping)).status == "fail"
    back = [("triage", "billing", 1), ("billing", "triage", 2)]
    assert verdict("X-023", a, run(handoffs=back)).status == "pass"


def test_x023_negatives_distinct_nesting_and_no_signal():
    a = agent(TOOLS)
    spans = [sp(0, "", "invoke_agent", "router"), sp(1, "s0", "invoke_agent", "billing"), sp(2, "s1", "execute_tool", tool="get"),
             sp(3, "s0", "invoke_agent", "router")]  # router twice, but siblings, not nested
    assert verdict("X-023", a, run(spans=spans)).status == "pass"
    assert verdict("X-023", a, run(spans=[sp(0, "", "chat")])).status == "n/a"


def test_x023_from_otlp_uses_span_ids():
    def s(sid, parent, name, attrs):
        return {"traceId": "t" * 32, "spanId": sid, "parentSpanId": parent, "name": name, "startTimeUnixNano": str(int(sid, 16)),
                "endTimeUnixNano": str(int(sid, 16) + 10), "attributes": [{"key": k, "value": {"stringValue": v}} for k, v in attrs.items()]}
    spans = [s("0000000000000001", "", "invoke_agent a", {"gen_ai.operation.name": "invoke_agent", "gen_ai.agent.name": "a"}),
             s("0000000000000002", "0000000000000001", "invoke_agent a", {"gen_ai.operation.name": "invoke_agent", "gen_ai.agent.name": "a"}),
             s("0000000000000003", "0000000000000002", "invoke_agent a", {"gen_ai.operation.name": "invoke_agent", "gen_ai.agent.name": "a"})]
    r = from_otlp({"resourceSpans": [{"scopeSpans": [{"spans": spans}]}]})
    assert [x["parent"] for x in r.spans] == ["", "0000000000000001", "0000000000000002"]
    assert verdict("X-023", agent(TOOLS), r).status == "fail"


# ------------------------------------------------------------------ X-024

def test_x024_read_after_write_shows_other_value_fails():
    seq = [call("set_status", 0, ticket_id="T1", status="closed"), call("lookup", 1, result=json.dumps({"ticket_id": "T1", "status": "open"}), ticket_id="T1")]
    v = verdict("X-024", agent(TOOLS), run(*seq))
    assert v.status == "fail" and "status='closed'" in v.detail


def test_x024_final_state_contradicts_last_write_fails():
    r = run(call("set_status", 0, ticket_id="T1", status="closed"), final_state={"tickets": [{"ticket_id": "T1", "status": "open"}]})
    assert verdict("X-024", agent(TOOLS), r).status == "fail"


def test_x024_negatives():
    a = agent(TOOLS)
    held = run(call("set_status", 0, ticket_id="T1", status="closed", priority=2),
               call("lookup", 1, result=json.dumps({"ticket_id": "T1", "status": "closed", "priority": 2.0}), ticket_id="T1"),
               final_state={"tickets": [{"ticket_id": "T1", "status": "closed"}, {"ticket_id": "T2", "status": "open"}]})
    assert verdict("X-024", a, held).status == "pass"  # numbers compare by value; other objects are not compared
    rewritten = run(call("set_status", 0, ticket_id="T1", status="closed"), call("set_status", 1, ticket_id="T1", status="open"),
                    final_state={"tickets": [{"ticket_id": "T1", "status": "open"}]})
    assert verdict("X-024", a, rewritten).status == "pass"  # the later write is the one the end state must show
    non_idem = run(call("put", 0, order_id="O1", amount=50), final_state={"orders": [{"order_id": "O1", "amount": 100}]})
    assert verdict("X-024", a, non_idem).status == "n/a"  # a non-idempotent write (e.g. a refund) does not set a field
    gated = run(call("set_status", 0, ticket_id="T1", status="closed"), final_state={"tickets": [{"ticket_id": "T1", "status": "open"}]})
    host = agent(TOOLS, {"approval": {"required": ["set_status"], "hostGated": True}})
    assert verdict("X-024", host, gated).status == "pass"  # the host may hold a gated write back


def test_ids_registered():
    from agentest.standards.catalog import ALL_IDS, X_WHAT

    assert {"X-021", "X-022", "X-023", "X-024"} <= set(X_WHAT) & set(rules.RULES) & set(ALL_IDS)
