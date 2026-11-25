# Pydantic AI import example

The same four hand-written `expense_bot` episodes as [`../langgraph_import/`](../langgraph_import/), recorded in the
shape of a Pydantic AI message history (`result.all_messages_json()`, one run per JSON line under `trace`). The ids,
timestamps and texts are examples. Importing them with the mapping file in [`import/`](import/) gives the same verdicts
as the LangGraph example (`tests/test_pydanticai_import.py`). The sample was written against Pydantic AI 2.75.0
(`pydantic-ai-slim==2.75.0`); no Pydantic AI install is needed to run it.

What is recorded, per run: a `request` message with the `user-prompt`, then for each tool a `response` with a
`tool-call` part (`tool_name`, `args`, `tool_call_id`) and a `request` with the matching `tool-return` part
(`content`, `outcome`), and a last `response` with the `text` reply. The `output` object is the example system of
record: what was actually submitted or reimbursed.

```shell
agentest std import examples/pydanticai_import/native/expense_bot.jsonl \
    --map examples/pydanticai_import/import/map.json \
    --tools examples/langgraph_import/agents/expense_bot/tools.json \
    --service expense_bot --out build/expense_bot.otlp.jsonl
agentest std run --otlp build/expense_bot.otlp.jsonl \
    --card examples/langgraph_import/agents/expense_bot/agent-card.json \
    --tools examples/langgraph_import/agents/expense_bot/tools.json
```

The map selects `"dialect": "file:pydanticai_adapter.py"`, so agentest loads
[`import/pydanticai_adapter.py`](import/pydanticai_adapter.py), a short field mapper. It needs no core
change and no runtime dependency.

To record your own agent, write one line per run after it finishes, for example:

```python
import json
result = agent.run_sync(task)
line = {"agent": "my_agent", "probe": "canon", "rep": 0, "input": task,
        "trace": json.loads(result.all_messages_json()),
        "output": {"final_answer": str(result.output)}}      # add what your system of record did
open("native/my_agent.jsonl", "a").write(json.dumps(line) + "\n")
```

What maps where: each `tool-call` part becomes an `execute_tool` span, and the `tool-return` with the same
`tool_call_id` gives its result; an `outcome` of `failed` or `retried` (or a 1.x `retry-prompt` part) marks that call
failed. `text` parts of a response become the reply, and a call to the `final_result` output tool (structured
`output_type`) becomes the reply as JSON. System prompts and `thinking` parts are not treated as replies. Outputs such
as `submitted` / `reimbursed` come from your own system of record, listed in the mapping file's `observations`.
