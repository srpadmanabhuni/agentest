"""New test NT-045 (batch 6): pass, fail and n/a on constructed traces.

Traces are OTLP/JSON documents read through ``from_otlp``. Names are neutral.
"""
from __future__ import annotations

import json
from pathlib import Path

import agentest.standards.new_tests.b6  # noqa: F401  registers NT-045
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
    """A run in which ``planner`` hands work to ``worker`` with the given payload (a JSON string, or None for no payload)."""
    root = {"agentest.task.handoff.required_context": required} if required is not None else {}
    attrs = {"gen_ai.operation.name": "invoke_agent", "gen_ai.agent.name": "worker", "agentest.handoff.source": "planner"}
    if payload is not None:
        attrs["agentest.handoff.payload"] = payload
    return doc([("invoke_agent worker", attrs)], root=root, rep=rep)


def status(docs):
    agent = Agent("use-case", Path("."), {"skills": []}, {}, {})
    runs = [from_otlp(json.loads(json.dumps(d))) for d in docs]
    return rules.evaluate(agent, runs, ids=["NT-045"])["NT-045"].status


def test_pass_when_payload_has_every_required_key():
    assert status([handoff_run(json.dumps({"order_id": "A-1", "customer_id": "C-9"}))]) == "pass"


def test_fail_when_a_required_key_is_missing():
    assert status([handoff_run(json.dumps({"order_id": "A-1"}))]) == "fail"


def test_fail_when_payload_is_not_an_object():
    assert status([handoff_run("not a json object")]) == "fail"


def test_comma_separated_declaration_is_read():
    ok_payload = json.dumps({"order_id": "A-1", "customer_id": "C-9"})
    assert status([handoff_run(ok_payload, required="order_id, customer_id")]) == "pass"
    assert status([handoff_run(json.dumps({"order_id": "A-1"}), required="order_id, customer_id")]) == "fail"


def test_na_when_no_handoff_occurs():
    d = doc([("chat", {"gen_ai.operation.name": "chat"})], root={"agentest.task.handoff.required_context": KEYS})
    assert status([d]) == "n/a"


def test_na_when_required_list_is_not_declared():
    assert status([handoff_run(json.dumps({"order_id": "A-1"}), required=None)]) == "n/a"
