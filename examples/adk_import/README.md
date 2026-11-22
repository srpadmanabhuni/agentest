# Google ADK import example

This example demonstrates importing Google Agent Development Kit (ADK) event-shaped session data into Agentest using a local mapping adapter.

The bundled `native/expense_bot.jsonl` contains four hand-authored representative fixtures. They illustrate the event structure and expected mappings; they are not claimed to be recordings exported from a live ADK session.

The example uses the same expense-bot evaluation definitions as [`../langgraph_import/`](../langgraph_import/). The imported episodes are checked against the LangGraph reference by `tests/test_adk_import.py`.

## Import and evaluate

Run these commands from the repository root:

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

## Event mapping

- `event.author` identifies the event author.
- `event.content.parts[].text` supplies assistant message text.
- `functionCall.name`, `functionCall.args`, and `functionCall.id` become tool-call data.
- `functionResponse.name`, `functionResponse.response`, and `functionResponse.id` provide tool results.
- Function responses are matched to calls by ID. When an ID is unavailable, the adapter can fall back to matching by function name.
- Event-level errors and response objects containing an `error` value mark a matched tool call as failed.
- User-authored text is not duplicated as an assistant message.

The adapter accepts both camelCase and snake_case function-call and response keys.

The mapping file also maps the fixture's `output` fields to Agentest observations: `final_answer`, `pending`, and `executed`.

## Using your own ADK session data

Export or serialize your own ADK session events into one JSON object per JSONL line. Each record should include the agent, input, trace event list, and any output fields needed by your evaluation mapping.

The adapter is intentionally offline: it does not start an ADK runtime, invoke a model, or make network requests. Adapt the export to the event structure expected by the adapter and validate it against a real session before relying on it.

For production integrations, preserve the original event data and verify the function-call/response pairing, event errors, and final output against the source session.

The importer is covered by `tests/test_adk_import.py`.
