"""Conformance with the real OpenTelemetry Python SDK (optional extras ``otlp`` / ``conformance``; skipped without them).

1. The official opentelemetry-proto runtime and agentest's standard-library codec decode the same bytes to the same
   OTLP/JSON, for the fixtures and for reference-agent traces (``AGENTEST_OTLP_PROTOBUF=official`` is a drop-in).
2. An agent instrumented with the official SDK (TracerProvider + OTLP/HTTP protobuf exporter, gzip on and off) is
   received by ``agentest std serve`` and gets exactly the verdicts of the hand-written current-semconv trace of the
   same behaviour in tests/test_otel_conformance.py.
CI installs ``.[dev,conformance]`` in a separate job so the core install stays pyyaml-only.
"""
from __future__ import annotations

import json
import socket
import threading
from pathlib import Path

import pytest

from agentest.standards import metadata, otel, otlp_proto, rules, runner

ROOT = Path(__file__).resolve().parents[1]
FIX = ROOT / "tests" / "fixtures" / "otlp"


def test_official_and_stdlib_decoders_agree():
    pytest.importorskip("opentelemetry.proto")
    docs = [json.loads((FIX / f"{n}.otlp.json").read_text()) for n in ("ticket_current", "ticket_events_1_28")]
    for d in sorted((ROOT / "agents").iterdir())[::6]:
        docs += otel.read_otlp_file(next((d / "traces").glob("*.otlp.jsonl")))[:2]
    for doc in docs:
        b = otlp_proto.encode_traces(doc)
        assert otlp_proto.decode_traces(b, "official") == otlp_proto.decode_traces(b, "stdlib")
    for n in ("ticket_current", "ticket_events_1_28"):
        b = (FIX / f"{n}.pb").read_bytes()
        assert otlp_proto.decode_traces(b, "official") == otlp_proto.decode_traces(b, "stdlib")


def test_official_backend_by_environment(monkeypatch):
    pytest.importorskip("opentelemetry.proto")
    b = (FIX / "ticket_current.pb").read_bytes()
    monkeypatch.setenv(otlp_proto.BACKEND_ENV, "official")
    assert otlp_proto.decode_traces(b) == otlp_proto.decode_traces(b, "stdlib")
    monkeypatch.setenv(otlp_proto.BACKEND_ENV, "nope")
    with pytest.raises(otlp_proto.DecodeError):
        otlp_proto.decode_traces(b)


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.mark.parametrize("compression", ["none", "gzip"])
def test_real_otel_sdk_agent_gets_the_same_verdicts(tmp_path, compression):
    pytest.importorskip("opentelemetry.sdk")
    pytest.importorskip("opentelemetry.exporter.otlp.proto.http")
    from opentelemetry.exporter.otlp.proto.http import Compression
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor

    from agentest.standards.serve import make_server
    from tests.test_otel_conformance import ANSWER, ASK, CALLS, CARD, TOOLS, _verdicts, otel_current

    port, out = _free_port(), tmp_path / "inbox"
    srv = make_server(out, port=port)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        pinned = otel.semconv()["pinned"]
        provider = TracerProvider(resource=Resource.create({"service.name": "ticket-desk"}, schema_url=pinned["schema_url"]))
        provider.add_span_processor(SimpleSpanProcessor(OTLPSpanExporter(
            endpoint=f"http://127.0.0.1:{port}/v1/traces", compression=Compression.Gzip if compression == "gzip" else Compression.NoCompression)))
        tracer = provider.get_tracer("ticket-desk-instrumentation", schema_url=pinned["schema_url"])
        msg = lambda role, text: json.dumps([{"role": role, "parts": [{"type": "text", "content": text}]}])  # noqa: E731
        # the agent's own instrumentation: plain OTel SDK calls with GenAI semantic-convention attributes, no agentest import
        with tracer.start_as_current_span("invoke_agent ticket-desk", attributes={
                "gen_ai.operation.name": "invoke_agent", "gen_ai.agent.name": "ticket-desk", "gen_ai.provider.name": "openai",
                "gen_ai.input.messages": msg("user", ASK)}) as root:
            for cid, name, args, res in CALLS:
                with tracer.start_as_current_span(f"execute_tool {name}", attributes={
                        "gen_ai.operation.name": "execute_tool", "gen_ai.tool.name": name, "gen_ai.tool.call.id": cid,
                        "gen_ai.tool.call.arguments": json.dumps(args), "gen_ai.tool.call.result": json.dumps(res)}):
                    pass
            root.set_attribute("gen_ai.output.messages", msg("assistant", ANSWER))
        provider.shutdown()
    finally:
        srv.shutdown()
    [f] = list(out.glob("ticket-desk/traces/*.otlp.jsonl"))
    [doc] = otel.read_otlp_file(f)
    assert otel.declared_semconv(doc) == [pinned["semconv"]]
    d = out / "ticket-desk"
    (d / "agent-card.json").write_text(json.dumps(CARD))
    (d / "tools.json").write_text(json.dumps(TOOLS))
    a = metadata.load_all(out)["ticket-desk"]
    got = {k: v.status for k, v in rules.evaluate(a, runner.runs(a)).items()}
    want = _verdicts(tmp_path / "hand", otel_current())
    assert got == want, {k: (got[k], want[k]) for k in got if got[k] != want[k]}
