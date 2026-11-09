"""n8n execution JSON -> OTel GenAI spans.

The logs in this file are synthetic. They follow the public n8n execution export (``data.resultData.runData``,
Chat Trigger item ``sessionId`` / ``chatInput``, AI Agent ``output`` and ``intermediateSteps``, tool-node
``inputOverride`` / ``ai_tool``, Simple Memory ``ai_memory``) and name no agent, case or desk.

Each execution is one turn. Turns that share a session id share ``gen_ai.conversation.id``.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from agentest.cli import main
from agentest.standards import otel
from agentest.standards.episode import Episode, Message, ToolCall
from agentest.standards.importers import N8nImportError, to_docs
from agentest.standards.metadata import Agent
from agentest.standards.rules import Ctx, _conversations

CHAT = "When chat message received"
AGENT = "AI Agent"
MEMORY = "Simple Memory"
CHAT_TYPE = "@n8n/n8n-nodes-langchain.chatTrigger"
AGENT_TYPE = "@n8n/n8n-nodes-langchain.agent"
MEMORY_TYPE = "@n8n/n8n-nodes-langchain.memoryBufferWindow"
TOOL_TYPE = "@n8n/n8n-nodes-langchain.toolCode"
MAP = {"dialect": "n8n", "framework": "n8n"}
SERVICE = "chat-workflow"
T0 = 1_767_225_600_000  # 2026-01-01T00:00:00.000Z
SPAN = 2_500  # execution length, milliseconds


def _iso(ms: int) -> str:
    dt = datetime.fromtimestamp(ms / 1000, UTC)
    return dt.strftime("%Y-%m-%dT%H:%M:%S.") + f"{dt.microsecond // 1000:03d}Z"


def _execution(eid: str, start_ms: int, chat_input, tools: list[dict], answer: str, *,
               session_id: str | None = "sess-18", session_key: str | None = None, history: list | None = None) -> dict:
    """One synthetic n8n execution, shaped like ``GET /api/v1/executions/:id?includeData=true``."""
    chat_json = {"action": "sendMessage", "chatInput": chat_input}
    if session_id is not None:
        chat_json["sessionId"] = session_id
    params = {"options": {"loadPreviousSession": "memory"}}
    if session_key is not None:
        params["sessionKey"] = session_key
    nodes = [
        {"name": CHAT, "type": CHAT_TYPE, "typeVersion": 1.1, "parameters": params},
        {"name": AGENT, "type": AGENT_TYPE, "typeVersion": 1.7, "parameters": {"promptType": "auto"}},
        {"name": MEMORY, "type": MEMORY_TYPE, "typeVersion": 1.3,
         "parameters": {"sessionIdType": "customKey", "sessionKey": "={{ $json.sessionId }}", "contextWindowLength": 5}},
    ]
    run_data = {
        CHAT: [{"startTime": start_ms, "executionTime": 8, "executionStatus": "success", "source": [None],
                "data": {"main": [[{"json": chat_json, "pairedItem": {"item": 0}}]]}}],
        MEMORY: [{"startTime": start_ms + 10, "executionTime": 2, "executionStatus": "success", "source": [],
                  "data": {"ai_memory": [[{"json": {"action": "loadMemoryVariables", "chatHistory": history or []}}]]}}],
    }
    steps = []
    for tool in tools:
        nodes.append({"name": tool["name"], "type": TOOL_TYPE, "typeVersion": 1.1, "parameters": {}})
        start = start_ms + tool["off"]
        entry = {"startTime": start, "executionTime": tool["dur"], "source": [{"previousNode": AGENT, "previousNodeOutput": 0, "previousNodeRun": 0}],
                 "inputOverride": {"ai_tool": [[{"json": tool["args"]}]]}}
        if tool.get("error"):
            entry["executionStatus"] = "error"
            entry["error"] = {"message": tool["error"], "name": "NodeApiError"}
        else:
            entry["executionStatus"] = "success"
            entry["data"] = {"ai_tool": [[{"json": {"response": tool["result"]}}]]}
        run_data[tool["name"]] = [entry]
        steps.append({"action": {"tool": tool["name"], "toolInput": tool["args"]}, "observation": tool.get("error") or tool["result"]})
    run_data[AGENT] = [{"startTime": start_ms + 20, "executionTime": SPAN - 40, "executionStatus": "success",
                        "source": [{"previousNode": CHAT}],
                        "data": {"main": [[{"json": {"output": answer, "intermediateSteps": steps}}]]}}]
    return {"id": eid, "finished": True, "mode": "webhook", "status": "error" if any(t.get("error") for t in tools) else "success",
            "startedAt": _iso(start_ms), "stoppedAt": _iso(start_ms + SPAN), "workflowId": "wf-chat",
            "workflowData": {"id": "wf-chat", "name": "Chat workflow", "active": True, "nodes": nodes, "connections": {}},
            "data": {"version": 1, "startData": {}, "resultData": {"runData": run_data, "pinData": {}, "lastNodeExecuted": AGENT}}}


def _turns() -> list[dict]:
    """Three turns of one chat. User text is wrapped differently on each turn; tools land on more than one turn."""
    first = "Where is record 18?"
    second = "Send a short note that it is still open."
    third = "What did the note say?"
    return [
        _execution("e1", T0, first, [{"name": "lookup", "args": {"record": "18"}, "result": "still open", "off": 100, "dur": 40}],
                   "Record 18 is still open.", history=[]),
        _execution("e2", T0 + 10_000, json.dumps({"chatInput": second}),
                   [{"name": "lookup", "args": {"record": "18"}, "result": "still open", "off": 80, "dur": 30},
                    {"name": "notify", "args": {"text": "still open"}, "result": "sent", "off": 200, "dur": 25}],
                   "The note was sent.", history=[{"type": "human", "data": {"content": first}}, {"type": "ai", "data": {"content": "Record 18 is still open."}}]),
        _execution("e3", T0 + 20_000, json.dumps({"type": "human", "content": third}),
                   [{"name": "notify", "args": {"text": "still open"}, "error": "upstream timeout", "off": 90, "dur": 15}],
                   "The note could not be sent.", history=[{"type": "human", "data": {"content": second}}]),
    ]


def _import(records: list[dict]) -> list[dict]:
    return to_docs(records, MAP, SERVICE)


def _runs(docs: list[dict]):
    return [otel.from_otlp(d) for d in docs]


def _attrs(span: dict) -> dict:
    return {a["key"]: otel._unv(a["value"]) for a in span.get("attributes", [])}


def _structure(doc: dict) -> list[dict]:
    """Span tree the rules see: operation, parent, tool payload and source timing. Ids and final_state are not part of it."""
    spans = [s for rs in doc["resourceSpans"] for ss in rs["scopeSpans"] for s in ss["spans"]]
    by = {s["spanId"]: s for s in spans}
    rows = []
    for s in sorted(spans, key=lambda s: (int(s["startTimeUnixNano"]), s.get("name", ""))):
        a = _attrs(s)
        parent = by.get(s.get("parentSpanId") or "")
        rows.append({"name": s.get("name"), "op": a.get("gen_ai.operation.name"), "parent": parent.get("name") if parent else "",
                     "tool": a.get("gen_ai.tool.name") or "", "args": a.get("gen_ai.tool.call.arguments"), "result": a.get("gen_ai.tool.call.result"),
                     "error": a.get("error.type"), "status": (s.get("status") or {}).get("code"),
                     "t0": s.get("startTimeUnixNano"), "t1": s.get("endTimeUnixNano"),
                     "conv": a.get("gen_ai.conversation.id"), "input": a.get("gen_ai.input.messages"), "output": a.get("gen_ai.output.messages")})
    return rows


def _native(eid: str, start_ms: int, text: str, answer: str, tools: list[dict], session: str = "sess-18") -> dict:
    """The same turn as a native OTel episode, not read from the n8n log."""
    ep = Episode(agent=SERVICE, probe=eid, rep=0, input=text, final_answer=answer, framework="n8n", conversation=session,
                 t0_ns=start_ms * 1_000_000, duration_s=SPAN / 1000)
    ep.messages.append(Message("assistant", answer, actor=AGENT))
    for tool in tools:
        start = (start_ms + tool["off"]) * 1_000_000
        ep.tool_calls.append(ToolCall(name=tool["name"], arguments=dict(tool["args"]), result=tool.get("error") or tool.get("result"),
                                       actor=AGENT, error=bool(tool.get("error")), start_ns=start, end_ns=start + tool["dur"] * 1_000_000))
    return otel.to_otlp(ep, SERVICE)


def test_single_turn_unwraps_message_object_and_emits_tool_span():
    text = "Where is record 18?"
    raw = _execution("e1", T0, json.dumps({"role": "user", "content": text}),
                     [{"name": "lookup", "args": {"record": "18"}, "result": "still open", "off": 100, "dur": 40}], "Record 18 is still open.")
    run = _runs(_import([raw]))[0]
    assert run.input == text
    assert run.conversation == "sess-18#0"
    assert run.answer == "Record 18 is still open."
    assert [(t.name, t.args, t.result, t.error) for t in run.tools] == [("lookup", {"record": "18"}, "still open", False)]
    start = (T0 + 100) * 1_000_000
    assert (run.tools[0].t, run.tools[0].t1) == (start, start + 40 * 1_000_000)
    assert run.t0 == T0 * 1_000_000
    assert not any(t.name == MEMORY for t in run.tools)


def test_multi_turn_groups_three_turns_by_session_id():
    docs = _import(list(reversed(_turns())))  # file order is not time order
    runs = _runs(docs)
    assert [r.input for r in runs] == ["What did the note say?", "Send a short note that it is still open.", "Where is record 18?"]
    assert len({r.conversation for r in runs}) == 1
    grouped = _conversations(Ctx(Agent("x", Path("."), {}, {}), runs, "strict"))
    assert len(grouped) == 1 and len(grouped[0]) == 3
    assert [r.input for r in grouped[0]] == ["Where is record 18?", "Send a short note that it is still open.", "What did the note say?"]
    assert [r.t0 for r in grouped[0]] == [T0 * 1_000_000, (T0 + 10_000) * 1_000_000, (T0 + 20_000) * 1_000_000]


def test_tools_on_several_turns_keep_their_own_calls():
    runs = {r.input: r for r in _runs(_import(_turns()))}
    assert [(t.name, t.args, t.result) for t in runs["Where is record 18?"].tools] == [("lookup", {"record": "18"}, "still open")]
    assert [(t.name, t.args, t.result, t.error) for t in runs["Send a short note that it is still open."].tools] == [
        ("lookup", {"record": "18"}, "still open", False), ("notify", {"text": "still open"}, "sent", False)]
    # the memory buffer holds the earlier turn; it is not this turn's user text and not a tool call
    assert runs["Send a short note that it is still open."].input == "Send a short note that it is still open."
    assert all(t.name not in {MEMORY, CHAT, AGENT} for r in runs.values() for t in r.tools)


def test_tool_error_span_carries_the_message():
    run = next(r for r in _runs(_import(_turns())) if r.input == "What did the note say?")
    assert len(run.tools) == 1
    tool = run.tools[0]
    assert (tool.name, tool.args, tool.result, tool.error) == ("notify", {"text": "still open"}, "upstream timeout", True)
    start = (T0 + 20_000 + 90) * 1_000_000
    assert (tool.t, tool.t1) == (start, start + 15 * 1_000_000)


def test_missing_session_id_falls_back_to_chat_trigger_session_key():
    key = "thread-7"
    other = "thread-8"
    a = _execution("k1", T0, "First note.", [], "Noted.", session_id=None, session_key=key)
    b = _execution("k2", T0 + 10_000, json.dumps({"chatInput": "Second note."}), [], "Still noted.", session_id=None, session_key=key)
    c = _execution("k3", T0 + 20_000, "Other thread.", [], "Other.", session_id=None, session_key=other)
    assert "sessionId" not in a["data"]["resultData"]["runData"][CHAT][0]["data"]["main"][0][0]["json"]
    runs = {r.input: r for r in _runs(_import([b, c, a]))}
    assert runs["First note."].conversation == runs["Second note."].conversation == f"{key}#0"
    assert runs["Other thread."].conversation == f"{other}#0"
    grouped = _conversations(Ctx(Agent("x", Path("."), {}, {}), list(runs.values()), "strict"))
    assert sorted(len(g) for g in grouped) == [2]


def test_non_wrapper_json_is_the_user_text():
    raw = _execution("j1", T0, '{"hello": "world"}', [], "OK.")
    assert _runs(_import([raw]))[0].input == '{"hello": "world"}'


def test_malformed_input_is_a_clear_error():
    broken = _execution("bad", T0, '{"chatInput": "hello"', [], "nope")
    with pytest.raises(N8nImportError, match="malformed JSON"):
        _import([broken])
    shape = {"id": "bad-shape", "workflowId": "wf-chat", "data": {"resultData": {"runData": []}}}
    with pytest.raises(N8nImportError, match="malformed"):
        _import([shape])
    nodes = {"id": "bad-nodes", "workflowId": "wf-chat", "workflowData": {"nodes": "nope"},
             "data": {"resultData": {"runData": {CHAT: []}}}}
    with pytest.raises(N8nImportError, match="malformed"):
        _import([nodes])


def test_malformed_log_cli_exits_with_the_message(tmp_path, capsys):
    path = tmp_path / "bad.jsonl"
    path.write_text("{not json\n")
    assert main(["std", "import", str(path), "--dialect", "n8n", "--service", SERVICE]) == 2
    assert "malformed" in capsys.readouterr().err
    path.write_text(json.dumps({"id": "x", "workflowId": "wf", "data": {"resultData": {"runData": {}}}}) + "\n")
    assert main(["std", "import", str(path), "--dialect", "n8n", "--service", SERVICE]) == 2
    assert "malformed" in capsys.readouterr().err


def test_golden_multiturn_matches_native_otlp_span_structure():
    """The imported conversation is the same span tree as the equivalent native OTel traces."""
    facts = [
        ("e1", T0, "Where is record 18?", "Record 18 is still open.",
         [{"name": "lookup", "args": {"record": "18"}, "result": "still open", "off": 100, "dur": 40}]),
        ("e2", T0 + 10_000, "Send a short note that it is still open.", "The note was sent.",
         [{"name": "lookup", "args": {"record": "18"}, "result": "still open", "off": 80, "dur": 30},
          {"name": "notify", "args": {"text": "still open"}, "result": "sent", "off": 200, "dur": 25}]),
        ("e3", T0 + 20_000, "What did the note say?", "The note could not be sent.",
         [{"name": "notify", "args": {"text": "still open"}, "error": "upstream timeout", "off": 90, "dur": 15}]),
    ]
    imported = {otel.from_otlp(d).input: _structure(d) for d in _import(_turns())}
    native = {text: _structure(_native(eid, start, text, answer, tools)) for eid, start, text, answer, tools in facts}
    assert set(imported) == set(native)
    for text in native:
        assert imported[text] == native[text]


def test_cli_import_round_trip(tmp_path):
    path = tmp_path / "turns.jsonl"
    path.write_text("".join(json.dumps(r) + "\n" for r in _turns()))
    out = tmp_path / "turns.otlp.jsonl"
    assert main(["std", "import", str(path), "--dialect", "n8n", "--service", SERVICE, "--out", str(out)]) == 0
    docs = [json.loads(ln) for ln in out.read_text().splitlines()]
    assert [_structure(d) for d in docs] == [_structure(d) for d in _import(_turns())]
