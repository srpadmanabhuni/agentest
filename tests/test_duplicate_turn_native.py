"""T1-006 / T1-011 / T2-003 on traces imported from native logs.

A native log of one multi-turn conversation is one record, and the importer used to drop the later user messages, so the
whole conversation became one turn. The importer now marks each user turn with an ``invoke_agent`` span whose input is
the user side of the conversation so far, and effects listed only at the end of the run take the turn of the tool call
they record. A record with one user turn is exported exactly as before. Synthetic logs only; no agent or product names.
"""

from __future__ import annotations

import json

import pytest

from agentest.standards import importers, metadata, otel, rules, runner

IDS = ["T1-006", "T1-011", "T2-003"]
TOOLS = {"tools": [
    {"name": "lookup", "description": "read a record", "inputSchema": {"type": "object", "properties": {"id": {"type": "string"}}},
     "annotations": {"readOnlyHint": True}},
    {"name": "place_hold", "description": "place a hold on a record",
     "inputSchema": {"type": "object", "properties": {"id": {"type": "string"}, "qty": {"type": "integer"}}},
     "annotations": {"readOnlyHint": False, "destructiveHint": False, "idempotentHint": False}}]}
ARGS = {"id": "R-17", "qty": 2}
MAP = {"dialect": "events", "framework": "generic event log",
       "observations": {"final_answer": ["output.final"], "executed": ["output.executed"]}}


def _ev(seq, kind, name, data):
    return {"seq": seq, "kind": kind, "name": name, "data": data}


def _events_log(steps, *, echo_input=True):
    """``steps``: ("user", text) | ("say", text) | ("call", name). Returns one native record of the events dialect."""
    first = next(t for k, t in steps if k == "user")
    tr, executed = [], []
    for k, v in steps:
        if k == "user":
            if v == first and not tr and not echo_input:
                continue
            tr.append(_ev(len(tr) + 1, "message", "user", {"source": "user", "content": v}))
        elif k == "say":
            tr.append(_ev(len(tr) + 1, "message", "assistant", {"source": "assistant", "content": v}))
        else:
            args = ARGS if v == "place_hold" else {"id": "R-17"}
            tr.append(_ev(len(tr) + 1, "tool", v, {"args": args, "result": {"ok": True}}))
            if v == "place_hold":
                executed.append({"tool": v, **args})
    return {"agent": "desk", "probe": "canon", "rep": 0, "input": first, "trace": tr,
            "output": {"final": "Done.", "executed": executed}}


def _docs(raw, mapping=MAP):
    tools = {t["name"]: t for t in TOOLS["tools"]}
    return importers.to_docs([raw], mapping, "desk", lambda n: not tools[n]["annotations"]["readOnlyHint"])


def _verdicts(tmp_path, docs):
    d = tmp_path / "desk"
    (d / "traces").mkdir(parents=True)
    (d / "tools.json").write_text(json.dumps(TOOLS))
    (d / "traces" / "desk.otlp.jsonl").write_text("\n".join(json.dumps(x) for x in docs) + "\n")
    a = metadata.load_all(tmp_path)["desk"]
    res = rules.evaluate(a, runner.runs(a), ids=IDS)
    return {i: res[i] for i in IDS}


TWO_TURNS = [("user", "Hold two units of R-17."), ("call", "lookup"), ("call", "place_hold"), ("say", "Hold placed."),
             ("user", "Another customer needs the same: hold two more units of R-17."), ("call", "place_hold"), ("say", "Done.")]


def test_repeat_after_a_new_user_message_passes(tmp_path):
    docs = _docs(_events_log(TWO_TURNS))
    run = otel.from_otlp(docs[0])
    assert len(run.turn_starts) == 1
    assert [run.turn_of(t.t) for t in run.tools] == [0, 0, 1]
    assert [e["turn"] for e in run.executed()] == [0, 1]  # end-of-run effects take their call's turn
    got = _verdicts(tmp_path, docs)
    assert all(v.status == "pass" for v in got.values()), got


def test_repeat_inside_one_turn_of_a_multi_turn_log_fails(tmp_path):
    steps = [("user", "Hold two units of R-17."), ("call", "place_hold"), ("say", "Hold placed."),
             ("user", "Thanks. Also check R-17 stock."), ("call", "lookup"), ("call", "place_hold"), ("call", "place_hold"), ("say", "Done.")]
    docs = _docs(_events_log(steps))
    assert len(otel.from_otlp(docs[0]).turn_starts) == 1
    got = _verdicts(tmp_path, docs)
    assert all(v.status == "fail" for v in got.values()), got
    assert "place_holdx2@turn2" in got["T2-003"].detail and "effect x2@turn2" in got["T2-003"].detail


def test_one_turn_log_fails_and_its_export_is_unchanged(tmp_path):
    """No later user message: no turn span is added (the OTLP is what the importer wrote before), the run is one turn and
    the repeat is counted as before."""
    steps = [("user", "Hold two units of R-17."), ("call", "lookup"), ("call", "place_hold"), ("call", "place_hold"), ("say", "Done.")]
    docs = _docs(_events_log(steps))
    names = [s["name"] for s in docs[0]["resourceSpans"][0]["scopeSpans"][0]["spans"]]
    assert names.count("invoke_agent desk") == 1  # the root only
    assert otel.from_otlp(docs[0]).turn_starts == []
    got = _verdicts(tmp_path, docs)
    assert all(v.status == "fail" for v in got.values()), got
    assert "@turn" not in got["T2-003"].detail


@pytest.mark.parametrize("echo_input", [True, False])
def test_the_input_echoed_as_the_first_event_is_the_same_turn(echo_input):
    steps = [("user", "Hold two units of R-17."), ("call", "place_hold"), ("call", "place_hold")]
    run = otel.from_otlp(_docs(_events_log(steps, echo_input=echo_input))[0])
    assert run.turn_starts == []


def test_two_user_messages_before_any_agent_step_are_one_turn():
    steps = [("user", "Hold two units of R-17."), ("user", "Make it quick."), ("call", "place_hold"), ("call", "place_hold")]
    assert otel.from_otlp(_docs(_events_log(steps))[0]).turn_starts == []


def test_message_list_dialect_gets_turns_too(tmp_path):
    raw = {"agent": "desk", "probe": "canon", "rep": 0, "input": "Hold two units of R-17.", "trace": [
        {"role": "human", "content": "Hold two units of R-17."},
        {"role": "ai", "content": "", "tool_calls": [{"name": "place_hold", "args": ARGS}]},
        {"role": "tool", "content": "{\"ok\": true}"},
        {"role": "ai", "content": "Hold placed."},
        {"role": "human", "content": "Same again for the next customer."},
        {"role": "ai", "content": "", "tool_calls": [{"name": "place_hold", "args": ARGS}]},
        {"role": "tool", "content": "{\"ok\": true}"},
        {"role": "ai", "content": "Done."}], "output": {"final": "Done.", "executed": [{"tool": "place_hold", **ARGS}] * 2}}
    docs = _docs(raw, dict(MAP, dialect="langgraph_msgs"))
    assert len(otel.from_otlp(docs[0]).turn_starts) == 1
    got = _verdicts(tmp_path, docs)
    assert all(v.status == "pass" for v in got.values()), got


def test_log_without_message_order_keeps_the_old_behaviour(tmp_path):
    """A dialect that records only tool steps (no user messages in the log) has no inferable boundary: one turn, as before."""
    raw = {"agent": "desk", "probe": "canon", "rep": 0, "input": "Hold two units of R-17.",
           "trace": [{"step": "agent", "log": [{"node": "place_hold", **ARGS}, {"node": "place_hold", **ARGS}]}],
           "output": {"final": "Done.", "executed": [{"tool": "place_hold", **ARGS}] * 2}}
    docs = _docs(raw, dict(MAP, dialect="steps"))
    assert otel.from_otlp(docs[0]).turn_starts == []
    got = _verdicts(tmp_path, docs)
    assert all(v.status == "fail" for v in got.values()), got


def test_sub_agent_invocation_without_growing_user_history_is_not_a_turn():
    """An agent invocation below the root that carries one delegated user message does not start a turn: the user side of
    the conversation did not grow."""
    docs = _docs(_events_log([("user", "Hold two units of R-17."), ("call", "place_hold"), ("call", "place_hold")]))
    spans = docs[0]["resourceSpans"][0]["scopeSpans"][0]["spans"]
    root = spans[0]
    t = int(spans[-1]["startTimeUnixNano"]) - 1
    spans.append({"traceId": root["traceId"], "spanId": "ab" * 8, "parentSpanId": root["spanId"], "name": "invoke_agent helper", "kind": 1,
                  "startTimeUnixNano": str(t), "endTimeUnixNano": str(t + 1),
                  "attributes": [{"key": "gen_ai.operation.name", "value": {"stringValue": "invoke_agent"}},
                                 {"key": "gen_ai.input.messages", "value": {"stringValue": json.dumps(
                                     [{"role": "user", "parts": [{"type": "text", "content": "check stock"}]}])}}]})
    assert otel.from_otlp(docs[0]).turn_starts == []
