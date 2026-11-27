# How to test Agno agents with OpenTelemetry and agentest

agentest (agentest-ai) — deterministic OpenTelemetry evals for AI agents.

agentest scores **recorded traces**, not your Agno code. An Agno run keeps its messages and tool calls on the
`RunOutput` that `agent.run()` returns. This page shows how to import those messages with a small local adapter, run
the catalogue checks, and (optionally) contribute a failing case. A complete offline example is
[`examples/agno_import/`](../../examples/agno_import/).

The sample was written against **Agno 3.2.1** (`agno.models.message.Message` and `agno.run.agent.RunOutput`). This
guide needs **no** Agno install, no API key and no network.

The distribution name is `agentest-ai` (import name `agentest`). Install from PyPI, or from a clone as in the
[install guide](../INSTALL-AND-QUICKSTART.md):

```bash
pip install agentest-ai
```

The only runtime dependency of agentest is PyYAML.

## Two ways in

| Path | When to use | Command shape |
|---|---|---|
| **Live OTLP** | An OpenTelemetry instrumentation around your Agno agent already exports GenAI spans | `agentest std run --otlp traces.jsonl --card … --tools …` |
| **Recorded run messages** | You can save `run_output.messages` after each run | `agentest std import … --map map.json` (with `"dialect": "file:agno_adapter.py"`) then `std run` |

Agno runs can be exported with third-party OpenTelemetry instrumentations. agentest reads the OpenTelemetry GenAI
attributes listed below; check that your exporter writes those names, or use the import path.

## Minimum GenAI shape agentest reads

One trace per run. Root span `invoke_agent`; each tool call is a child `execute_tool`.

| Span | Required attributes | Useful extras |
|---|---|---|
| root `invoke_agent <name>` | `gen_ai.operation.name=invoke_agent`, `gen_ai.agent.name` | `gen_ai.input.messages`, `gen_ai.output.messages`, `gen_ai.conversation.id` |
| `execute_tool <tool>` | `gen_ai.operation.name=execute_tool`, `gen_ai.tool.name` | `gen_ai.tool.call.arguments`, `gen_ai.tool.call.result`, `gen_ai.tool.call.id`, error status |

Full attribute tables and a stdlib-only emitter:
[Instrumenting an agent](../developers/INSTRUMENTING.md) and
[`examples/otel_plain/emit_trace.py`](../../examples/otel_plain/emit_trace.py).

## Recording an Agno run

After each run, write one JSON line with the run's messages under `trace`:

```python
import json
run = agent.run(task)                              # agno.run.agent.RunOutput
line = {"agent": "my_agent", "probe": "canon", "rep": 0, "input": task,
        "trace": [m.to_dict() for m in run.messages or []],
        "output": {"final_answer": str(run.content)}}
open("native/my_agent.jsonl", "a").write(json.dumps(line, default=str) + "\n")
```

`run.to_dict()["messages"]` gives the same list. Add to `output` what your own system of record shows after the run
(for example a claim that was submitted or paid): Agno does not know whether a tool's write took effect.

## Importing recorded run messages

Copy [`import/agno_adapter.py`](../../examples/agno_import/import/agno_adapter.py) and
[`import/map.json`](../../examples/agno_import/import/map.json) into one folder. The mapping selects
`"dialect": "file:agno_adapter.py"` and points at the observation fields and input labels.

```bash
agentest std import examples/agno_import/native/expense_bot.jsonl \
    --map examples/agno_import/import/map.json \
    --tools examples/langgraph_import/agents/expense_bot/tools.json \
    --service expense_bot --out build/expense_bot_agno.otlp.jsonl

agentest std run --otlp build/expense_bot_agno.otlp.jsonl \
    --card examples/langgraph_import/agents/expense_bot/agent-card.json \
    --tools examples/langgraph_import/agents/expense_bot/tools.json
```

### How run messages become a trace

- Each entry of an assistant message's `tool_calls` (`{"id", "type": "function", "function": {"name", "arguments"}}`)
  becomes an `execute_tool` span with the tool name, the parsed JSON arguments and the call id.
- The `tool` message with the same `tool_call_id` gives the result (`content`); `tool_call_error: true` marks the call
  failed. A `tool` message without a matching request still becomes a call, from `tool_name` and `tool_args`.
- Assistant text becomes the reply. `system` messages are instructions and are skipped. A `user` message equal to the
  run input is not repeated.
- Messages with `from_history: true` were replayed from earlier runs of the session and are skipped.

## What is and is not visible

- Visible: every tool the model asked for, its arguments, its result and whether it raised an error, and the reply.
- Not visible: whether a write took effect in your system. Record that under `output` and list it in the mapping's
  `observations` (`pending`, `executed`), as the example does.
- Not visible: tools called inside a nested agent or team member run, unless you record that run's messages too.
- Human-in-the-loop pauses (`requires_confirmation` on a tool) are not mapped by this adapter.

The importer is covered by `tests/test_agno_import.py`: the imported example gives the same verdicts as the LangGraph
example on all checks.

## See also

- [Agno import example](../../examples/agno_import/)
- [LangGraph](langgraph.md) (the expense-bot example uses the same episodes)
- [Author Guide §3](../AUTHOR-GUIDE.md#3-a-framework-adapter): writing a `file:my.py` adapter
- [Contributing a failing case from your own agent](../../CONTRIBUTING.md)
