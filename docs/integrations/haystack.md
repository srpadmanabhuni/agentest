# How to test Haystack agents with OpenTelemetry and agentest

agentest (agentest-ai) — deterministic OpenTelemetry evals for AI agents.

agentest scores recorded traces, not your Haystack pipeline or agent code. Haystack users can provide OpenTelemetry
GenAI spans directly, or import a recorded Agent.run() message list with a small local mapping function.

## Version used by the example

The offline example was written against **Haystack 3.5.0**. It uses the public Agent.run() result's messages
list and serializes each ChatMessage with to_dict(). In that version, a serialized message has role, meta,
name and content fields. Content parts use text, tool_call or tool_call_result keys; a tool result includes
its originating ToolCall and its error flag.

References: [Haystack Agents API](https://docs.haystack.deepset.ai/reference/agents-api),
[ChatMessage source at v3.5.0](https://github.com/deepset-ai/haystack/blob/v3.5.0/haystack/dataclasses/chat_message.py).

## Two ways in

| Path | When to use | Command shape |
|---|---|---|
| **Live OpenTelemetry** (preferred) | Your Haystack run is instrumented and exports the GenAI/tool spans you need | agentest std run --otlp traces.jsonl --card … --tools … |
| **Recorded messages** | You have the messages returned by Agent.run() | agentest std import … --map … then std run |

Haystack documents an OpenTelemetry integration in
[Tracing with OpenTelemetry](https://docs.haystack.deepset.ai/docs/tracing-opentelemetry). Prefer the standard
trace path when it exposes the tool calls, arguments, results and errors required by your checks. The native-message
example is a lightweight alternative for a saved run; it is not a replacement for complete instrumentation.

## Import the recorded example

The complete offline fixture is in [examples/haystack_import/](../../examples/haystack_import/). It contains
four synthetic expense-bot episodes in the Haystack 3.5.0 ChatMessage.to_dict() shape, a map file and a
format-specific Python adapter.

From the repository root:

~~~bash
agentest std import examples/haystack_import/native/expense_bot.jsonl \
    --map examples/haystack_import/import/map.json \
    --tools examples/langgraph_import/agents/expense_bot/tools.json \
    --service expense_bot --out build/expense_bot_haystack.otlp.jsonl

agentest std run --otlp build/expense_bot_haystack.otlp.jsonl \
    --card examples/langgraph_import/agents/expense_bot/agent-card.json \
    --tools examples/langgraph_import/agents/expense_bot/tools.json
~~~

The map declares the application-owned output.submitted and output.reimbursed fields as pending and executed
observations. Those facts must come from the application or its system of record, not from the assistant's reply.
The test [tests/test_haystack_import.py](../../tests/test_haystack_import.py) asserts that all 130 check verdicts
match the equivalent LangGraph fixture.

## How the mapper reads Haystack messages

The local adapter is selected with dialect file:haystack.py in examples/haystack_import/import/map.json.
It reads only serialized dictionaries; neither the example importer nor its tests import or install Haystack.

| Haystack message content | Agentest representation |
|---|---|
| text part | User/system/assistant message text |
| tool_call part | Tool call with its name, arguments, call ID and actor |
| tool_call_result part | Result/error attached to the originating tool call by ID |

The adapter matches results by the origin call ID. If an ID is absent, it matches the origin tool name and, when
present, its arguments; ambiguous matches are rejected. Unknown IDs, duplicate IDs and orphan results are errors.
Assistant reasoning parts and image/file payloads are deliberately omitted. The native mapper is intentionally
single-turn: it takes the user input from the top-level record, rejects non-empty system messages and multi-user-message
history instead of silently flattening them. Use complete OpenTelemetry instrumentation when those messages or nested
tool activity inside arbitrary tool code are needed.

One JSONL record represents one request. The top-level input opens the request, trace contains the serialized
Haystack messages, and output contains application-owned observations. A minimal recording pattern is in the
[example README](../../examples/haystack_import/README.md).

## What the example does not do

- It does not run a model, import Haystack in tests, or make network calls.
- It does not add a Haystack dependency to Agentest.
- It does not change Agentest rules, reference traces or verdicts.
- It does not treat a text claim as proof that an external action completed.

## See also

- [Instrumenting agents with OpenTelemetry](../developers/INSTRUMENTING.md)
- [LangGraph](langgraph.md), which provides the equivalent reference episode
- [Author Guide §3: a framework adapter](../AUTHOR-GUIDE.md#3-a-framework-adapter)
- [Contributing](../../CONTRIBUTING.md)
