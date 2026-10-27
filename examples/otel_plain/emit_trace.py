"""Write one OTel GenAI trace as OTLP/JSON with the standard library only (no agentest, no OTel SDK).

Shows the exact shape agentest reads. Run:  python emit_trace.py > trace.otlp.json
Then:  agentest std run --otlp trace.otlp.json --card agent-card.json --tools tools.json
"""

import json
import os
import sys
import time


def attr(k, v):
    if isinstance(v, bool):
        return {"key": k, "value": {"boolValue": v}}
    if isinstance(v, int):
        return {"key": k, "value": {"intValue": str(v)}}
    return {"key": k, "value": {"stringValue": v if isinstance(v, str) else json.dumps(v)}}


def span(trace, sid, parent, name, attrs, t0, t1, error=False):
    return {"traceId": trace, "spanId": sid, "parentSpanId": parent, "name": name,
            "startTimeUnixNano": str(t0), "endTimeUnixNano": str(t1),
            "attributes": [attr(k, v) for k, v in attrs.items()], "status": {"code": 2 if error else 1}}


def main():
    trace, now = os.urandom(16).hex(), time.time_ns()
    msgs = lambda role, text: [{"role": role, "parts": [{"type": "text", "content": text}]}]  # noqa: E731
    spans = [
        span(trace, "a" * 16, "", "invoke_agent refund_helper", {
            "gen_ai.operation.name": "invoke_agent", "gen_ai.agent.name": "refund_helper",
            "gen_ai.conversation.id": "case-1",
            "gen_ai.input.messages": msgs("user", "Refund order ORD-7 please"),
            "gen_ai.output.messages": msgs("assistant", "Your refund for ORD-7 is waiting for approval.")}, now, now + 3_000_000),
        span(trace, "b" * 16, "a" * 16, "execute_tool lookup_order", {
            "gen_ai.operation.name": "execute_tool", "gen_ai.tool.name": "lookup_order", "gen_ai.tool.call.id": "c1",
            "gen_ai.tool.call.arguments": {"order_id": "ORD-7"}, "gen_ai.tool.call.result": {"total": 40}}, now + 1, now + 1_000_000),
        span(trace, "c" * 16, "a" * 16, "execute_tool request_refund", {
            "gen_ai.operation.name": "execute_tool", "gen_ai.tool.name": "request_refund", "gen_ai.tool.call.id": "c2",
            "gen_ai.tool.call.arguments": {"order_id": "ORD-7", "reason": "customer asked for a refund"},
            "gen_ai.tool.call.result": {"status": "pending_approval"}}, now + 1_000_001, now + 2_000_000),
    ]
    # schemaUrl declares which OTel semantic-conventions version the attributes follow (agentest pins 1.42.0 and
    # reports a newer or unknown one); it is optional.
    doc = {"resourceSpans": [{"resource": {"attributes": [attr("service.name", "refund_helper")]},
                              "schemaUrl": "https://opentelemetry.io/schemas/1.42.0",
                              "scopeSpans": [{"scope": {"name": "manual"}, "spans": spans,
                                              "schemaUrl": "https://opentelemetry.io/schemas/1.42.0"}]}]}
    json.dump(doc, sys.stdout, indent=1)


if __name__ == "__main__":
    main()
