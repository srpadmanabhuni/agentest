"""New tests batch 2 (NT-010..NT-014, NT-027): pass, fail and n/a cases on constructed use case traces.

Every trace is an OTLP/JSON document read through ``from_otlp``, so the attributes each check needs are shown to survive
the trace reader. Tool and agent names are neutral.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from agentest.standards import rules
from agentest.standards.catalog import new_tests
from agentest.standards.metadata import Agent
from agentest.standards.otel import from_otlp

S = 1_000_000_000
B2 = ("NT-010", "NT-011", "NT-012", "NT-013", "NT-014", "NT-027")


def _v(x):
    if isinstance(x, bool):
        return {"boolValue": x}
    if isinstance(x, int):
        return {"intValue": str(x)}
    if isinstance(x, float):
        return {"doubleValue": x}
    if isinstance(x, str):
        return {"stringValue": x}
    return {"stringValue": json.dumps(x)}


def span(name, t0, t1=None, **attrs):
    """One span: start/end in seconds from the run start; attribute keys use __ for dots."""
    return {"name": name, "t0": t0, "t1": t0 + 0.1 if t1 is None else t1, "attrs": {k.replace("__", "."): v for k, v in attrs.items()}}


def tool(name, t0, args=None, error=False, **attrs):
    s = span(f"execute_tool {name}", t0, gen_ai__operation__name="execute_tool", gen_ai__tool__name=name,
             gen_ai__tool__call__arguments=json.dumps(args or {}), **attrs)
    s["error"] = error
    return s


def approval(action, t0, kind="", granted=True):
    return span("agentest.approval", t0, agentest__approval__action=action, agentest__approval__granted=granted,
                agentest__approval__kind=kind, agentest__approval__approver="reviewer")


def human(t0):
    return span("agentest.human_input", t0)


def msg(mid, direction, t0, **attrs):
    return span(f"a2a.{direction}", t0, agentest__a2a__message_id=mid, agentest__a2a__direction=direction, **attrs)


def trace(children, task=None, end=None, input_id="uc-1"):
    base = 1_700_000_000 * S
    root_attrs = {"agentest.input.id": input_id, "gen_ai.operation.name": "invoke_agent"}
    for k, v in (task or {}).items():
        root_attrs[f"agentest.task.{k}"] = v
    last = max([c["t1"] for c in children] + [1.0])
    spans = [{"traceId": "ab" * 16, "spanId": "0" * 16, "name": "invoke_agent coordinator", "startTimeUnixNano": str(base),
              "endTimeUnixNano": str(base + int((end if end is not None else last) * S)),
              "attributes": [{"key": k, "value": _v(v)} for k, v in root_attrs.items()]}]
    for i, c in enumerate(children, 1):
        s = {"traceId": "ab" * 16, "spanId": f"{i:016x}", "parentSpanId": "0" * 16, "name": c["name"],
             "startTimeUnixNano": str(base + int(c["t0"] * S)), "endTimeUnixNano": str(base + int(c["t1"] * S)),
             "attributes": [{"key": k, "value": _v(v)} for k, v in c["attrs"].items()]}
        if c.get("error"):
            s["status"] = {"code": 2}
        spans.append(s)
    return from_otlp({"resourceSpans": [{"resource": {"attributes": []}, "scopeSpans": [{"scope": {"name": "uc"}, "spans": spans}]}]})


def agent(gov=None):
    return Agent("use-case", Path("."), {}, {}, gov or {})


def run(tid, *runs, gov=None):
    return rules.evaluate(agent(gov), list(runs), ids=[tid])[tid]


# ---------------------------------------------------------------- registry

def test_rows_and_rules_for_batch_2():
    rows = {k: v for k, v in new_tests().items() if v.get("batch") == "b2"}
    assert tuple(rows) == B2
    assert {r["article_test"] for r in rows.values()} == {"A012", "A013", "A014", "A018", "A019", "A088"}
    for i in B2:
        assert i in rules.RULES
    assert not set(B2) & set(rules.evaluate(agent(), [trace([])]))  # opt-in: not in the default set


def test_otlp_round_trip_keeps_batch_2_attributes():
    r = trace([msg("m1", "send", 1, agentest__a2a__payload={"amount": 10}, agentest__a2a__message_type="subgoal"),
               span("ack", 2, agentest__a2a__ack_of="m1")],
              task={"ack_within_s": 5, "limits": {"tool_calls": 2}, "step_up_tools": ["place_order"]})
    names = [s["name"] for s in r.spans]
    assert "a2a.send" in names and "ack" in names
    snd = next(s for s in r.spans if s["name"] == "a2a.send")
    assert snd["attrs"]["agentest.a2a.message_id"] == "m1" and json.loads(snd["attrs"]["agentest.a2a.payload"]) == {"amount": 10}
    assert json.loads(r.attrs["agentest.task.limits"]) == {"tool_calls": 2}
    assert r.spans[0]["t1"] - r.spans[0]["t0"] > 0


# ---------------------------------------------------------------- NT-010

def test_nt010_pass_same_payload_and_hash():
    r = trace([msg("m1", "send", 1, agentest__a2a__payload={"amount": 120, "currency": "EUR"}),
               msg("m1", "receive", 2, agentest__a2a__payload='{"currency": "EUR", "amount": 120}'),
               msg("m2", "send", 3, agentest__a2a__payload_hash="sha256:ABC123"),
               msg("m2", "receive", 4, agentest__a2a__payload_hash="sha256:abc123")])
    assert run("NT-010", r).status == "pass"


def test_nt010_pass_declared_transform():
    r = trace([msg("m1", "send", 1, agentest__a2a__payload={"amount": 120}),
               msg("m1", "receive", 2, agentest__a2a__payload={"amount_cents": 12000}, agentest__a2a__transform="unit: cents")])
    assert run("NT-010", r).status == "pass"


def test_nt010_fail_payload_changed():
    r = trace([msg("m1", "send", 1, agentest__a2a__payload={"amount": 120}),
               msg("m1", "receive", 2, agentest__a2a__payload={"amount": 210})])
    v = run("NT-010", r)
    assert v.status == "fail" and "m1" in v.detail


def test_nt010_fail_hash_vs_payload():
    import hashlib

    good = hashlib.sha256(b'{"amount":120}').hexdigest()
    ok_run = trace([msg("m1", "send", 1, agentest__a2a__payload={"amount": 120}), msg("m1", "receive", 2, agentest__a2a__payload_hash=good)])
    bad_run = trace([msg("m1", "send", 1, agentest__a2a__payload={"amount": 121}), msg("m1", "receive", 2, agentest__a2a__payload_hash=good)],
                    input_id="uc-2")
    assert run("NT-010", ok_run).status == "pass"
    assert run("NT-010", ok_run, bad_run).status == "fail"


def test_nt010_na_without_pairs():
    assert run("NT-010", trace([msg("m1", "send", 1, agentest__a2a__payload={"a": 1})])).status == "n/a"
    assert run("NT-010", trace([tool("lookup", 1)])).status == "n/a"


# ---------------------------------------------------------------- NT-011

SCHEMA = {"message_types": ["request", "accept", "result"], "required": {"*": ["task_id"], "result": ["task_id", "outcome"]},
          "order": ["request", "accept", "result"]}


def _hand(mid, mtype, t0, **fields):
    return msg(mid, "send", t0, agentest__a2a__message_type=mtype, agentest__a2a__fields=fields)


def test_nt011_pass():
    r = trace([_hand("h1", "request", 1, task_id="T-1"), msg("h1", "receive", 1.5, agentest__a2a__message_type="request"),
               _hand("h2", "accept", 2, task_id="T-1"), _hand("h3", "result", 3, task_id="T-1", outcome="done")],
              task={"handover_schema": SCHEMA})
    assert run("NT-011", r).status == "pass"


@pytest.mark.parametrize("children,needle", [
    ([_hand("h1", "request", 1, task_id="T-1"), _hand("h2", "result", 2, task_id="T-1")], "outcome"),
    ([_hand("h1", "request", 1, task_id="T-1"), _hand("h2", "gossip", 2, task_id="T-1")], "not allowed"),
    ([_hand("h1", "accept", 1, task_id="T-1"), _hand("h2", "request", 2, task_id="T-1")], "order"),
])
def test_nt011_fail(children, needle):
    v = run("NT-011", trace(children, task={"handover_schema": SCHEMA}))
    assert v.status == "fail" and needle in v.detail


def test_nt011_payload_fields_and_list_required():
    sch = {"message_types": ["request"], "required": ["task_id"]}
    r = trace([msg("h1", "send", 1, agentest__a2a__message_type="request", agentest__a2a__payload={"task_id": "T-9"})], task={"handover_schema": sch})
    assert run("NT-011", r).status == "pass"


def test_nt011_na():
    assert run("NT-011", trace([_hand("h1", "request", 1, task_id="T-1")])).status == "n/a"  # no schema
    assert run("NT-011", trace([tool("lookup", 1)], task={"handover_schema": SCHEMA})).status == "n/a"  # no handover


# ---------------------------------------------------------------- NT-012

def _sub(mid, t0):
    return msg(mid, "send", t0, agentest__a2a__message_type="subgoal")


def _ack(mid, t0):
    return span("a2a.ack", t0, agentest__a2a__ack_of=mid)


def test_nt012_pass():
    r = trace([_sub("g1", 1), _sub("g2", 2), _ack("g1", 3), _ack("g2", 6.5)], task={"ack_within_s": 5})
    assert run("NT-012", r).status == "pass"


def test_nt012_fail_late_or_missing():
    late = trace([_sub("g1", 1), _ack("g1", 9)], task={"ack_within_s": 5})
    missing = trace([_sub("g1", 1), tool("lookup", 20)], task={"ack_within_s": 5}, input_id="uc-2")
    v1, v2 = run("NT-012", late), run("NT-012", missing)
    assert v1.status == "fail" and "after" in v1.detail
    assert v2.status == "fail" and "no ack" in v2.detail


def test_nt012_na():
    assert run("NT-012", trace([_sub("g1", 1), _ack("g1", 2)])).status == "n/a"  # no bound declared
    assert run("NT-012", trace([tool("lookup", 1)], task={"ack_within_s": 5})).status == "n/a"  # no sub-goal
    assert run("NT-012", trace([_sub("g1", 1)], task={"ack_within_s": 5}, end=3)).status == "n/a"  # ended before the bound


# ---------------------------------------------------------------- NT-013

def test_nt013_pass_handoff_or_human_or_stop():
    hand = trace([tool("search", 1), tool("search", 2), tool("search", 3), span("handoff", 4, agentest__handoff__source="worker")],
                 task={"limits": {"tool_calls": 3}})
    hum = trace([tool("search", 1), tool("search", 2), human(3), tool("search", 4)], task={"limits": {"tool_calls": 2}}, input_id="uc-2")
    stop = trace([tool("search", 1), tool("search", 2)], task={"limits": {"tool_calls": 2}}, input_id="uc-3")
    assert run("NT-013", hand, hum, stop).status == "pass"


def test_nt013_fail_tool_after_limit():
    r = trace([tool("search", 1), tool("search", 2), tool("search", 3), tool("book", 4)], task={"limits": {"tool_calls": 3}})
    v = run("NT-013", r)
    assert v.status == "fail" and "tool_calls" in v.detail and "book" in v.detail


def test_nt013_fail_spend_and_scope():
    spend = trace([tool("quote", 1, agentest__usage__cost=0.6), tool("quote", 2, agentest__usage__cost=0.6), tool("quote", 3)],
                  task={"limits": {"spend": 1.0}})
    scope = trace([tool("search", 1), tool("refund", 2), tool("search", 3)], task={"limits": {"scope": ["search"]}}, input_id="uc-2")
    assert run("NT-013", spend).status == "fail"
    v = run("NT-013", scope)
    assert v.status == "fail" and "scope" in v.detail


def test_nt013_na():
    assert run("NT-013", trace([tool("search", 1)] * 1)).status == "n/a"  # no limits
    assert run("NT-013", trace([tool("search", 1)], task={"limits": {"tool_calls": 5}})).status == "n/a"  # not reached


# ---------------------------------------------------------------- NT-014

def test_nt014_pass():
    quiet = trace([tool("check", 10), tool("check", 50)], task={"autonomy_window_s": 60}, end=90)
    asked = trace([tool("check", 10), human(61), tool("check", 70)], task={"autonomy_window_s": 60}, input_id="uc-2")
    tol = trace([tool("check", 10), tool("check", 62)], task={"autonomy_window_s": 60, "autonomy_window_tolerance_s": 5}, end=70, input_id="uc-3")
    assert run("NT-014", quiet, asked, tol).status == "pass"


def test_nt014_fail():
    r = trace([tool("check", 10), tool("transfer", 90)], task={"autonomy_window_s": 60})
    early_human = trace([tool("check", 10), human(30), tool("transfer", 90)], task={"autonomy_window_s": 60}, input_id="uc-2")
    v = run("NT-014", r)
    assert v.status == "fail" and "transfer" in v.detail
    assert run("NT-014", early_human).status == "fail"  # human input inside the window does not cover later calls


def test_nt014_na():
    assert run("NT-014", trace([tool("check", 90)])).status == "n/a"  # no window
    assert run("NT-014", trace([tool("check", 10)], task={"autonomy_window_s": 60}, end=40)).status == "n/a"  # ended inside


# ---------------------------------------------------------------- NT-027

def test_nt027_pass_task_and_governance():
    r = trace([approval("place_order", 1, kind="mfa"), tool("place_order", 2), approval("place_order", 3, kind="step-up"), tool("place_order", 4)],
              task={"step_up_tools": ["place_order"]})
    g = trace([approval("wire_funds", 1, kind="second_factor"), tool("wire_funds", 2)], input_id="uc-2")
    assert run("NT-027", r).status == "pass"
    assert run("NT-027", g, gov={"approval": {"stepUp": ["wire_funds"]}}).status == "pass"


@pytest.mark.parametrize("children", [
    [approval("place_order", 1), tool("place_order", 2)],  # single ordinary approval
    [tool("place_order", 2)],  # none
    [tool("place_order", 1), approval("place_order", 2, kind="mfa")],  # after the call
    [approval("place_order", 1, kind="mfa", granted=False), tool("place_order", 2)],  # denied
    [approval("place_order", 1, kind="mfa"), tool("place_order", 2), tool("place_order", 3)],  # one step-up, two calls
    [approval("cancel_order", 1, kind="mfa"), tool("place_order", 2)],  # other action
])
def test_nt027_fail(children):
    v = run("NT-027", trace(children, task={"step_up_tools": ["place_order"]}))
    assert v.status == "fail" and "place_order" in v.detail


def test_nt027_na():
    assert run("NT-027", trace([tool("place_order", 1)])).status == "n/a"  # nothing declared
    assert run("NT-027", trace([tool("lookup", 1)], task={"step_up_tools": ["place_order"]})).status == "n/a"  # no such call
    assert run("NT-027", trace([tool("place_order", 1, error=True)], task={"step_up_tools": ["place_order"]})).status == "n/a"  # blocked
