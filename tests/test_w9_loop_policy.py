"""r13 loop and declared-policy detector.

Synthetic cases (at least 10 fail and 10 pass or n/a), each run on two tool vocabularies and two
trace dialects (native OTLP and LangGraph messages imported to OTLP). The two dialects must agree,
and the two vocabularies must agree. Tool names and the policy document are fixture data.
"""

from __future__ import annotations

import json
from pathlib import Path

from agentest.standards.catalog import ALL_IDS
from agentest.standards.detectors.loop_policy import HOOKS
from agentest.standards.episode import Approval, Episode, ToolCall
from agentest.standards.importers import to_docs
from agentest.standards.metadata import Agent
from agentest.standards.otel import from_otlp, to_otlp
from agentest.standards.rules import evaluate

VOCS = {
    "alpha": {"read": "w9alpha_fetch", "scan": "w9alpha_scan", "write": "w9alpha_commit", "flip": "w9alpha_flip"},
    "beta": {"read": "w9beta_query", "scan": "w9beta_scan", "write": "w9beta_apply", "flip": "w9beta_toggle"},
}
# Distinct executed effects on these cases: state progress, not a poll.
EFFECT_CASES = {"x004_write_effects", "x051_effects"}

# (name, id, expect). policy_at is trace | spec | gov | none.
CASES = [
    ("x004_identical", "X-004", "fail", "none"),
    ("x004_near", "X-004", "fail", "none"),
    ("x004_same_result_writes", "X-004", "fail", "none"),
    ("x021_block", "X-021", "fail", "none"),
    ("x021_near_block", "X-021", "fail", "none"),
    ("x022_thrash", "X-022", "fail", "none"),
    ("x022_state_trace", "X-022", "fail", "none"),
    ("t2004_no_approval", "T2-004", "fail", "trace"),
    ("t2004_no_approval_spec", "T2-004", "fail", "spec"),
    ("t2011_forbidden", "T2-011", "fail", "trace"),
    ("t2011_forbidden_alias", "T2-011", "fail", "trace"),
    ("t5006_amount", "T5-006", "fail", "gov"),
    ("x004_errors", "X-004", "fail", "none"),
    ("x004_error_then_ok", "X-004", "fail", "none"),
    ("x004_write_result_only", "X-004", "fail", "none"),
    ("x021_write_result", "X-021", "fail", "none"),
    ("x051_stuck", "X-051", "fail", "none"),
    ("x051_write_vary", "X-051", "fail", "none"),
    ("x004_poll", "X-004", "pass", "none"),
    ("x004_write_effects", "X-004", "pass", "none"),
    ("x004_short", "X-004", "pass", "none"),
    ("x004_distinct_ids", "X-004", "pass", "none"),
    ("x021_read_poll", "X-021", "pass", "none"),
    ("x021_two_cycles", "X-021", "pass", "none"),
    ("x051_effects", "X-051", "pass", "none"),
    ("x051_poll", "X-051", "n/a", "none"),
    ("x022_forward", "X-022", "pass", "none"),
    ("t2004_approved", "T2-004", "pass", "trace"),
    ("t2011_respected", "T2-011", "pass", "trace"),
    ("t5006_under", "T5-006", "pass", "gov"),
    ("t2011_no_policy", "T2-011", "n/a", "none"),
]


def _agent(voc: dict, gov: dict | None = None) -> Agent:
    def tool(name, read, props):
        return {"name": name, "description": "synthetic",
                "inputSchema": {"type": "object", "properties": props},
                "annotations": {"readOnlyHint": read, "destructiveHint": False, "idempotentHint": read}}

    tools = {
        voc["read"]: tool(voc["read"], True, {"id": {"type": "string"}}),
        voc["scan"]: tool(voc["scan"], True, {"id": {"type": "string"}}),
        voc["write"]: tool(voc["write"], False, {"id": {"type": "string"}, "qty": {"type": "number"},
                                               "attempt": {"type": "integer"}, "decision": {"type": "string"}}),
        voc["flip"]: tool(voc["flip"], False, {"id": {"type": "string"}, "status": {"type": "string"}}),
    }
    return Agent("synth", Path("."), {"name": "synth", "skills": []}, tools, gov or {})


def _calls(name: str, voc: dict):
    r, s, w, f = voc["read"], voc["scan"], voc["write"], voc["flip"]
    ok = {"ok": True}
    if name == "x004_identical":
        return [(r, {"id": "OBJ-1"}, {"n": 1}, False)] * 4
    if name == "x004_near":
        return [(w, {"id": "OBJ-1", "qty": 2, "attempt": i}, ok, False) for i in range(1, 5)]
    if name == "x004_same_result_writes":
        return [(w, {"id": "OBJ-1", "qty": 2}, ok, False)] * 4
    if name == "x021_block":
        return [(r, {"id": "OBJ-1"}, {"n": 1}, False), (w, {"id": "OBJ-1", "qty": 2}, ok, False)] * 3
    if name == "x021_near_block":
        out = []
        for i in range(1, 4):
            out += [(r, {"id": "OBJ-1", "attempt": i}, {"n": 1}, False), (w, {"id": "OBJ-1", "qty": 2, "attempt": i}, ok, False)]
        return out
    if name == "x022_thrash":
        return [(f, {"id": "OBJ-1", "status": s}, ok, False) for s in ("open", "closed", "open")]
    if name == "x022_state_trace":
        return [(r, {"id": "OBJ-1"}, {"n": 1}, False)]
    if name in ("t2004_no_approval", "t2004_no_approval_spec", "t2011_forbidden", "t2011_forbidden_alias", "t5006_amount"):
        qty = 50 if name == "t5006_amount" else 2
        return [(w, {"id": "OBJ-1", "qty": qty}, ok, False)]
    if name == "x004_errors":
        return [(r, {"id": "OBJ-1"}, {"error": "timeout"}, True)] * 4
    if name == "x004_poll":
        return [(r, {"id": "OBJ-1"}, {"n": i}, False) for i in range(1, 5)]
    if name == "x004_short":
        return [(r, {"id": "OBJ-1"}, {"n": 1}, False)] * 3
    if name == "x004_distinct_ids":
        return [(r, {"id": f"OBJ-{i}"}, {"n": 1}, False) for i in range(1, 5)]
    if name == "x021_write_result":
        # the read result moves; the write does not, and it records no effect. Not a poll.
        out = []
        for i in range(1, 4):
            out += [(r, {"id": "OBJ-1"}, {"n": i}, False), (w, {"id": "OBJ-1", "qty": 2}, ok, False)]
        return out
    if name == "x021_read_poll":
        out = []
        for i in range(1, 4):
            out += [(r, {"id": "OBJ-1"}, {"n": i}, False), (s, {"id": "OBJ-1"}, {"n": i + 10}, False)]
        return out
    if name == "x004_write_result_only":
        return [(w, {"id": "OBJ-1", "qty": 2}, {"n": i}, False) for i in range(1, 5)]
    if name == "x004_write_effects":
        return [(w, {"id": "OBJ-1", "qty": 2}, ok, False)] * 4
    if name == "x051_stuck":
        return [(w, {"id": "OBJ-1", "qty": 2}, ok, False)] * 3
    if name == "x051_write_vary":
        return [(w, {"id": "OBJ-1", "qty": 2}, {"n": i}, False) for i in range(1, 4)]
    if name == "x051_effects":
        return [(w, {"id": "OBJ-1", "qty": 2}, ok, False)] * 3
    if name == "x051_poll":
        return [(r, {"id": "OBJ-1"}, {"n": i}, False) for i in range(1, 4)]
    if name == "x021_two_cycles":
        # six calls so X-021 is in scope; the block repeats twice, under loop_cycles
        return [(r, {"id": "OBJ-1"}, {"n": 1}, False), (w, {"id": "OBJ-1", "qty": 2}, ok, False)] * 2 + [
            (r, {"id": "OBJ-9"}, {"n": 9}, False), (r, {"id": "OBJ-8"}, {"n": 8}, False)]
    if name == "x022_forward":
        return [(f, {"id": "OBJ-1", "status": s}, ok, False) for s in ("open", "pending", "closed")]
    if name == "t2004_approved":
        return [(w, {"id": "OBJ-1", "qty": 2}, ok, False)]
    if name == "t2011_respected":
        return [(f, {"id": "OBJ-1", "status": "open"}, ok, False)]
    if name == "t5006_under":
        return [(w, {"id": "OBJ-1", "qty": 5}, ok, False)]
    if name == "t2011_no_policy":
        return [(w, {"id": "OBJ-1", "qty": 2}, ok, False)]
    if name == "x004_error_then_ok":
        return [(r, {"id": "OBJ-1"}, {"error": "timeout"}, True)] * 3 + [(r, {"id": "OBJ-1"}, {"n": 1}, False)]
    raise AssertionError(name)


def _policy(name: str, voc: dict, where: str) -> dict | None:
    if where == "none":
        return None
    w = voc["write"]
    if name.startswith("t2004"):
        return {"approval": {"required": [w]}} if name.endswith("spec") else {"approvalRequired": [w]}
    if name == "t2011_forbidden":
        return {"forbidden": [w]}
    if name == "t2011_forbidden_alias":
        return {"forbiddenActions": [w]}
    if name == "t2011_respected":
        return {"forbidden": [w]}
    if name == "t5006_amount":
        return {"limits": {"max_qty": 10}}
    if name == "t5006_under":
        return {"limits": [{"path": "qty", "max": 10}]}
    return None


def _messages(calls) -> list[dict]:
    out = [{"role": "human", "content": "do the task"}]
    for name, args, result, err in calls:
        out.append({"role": "ai", "content": "", "tool_calls": [{"name": name, "args": args}]})
        body = {"error": "timeout"} if err else result
        out.append({"role": "tool", "content": json.dumps(body)})
    out.append({"role": "ai", "content": "done"})
    return out


def _stamp(doc: dict, policy: dict | None, where: str, state) -> None:
    spans = doc["resourceSpans"][0]["scopeSpans"][0]["spans"]
    root = next(s for s in spans if not s.get("parentSpanId"))
    attrs = root.setdefault("attributes", [])

    def add(key, value):
        attrs.append({"key": key, "value": {"stringValue": json.dumps(value)}})

    if policy and where == "trace":
        add("agentest.policy", policy)
    elif policy and where == "spec":
        add("agentest.task.spec", {"goal": "complete the task", "policy": policy})
    if state is not None:
        add("agentest.state.trace", state)
    _shift_approvals(spans)


def _shift_approvals(spans) -> None:
    tools = [s for s in spans if s.get("name", "").startswith("execute_tool") or any(
        a.get("key") == "gen_ai.operation.name" and (a.get("value") or {}).get("stringValue") == "execute_tool"
        for a in s.get("attributes") or [])]
    approvals = [s for s in spans if s.get("name") == "agentest.approval"]
    if not tools or not approvals:
        return
    first = min(int(s["startTimeUnixNano"]) for s in tools)
    for i, s in enumerate(approvals):
        s["startTimeUnixNano"] = str(first - 20 + i)
        s["endTimeUnixNano"] = str(first - 10 + i)


def _run_native(calls, policy, where, state, approve: bool):
    ep = Episode(agent="synthetic", probe="case", input="do the task", final_answer="done", rep=0)
    for name, args, result, err in calls:
        ep.tool_calls.append(ToolCall(name=name, arguments=dict(args), result=dict(result), error=err))
    if approve:
        ep.approvals.append(Approval(action=calls[0][0], granted=True, approver="reviewer", target="OBJ-1", policy_version="p1"))
    doc = to_otlp(ep, "synthetic")
    _stamp(doc, policy, where, state)
    return from_otlp(doc)


def _run_langgraph(calls, policy, where, state, approve: bool):
    approvals = []
    if approve:
        approvals.append({"action": calls[0][0], "granted": True, "approver": "reviewer", "object": "OBJ-1", "policy_version": "p1"})
    raw = {"probe": "case", "input": "do the task", "rep": 0, "trace": _messages(calls),
           "output": {"final": "done", "approvals": approvals}}
    mapping = {"dialect": "langgraph_msgs", "framework": "LangGraph",
               "observations": {"final_answer": ["output.final"], "approvals": ["output.approvals"]}}
    doc = to_docs([raw], mapping, "synthetic")[0]
    _stamp(doc, policy, where, state)
    return from_otlp(doc)


def _with_effects(run):
    """One executed effect inside each call span, a new object each time. Not a tool name."""
    for i, t in enumerate(run.tools):
        span = (t.t1 or t.t) - t.t
        when = t.t + max(span // 2, 1) if span > 1 else t.t
        run.effects.append({"kind": "executed", "effect": "record", "data": {"object": f"ROW-{i + 1}"}, "t": when})
    return run


def _status(agent, run, tid) -> str:
    return evaluate(agent, [run], [tid])[tid].status


def test_hooks_are_existing_catalogue_ids():
    assert set(HOOKS) <= set(ALL_IDS)
    assert {"X-004", "X-021", "X-022", "T2-004", "T2-011", "T5-006"} <= set(HOOKS)


def test_fixture_matrix_agrees_across_vocabularies_and_dialects():
    pos = [c for c in CASES if c[2] == "fail"]
    neg = [c for c in CASES if c[2] != "fail"]
    assert len(CASES) >= 20 and len(pos) >= 10 and len(neg) >= 10
    mismatches = []
    for name, tid, expect, where in CASES:
        by_voc = {}
        for label, voc in VOCS.items():
            policy = _policy(name, voc, where)
            gov = {"policy": policy} if where == "gov" else {}
            agent = _agent(voc, gov)
            calls = _calls(name, voc)
            state = ["open", "closed", "open"] if name == "x022_state_trace" else None
            approve = name == "t2004_approved"
            native_run = _run_native(calls, policy if where != "gov" else None, where, state, approve)
            graph_run = _run_langgraph(calls, policy if where != "gov" else None, where, state, approve)
            if name in EFFECT_CASES:
                _with_effects(native_run)
                _with_effects(graph_run)
            native = _status(agent, native_run, tid)
            graph = _status(agent, graph_run, tid)
            if native != graph or native != expect:
                mismatches.append((name, label, tid, expect, native, graph))
            by_voc[label] = native
        if by_voc["alpha"] != by_voc["beta"]:
            mismatches.append((name, "vocab", tid, by_voc["alpha"], by_voc["beta"]))
    assert not mismatches, mismatches
