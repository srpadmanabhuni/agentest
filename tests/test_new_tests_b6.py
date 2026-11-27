"""New tests NT-044 and NT-045 (batch 6): pass, fail and n/a on constructed traces.

Traces are OTLP/JSON documents read through ``from_otlp``. Names are neutral.
"""
from __future__ import annotations

import json
from pathlib import Path

import agentest.standards.new_tests.b6  # noqa: F401  registers NT-044, NT-045 and NT-046
from agentest.standards import rules
from agentest.standards.metadata import Agent
from agentest.standards.otel import from_otlp

S = 1_000_000_000
B6 = ["NT-044", "NT-045", "NT-046"]
KEYS = ["order_id", "customer_id"]
TOOLS = {
    "get_record": {"annotations": {"readOnlyHint": True}},
    "update_record": {"annotations": {"readOnlyHint": False}},
}


def _v(x):
    if isinstance(x, bool):
        return {"boolValue": x}
    if isinstance(x, int):
        return {"intValue": str(x)}
    if isinstance(x, list) and all(isinstance(y, str) for y in x):
        return {"arrayValue": {"values": [{"stringValue": y} for y in x]}}
    return {"stringValue": x if isinstance(x, str) else json.dumps(x)}


def doc(spans, root=None, rep=0, root_t0=None, events=None):
    ra = {"gen_ai.operation.name": "invoke_agent", "agentest.input.id": "uc-1", "agentest.run.rep": rep, **(root or {})}
    t0_start = int(root_t0) if root_t0 is not None else int((rep + 1) * S)
    root_span = {"traceId": f"{rep + 1:032x}", "spanId": f"{rep + 1:016x}", "name": "invoke_agent desk", "kind": 1,
                 "startTimeUnixNano": str(t0_start), "endTimeUnixNano": str(t0_start + 1000 * S),
                 "attributes": [{"key": k, "value": _v(v)} for k, v in ra.items()], "status": {"code": 1}}
    out = [root_span]
    for i, sp in enumerate(spans):
        name, attrs = sp[0], sp[1]
        t0, t1 = (sp[2], sp[3]) if len(sp) > 2 else (i + 1, i + 1.5)
        err = sp[4] if len(sp) > 4 else False
        status_code = 2 if err else 1
        out.append({"traceId": root_span["traceId"], "spanId": f"{rep + 1:08x}{i + 2:08x}", "parentSpanId": root_span["spanId"],
                    "name": name, "kind": 1, "startTimeUnixNano": str(int(root_span["startTimeUnixNano"]) + int(t0 * S)),
                    "endTimeUnixNano": str(int(root_span["startTimeUnixNano"]) + int(t1 * S)),
                    "attributes": [{"key": k, "value": _v(v)} for k, v in attrs.items()], "status": {"code": status_code}})
    if events:
        root_span["events"] = [
            {
                "timeUnixNano": str(int(root_span["startTimeUnixNano"]) + int(t * S)),
                "name": name,
                "attributes": [{"key": k, "value": _v(v)} for k, v in attrs.items()],
            }
            for name, attrs, t in events
        ]
    return {"resourceSpans": [{"resource": {"attributes": []}, "scopeSpans": [{"scope": {"name": "uc"}, "spans": out}]}]}


def tool(name, call_id="c1", **attrs):
    return {"gen_ai.operation.name": "execute_tool", "gen_ai.tool.name": name, "gen_ai.tool.call.id": call_id, **attrs}


def handoff_run(payload, required=KEYS, rep=0):
    """A run in which ``planner`` hands work to ``worker`` with the given payload (a JSON string, or None for no payload)."""
    root = {"agentest.task.handoff.required_context": required} if required is not None else {}
    attrs = {"gen_ai.operation.name": "invoke_agent", "gen_ai.agent.name": "worker", "agentest.handoff.source": "planner"}
    if payload is not None:
        attrs["agentest.handoff.payload"] = payload
    return doc([("invoke_agent worker", attrs)], root=root, rep=rep)


def status(tid, docs, tools=None):
    agent = Agent("use-case", Path("."), {"skills": []}, tools or {}, {})
    runs = [from_otlp(json.loads(json.dumps(d))) for d in docs]
    return rules.evaluate(agent, runs, ids=[tid])[tid].status


def test_b6_not_in_default_set():
    res = rules.evaluate(Agent("use-case", Path("."), {}, {}, {}), [from_otlp(doc([]))])
    assert not set(B6) & set(res)


# ---------------------------------------------------------------- NT-044


def test_nt_044_relative_seconds_pass_and_fail():
    w_ok = ("execute_tool write", tool("update_record", "c1"), 2, 3)
    w_late = ("execute_tool write", tool("update_record", "c2"), 12, 13)
    r_late = ("execute_tool read", tool("get_record", "c3"), 12, 13)

    # Pass: write is within deadline (10s), read-only call after deadline is ignored
    assert status("NT-044", [doc([w_ok, r_late], root={"agentest.task.deadline": 10})], tools=TOOLS) == "pass"

    # Fail: write starts after deadline (10s)
    assert status("NT-044", [doc([w_ok, w_late], root={"agentest.task.deadline": 10})], tools=TOOLS) == "fail"


def test_nt_044_failed_write_after_deadline_does_not_fail():
    w_ok = ("execute_tool write", tool("update_record", "c1"), 2, 3)
    w_late_err = ("execute_tool write", tool("update_record", "c2"), 12, 13, True)
    assert status("NT-044", [doc([w_ok, w_late_err], root={"agentest.task.deadline": 10})], tools=TOOLS) == "pass"


def test_nt_044_epoch_nanoseconds():
    epoch_base = 1_700_000_000_000_000_000
    epoch_deadline = epoch_base + 10 * S
    w_ok = ("execute_tool write", tool("update_record", "c1"), 2, 3)
    w_late = ("execute_tool write", tool("update_record", "c2"), 12, 13)

    assert status("NT-044", [doc([w_ok], root={"agentest.task.deadline": epoch_deadline}, root_t0=epoch_base)], tools=TOOLS) == "pass"
    assert status("NT-044", [doc([w_late], root={"agentest.task.deadline": epoch_deadline}, root_t0=epoch_base)], tools=TOOLS) == "fail"


def test_nt_044_iso_timestamp_with_z():
    root_t0 = 1_795_608_000 * S
    deadline_iso = "2026-11-25T12:00:10Z"
    w_ok = ("execute_tool write", tool("update_record", "c1"), 2, 3)
    w_late = ("execute_tool write", tool("update_record", "c2"), 12, 13)

    assert status("NT-044", [doc([w_ok], root={"agentest.task.deadline": deadline_iso}, root_t0=root_t0)], tools=TOOLS) == "pass"
    assert status("NT-044", [doc([w_late], root={"agentest.task.deadline": deadline_iso}, root_t0=root_t0)], tools=TOOLS) == "fail"


def test_nt_044_naive_iso_timestamp_treated_as_utc():
    root_t0 = 1_795_608_000 * S
    deadline_iso = "2026-11-25T12:00:10"
    w_ok = ("execute_tool write", tool("update_record", "c1"), 2, 3)
    w_late = ("execute_tool write", tool("update_record", "c2"), 12, 13)

    assert status("NT-044", [doc([w_ok], root={"agentest.task.deadline": deadline_iso}, root_t0=root_t0)], tools=TOOLS) == "pass"
    assert status("NT-044", [doc([w_late], root={"agentest.task.deadline": deadline_iso}, root_t0=root_t0)], tools=TOOLS) == "fail"


def test_nt_044_na_when_deadline_absent():
    w = ("execute_tool write", tool("update_record", "c1"), 2, 3)
    assert status("NT-044", [doc([w])], tools=TOOLS) == "n/a"


def test_nt_044_na_when_deadline_unreadable_or_non_finite():
    w = ("execute_tool write", tool("update_record", "c1"), 2, 3)
    assert status("NT-044", [doc([w], root={"agentest.task.deadline": "not-a-timestamp"})], tools=TOOLS) == "n/a"
    assert status("NT-044", [doc([w], root={"agentest.task.deadline": float("inf")})], tools=TOOLS) == "n/a"
    assert status("NT-044", [doc([w], root={"agentest.task.deadline": "inf"})], tools=TOOLS) == "n/a"


# ---------------------------------------------------------------- NT-045


def test_pass_when_payload_has_every_required_key():
    assert status("NT-045", [handoff_run(json.dumps({"order_id": "A-1", "customer_id": "C-9"}))]) == "pass"


def test_fail_when_a_required_key_is_missing():
    assert status("NT-045", [handoff_run(json.dumps({"order_id": "A-1"}))]) == "fail"


def test_fail_when_payload_is_not_an_object():
    assert status("NT-045", [handoff_run("not a json object")]) == "fail"


def test_comma_separated_declaration_is_read():
    ok_payload = json.dumps({"order_id": "A-1", "customer_id": "C-9"})
    assert status("NT-045", [handoff_run(ok_payload, required="order_id, customer_id")]) == "pass"
    assert status("NT-045", [handoff_run(json.dumps({"order_id": "A-1"}), required="order_id, customer_id")]) == "fail"


def test_na_when_no_handoff_occurs():
    d = doc([("chat", {"gen_ai.operation.name": "chat"})], root={"agentest.task.handoff.required_context": KEYS})
    assert status("NT-045", [d]) == "n/a"


def test_na_when_required_list_is_not_declared():
    assert status("NT-045", [handoff_run(json.dumps({"order_id": "A-1"}), required=None)]) == "n/a"


def approval_run(effects, approvals, rep=0):
    """Build OTLP traces containing state-change events and approval spans."""
    events = [
        (
            "agentest.state_change",
            {
                "agentest.state_change.kind": "executed",
                "agentest.state_change.effect": action,
                "agentest.state_change.data": json.dumps({"target": target, "fixture": True}),
            },
            t,
        )
        for action, target, t in effects
    ]
    spans = []
    for action, target, granted, t in approvals:
        attrs = {"agentest.approval.granted": granted}
        if action is not None:
            attrs["agentest.approval.action"] = action
        if target is not None:
            attrs["agentest.approval.target"] = target
        spans.append(("agentest.approval", attrs, t, t + 0.1))
    return doc(spans, rep=rep, events=events)


def approval_status(docs):
    return status("NT-046", docs)


def test_nt046_passes_for_matching_prior_approval():
    d = approval_run(
        [("write_file", "note.txt", 2)],
        [("write_file", "note.txt", True, 1)],
    )
    assert approval_status([d]) == "pass"


def test_nt046_fails_when_action_does_not_match():
    d = approval_run(
        [("write_file", "note.txt", 2)],
        [("different_action", "note.txt", True, 1)],
    )
    assert approval_status([d]) == "fail"


def test_nt046_fails_when_target_does_not_match():
    d = approval_run(
        [("write_file", "note.txt", 2)],
        [("write_file", "other.txt", True, 1)],
    )
    assert approval_status([d]) == "fail"


def test_nt046_passes_when_each_effect_has_a_fresh_grant():
    d = approval_run(
        [("write_file", "note.txt", 2), ("write_file", "note.txt", 6)],
        [("write_file", "note.txt", True, 1), ("write_file", "note.txt", True, 4)],
    )
    assert approval_status([d]) == "pass"


def test_nt046_fails_when_one_grant_is_reused():
    d = approval_run(
        [("write_file", "note.txt", 2), ("write_file", "note.txt", 6)],
        [("write_file", "note.txt", True, 1)],
    )
    assert approval_status([d]) == "fail"


def test_nt046_fails_when_matching_approval_is_late():
    d = approval_run(
        [("write_file", "note.txt", 2)],
        [("write_file", "note.txt", True, 3)],
    )
    assert approval_status([d]) == "fail"


def test_nt046_fails_when_approval_is_denied():
    d = approval_run(
        [("write_file", "note.txt", 2)],
        [("write_file", "note.txt", False, 1)],
    )
    assert approval_status([d]) == "fail"


def test_nt046_na_when_there_is_no_executed_effect():
    d = doc(
        [("agentest.approval", {
            "agentest.approval.action": "write_file",
            "agentest.approval.target": "note.txt",
            "agentest.approval.granted": True,
        })]
    )
    assert approval_status([d]) == "n/a"


def test_nt046_na_when_effect_identifiers_are_missing():
    d = doc(
        [("agentest.approval", {
            "agentest.approval.action": "write_file",
            "agentest.approval.target": "note.txt",
            "agentest.approval.granted": True,
        })],
        events=[("agentest.state_change", {
            "agentest.state_change.kind": "executed",
            "agentest.state_change.data": json.dumps({"target": "note.txt"}),
        }, 2)],
    )
    assert approval_status([d]) == "n/a"


def test_nt046_na_when_approval_identifiers_are_missing():
    d = approval_run(
        [("write_file", "note.txt", 2)],
        [(None, "note.txt", True, 1)],
    )
    assert approval_status([d]) == "n/a"
