# Standards primer

agentest reads four kinds of input. This page lists the fields it uses; the full field-by-rule table is in the
[agent-independence audit](../standards/AGENT-INDEPENDENCE-AUDIT.md#4-standard-fields-per-rule).

## OpenTelemetry GenAI semantic conventions

Specification: <https://opentelemetry.io/docs/specs/semconv/gen-ai/> (status: Development, so names can change;
agentest tracks the published names). Transport: OTLP/JSON
(<https://opentelemetry.io/docs/specs/otlp/#json-protobuf-encoding>).

| Field | Where | Used for |
|---|---|---|
| `gen_ai.operation.name` = `invoke_agent`, `execute_tool`, `chat` | span attribute | span roles |
| `gen_ai.agent.name`, `gen_ai.agent.id` | `invoke_agent` span | which (sub-)agent acted; handoffs |
| `gen_ai.tool.name`, `gen_ai.tool.call.id` | `execute_tool` span | tool calls |
| `gen_ai.tool.call.arguments`, `gen_ai.tool.call.result` | `execute_tool` span (opt-in content) | arguments and results |
| `gen_ai.input.messages`, `gen_ai.output.messages` | root / `chat` spans (opt-in content) | request and final answer |
| `gen_ai.conversation.id` | root span | input id when `agentest.input.id` is absent |
| span status, `error.type` | any span | failed steps |
| span start/end time | any span | ordering, durations |
| event `gen_ai.evaluation.result` (`gen_ai.evaluation.score.label`, ...) | root span | harness verdicts (strict mode success signal) |

Message content is opt-in in the semantic conventions. Without it, the text-based checks return n/a.

## A2A AgentCard

Specification: <https://a2a-protocol.org/latest/specification/>. agentest reads `name`, `skills[]`
(`id`, `description`, `tags`, `examples`) and `capabilities.extensions[]`. Skill examples seed generated inputs;
tags such as `lang:hi` give languages when the extension does not.

## MCP tool descriptors

Specification: <https://modelcontextprotocol.io/specification/2025-06-18/server/tools>. agentest reads the
`tools/list` result: `name`, `inputSchema` (JSON Schema, <https://json-schema.org/>) and `annotations`:

| Annotation | MCP default | Meaning for agentest |
|---|---|---|
| `readOnlyHint` | false | false means the tool may change state: it is a **write** (an undeclared tool is a write) |
| `destructiveHint` | true | a write that destroys or overwrites |
| `idempotentHint` | false | repeated identical calls are a defect (T2-003, T1-006) |
| `openWorldHint` | true | the tool reaches outside systems (T5-017) |

MCP says annotations are hints from the server; agentest treats them as the agent owner's declaration.

## Governance extension (optional)

URI `urn:agentest:a2a-ext:governance:v1`, carried in `capabilities.extensions[]` of the AgentCard.
Schema: [governance-extension.schema.json](../../src/agentest/standards/schemas/governance-extension.schema.json).
Field reference and rationale: [EXTENSION.md](../standards/EXTENSION.md). Every field is optional; a rule whose fact
is missing returns n/a.

```json
{"uri": "urn:agentest:a2a-ext:governance:v1", "required": false, "params": {
  "approval": {"required": ["issue_refund"], "hostGated": true},
  "dataClassification": {"restricted": ["card", "pan"]},
  "limits": {"max_tool_calls": 20, "max_amount": 50000},
  "prerequisites": {"issue_refund": ["lookup_order"]},
  "policyCheckTools": ["check_eligibility"]
}}
```

## Standards the catalogue maps to

The [standards map](../standards/STANDARDS-MAP.md) relates each ID to the OWASP Top 10 for LLM Applications 2025
(<https://genai.owasp.org/llm-top-10/>), OWASP Agentic AI Threats and Mitigations
(<https://genai.owasp.org/resource/agentic-ai-threats-and-mitigations/>), NIST AI RMF 1.0
(<https://doi.org/10.6028/NIST.AI.100-1>) and ISO/IEC 42001:2023 Annex A (<https://www.iso.org/standard/81230.html>).
