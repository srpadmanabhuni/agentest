"""A trace emitted by the official OpenTelemetry GenAI instrumentation library (``opentelemetry-util-genai``, which
follows the GenAI semantic conventions and is itself in pre-release) gets the verdicts of the hand-written
trace of the same behaviour in tests/test_otel_conformance.py, in every content-capture mode:

* ``SPAN_ONLY``: messages and tool values are span attributes;
* ``EVENT_ONLY``: the model-call content is on the ``gen_ai.client.inference.operation.details`` log record, as structured values;
* ``SPAN_AND_EVENT``: both.

Skipped when the library is not installed (``pip install --pre opentelemetry-util-genai``). CI sets
``AGENTEST_REQUIRE_GENAI_SDK=1`` after installing it, so a broken install fails there instead of skipping.
"""
from __future__ import annotations

import base64
import importlib
import json
import os

import pytest

from agentest.standards import otel, otlp_proto
from tests.test_otel_conformance import ANSWER, ASK, CALLS, _verdicts, otel_current

REQUIRED = os.environ.get("AGENTEST_REQUIRE_GENAI_SDK") == "1"


def _import(name: str):
    try:
        return importlib.import_module(name)
    except ImportError:
        if REQUIRED:
            raise
        pytest.skip(f"{name} is not installed")


def _hex(b64: str) -> str:
    return base64.b64decode(b64).hex() if b64 else ""


def _emit(monkeypatch, mode: str) -> dict:
    """Run the ticket-desk behaviour through the official handler; return one OTLP/JSON document (spans and log records)."""
    monkeypatch.setenv("OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT", mode)
    monkeypatch.setenv("OTEL_INSTRUMENTATION_GENAI_EMIT_EVENT", "true")
    _import("opentelemetry.util.genai.handler")
    from google.protobuf.json_format import MessageToDict
    from opentelemetry.exporter.otlp.proto.common._internal._log_encoder import encode_logs
    from opentelemetry.exporter.otlp.proto.common.trace_encoder import encode_spans
    from opentelemetry.sdk._logs import LoggerProvider
    from opentelemetry.sdk._logs.export import InMemoryLogRecordExporter, SimpleLogRecordProcessor
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
    from opentelemetry.util.genai.handler import TelemetryHandler
    from opentelemetry.util.genai.types import InputMessage, OutputMessage, Text, ToolCallRequestPart, ToolCallResponse

    res = Resource.create({"service.name": "ticket-desk"})
    spans, logs = InMemorySpanExporter(), InMemoryLogRecordExporter()
    tp, lp = TracerProvider(resource=res), LoggerProvider(resource=res)
    tp.add_span_processor(SimpleSpanProcessor(spans))
    lp.add_log_record_processor(SimpleLogRecordProcessor(logs))
    h = TelemetryHandler(tracer_provider=tp, logger_provider=lp)

    history = [InputMessage(role="user", parts=[Text(content=ASK)])]
    with h.invoke_local_agent(agent_name="ticket-desk") as agent:
        agent.input_messages = list(history)
        for cid, name, args, result in CALLS:
            with h.inference("openai", request_model="gpt-4o") as call:
                call.input_messages = list(history)
                out = OutputMessage(role="assistant", parts=[ToolCallRequestPart(arguments=args, name=name, id=cid)], finish_reason="tool_calls")
                call.output_messages = [out]
            with h.tool(name, agent_name="ticket-desk") as tool:
                tool.tool_call_id, tool.arguments, tool.tool_result = cid, args, result
            history += [InputMessage(role="assistant", parts=out.parts),
                        InputMessage(role="tool", parts=[ToolCallResponse(response=result, id=cid)])]
        with h.inference("openai", request_model="gpt-4o") as call:
            call.input_messages = list(history)
            final = OutputMessage(role="assistant", parts=[Text(content=ANSWER)], finish_reason="stop")
            call.output_messages = [final]
        agent.output_messages = [final]

    doc = otlp_proto.decode_traces(encode_spans(spans.get_finished_spans()).SerializeToString())
    recs = [r for rl in MessageToDict(encode_logs(logs.get_finished_logs())).get("resourceLogs", [])
            for sl in rl.get("scopeLogs", []) for r in sl.get("logRecords", [])]
    for r in recs:  # protobuf JSON carries ids as base64; OTLP/JSON as hex
        r["traceId"], r["spanId"] = _hex(r.get("traceId", "")), _hex(r.get("spanId", ""))
    if recs:
        doc["resourceLogs"] = [{"scopeLogs": [{"logRecords": recs}]}]
    return doc


@pytest.mark.parametrize("mode", ["SPAN_ONLY", "EVENT_ONLY", "SPAN_AND_EVENT"])
def test_official_genai_instrumentation_gets_the_same_verdicts(monkeypatch, tmp_path, mode):
    doc = _emit(monkeypatch, mode)
    [one] = otel.split_traces(doc)
    run = otel.from_otlp(one)
    assert run.input == ASK and run.answer == ANSWER
    assert [(t.name, t.args) for t in run.tools] == [(c[1], c[2]) for c in CALLS]
    assert [json.loads(t.result) for t in run.tools] == [c[3] for c in CALLS]
    got, want = _verdicts(tmp_path / "g", doc), _verdicts(tmp_path / "w", otel_current(chats=True))
    assert got["T1-006"] == "fail"  # the duplicate non-idempotent write is caught from the library's own spans
    assert got == want, {k: (got[k], want[k]) for k in got if got[k] != want[k]}


def test_event_only_mode_leaves_the_content_off_the_spans(monkeypatch):
    doc = _emit(monkeypatch, "EVENT_ONLY")
    keys = {a["key"] for rs in doc["resourceSpans"] for ss in rs["scopeSpans"] for s in ss["spans"] for a in s["attributes"]}
    assert "gen_ai.output.messages" not in keys and "gen_ai.input.messages" not in keys  # why the importer must read the event
    assert doc["resourceLogs"][0]["scopeLogs"][0]["logRecords"]
