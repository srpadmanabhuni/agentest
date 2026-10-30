# Instrumenting an agent to emit OTel GenAI traces

agentest needs OTLP/JSON traces that follow the OTel GenAI semantic conventions
(<https://opentelemetry.io/docs/specs/semconv/gen-ai/>). Your agent does **not** import agentest. Two routes:

1. **Live OTel** (preferred): instrument the agent with any OpenTelemetry SDK, send spans over OTLP to any
   OpenTelemetry Collector, and write them to a file with the Collector's `file` exporter. Then run
   `agentest std run --otlp traces.json --card agent-card.json --tools tools.json`. Or point the exporter straight at
   `agentest std serve` (OTLP/HTTP, JSON or protobuf, gzip; see the [User Guide](../USER-GUIDE.md#5-getting-traces-in)).
2. **Recorded logs**: if you already log runs in some format, convert them with an adapter dialect
   (`steps`, `openai_agents`, `langgraph_msgs`, `autogen`, `events`) or a `file:my_dialect.py` mapping passed to `agentest std import --dialect` / `--map` (see the [Author Guide](../AUTHOR-GUIDE.md#3-a-framework-adapter)).
   See [onboarding](ONBOARDING.md).

## The minimum trace

One trace per run. The root span is `invoke_agent`; each tool call is a child `execute_tool` span.

| Span | Required attributes | Recommended |
|---|---|---|
| root `invoke_agent <name>` | `gen_ai.operation.name=invoke_agent`, `gen_ai.agent.name` | `gen_ai.input.messages`, `gen_ai.output.messages`, `gen_ai.conversation.id` (input id) |
| `execute_tool <tool>` | `gen_ai.operation.name=execute_tool`, `gen_ai.tool.name` | `gen_ai.tool.call.arguments`, `gen_ai.tool.call.result`, `gen_ai.tool.call.id`, error status |
| sub-agent `invoke_agent <name>` | as root | gives handoffs and per-actor checks |

Optional `agentest.*` additions (no standard yet; see [EXTENSION.md](../standards/EXTENSION.md)):
`agentest.tool.reason` on tool spans, an `agentest.approval` span with `agentest.approval.action`, `.target`,
`.approver`, `.granted`, `.policy_version`, `agentest.state_change` events on the root span and
`agentest.final_state` on the root span. Without them the related checks return n/a.

A complete stdlib-only example that writes such a trace: [examples/otel_plain/emit_trace.py](../../examples/otel_plain/emit_trace.py).

## Collector configuration (any vendor-neutral Collector)

```yaml
receivers:
  otlp:
    protocols: {grpc: {}, http: {}}
exporters:
  file:
    path: ./traces.json      # OTLP/JSON, one export per line; agentest reads .json and .jsonl
service:
  pipelines:
    traces: {receivers: [otlp], exporters: [file]}
```

If your instrumentation uses a different naming convention (for example OpenInference `tool.name`), rename the
attributes in the Collector with the `transform` processor before export:

```yaml
processors:
  transform:
    trace_statements:
      - context: span
        statements:
          - set(attributes["gen_ai.tool.name"], attributes["tool.name"]) where attributes["tool.name"] != nil
          - set(attributes["gen_ai.operation.name"], "execute_tool") where attributes["openinference.span.kind"] == "TOOL"
```

## Plain Python with the OpenTelemetry SDK

```python
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
import json

trace.set_tracer_provider(TracerProvider())
trace.get_tracer_provider().add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))  # to your Collector
tr = trace.get_tracer("my-agent")

def run(user_text):
    with tr.start_as_current_span("invoke_agent refund_helper", attributes={
            "gen_ai.operation.name": "invoke_agent", "gen_ai.agent.name": "refund_helper",
            "gen_ai.input.messages": json.dumps([{"role": "user", "parts": [{"type": "text", "content": user_text}]}])}) as root:
        with tr.start_as_current_span("execute_tool lookup_order", attributes={
                "gen_ai.operation.name": "execute_tool", "gen_ai.tool.name": "lookup_order",
                "gen_ai.tool.call.arguments": json.dumps({"order_id": "ORD-7"})}) as s:
            result = lookup_order("ORD-7")
            s.set_attribute("gen_ai.tool.call.result", json.dumps(result))
        answer = "..."
        root.set_attribute("gen_ai.output.messages", json.dumps([{"role": "assistant", "parts": [{"type": "text", "content": answer}]}]))
        return answer
```

The same pattern works in any language with an OpenTelemetry SDK.

## Frameworks

Framework instrumentations change quickly. Before relying on one, export one trace and run
`agentest std run --otlp it.json` to see which IDs get a signal; any field it does not emit gives n/a.

| Framework | Route | Notes |
|---|---|---|
| LangGraph / LangChain | an OTel instrumentation for LangChain that emits GenAI attributes, or manual spans around tool nodes; recorded message lists, graph state and checkpoints also work with the `langgraph_msgs` dialect ([converter](CONVERTERS.md)) | tool nodes map to `execute_tool` spans |
| CrewAI | CrewAI's OpenTelemetry support or an OTel instrumentation for CrewAI; or manual spans in tool `_run` | each crew agent should be its own `invoke_agent` span so role checks work |
| AutoGen (AgentChat / Core) | AutoGen's built-in OpenTelemetry tracing (pass a tracer provider to the runtime); recorded message streams also work with the `autogen` dialect | |
| OpenAI Agents SDK | an OTel processor for the SDK's tracing, or the `openai_agents` dialect over run items ([converter](CONVERTERS.md)) | handoffs become `invoke_agent` children |
| LlamaIndex | an OTel instrumentation for LlamaIndex; rename to `gen_ai.*` in the Collector if it uses another convention | retrieval: add `agentest.citations` |
| MCP servers / clients | wrap each `tools/call` in an `execute_tool` span; save the server's `tools/list` result as `tools.json` | annotations come straight from the server |
| n8n | n8n has no GenAI trace export today; export executions as JSON and convert with a `file:` adapter, or emit spans from a Code node to a Collector | |
| Plain Python | the SDK example above, or the stdlib example | |

agentest does not depend on any of these packages; they are your agent's dependencies, not ours.

## Content capture

The GenAI conventions make message and argument content opt-in. Many checks (claims, injected directives,
leaks of restricted data) need it. Capture content in test environments; if you cannot, those IDs return n/a.
