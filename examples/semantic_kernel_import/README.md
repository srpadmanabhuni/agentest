# Semantic Kernel import example

Four hand-written expense-bot episodes use the serialized `ChatHistory` shape from Microsoft Semantic Kernel
**Python 1.47.0**. They cover two recordings of the same submission request, reimbursement
without verified approval, and an empty request. The example reuses the LangGraph expense bot's AgentCard and
MCP tools list. Both imports produce identical verdict reports.

## Import and evaluate

Run from the repository root with the `agentest` CLI available. The commands use local files and require no
Semantic Kernel installation, model, or API key.

```bash
agentest std import examples/semantic_kernel_import/native/expense_bot.jsonl \
  --map examples/semantic_kernel_import/import/map.json \
  --tools examples/langgraph_import/agents/expense_bot/tools.json \
  --service expense_bot --out build/expense_bot_semantic_kernel.otlp.jsonl
agentest std run --otlp build/expense_bot_semantic_kernel.otlp.jsonl \
  --card examples/langgraph_import/agents/expense_bot/agent-card.json \
  --tools examples/langgraph_import/agents/expense_bot/tools.json
```

The report includes failures because the example bot reimburses an expense based on the user's claim of approval.

## Record your own agent

Keep the Python `ChatHistory` used to run the agent with automatic function calling. Capture it before any history
reduction that removes call/result pairs. When using the chat completion service directly, append its final
assistant message to the history before recording. See [Microsoft's chat history guide](https://learn.microsoft.com/en-us/semantic-kernel/concepts/ai-services/chat-completion/chat-history).

Write one JSON object per completed episode with the serialized history under `history`. Here `prompt` and
`final_answer` are the user's input and the final reply returned by your app.

```python
import json
from pathlib import Path

record = {
    "agent": "my_agent",
    "probe": "canon",
    "rep": 0,
    "input": prompt,
    "history": json.loads(chat_history.serialize()),
    "output": {"final_answer": final_answer},
}
with Path("my_agent.jsonl").open("a", encoding="utf-8") as out:
    out.write(json.dumps(record) + "\n")
```

Use a distinct `probe` and `rep` pair for each episode. Swap in your AgentCard and MCP tools list, and point
the map's `observations` at any state confirmed by your app's system of record. Redact sensitive text, tool
arguments, results, and metadata before sharing the recording. Keep matching call and result IDs consistent.
For the field mapping and the limits of chat history, see the [Semantic Kernel integration guide](../../docs/integrations/semantic-kernel.md).
