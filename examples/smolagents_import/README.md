# smolagents import example

The same four hand-written `expense_bot` episodes as [`../langgraph_import/`](../langgraph_import/), recorded in the
shape of smolagents memory steps (`agent.memory.get_full_steps()`, one run per JSON line under `trace`). Importing them
with the `smolagents` dialect gives the same verdict on all 130 checks as the LangGraph example
(`tests/test_smolagents_import.py`).

```shell
agentest std import examples/smolagents_import/native/expense_bot.jsonl \
    --map examples/smolagents_import/import/map.json \
    --tools examples/langgraph_import/agents/expense_bot/tools.json \
    --service expense_bot --out build/expense_bot_smol.otlp.jsonl
agentest std run --otlp build/expense_bot_smol.otlp.jsonl \
    --card examples/langgraph_import/agents/expense_bot/agent-card.json \
    --tools examples/langgraph_import/agents/expense_bot/tools.json
```

To record your own agent, write one line per run after it finishes, for example:

```python
import json
steps = agent.memory.get_full_steps()          # list of dicts: TaskStep, PlanningStep, ActionStep
line = {"agent": "my_agent", "probe": "canon", "rep": 0, "input": task, "trace": steps,
        "output": {"final_answer": str(result)}}
open("native/my_agent.jsonl", "a").write(json.dumps(line, default=str) + "\n")
```

What maps where: each ActionStep tool call becomes an `execute_tool` span (its `observations` is the result of the
step's last call, and a step `error` marks that call failed); the `final_answer` tool or a final `action_output`
becomes the reply; model thoughts and plans are not treated as replies. A `CodeAgent` records one `python_interpreter`
call per step with the code as its argument, so the tools called inside the code are not visible in memory: add
OpenTelemetry spans around those tools (see [Instrumenting your agent](../../docs/developers/INSTRUMENTING.md)) to
get per-tool evidence. Outputs such as `submitted` / `reimbursed` in the example come from your own system of record,
listed in the mapping file's `observations`.
