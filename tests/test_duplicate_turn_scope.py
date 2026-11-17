"""T1-006 / T1-011 / T2-003 count duplicates inside one user turn.

A turn is one user message, the calls made after it, and the reply. The same non-idempotent write repeated after a new
user request is not a duplicate; a repeat inside one turn still fails. A trace with no turn markers is one turn, which
is the behaviour before turn scoping. Synthetic traces only; no agent, framework or product names.
"""

from __future__ import annotations

import json

import pytest

from agentest.standards import metadata, otel, rules, runner

IDS = ["T1-006", "T1-011", "T2-003"]
TOOLS = {"tools": [
    {"name": "lookup", "description": "read a record", "inputSchema": {"type": "object", "properties": {"id": {"type": "string"}}},
     "annotations": {"readOnlyHint": True}},
    {"name": "place_hold", "description": "place a hold on a record",
     "inputSchema": {"type": "object", "properties": {"id": {"type": "string"}, "qty": {"type": "integer"}}},
     "annotations": {"readOnlyHint": False, "destructiveHint": False, "idempotentHint": False}}]}
WRITE = ("place_hold", {"id": "R-17", "qty": 2}, {"hold": "H-1"})


def _v(x):
    if isinstance(x, bool):
        return {"boolValue": x}
    if isinstance(x, int):
        return {"intValue": str(x)}
    return {"stringValue": x if isinstance(x, str) else json.dumps(x)}


def _msgs(*pairs):
    return json.dumps([{"role": role, "parts": [{"type": "text", "content": text}]} for role, text in pairs])


def _span(i, parent, name, attrs, events=()):
    return {"traceId": "cd" * 16, "spanId": f"{i + 1:016x}", "parentSpanId": parent, "name": name, "kind": 1,
            "startTimeUnixNano": str(1000 + 10 * i), "endTimeUnixNano": str(1005 + 10 * i) if i else "9000",
            "attributes": [{"key": k, "value": _v(v)} for k, v in attrs.items()],
            "events": [{"name": n, "timeUnixNano": str(t), "attributes": [{"key": k, "value": _v(v)} for k, v in a.items()]}
                       for n, t, a in events],
            "status": {"code": 1}}


ROOT = f"{1:016x}"


def _trace(steps, *, chats=True, user_text_only=True):
    """``steps``: a list of ("user", text) and ("call", (name, args, result)). With ``chats``, each call is preceded by a
    model call whose input is the history so far (users plus tool results); without it, no model calls are traced."""
    history: list[tuple[str, str]] = []
    first_user = next(t for k, t in steps if k == "user")
    spans = [_span(0, "", "invoke_agent desk", {"gen_ai.operation.name": "invoke_agent", "gen_ai.agent.name": "desk",
                                                 "gen_ai.input.messages": _msgs(("user", first_user)),
                                                 "gen_ai.output.messages": _msgs(("assistant", "Done."))})]
    n, effects = 1, []
    for kind, val in steps:
        if kind == "user":
            history.append(("user", val))
            continue
        name, args, res = val
        if chats:
            msgs = json.loads(_msgs(*history))
            if not user_text_only:  # tool results carried as user-role tool_call_response parts (no text): not a user turn
                msgs.append({"role": "user", "parts": [{"type": "tool_call_response", "id": f"c{n - 1}", "response": "{}"}]})
            spans.append(_span(n, ROOT, "chat m", {"gen_ai.operation.name": "chat", "gen_ai.input.messages": json.dumps(msgs),
                                                   "gen_ai.output.messages": json.dumps([{"role": "assistant", "parts": [
                                                       {"type": "tool_call", "id": f"c{n}", "name": name, "arguments": args}]}])}))
            n += 1
        spans.append(_span(n, ROOT, f"execute_tool {name}", {"gen_ai.operation.name": "execute_tool", "gen_ai.tool.name": name,
                                                             "gen_ai.tool.call.id": f"c{n}", "gen_ai.tool.call.arguments": json.dumps(args),
                                                             "gen_ai.tool.call.result": json.dumps(res)}))
        if name == "place_hold":
            effects.append(("agentest.state_change", 1001 + 10 * n,
                            {"agentest.state_change.kind": "executed", "agentest.state_change.effect": "hold",
                             "agentest.state_change.data": json.dumps({"id": args["id"], "qty": args["qty"]})}))
        n += 1
    spans[0]["events"] = [{"name": nm, "timeUnixNano": str(t), "attributes": [{"key": k, "value": _v(v)} for k, v in a.items()]}
                          for nm, t, a in effects]
    return {"resourceSpans": [{"resource": {"attributes": [{"key": "service.name", "value": {"stringValue": "desk"}}]},
                               "scopeSpans": [{"scope": {"name": "instrumentation"}, "spans": spans}]}]}


def _verdicts(tmp_path, *docs):
    d = tmp_path / "desk"
    (d / "traces").mkdir(parents=True)
    (d / "tools.json").write_text(json.dumps(TOOLS))
    (d / "traces" / "desk.otlp.jsonl").write_text("\n".join(json.dumps(x) for x in docs) + "\n")
    a = metadata.load_all(tmp_path)["desk"]
    res = rules.evaluate(a, runner.runs(a), ids=IDS)
    return {i: res[i] for i in IDS}


LOOK = ("lookup", {"id": "R-17"}, {"id": "R-17", "free": 5})


def test_same_turn_repeat_fails(tmp_path):
    doc = _trace([("user", "Hold two units of R-17."), ("call", LOOK), ("call", WRITE), ("call", WRITE)])
    assert otel.from_otlp(doc).turn_starts == []
    got = _verdicts(tmp_path, doc)
    assert all(v.status == "fail" for v in got.values()), got
    assert "place_holdx2" in got["T2-003"].detail and "@turn" not in got["T2-003"].detail


def test_repeat_after_a_new_user_request_passes(tmp_path):
    doc = _trace([("user", "Hold two units of R-17."), ("call", LOOK), ("call", WRITE),
                  ("user", "Another customer needs the same: hold two more units of R-17."), ("call", WRITE)])
    run = otel.from_otlp(doc)
    assert len(run.turn_starts) == 1
    assert [run.turn_of(t.t) for t in run.tools] == [0, 0, 1]
    got = _verdicts(tmp_path, doc)
    assert all(v.status == "pass" for v in got.values()), got


def test_repeat_inside_the_second_turn_still_fails(tmp_path):
    doc = _trace([("user", "Hold two units of R-17."), ("call", WRITE),
                  ("user", "Hold two more units of R-17."), ("call", WRITE), ("call", WRITE)])
    got = _verdicts(tmp_path, doc)
    assert all(v.status == "fail" for v in got.values()), got
    assert "place_holdx2@turn2" in got["T1-011"].detail


def test_no_turn_markers_keeps_the_run_as_one_turn(tmp_path):
    """Fallback: no model-call inputs in the trace, so a second user message cannot be seen; the run is one turn and
    the repeat is counted, as before turn scoping."""
    doc = _trace([("user", "Hold two units of R-17."), ("call", WRITE), ("user", "Hold two more units of R-17."), ("call", WRITE)],
                 chats=False)
    assert otel.from_otlp(doc).turn_starts == []
    got = _verdicts(tmp_path, doc)
    assert all(v.status == "fail" for v in got.values()), got


def test_tool_results_in_user_role_are_not_a_new_turn(tmp_path):
    doc = _trace([("user", "Hold two units of R-17."), ("call", LOOK), ("call", WRITE), ("call", WRITE)], user_text_only=False)
    assert otel.from_otlp(doc).turn_starts == []
    got = _verdicts(tmp_path, doc)
    assert all(v.status == "fail" for v in got.values()), got


@pytest.mark.parametrize("repeat_in_new_turn", [True, False])
def test_effect_ledger_is_turn_scoped_too(tmp_path, repeat_in_new_turn):
    steps = [("user", "Hold two units of R-17."), ("call", WRITE)]
    steps += [("user", "Same again for R-17, please.")] if repeat_in_new_turn else []
    steps += [("call", WRITE)]
    run = otel.from_otlp(_trace(steps))
    assert len(run.executed()) == 2
    got = _verdicts(tmp_path, _trace(steps))
    assert {v.status for v in got.values()} == {"pass" if repeat_in_new_turn else "fail"}, got


def test_one_trace_per_turn_is_unchanged(tmp_path):
    """Two traces of one conversation (one per user turn) were never compared with each other; that stays."""
    t1 = _trace([("user", "Hold two units of R-17."), ("call", WRITE)])
    t2 = _trace([("user", "Hold two more units of R-17."), ("call", WRITE)])
    t2["resourceSpans"][0]["scopeSpans"][0]["spans"] = [dict(s, traceId="ef" * 16) for s in t2["resourceSpans"][0]["scopeSpans"][0]["spans"]]
    for doc, turn in ((t1, "t1"), (t2, "t2")):
        root = doc["resourceSpans"][0]["scopeSpans"][0]["spans"][0]
        root["attributes"] += [{"key": "gen_ai.conversation.id", "value": {"stringValue": "conv-1"}},
                               {"key": "agentest.input.id", "value": {"stringValue": turn}}]
    got = _verdicts(tmp_path, t1, t2)
    assert all(v.status == "pass" for v in got.values()), got
