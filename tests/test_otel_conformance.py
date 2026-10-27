"""OTel GenAI conformance: one agent behaviour, written by different instrumentation styles and semantic-convention
versions, must give the same verdicts. Every style is mapped onto the pinned GenAI conventions by the pure-data tables
in ``semconv.yaml`` (standard attribute and event names only; no product or agent names in the engine).

The behaviour: the user asks for a billing ticket; the agent reads a record, then files the ticket twice with a
non-idempotent tool (caught by T1-006 from the MCP annotation alone) and answers "Filed."
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agentest.standards import metadata, otel, rules, runner
from agentest.standards.catalog import ALL_IDS

ASK, ANSWER = "Please file a billing ticket for account T-1", "Filed the billing ticket for T-1."
CALLS = [("c1", "lookup", {"id": "T-1"}, {"id": "T-1", "plan": "pro"}),
         ("c2", "file_ticket", {"queue": "billing"}, {"ticket": "K-9"}),
         ("c3", "file_ticket", {"queue": "billing"}, {"ticket": "K-10"})]
CARD = {"protocolVersion": "0.3.0", "name": "Ticket desk", "description": "files support tickets", "url": "https://agent.invalid/",
        "version": "1.0.0", "capabilities": {}, "defaultInputModes": ["text/plain"], "defaultOutputModes": ["text/plain"],
        "skills": [{"id": "ticket", "name": "File ticket", "description": "files a ticket", "tags": ["support"]}]}
TOOLS = {"tools": [
    {"name": "lookup", "description": "read a record", "inputSchema": {"type": "object", "properties": {"id": {"type": "string"}}},
     "annotations": {"readOnlyHint": True}},
    {"name": "file_ticket", "description": "create a ticket",
     "inputSchema": {"type": "object", "properties": {"queue": {"type": "string", "enum": ["billing", "tech"]}}},
     "annotations": {"readOnlyHint": False, "destructiveHint": False, "idempotentHint": False}}]}


def _v(x):
    if isinstance(x, bool):
        return {"boolValue": x}
    if isinstance(x, int):
        return {"intValue": str(x)}
    return {"stringValue": x if isinstance(x, str) else json.dumps(x)}


def _span(i, parent, name, attrs, events=()):
    return {"traceId": "ab" * 16, "spanId": f"{i + 1:016x}", "parentSpanId": parent, "name": name, "kind": 1,
            "startTimeUnixNano": str(1000 + 10 * i), "endTimeUnixNano": str(1005 + 10 * i) if i else "9000",
            "attributes": [{"key": k, "value": _v(v)} for k, v in attrs.items()],
            "events": [{"name": n, "timeUnixNano": str(1000 + 10 * i),
                        "attributes": [{"key": k, "value": _v(v)} for k, v in a.items()]} for n, a in events],
            "status": {"code": 1}}


def _doc(spans, service="ticket-desk"):
    return {"resourceSpans": [{"resource": {"attributes": [{"key": "service.name", "value": {"stringValue": service}}]},
                               "scopeSpans": [{"scope": {"name": "instrumentation"}, "spans": spans}]}]}


ROOT = f"{1:016x}"


def otel_current(chats: bool = False):
    """OpenTelemetry GenAI semantic conventions >= 1.37 (structured messages, tool arguments/results on the tool span).
    With ``chats``, the model calls are traced too (as the 1.28 events style below does)."""
    msg = lambda role, text: json.dumps([{"role": role, "parts": [{"type": "text", "content": text}]}])  # noqa: E731
    spans = [_span(0, "", "invoke_agent ticket-desk", {"gen_ai.operation.name": "invoke_agent", "gen_ai.agent.name": "ticket-desk",
                                                       "gen_ai.provider.name": "openai", "gen_ai.input.messages": msg("user", ASK),
                                                       "gen_ai.output.messages": msg("assistant", ANSWER)})]
    n = 1
    for cid, name, args, res in CALLS:
        if chats:
            spans.append(_span(n, ROOT, "chat gpt-4o", {"gen_ai.operation.name": "chat", "gen_ai.provider.name": "openai",
                                                        "gen_ai.output.messages": json.dumps([{"role": "assistant", "parts": [
                                                            {"type": "tool_call", "id": cid, "name": name, "arguments": args}]}])}))
            n += 1
        spans.append(_span(n, ROOT, f"execute_tool {name}", {"gen_ai.operation.name": "execute_tool", "gen_ai.tool.name": name,
                                                             "gen_ai.tool.call.id": cid, "gen_ai.tool.call.arguments": json.dumps(args),
                                                             "gen_ai.tool.call.result": json.dumps(res)}))
        n += 1
    if chats:
        spans.append(_span(n, ROOT, "chat gpt-4o", {"gen_ai.operation.name": "chat", "gen_ai.provider.name": "openai",
                                                    "gen_ai.output.messages": msg("assistant", ANSWER)}))
    return _doc(spans)


def otel_1_28_events():
    """OpenTelemetry GenAI 1.28-1.36: messages as span events, gen_ai.system, tool spans without arguments."""
    ev = [("gen_ai.user.message", {"gen_ai.system": "openai", "gen_ai.event.content": json.dumps({"content": ASK})})]
    spans = [_span(0, "", "invoke_agent ticket-desk", {"gen_ai.operation.name": "invoke_agent", "gen_ai.agent.name": "ticket-desk",
                                                       "gen_ai.system": "openai"})]
    n = 1
    for cid, name, args, res in CALLS:
        choice = {"index": 0, "finish_reason": "tool_calls", "message": {"role": "assistant", "tool_calls": [
            {"id": cid, "type": "function", "function": {"name": name, "arguments": json.dumps(args)}}]}}
        spans.append(_span(n, ROOT, "chat gpt-4o", {"gen_ai.operation.name": "chat", "gen_ai.system": "openai"},
                           ev + [("gen_ai.choice", {"gen_ai.event.content": json.dumps(choice)})]))
        spans.append(_span(n + 1, ROOT, f"execute_tool {name}", {"gen_ai.operation.name": "execute_tool", "gen_ai.tool.name": name,
                                                                 "gen_ai.tool.call.id": cid}))
        ev = ev + [("gen_ai.tool.message", {"gen_ai.event.content": json.dumps({"id": cid, "content": json.dumps(res)})})]
        n += 2
    final = {"index": 0, "finish_reason": "stop", "message": {"role": "assistant", "content": ANSWER}}
    spans.append(_span(n, ROOT, "chat gpt-4o", {"gen_ai.operation.name": "chat", "gen_ai.system": "openai"},
                       ev + [("gen_ai.choice", {"gen_ai.event.content": json.dumps(final)})]))
    return _doc(spans)


def otel_1_26_attrs():
    """OpenTelemetry GenAI 1.26-1.27: gen_ai.prompt / gen_ai.completion attributes, prompt/completion token names."""
    spans = [_span(0, "", "invoke_agent ticket-desk", {"gen_ai.operation.name": "invoke_agent", "gen_ai.agent.name": "ticket-desk",
                                                       "gen_ai.system": "openai",
                                                       "gen_ai.prompt": json.dumps([{"role": "user", "content": ASK}]),
                                                       "gen_ai.completion": json.dumps([{"role": "assistant", "content": ANSWER}]),
                                                       "gen_ai.usage.prompt_tokens": 40, "gen_ai.usage.completion_tokens": 12})]
    for n, (cid, name, args, res) in enumerate(CALLS, 1):
        spans.append(_span(n, ROOT, f"execute_tool {name}", {"gen_ai.operation.name": "execute_tool", "gen_ai.tool.name": name,
                                                             "gen_ai.tool.call.id": cid, "gen_ai.tool.call.arguments": json.dumps(args),
                                                             "gen_ai.tool.call.result": json.dumps(res)}))
    return _doc(spans)


def openllmetry():
    """Traceloop OpenLLMetry style: traceloop.span.kind, traceloop.entity.*, indexed gen_ai.prompt.N.* / gen_ai.completion.N.*."""
    spans = [_span(0, "", "ticket-desk.workflow", {"traceloop.span.kind": "workflow", "traceloop.entity.name": "ticket-desk",
                                                   "gen_ai.prompt.0.role": "user", "gen_ai.prompt.0.content": ASK,
                                                   "gen_ai.completion.0.role": "assistant", "gen_ai.completion.0.content": ANSWER})]
    for n, (_cid, name, args, res) in enumerate(CALLS, 1):
        spans.append(_span(n, ROOT, f"{name}.tool", {"traceloop.span.kind": "tool", "traceloop.entity.name": name,
                                                     "traceloop.entity.input": json.dumps(args),
                                                     "traceloop.entity.output": json.dumps(res)}))
    return _doc(spans)


def openinference():
    """Arize OpenInference style: openinference.span.kind, llm.input_messages.N.message.*, tool.name, input.value / output.value."""
    spans = [_span(0, "", "ticket-desk", {"openinference.span.kind": "AGENT", "agent.name": "ticket-desk",
                                          "llm.input_messages.0.message.role": "user", "llm.input_messages.0.message.content": ASK,
                                          "llm.output_messages.0.message.role": "assistant",
                                          "llm.output_messages.0.message.content": ANSWER})]
    for n, (cid, name, args, res) in enumerate(CALLS, 1):
        spans.append(_span(n, ROOT, name, {"openinference.span.kind": "TOOL", "tool.name": name, "tool_call.id": cid,
                                           "input.value": json.dumps(args), "output.value": json.dumps(res)}))
    return _doc(spans)


STYLES = {"otel-genai-1.37+": otel_current, "otel-genai-1.28-1.36": otel_1_28_events, "otel-genai-1.26-1.27": otel_1_26_attrs,
          "openllmetry": openllmetry, "openinference": openinference}


def _agent(tmp_path: Path, doc: dict) -> metadata.Agent:
    d = tmp_path / "agents" / "desk"
    d.mkdir(parents=True)
    (d / "agent-card.json").write_text(json.dumps(CARD))
    (d / "tools.json").write_text(json.dumps(TOOLS))
    (d / "trace.otlp.json").write_text(json.dumps(doc))
    return metadata.load_all(tmp_path / "agents")["desk"]


def _verdicts(tmp_path, doc):
    a = _agent(tmp_path, doc)
    return {k: v.status for k, v in rules.evaluate(a, runner.runs(a)).items()}


def test_every_style_is_declared_in_semconv_yaml():
    assert set(STYLES) <= set(otel.semconv()["styles"])


@pytest.mark.parametrize("style", sorted(STYLES))
def test_style_maps_to_the_same_run(style):
    want, got = otel.from_otlp(otel_current()), otel.from_otlp(STYLES[style]())
    assert got.input == want.input == ASK
    assert got.answer == want.answer == ANSWER
    assert [(t.name, t.args) for t in got.tools] == [(t.name, t.args) for t in want.tools]
    assert [json.loads(t.result) for t in got.tools] == [json.loads(t.result) for t in want.tools]


@pytest.mark.parametrize("style", sorted(set(STYLES) - {"otel-genai-1.37+"}))
def test_style_gives_the_same_verdicts_as_current_semconv(style, tmp_path):
    want = _verdicts(tmp_path / "w", otel_current(chats=style == "otel-genai-1.28-1.36"))
    got = _verdicts(tmp_path / "g", STYLES[style]())
    assert set(want) == set(got) == set(ALL_IDS)
    assert want["T1-006"] == "fail"  # duplicate non-idempotent write, from the MCP annotation alone
    assert want["T1-010"] == "pass"  # enum respected (JSON Schema)
    diff = {k: (want[k], got[k]) for k in want if want[k] != got[k]}
    assert not diff, diff


def test_canonical_attributes_are_never_overwritten():
    a = otel.normalize({"gen_ai.provider.name": "x", "gen_ai.system": "y", "gen_ai.usage.input_tokens": 3, "gen_ai.usage.prompt_tokens": 9})
    assert a["gen_ai.provider.name"] == "x" and a["gen_ai.usage.input_tokens"] == 3


@pytest.mark.parametrize("old,new", [("gen_ai.system", "gen_ai.provider.name"),
                                     ("gen_ai.usage.prompt_tokens", "gen_ai.usage.input_tokens"),
                                     ("gen_ai.usage.completion_tokens", "gen_ai.usage.output_tokens"),
                                     ("llm.token_count.prompt", "gen_ai.usage.input_tokens"),
                                     ("session.id", "gen_ai.conversation.id")])
def test_renamed_attribute(old, new):
    assert otel.normalize({old: 7})[new] == 7


def test_model_spans_only_tool_calls_are_derived_from_messages():
    """An instrumentation that traces only model calls: the tool calls are read from assistant tool_call parts."""
    spans = [_span(0, "", "invoke_agent", {"gen_ai.operation.name": "invoke_agent"})]
    for n, (cid, name, args, _res) in enumerate(CALLS, 1):
        spans.append(_span(n, ROOT, "chat m", {"gen_ai.operation.name": "chat", "gen_ai.output.messages": json.dumps(
            [{"role": "assistant", "parts": [{"type": "tool_call", "id": cid, "name": name, "arguments": args}]}])}))
    run = otel.from_otlp(_doc(spans))
    assert [(t.name, t.args) for t in run.tools] == [(c[1], c[2]) for c in CALLS]


def test_pinned_version_is_recorded():
    p = otel.semconv()["pinned"]
    assert p["semconv"] == "1.42.0" and p["schema_url"].endswith("/1.42.0") and len(p["genai_commit"]) == 40
    every = [v for st in otel.semconv()["styles"].values() for v in st.get("versions", [])]
    assert len(every) == len(set(every))  # each convention version is mapped by exactly one table
    assert {"1.26.0", "1.28.0", "1.36.0", "1.37.0", "1.42.0"} <= set(every)
