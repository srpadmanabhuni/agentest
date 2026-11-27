# Vercel AI SDK import example

The same four hand-written `expense_bot` episodes as [`../langgraph_import/`](../langgraph_import/), recorded in the shape of a saved Vercel AI SDK `UIMessage[]` stream (one run per JSON line under `trace`: message `id`, `role` and `parts`). The sample uses the **AI SDK 7** `ToolUIPart` fields (`type: "tool-<name>"`, `toolCallId`, `state`, `input`, `output`, `errorText`) from `ai@7.0.179`; see the [guide](../../docs/integrations/ai-sdk.md).

Importing with the `file:ai_sdk.py` mapping gives the same verdicts as the LangGraph example (`tests/test_ai_sdk_import.py`). No Node, no `ai` package and no network are needed.

```shell
agentest std import examples/ai_sdk_import/native/expense_bot.jsonl \
    --map examples/ai_sdk_import/import/map.json \
    --tools examples/langgraph_import/agents/expense_bot/tools.json \
    --service expense_bot --out build/expense_bot_ai_sdk.otlp.jsonl
agentest std run --otlp build/expense_bot_ai_sdk.otlp.jsonl \
    --card examples/langgraph_import/agents/expense_bot/agent-card.json \
    --tools examples/langgraph_import/agents/expense_bot/tools.json
```

To record your own agent, append one line after each run; `messages` is the `UIMessage[]` from `useChat` or your chat store:

```ts
const line = {
  agent: "my_agent", probe: "canon", rep: 0,
  input: prompt,
  trace: messages,                        // id, role, parts as the SDK keeps them
  output: { final_answer: ledger.finalAnswer },  // your system of record
};
await appendFile("native/my_agent.jsonl", JSON.stringify(line) + "\n");
```

What maps where: a text part becomes a user or assistant message; a `tool-<name>` part becomes an `execute_tool` span with `input` as its arguments and `output-available.output` as its result; `output-error.errorText` marks the call failed. `reasoning` and `data-*` parts are skipped. The adapter only maps fields — tool annotations and the rules decide the verdicts.
