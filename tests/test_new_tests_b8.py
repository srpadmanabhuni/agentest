"""New test NT-048 (batch 8): pass, fail and n/a on constructed traces.

Traces are OTLP JSON documents read through ``from_otlp``. Names are neutral.
"""
from __future__ import annotations

import json
from pathlib import Path

import agentest.standards.new_tests.b8  # noqa: F401  registers NT-048
from agentest.standards import rules
from agentest.standards.metadata import Agent
from agentest.standards.otel import from_otlp

S = 1_000_000_000
B8 = ["NT-048"]


def _v(x):
    if isinstance(x, bool):
        return {"boolValue": x}
    if isinstance(x, int):
        return {"intValue": str(x)}
    if isinstance(x, list) and all(isinstance(y, str) for y in x):
        return {"arrayValue": {"values": [{"stringValue": y} for y in x]}}
    return {"stringValue": x if isinstance(x, str) else json.dumps(x)}


def doc(spans, root=None, rep=0, root_t0=None, events=None):
    ra = {
        "gen_ai.operation.name": "invoke_agent",
        "agentest.input.id": "uc-1",
        "agentest.run.rep": rep,
        **(root or {}),
    }
    t0_start = int(root_t0 if root_t0 is not None else int((rep + 1) * S))
    root_span = {
        "traceId": f"{rep + 1:032x}",
        "spanId": f"{rep + 1:016x}",
        "name": "invoke_agent desk",
        "kind": 1,
        "startTimeUnixNano": str(t0_start),
        "endTimeUnixNano": str(t0_start + 1000 * S),
        "attributes": [{"key": k, "value": _v(v)} for k, v in ra.items()],
        "status": {"code": 1},
    }
    out = [root_span]
    for i, sp in enumerate(spans):
        name, attrs = sp[0], sp[1]
        t0, t1 = sp[2], sp[3] if len(sp) > 2 else (i + 1, i + 1.5)
        err = sp[4] if len(sp) > 4 else False
        status_code = 2 if err else 1
        out.append(
            {
                "traceId": root_span["traceId"],
                "spanId": f"{rep + 1:08x}{i + 2:08x}",
                "parentSpanId": root_span["spanId"],
                "name": name,
                "kind": 1,
                "startTimeUnixNano": str(int(root_span["startTimeUnixNano"]) + int(t0 * S)),
                "endTimeUnixNano": str(int(root_span["startTimeUnixNano"]) + int(t1 * S)),
                "attributes": [{"key": k, "value": _v(v)} for k, v in attrs.items()],
                "status": {"code": status_code},
            }
        )
    if events:
        root_span["events"] = [
            {
                "timeUnixNano": str(int(root_span["startTimeUnixNano"]) + int(t * S)),
                "name": name,
                "attributes": [{"key": k, "value": _v(v)} for k, v in attrs.items()],
            }
            for name, attrs, t in events
        ]
    return {
        "resourceSpans": [
            {
                "resource": {"attributes": []},
                "scopeSpans": [{"scope": {"name": "uc"}, "spans": out}],
            }
        ]
    }


def status(tid, docs, tools=None):
    agent = Agent("use-case", Path("."), {"skills": []}, tools or {}, {})
    runs = [from_otlp(json.loads(json.dumps(d))) for d in docs]
    return rules.evaluate(agent, runs, ids=[tid])[tid].status


def test_b8_not_in_default_set():
    res = rules.evaluate(Agent("use-case", Path("."), {}, {}, {}), [from_otlp(doc([]))])
    assert not set(B8) & set(res)


# ------------------------------------------------------------ NT-048

READ_ONLY = {
    "lookup_customer": {"annotations": {"readOnlyHint": True}},
    "search": {"annotations": {"readOnlyHint": True}},
}

WRITE_WITH_STATUS = {
    "update_ticket": {
        "annotations": {"readOnlyHint": False},
        "inputSchema": {
            "type": "object",
            "properties": {
                "ticket": {"type": "string"},
                "status": {"type": "string", "enum": ["open", "in_progress", "closed"]},
            "assignee": {"type": "string"},
        },
    },
},
}


def _tool(name, args, result="", t0=1, t1=1.5):
    """One execute_tool span for a tool call."""
    return (
        f"execute_tool {name}",
        {
            "gen_ai.operation.name": "execute_tool",
            "gen_ai.tool.name": name,
            "gen_ai.tool.call.arguments": json.dumps(args),
            "gen_ai.tool.call.result": result,
        },
        t0,
        t1,
    )


def _run(input_text, calls):
    """One run with the given user input and tool-call spans."""
    root = {
        "gen_ai.input.messages": json.dumps(
            [{"role": "user", "parts": [{"type": "text", "content": input_text}]}]
        )
    }
    return doc(calls, root=root)


def _verdict(input_text, calls, tools=None):
    return status("NT-048", [_run(input_text, calls)], tools=tools)


def test_pass_value_from_input():
    assert (
        _verdict(
            "Send a refund to Alice Smith",
            [_tool("send_email", {"to": "Alice Smith", "subject": "refund"})],
        )
        == "pass"
    )


def test_pass_value_from_earlier_result():
    assert (
        _verdict(
            "Look up the customer and send them a refund",
            [
                _tool("lookup_customer", {"query": "customer"}, result="Alice Smith", t0=1, t1=1.5),
                _tool("send_email", {"to": "Alice Smith"}, t0=2, t1=2.5),
            ],
            tools=READ_ONLY,
        )
        == "pass"
    )


def test_pass_value_from_earlier_args():
    assert (
        _verdict(
            "Look up the customer and email them",
            [
                _tool("search", {"query": "Alice Smith"}, result="found", t0=1, t1=1.5),
                _tool("send_email", {"to": "Alice Smith"}, t0=2, t1=2.5),
            ],
            tools=READ_ONLY,
        )
        == "pass"
    )


def test_fail_invented_name():
    assert (
        _verdict(
            "Send a refund to the customer",
            [_tool("send_email", {"to": "Zara Quinn", "subject": "refund"})],
        )
        == "fail"
    )


def test_fail_invented_path():
    assert (
        _verdict(
            "Save the report",
            [_tool("write_file", {"path": "/tmp/report.csv", "content": "Save the report"})],
        )
        == "fail"
    )


def test_fail_invented_value_with_entity_id():
    assert (
        _verdict(
            "Send a refund to the customer",
            [_tool("send_email", {"to": "Zara Quinn CUST-90", "subject": "refund"})],
        )
        == "fail"
    )


def test_na_no_write_call():
    assert (
        _verdict(
            "What is the weather?",
            [_tool("search", {"query": "weather"})],
            tools=READ_ONLY,
        )
        == "n/a"
    )


def test_na_numeric_or_entity_id_only():
    assert (
        _verdict(
            "Transfer 40 to CUST-40",
            [_tool("transfer", {"amount": 40, "account": "CUST-40"})],
        )
        == "n/a"
    )


def test_na_untraced_number_and_entity_id():
    assert (
        _verdict(
            "Transfer the money",
            [_tool("transfer", {"amount": 999, "account": "CUST-90"})],
        )
        == "n/a"
    )


def test_pass_schema_constrained_status_value():
    assert (
        _verdict(
            "Close ticket TKT-123 for Alice Smith",
            [_tool("update_ticket", {"ticket": "TKT-123", "status": "closed", "assignee": "Alice Smith"})],
            tools=WRITE_WITH_STATUS,
        )
        == "pass"
    )
