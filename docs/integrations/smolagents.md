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

What maps where is in the [example README](../../examples/smolagents_import/README.md). A `CodeAgent` records one `python_interpreter` call per step with the code as its argument, so tools called inside that code are not visible in memory: add OpenTelemetry spans around those tools to get per-tool evidence. The importer is covered by `tests/test_smolagents_import.py`.

## See also

- [Instrumenting your agent](../developers/INSTRUMENTING.md)
- [LangGraph](langgraph.md) (the expense-bot example uses the same episodes)
- [Getting started](../GETTING-STARTED.md)
