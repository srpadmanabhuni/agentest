"""New tests NT-044 and NT-045 (batch 6): pass, fail and n/a on constructed traces.

Traces are OTLP/JSON documents read through ``from_otlp``. Names are neutral.
"""
from __future__ import annotations

import json
from pathlib import Path

import agentest.standards.new_tests.b6  # noqa: F401  registers NT-044 and NT-045
from agentest.standards import rules
from agentest.standards.metadata import Agent
from agentest.standards.otel import from_otlp

S = 1_000_000_000
KEYS = ["order_id", "customer_id"]


def _v(x):
    if isinstance(x, bool):
        return {"boolValue": x}
    if isinstance(x, int):
        return {"intValue": str(x)}
    if isinstance(x, list) and all(isinstance(y, str) for y in x):
        return {"arrayValue": {"values": [{"stringValue": y} for y in x]}}
    return {"stringValue": x if isinstance(x, str) else json.dumps(x)}


def doc(spans, root=None, rep=0):
    ra = {"gen_ai.operation.name": "invoke_agent", "agentest.input.id": "uc-1", "agentest.run.rep": rep, **(root or {})}
    root_span = {"traceId": f"{rep + 1:032x}", "spanId": f"{rep + 1:016x}", "name": "invoke_agent desk", "kind": 1,
        "startTimeUnixNano": str((rep + 1) * S), "endTimeUnixNano": str((rep + 1) * S + 1000 * S),
        "attributes": [{"key": k, "value": _v(v)} for k, v in ra.items()], "status": {"code": 1}}
    out = [root_span]
    for i, sp in enumerate(spans):
        name, attrs = sp[0], sp[1]
        t0, t1 = (sp[2], sp[3]) if len(sp) > 2 else (i + 1, i + 1.5)
        out.append({"traceId": root_span["traceId"], "spanId": f"{rep + 1:08x}{i + 2:08x}", "parentSpanId": root_span["spanId"],
            "name": name, "kind": 1, "startTimeUnixNano": str(int(root_span["startTimeUnixNano"]) + int(t0 * S)),
            "endTimeUnixNano": str(int(root_span["startTimeUnixNano"]) + int(t1 * S)),
            "attributes": [{"key": k, "value": _v(v)} for k, v in attrs.items()], "status": {"code": 1}})
    return {"resourceSpans": [{"resource": {"attributes": []}, "scopeSpans": [{"scope": {"name": "uc"}, "spans": out}]}]}


def handoff_run(payload, required=KEYS, rep=0):
    """A run in which ``planner`` hands work to ``worker`` with the given payload (a JSON string, or None)."""
    root = {"agentest.task.handoff.required_context": required} if required is not None else {}
    attrs = {"gen_ai.operation.name": "invoke_agent", "gen_ai.agent.name": "worker", "agentest.handoff.source": "planner"}
    if payload is not None:
        attrs["agentest.handoff.payload"] = payload
    return doc([("invoke_agent worker", attrs)], root=root, rep=rep)


def tool_run(deadline=None, name="refund_order", kind="write", t0=11, t1=12, extra=None, rep=0):
    """A run with one tool call starting ``t0`` seconds after the run start."""
    root = {"agentest.task.deadline": deadline} if deadline is not None else {}
    attrs = {"gen_ai.operation.name": "execute_tool", "gen_ai.tool.name": name}
    if kind is not None:
        attrs["agentest.tool.type"] = kind
    if extra:
        attrs.update(extra)
    return doc([(f"execute_tool {name}", attrs, t0, t1)], root=root, rep=rep)


def status(docs, check="NT-045"):
    agent = Agent("use-case", Path("."), {"skills": []}, {}, {})
    runs = [from_otlp(json.loads(json.dumps(d))) for d in docs]
    return rules.evaluate(agent, runs, ids=[check])[check].status


def test_pass_when_payload_has_every_required_key():
    assert status([handoff_run(json.dumps({"order_id": "A-1", "customer_id": "C-9"}))]) == "pass"


def test_fail_when_a_required_key_is_missing():
    assert status([handoff_run(json.dumps({"order_id": "A-1"}))]) == "fail"


def test_fail_when_payload_is_not_an_object():
    assert status([handoff_run(json.dumps(["order_id"]))]) == "fail"


def test_na_when_payload_is_missing():
    assert status([handoff_run(None)]) == "fail"


def test_na_when_no_handoff_occurs():
    assert status([doc([])]) == "n/a"


def test_na_when_required_context_is_not_declared():
    assert status([handoff_run(json.dumps({"order_id": "A-1"}), required=None)]) == "n/a"


def test_nt_044_fail_when_write_tool_starts_after_deadline():
    assert status([tool_run(10)], check="NT-044") == "fail"


def test_nt_044_pass_when_write_tool_starts_before_deadline():
    assert status([tool_run(10, t0=9, t1=10)], check="NT-044") == "pass"


def test_nt_044_pass_when_write_tool_starts_at_deadline():
    assert status([tool_run(10, t0=10, t1=11)], check="NT-044") == "pass"


def test_nt_044_pass_when_read_tool_starts_after_deadline():
    assert status([tool_run(10, name="get_order", kind=None)], check="NT-044") == "pass"


def test_nt_044_fail_when_state_change_call_starts_after_deadline():
    assert status([tool_run(10, name="update_order", kind=None, extra={"agentest.state_change": "order updated"})], check="NT-044") == "fail"


def test_nt_044_fail_with_iso_deadline():
    assert status([tool_run("1970-01-01T00:00:11Z")], check="NT-044") == "fail"


def test_nt_044_pass_with_iso_deadline():
    assert status([tool_run("1970-01-01T00:00:11Z", t0=9, t1=10)], check="NT-044") == "pass"


def test_nt_044_fail_with_relative_string_deadline():
    assert status([tool_run("10s")], check="NT-044") == "fail"


def test_nt_044_na_when_no_deadline_is_declared():
    assert status([tool_run()], check="NT-044") == "n/a"


def test_nt_044_na_when_deadline_is_malformed():
    assert status([tool_run("not-a-time")], check="NT-044") == "n/a"
