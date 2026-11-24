# How to test LlamaIndex workflows with agentest

agentest evaluates recorded workflow behavior, including tool calls, results,
and side effects. It imports the recording as OpenTelemetry GenAI spans and
uses an agent card and a tool list to interpret them.

## 1. Try the offline recording

Follow the two commands in the [LlamaIndex import example](../../examples/llamaindex_import/#import-and-evaluate-the-recording).
The four example runs use event fields from
[`llama-index-core` 0.14.26](https://pypi.org/project/llama-index-core/0.14.26/).
Once agentest is installed, the commands need no LlamaIndex installation, API
key, or network access. The recording should match the
[LangGraph example](langgraph.md) on every check, including the failures from
the reimbursement made on an unsupported approval claim.

## 2. Import your own recordings

Use the [recording snippet](../../examples/llamaindex_import/#record-your-own-workflow)
to write a JSONL file from `handler.stream_events()`. Keep the completed tool
calls and the final assistant reply. The example adds `kind`, `name`, and
`data` to those events for agentest's built-in `events` dialect:

| LlamaIndex event | Fields used by agentest |
| --- | --- |
| `ToolCallResult` | `kind: "tool"`, with `tool_name` as `name`, `tool_kwargs` as `data.args`, and the tool output as `data.result` and `data.error` |
| Final `AgentOutput` | `kind: "message"`, with `current_agent_name` as `data.source` and `response.content` as `data.content` |

The [mapping file](../../examples/llamaindex_import/import/map.json) takes the
final answer from `output.response`. It uses the application-state fields
`output.submitted` and `output.reimbursed` for pending and executed effects,
and assigns input families using the run's `probe`. Update those paths and
labels for your application, then pass your recording, mapping, agent card,
and tool list to the same two commands. The simpler `steps` dialect can read a
retrieval step with `sources`. The `events` format carries the arguments and
results for all the expense bot's tools, which are needed for verdict parity.

If you already export OpenTelemetry, follow the
[instrumentation guide](../developers/INSTRUMENTING.md) to emit GenAI spans
that you can pass directly to `agentest std run --otlp`.
