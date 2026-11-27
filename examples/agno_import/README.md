# Agno import example

The same four hand-written `expense_bot` episodes as [`../langgraph_import/`](../langgraph_import/), recorded in the
shape of an Agno run's messages (`[m.to_dict() for m in run_output.messages]`, one run per JSON line under `trace`).
Importing them with the local adapter [`import/agno_adapter.py`](import/agno_adapter.py) gives the same verdicts as
the LangGraph example (`tests/test_agno_import.py`). The sample was written against **Agno 3.2.1**; the ids and
timestamps are example values, and the episodes are not a recording of a live Agno agent.

## What is recorded

Each line is one run: `agent`, `probe` (which kind of input it was), `rep`, `input`, `trace` and `output`.

- `trace` is the run's message list: a `system` message (instructions, skipped), the `user` message, `assistant`
  messages with `tool_calls` (`{"id", "type": "function", "function": {"name", "arguments"}}`), `tool` messages with
  the result in `content` plus `tool_call_id`, `tool_name`, `tool_args` and `tool_call_error`, and the final
  `assistant` reply.
- `output` holds what your own system of record shows after the run (`submitted` / `reimbursed` claims) and the final
  answer. The mapping file [`import/map.json`](import/map.json) points agentest at those fields.

## Import, then run

From the repository root, offline:

```bash
agentest std import examples/agno_import/native/expense_bot.jsonl \
    --map examples/agno_import/import/map.json \
    --tools examples/langgraph_import/agents/expense_bot/tools.json \
    --service expense_bot --out build/expense_bot_agno.otlp.jsonl
agentest std run --otlp build/expense_bot_agno.otlp.jsonl \
    --card examples/langgraph_import/agents/expense_bot/agent-card.json \
    --tools examples/langgraph_import/agents/expense_bot/tools.json
```

The social-engineering episode (`probe: social`) reimburses without approval, and the run reports it as a fail.

## Record your own agent

After each run, write one line with the run's messages:

```python
import json
run = agent.run(task)                              # agno.run.agent.RunOutput
line = {"agent": "my_agent", "probe": "canon", "rep": 0, "input": task,
        "trace": [m.to_dict() for m in run.messages or []],
        "output": {"final_answer": str(run.content)}}
open("native/my_agent.jsonl", "a").write(json.dumps(line, default=str) + "\n")
```

Copy `import/map.json` and `import/agno_adapter.py` next to each other, keep `"dialect": "file:agno_adapter.py"`,
and change `observations` and `labels` to the fields and inputs of your agent.

What maps where: each `tool_calls` entry becomes an `execute_tool` span; the `tool` message with the same
`tool_call_id` gives its result, and `tool_call_error: true` marks it failed. Assistant text becomes the reply. A
`user` message equal to the run input is not repeated, and messages with `from_history: true` (replayed from earlier
runs in the session) are skipped. Effects such as `submitted` / `reimbursed` come from your own system of record,
listed in the mapping file's `observations`.
