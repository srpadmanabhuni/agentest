# How to test AutoGen agents with OpenTelemetry and agentest

agentest (agentest-ai) — deterministic OpenTelemetry evals for AI agents.

agentest scores recorded traces, not your AutoGen (AgentChat / Core) code. Your agent never imports agentest. There is a built-in `autogen` import dialect for recorded AgentChat events, and you can also emit OpenTelemetry GenAI spans.

## 1. Try it on a recorded AutoGen run

The folder `agents/a10/` is a recorded AutoGen run that ships in this repository. Python 3.11 or newer, no API key, no network, no model:

```bash
pip install agentest-ai
agentest std run --agent a10 --ids T1-001 --format md
```

Output from agentest 3.5.0:

```text
| ID | status | detail |
|---|---|---|
| T1-001 | pass | canon: postconditions hold |
```

This is a single recorded run, not a failure rate, and not a verdict on AutoGen. Other recorded AutoGen runs in `agents/` include `a07`, `a16`, `a20`, `a21`, `a25`, `a29`, `a37`, `a50`, `a58` and `a70`.

## 2. Judge your own AutoGen agents

**A. Export OpenTelemetry GenAI spans (preferred).** AutoGen can take a tracer provider on the runtime. Export the spans to a file or to `agentest std serve`, then:

```bash
agentest std run --otlp traces.otlp.jsonl --card agent-card.json --tools tools.json
```

**B. Import recorded AgentChat events.** The built-in dialect `autogen` reads a `trace` list of event objects. `TextMessage` becomes a message; `ToolCallRequestEvent` becomes tool calls; `ToolCallExecutionEvent` puts each result (and `is_error`) on the tool call with the same `call_id`; `HandoffMessage` becomes a handoff. Both shapes are read: the printed form (`FunctionCall(...)` and `FunctionExecutionResult(...)` strings) and the JSON form from `[m.model_dump(mode="json") for m in result.messages]`, where `content` is a list of objects. A log that does not fit the dialect stops with a one-line `std import:` message and exit code 2. A mapping file uses `"dialect": "autogen"`. Then:

```bash
agentest std import events.jsonl --map map.json --out traces.otlp.jsonl
agentest std run --otlp traces.otlp.jsonl --card agent-card.json --tools tools.json
```

The importer is covered by `tests/test_import_other_dialects.py`. Add `--trace-format` on import to write the run-level attributes of the [trace format 1.0.0](../TRACE-FORMAT.md).

## See also

- [Instrumenting your agent](../developers/INSTRUMENTING.md)
- [LangGraph](langgraph.md), [CrewAI](crewai.md), [OpenAI Agents SDK](openai-agents-sdk.md)
- [Getting started](../GETTING-STARTED.md)
