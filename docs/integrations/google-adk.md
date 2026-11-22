# Google ADK

Agentest can import recorded Google Agent Development Kit (ADK) events through a local mapping adapter. This lets you evaluate an ADK agent's recorded tool calls, responses, and assistant messages without running the ADK runtime during import.

## Try the bundled example

The bundled expense-bot JSONL file contains four hand-authored representative fixtures. They demonstrate the expected event shape; they are not recordings exported from a live ADK session.

From the repository root, run:

```bash
agentest std import examples/adk_import/native/expense_bot.jsonl \
  --map examples/adk_import/import/map.json \
  --tools examples/langgraph_import/agents/expense_bot/tools.json \
  --service expense_bot \
  --out build/expense_bot_adk.otlp.jsonl

agentest std run --otlp build/expense_bot_adk.otlp.jsonl \
  --card examples/langgraph_import/agents/expense_bot/agent-card.json \
  --tools examples/langgraph_import/agents/expense_bot/tools.json
```

The fixture uses the same expense-bot evaluation definitions as the [LangGraph example](../../examples/langgraph_import/). The ADK import regression tests compare its evaluation verdicts with the LangGraph reference.

## Import your own ADK events

Serialize your recorded ADK session into JSONL, with one episode object per line. The adapter expects an episode containing a `trace` array. Each event can include an `author` and `content.parts` array.

Text parts are read from `text`. Tool calls are read from `functionCall` or `function_call` and use the function name, arguments, and optional call ID. Tool responses are read from `functionResponse` or `function_response` and matched to calls by ID, with a function-name fallback when an ID is unavailable.

An event-level error or an error value in a matched function response marks the corresponding tool call as failed. User-authored text is not emitted as an assistant message.

## Configure the mapping

Use the local adapter file as the dialect in your mapping JSON:

```json
{
  "dialect": "file:adk_adapter.py",
  "framework": "Google Agent Development Kit (ADK)"
}
```

The bundled mapping also defines the fixture's output observations. Its `final_answer`, `pending`, and `executed` fields are mapped from the episode's `output` object.

## Scope and limitations

The adapter is offline and works from recorded event data. It does not start an ADK runtime, invoke a model, or make network requests.

The bundled fixtures are illustrative, not verified live ADK exports. Before using the adapter with production sessions, validate the serialized event structure and tool-call/response pairing against actual ADK session data.

Regression coverage is provided by `tests/test_adk_import.py`.

## See also

- [ADK import example](../../examples/adk_import/)
- [LangGraph integration](langgraph.md)
