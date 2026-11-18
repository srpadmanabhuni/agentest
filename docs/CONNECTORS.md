# Connectors: emitting the trace format

Connectors write traces in the [trace format 1.0.0](TRACE-FORMAT.md). Every connector is checked by round-trip tests:
the run is emitted, read back, and must get the same verdicts on the default checks as the same behaviour written by
the importer path.

## Plain OpenTelemetry and the Python emitter

`agentest.standards.emit` uses the standard library only and does not import any framework.

With an OpenTelemetry SDK, set the attributes from the `attrs_*` helpers on your own spans:

```python
from agentest.standards import emit

with tracer.start_as_current_span("invoke_agent refund_desk") as root:
    root.set_attributes(emit.attrs_root("refund_desk", "Refund ORD-7", input_id="case-1"))
    with tracer.start_as_current_span("execute_tool lookup_order") as s:
        s.set_attributes(emit.attrs_tool("lookup_order", {"order_id": "ORD-7"}, {"total": 40}, call_id="c1"))
    root.add_event("agentest.state_change", emit.attrs_state_change("executed", "request_refund", {"order_id": "ORD-7"}))
```

Without an SDK, `TraceBuilder` writes one run as OTLP/JSON:

```python
t = emit.TraceBuilder("refund_desk", input_text="Refund ORD-7", input_id="case-1")
t.tool("lookup_order", {"order_id": "ORD-7"}, {"total": 40})
t.approval("request_refund", True, approver="ops")
t.answer("Your refund is approved.")
t.write("traces/run.otlp.jsonl")
```

The emitter follows the format decisions:

- Lists of strings stay OTLP arrays and objects become JSON strings (D4).
- The format version goes on the resource (D5).
- Records can be spans or span events (D8).
- `run_id`, `user_id` and span links identify the run (D9).
- Keyword attributes use `__` for dots, for example `agentest__tool__kind="page_snapshot"`.

Tests:

- `tests/test_emit_roundtrip.py` checks the schema, the read-back and the verdicts.
- `tests/test_emit_sdk.py` does the same with the real OTel SDK. It runs only with the `conformance` extra.
