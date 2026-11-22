# How to test Vercel AI SDK agents with OpenTelemetry and agentest

agentest (agentest-ai) — deterministic OpenTelemetry evals for AI agents.

agentest scores **recorded traces**, not your agent code. The Vercel AI SDK (official AI SDK) keeps conversation state as `UIMessage[]`: a message has `id`, `role` and `parts`, and a tool invocation is a part whose type is `tool-<toolName>` with `toolCallId`, `state`, `input` and `output`. This guide saves that recorded stream as plain JSON and imports it offline — no Node install, no `ai` package, no API key. Theme: *Bring an agent trace, contribute a test.*

The sample was written against **AI SDK 7, `ai@7.0.179`** (the `ai` npm `latest` tag), using the [UIMessage reference](https://ai-sdk.dev/docs/reference/ai-sdk-core/ui-message) and its `ToolUIPart` field names (`type`, `toolCallId`, `state`, `input`, `output`, `errorText`). Those field names are the same in 6.x, so the mapping works for 6.x recordings too.

## Two ways in

| Path | When to use | Command shape |
|---|---|---|
| **Live OTLP** (preferred) | Your app or an instrumentation already emits OpenTelemetry GenAI spans | `agentest std run --otlp traces.jsonl --card … --tools …` |
| **Recorded UI messages** | You persist `messages` from `useChat` or your chat store | `agentest std import … --map …` (below), then `std run` |

The importer is a pure field mapper in [`examples/ai_sdk_import/import/ai_sdk.py`](../../examples/ai_sdk_import/import/ai_sdk.py), selected by `"dialect": "file:ai_sdk.py"` in the map. It needs no agentest core change and no runtime dependency.

## 1. Try it on a recorded AI SDK run

The four hand-written `expense_bot` episodes in [`examples/ai_sdk_import/`](../../examples/ai_sdk_import/) are the same intents as the [LangGraph example](../../examples/langgraph_import/), written as `UIMessage` parts. Python 3.11 or newer, no network:

```bash
pip install agentest-ai
agentest std import examples/ai_sdk_import/native/expense_bot.jsonl \
    --map examples/ai_sdk_import/import/map.json \
    --tools examples/langgraph_import/agents/expense_bot/tools.json \
    --service expense_bot --out build/expense_bot_ai_sdk.otlp.jsonl
agentest std run --otlp build/expense_bot_ai_sdk.otlp.jsonl \
    --card examples/langgraph_import/agents/expense_bot/agent-card.json \
    --tools examples/langgraph_import/agents/expense_bot/tools.json
```

For one check, add `--ids T1-001 --format md`:

```text
# agentest 3.5.3 report (examples mode)

| ID | status | detail |
|---|---|---|
| T1-001 | pass | canon: postconditions hold |
```

`tests/test_ai_sdk_import.py` checks that all 130 check IDs give the same verdicts as the equivalent LangGraph message log, including the social-engineering episode that is still caught. This is one recorded run, not a verdict on the AI SDK.

## 2. Judge your own AI SDK runs

Record one JSON line per finished run. `trace` is the `UIMessage[]` you already have; `input` opens the user turn and `output.final_answer` comes from your system of record:

```ts
import { appendFile } from 'node:fs/promises';
import type { UIMessage } from 'ai';

// `messages` is UIMessage[] from useChat (or loaded from your chat store);
// `ledger` is what your backend actually did, not what the model claimed.
const line = {
  agent: 'my_agent',
  probe: 'canon',                 // your own label for the stimulus
  rep: 0,
  input: prompt,
  trace: messages,                // id, role, parts — keep the SDK's shape
  output: { final_answer: ledger.finalAnswer, submitted: ledger.submitted, reimbursed: ledger.reimbursed },
};
await appendFile('native/my_agent.jsonl', JSON.stringify(line) + '\n');
```

Then point the map's `observations` at your output paths and run the two commands above with your own file. The adapter writes `gen_ai.tool.name` / `gen_ai.tool.call.arguments` from the SDK's `tool-<name>` parts and `input`; the `submitted` / `reimbursed` effects in this example come from the example system of record, not from the model.

## What the adapter reads

| AI SDK field | OTel evidence in the imported trace |
|---|---|
| `parts[]` with `type: "text"` | user / assistant message |
| `type: "tool-<name>"`, `input` | `gen_ai.tool.name`, `gen_ai.tool.call.arguments` |
| `state: "output-available"`, `output` | `gen_ai.tool.call.result` |
| `state: "output-error"`, `errorText` | failed tool call with the error as result |
| `toolCallId` | `gen_ai.tool.call.id` |
| `reasoning`, `data-*` parts | ignored: neither replies nor tool evidence |

## What this does not cover

The adapter maps fields; it never decides what is a write, what needs approval or what success means. Those come from the MCP [tools list](../../examples/langgraph_import/agents/expense_bot/tools.json), the [agent card](../../examples/langgraph_import/agents/expense_bot/agent-card.json) and agentest's rules. Only what you record is visible: `input-streaming` / `input-available` parts become tool calls with no result, and `approval-*` parts are not mapped in this example (add a branch calling `ep.approval(...)` if you record them). If you use AI SDK Core without the UI message layer, emit GenAI spans directly and run `std run --otlp` — no importer needed.

See the [Author Guide](../AUTHOR-GUIDE.md#3-a-framework-adapter) for writing your own `file:` mapping, and [Instrumenting your agent](../developers/INSTRUMENTING.md) for live spans.
