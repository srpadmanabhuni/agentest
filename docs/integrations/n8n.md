# How to test n8n agents with OpenTelemetry and agentest

agentest (agentest-ai) — deterministic OpenTelemetry evals for AI agents.

agentest scores recorded traces, not your n8n workflow source. There is a built-in `n8n` import dialect for exported execution data, and recorded n8n runs ship in this repository. Read the limitation below before you rely on per-episode tool-call checks.

## 1. Try it on a recorded n8n run

The folder `agents/a01/` is a recorded n8n run that ships in this repository. Python 3.11 or newer, no API key, no network, no model:

```bash
pip install agentest-ai
agentest std run --agent a01 --ids T1-001 --format md
```

Output from agentest 3.5.0:

```text
| ID | status | detail |
|---|---|---|
| T1-001 | pass | canon: postconditions hold |
```

This is a single recorded run, not a failure rate, and not a verdict on n8n. Other recorded n8n runs in `agents/` include `a08` and `a23`.

## 2. Judge your own n8n executions

**A. Emit OpenTelemetry GenAI spans (preferred when you need per-step tool evidence).** n8n has no built-in GenAI trace export. You can emit spans from a Code node to a Collector or to `agentest std serve`, then:

```bash
agentest std run --otlp traces.otlp.jsonl --card agent-card.json --tools tools.json
```

**B. Import an n8n execution export.** The built-in dialect is `n8n`. A mapping file uses `"dialect": "n8n"`. Then:

```bash
agentest std import executions.jsonl --map map.json --out traces.otlp.jsonl
agentest std run --otlp traces.otlp.jsonl --card agent-card.json --tools tools.json
```

**Execution export.** The `n8n` dialect also reads the public execution export (`data.resultData.runData`, as returned by the n8n executions API with data included). One execution is one turn. Turns that share the Chat Trigger `sessionId` (or its literal `sessionKey`) become one conversation, `chatInput` is stored as text, and each tool node run becomes an `execute_tool` span with its arguments, result and timing. See [Instrumenting](../developers/INSTRUMENTING.md#n8n-execution-json).

**Limitation (recordings that are not an execution export):** per-episode tool calls are not recoverable from the recorded shape. `tool_inputs_whole_run` lists the tool definitions the AI Agent node was offered (name and description, no arguments) and `tool_results_whole_run` lists results for the whole recording run; both are identical across episodes. The importer therefore records no per-episode tool calls. Run-level calls actually made (a definition paired with a result) go to `final_state["run_tool_calls"]` for checks that can use run-level evidence. Checks that need per-episode arguments or order will return `n/a` unless you also emit OpenTelemetry `execute_tool` spans.

The importer is covered by `tests/test_import_n8n.py`. Add `--trace-format` on import to write the run-level attributes of the [trace format 1.0.0](../TRACE-FORMAT.md).

## See also

- [Instrumenting your agent](../developers/INSTRUMENTING.md)
- [Getting started](../GETTING-STARTED.md)
