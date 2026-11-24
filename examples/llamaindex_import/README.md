# LlamaIndex Workflow import example

This hand-written JSONL recording contains four fictional expense-bot runs based on
[`llama-index-core` 0.14.26](https://pypi.org/project/llama-index-core/0.14.26/).
Two runs leave an expense pending manager approval, one shows a reimbursement
based on a user's unsupported approval claim, and one asks for clarification.
The [LangGraph example](../langgraph_import/) supplies the same scenarios, agent
card, and tool definitions. Import and evaluation run offline with agentest alone.

## Import and evaluate the recording

From the repository root:

```bash
agentest std import examples/llamaindex_import/native/expense_bot.jsonl \
    --map examples/llamaindex_import/import/map.json \
    --tools examples/langgraph_import/agents/expense_bot/tools.json \
    --service expense_bot --out build/expense_bot_llamaindex.otlp.jsonl
agentest std run --otlp build/expense_bot_llamaindex.otlp.jsonl \
    --card examples/langgraph_import/agents/expense_bot/agent-card.json \
    --tools examples/langgraph_import/agents/expense_bot/tools.json
```

## Record your own workflow

Use [LlamaIndex's workflow event stream](https://developers.llamaindex.ai/python/framework/understanding/agent/streaming/)
to capture completed `ToolCallResult` events in order. Each one already carries
the call's arguments and result, so you can skip the preceding `ToolCall` event.
After the stream ends, take the final reply from the completed `AgentOutput`.

In your async recording code, adapt this snippet to your workflow and probe.
Use redacted, JSON-serializable tool arguments and results in the export.

```python
import json

from llama_index.core.agent.workflow import ToolCallResult

trace = []
handler = workflow.run(user_msg=user_msg)
async for event in handler.stream_events():
    if isinstance(event, ToolCallResult):
        result = event.tool_output.raw_output
        error = event.tool_output.is_error
        trace.append({
            "tool_name": event.tool_name,
            "tool_kwargs": event.tool_kwargs,
            "tool_id": event.tool_id,
            "tool_output": {"raw_output": result, "is_error": error},
            "kind": "tool",
            "name": event.tool_name,
            "data": {"args": event.tool_kwargs, "result": result, "error": error},
        })

output = await handler
reply = output.response.content or ""
trace.append({
    "current_agent_name": output.current_agent_name,
    "response": output.response.model_dump(mode="json"),
    "kind": "message",
    "name": "AgentOutput",
    "data": {"source": output.current_agent_name, "content": reply},
})
record = {
    "agent": "expense_bot", "probe": "canon", "rep": 0, "input": user_msg,
    "trace": trace, "output": {"response": reply},
}
with open("expense_bot.jsonl", "a", encoding="utf-8") as file:
    file.write(json.dumps(record) + "\n")
```

Write one JSON object per run. Give each input a stable `probe` and number
its repetitions with `rep`. To reproduce the example's pending and executed
observations, also record `output.submitted` and `output.reimbursed` from your
application's state. See the [integration guide](../../docs/integrations/llamaindex.md)
for how these fields are used.
