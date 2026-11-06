# LangGraph integration (flagship)

agentest scores **recorded traces**, not your graph code. LangGraph is the flagship
framework example: bring a message-list or OTLP export, run the catalogue checks, and
(optionally) contribute a failing case. Theme: *Bring an agent trace, contribute a test.*

The distribution name will be `agentest-ai` (import name `agentest`). It is not on PyPI yet; install from a clone or from git, as in the [README](../../README.md#quickstart-from-a-clone-copy-and-paste). The only
runtime dependency of agentest is PyYAML. This guide needs **no** LangGraph install to
follow the recorded example.

## Two ways in

| Path | When to use | Command shape |
|---|---|---|
| **Live OTLP** (preferred) | Your graph (or an OpenTelemetry instrumentation around its nodes) already emits GenAI spans | `agentest std run --otlp traces.jsonl --card … --tools …` |
| **Recorded message lists** | You have LangGraph / LangChain-style `{role, content, tool_calls}` episodes | `agentest std import … --dialect langgraph_msgs` then `std run` |

A complete offline walk-through of the second path is
[`examples/langgraph_import/`](../../examples/langgraph_import/)
(`test_langgraph.py` imports the bundled episodes and prints a short report).

## Minimum GenAI shape agentest reads

One trace per run. Root span `invoke_agent`; each tool node is a child `execute_tool`.

| Span | Required attributes | Useful extras |
|---|---|---|
| root `invoke_agent <name>` | `gen_ai.operation.name=invoke_agent`, `gen_ai.agent.name` | `gen_ai.input.messages`, `gen_ai.output.messages`, `gen_ai.conversation.id` |
| `execute_tool <tool>` | `gen_ai.operation.name=execute_tool`, `gen_ai.tool.name` | `gen_ai.tool.call.arguments`, `gen_ai.tool.call.result`, `gen_ai.tool.call.id`, error status |
| handoff / interrupt | recorded as a handoff span or a declared escalation tool call | unlocks T3 / X human-gate checks; see [EXTENSION.md](../standards/EXTENSION.md) |

Full attribute tables and a stdlib-only emitter:
[Instrumenting an agent](../developers/INSTRUMENTING.md) and
[`examples/otel_plain/emit_trace.py`](../../examples/otel_plain/emit_trace.py).

## Emitting OTLP from a LangGraph app

1. Instrument tool nodes (or use a GenAI-aware OpenTelemetry instrumentation for the
   stack you already run). Map each tool invocation to an `execute_tool` span with the
   attributes above.
2. Export spans with any OpenTelemetry Collector `file` exporter (OTLP/JSON or JSONL),
   or POST them to `agentest std serve`.
3. Ship an [Agent Card](../developers/AGENT-CARD.md) and an MCP-style `tools.json` (read-only
   vs state-changing hints matter for T2/T3/T5).
4. Score:

```bash
agentest std run --otlp traces.otlp.jsonl \
  --card path/to/agent-card.json \
  --tools path/to/tools.json
```

Human-in-the-loop interrupts should appear either as a handoff span or as a call to the
tool named in `governance.escalation.handoffTool` / `escalation.tools` on the card.

## Importing recorded LangGraph message lists

Dialect: `langgraph_msgs`. Each episode is one JSON object with a `trace` array of
messages (`human` / `ai` / `tool`, optional `tool_calls`). A mapping file points at
observation fields and input labels — see
[`examples/langgraph_import/import/map.json`](../../examples/langgraph_import/import/map.json).

```bash
agentest std import examples/langgraph_import/native/expense_bot.jsonl \
  --map examples/langgraph_import/import/map.json \
  --tools examples/langgraph_import/agents/expense_bot/tools.json \
  --service expense_bot --out build/expense_bot.otlp.jsonl

agentest std run --otlp build/expense_bot.otlp.jsonl \
  --card examples/langgraph_import/agents/expense_bot/agent-card.json \
  --tools examples/langgraph_import/agents/expense_bot/tools.json
```

Or run the flagship script (same steps, prints a short sample report):

```bash
python examples/langgraph_import/test_langgraph.py
```

## What this example deliberately is not

- Not a live model call and not a paid API path.
- Not a second eval framework and not a vendor wrapper — only a dialect + docs.
- Other framework templates stay out of this folder on purpose; LangGraph is the single
  flagship integration for now. Further adapters are tracked on the
  [roadmap](../ROADMAP.md).

## Next steps

- Walkthroughs built on recorded traces: [docs/walkthroughs/](../walkthroughs/README.md)
- Authoring a new adapter dialect: [Author Guide §3](../AUTHOR-GUIDE.md#3-a-framework-adapter)
- Contributing a failing case from your own agent: [CONTRIBUTING.md](../../CONTRIBUTING.md)
