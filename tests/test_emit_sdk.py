"""Plain OpenTelemetry connector: an agent instrumented with the real OTel Python SDK, with attributes from
agentest.standards.emit, exported as OTLP protobuf, gets the same verdicts on the default checks as the same behaviour
written by the importer path. Skipped without the optional ``conformance`` extra (CI runs it in its own job)."""

from __future__ import annotations

import json

import pytest

from agentest.standards import emit, otlp_proto
from agentest.standards.otel import from_otlp, split_traces
from tests.test_emit_roundtrip import _episodes, _reference, _verdicts

pytest.importorskip("opentelemetry.sdk")
encoder = pytest.importorskip("opentelemetry.exporter.otlp.proto.common.trace_encoder")


def _sdk_docs(eps) -> list[dict]:
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
    from opentelemetry.trace import Status, StatusCode

    exp = InMemorySpanExporter()
    tp = TracerProvider(resource=Resource.create(emit.resource_attrs("refund_desk")))
    tp.add_span_processor(SimpleSpanProcessor(exp))
    tr = tp.get_tracer("use-case-agent")
    for ep in eps:
        with tr.start_as_current_span(f"invoke_agent {ep.agent}") as root:
            root.set_attributes(emit.attrs_root(ep.agent, ep.input, ep.final_answer, ep.probe, ep.rep, f"{ep.probe}#{ep.rep}",
                                                final_state=ep.final_state or {}, gen_ai__agent__id=None))
            agents = {}
            for h in ep.handoffs:
                for name, src in ((h.source, ""), (h.target, h.source)):
                    if name not in agents:
                        with tr.start_as_current_span(f"invoke_agent {name}") as s:
                            s.set_attributes(emit.attrs_agent(name, src))
                        agents[name] = True
            for i, c in enumerate(ep.tool_calls):
                with tr.start_as_current_span(f"execute_tool {c.name}") as s:
                    s.set_attributes(emit.attrs_tool(c.name, c.arguments, c.result, f"call_{i}", c.actor, c.error))
                    if c.error:
                        s.set_status(Status(StatusCode.ERROR, "tool error"))
            for a in ep.approvals:
                with tr.start_as_current_span("agentest.approval") as s:
                    s.set_attributes(emit.attrs_approval(a.action, a.granted, a.approver, a.target, a.policy_version))
            for sc in ep.state_changes:
                root.add_event("agentest.state_change", emit.attrs_state_change(sc.kind, sc.effect, sc.data))
    raw = encoder.encode_spans(exp.get_finished_spans()).SerializeToString()
    return split_traces(otlp_proto.decode_traces(raw))


def test_sdk_instrumented_runs_get_the_same_verdicts(tmp_path):
    eps = [e for e in _episodes() if e.probe in ("refund-ok", "refund-unapproved", "lookup-error")]
    docs = _sdk_docs(eps)
    assert len(docs) == len(eps)
    got = _verdicts(tmp_path, docs)
    want = _verdicts(tmp_path, [_reference(e) for e in eps])
    assert {k: (got[k], v) for k, v in want.items() if got[k] != v} == {}
    runs = sorted((from_otlp(json.loads(json.dumps(d))) for d in docs), key=lambda r: (r.input_id, r.rep))
    assert [len(r.tools) for r in runs] == [1, 2, 2, 2, 2]
