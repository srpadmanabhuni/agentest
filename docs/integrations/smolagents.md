# How to test smolagents agents with OpenTelemetry and agentest

agentest (agentest-ai) — deterministic OpenTelemetry evals for AI agents.

agentest scores recorded traces, not your smolagents code. There is a built-in `smolagents` import dialect for `agent.memory.get_full_steps()` (or `get_succinct_steps()`), and a worked example at [`examples/smolagents_import/`](../../examples/smolagents_import/).

## 1. Try it on a recorded smolagents run

The folder `agents/a52/` is a recorded smolagents run that ships in this repository. Python 3.11 or newer, no API key, no network, no model:

```bash
pip install agentest-ai
agentest std run --agent a52 --ids T1-001 --format md
```

Output from agentest 3.5.0:

```text
| ID | status | detail |
|---|---|---|
| T1-001 | pass | case0: postconditions hold |
```

This is a single recorded run, not a failure rate, and not a verdict on smolagents. Other recorded smolagents runs in `agents/` include `a32`, `a41`, `a59` and `a68`.

## 2. Judge your own smolagents runs

**A. Export OpenTelemetry GenAI spans (preferred).** Instrument the agent so tool calls become `execute_tool` spans, export the traces, then:

```bash
agentest std run --otlp traces.otlp.jsonl --card agent-card.json --tools tools.json
```

**B. Import memory steps.** After a run, write one JSON line per run with a `trace` array of memory-step dicts:

```python
import json
steps = agent.memory.get_full_steps()
line = {"agent": "my_agent", "probe": "canon", "rep": 0, "input": task, "trace": steps,
        "output": {"final_answer": str(result)}}
open("native/my_agent.jsonl", "a").write(json.dumps(line, default=str) + "\n")
```

Point a mapping file at it with `"dialect": "smolagents"`, then:

```bash
agentest std import examples/smolagents_import/native/expense_bot.jsonl \
    --map examples/smolagents_import/import/map.json \
    --tools examples/langgraph_import/agents/expense_bot/tools.json \
    --service expense_bot --out build/expense_bot_smol.otlp.jsonl
agentest std run --otlp build/expense_bot_smol.otlp.jsonl \
    --card examples/langgraph_import/agents/expense_bot/agent-card.json \
    --tools examples/langgraph_import/agents/expense_bot/tools.json
```

### How memory steps become a trace

The importer translates smolagents memory steps into trace events:

- Each `ActionStep` tool call becomes an `execute_tool` span containing the tool name, arguments, and call ID.
- The step's `observations` value becomes the result of its last tool call. A step-level `error` marks that call as failed.
- The assistant reply is taken from a `final_answer` tool call, a final ActionStep's `action_output`, or a FinalAnswerStep's `output`.
- Model thoughts (`model_output`) and planning steps are not treated as user or assistant replies.

The mapping file handles application-specific data separately. In the bundled example, `output.submitted` and `output.reimbursed` are mapped to pending and executed observations, while input labels are mapped to test families. These values come from your run record's `output`; they are not automatically inferred from the smolagents step observations.

A `CodeAgent` records one `python_interpreter` call per step, with the generated code as its argument. That wrapper is how the agent runs code, so the importer does not count it as a tool call. It reads the code with Python's `ast` module (the code is parsed, never run) and turns each tool the code calls into a tool call: a bare-name call such as `suggest_menu(diet='veg')` that is a declared tool, or that is not a Python builtin and is not defined or imported in the code. Pass your `tools.json` to `agentest std import --tools` so declared tool names are recognised, including names that shadow a builtin. Checks such as T5-001 and T5-018 then judge the real tools: a tool the code calls that is not declared still fails, and the wrapper alone does not.

Limits: calls are read statically, one per call site, so a call inside a branch that did not run, or in a loop, is listed once; calls through helpers, attributes or `getattr` are not followed; arguments that are not literals are kept as source text; and code that does not parse gives no tool calls. For per-call evidence of what actually ran, export OpenTelemetry spans around the tools; see [Instrumenting your agent](../developers/INSTRUMENTING.md). If you declare a tool named `python_interpreter` in `tools.json`, it is kept as a tool call.

See the [example README](../../examples/smolagents_import/README.md) for the complete recording and mapping walkthrough. The importer is covered by `tests/test_smolagents_import.py`.

## See also

- [Instrumenting your agent](../developers/INSTRUMENTING.md)
- [LangGraph](langgraph.md) (the expense-bot example uses the same episodes)
- [Getting started](../GETTING-STARTED.md)
