# How to test Semantic Kernel agents with agentest

Import a Microsoft Semantic Kernel Python chat history into OpenTelemetry GenAI spans, then run agentest against
the resulting trace. The [offline expense-bot example](../../examples/semantic_kernel_import/README.md) includes
the recording snippet and both commands. See the [install guide](../INSTALL-AND-QUICKSTART.md) for the CLI.

## Choose an input

| Input | Command |
|---|---|
| Recorded Python chat history with function calls and results | `agentest std import … --map …`, then `agentest std run --otlp …` |
| Existing OTLP export with GenAI agent and tool spans | `agentest std run --otlp … --card … --tools …` |

Use an [A2A AgentCard](../developers/AGENT-CARD.md) and an MCP-style tools list to describe the agent and its
tools. Use the same tool names in the recording, card, and tools list. For direct OTLP export, see
[Instrumenting an agent](../developers/INSTRUMENTING.md).

## Import a Python chat history

The example follows **Semantic Kernel Python 1.47.0**. Each JSONL row wraps the object returned by
`json.loads(chat_history.serialize())` under `history`. The SDK writes an ordered `messages` array, with
`role` and typed `items` on each message. See the [Microsoft Learn guide](https://learn.microsoft.com/en-us/semantic-kernel/concepts/ai-services/chat-completion/chat-history)
and the [versioned serializer](https://github.com/microsoft/semantic-kernel/blob/python-1.47.0/python/semantic_kernel/contents/chat_history.py).

| History item | How it maps |
|---|---|
| `text` | The mapper walks messages and their items in recorded order. The import uses the episode input and final reply plus the chat text available to the trace exporter. |
| `function_call` | Each call becomes an `execute_tool` span. The mapper uses the recorded `name` or reconstructs it from `plugin_name` and `function_name` with the SDK's hyphen separator. Arguments can be objects or JSON strings. Malformed argument strings are kept under `raw`. |
| `function_result` | The result joins its call by `call_id` when present, otherwise by `id`. Results can arrive in a different order from the calls. The SDK serializes the result to a string, which the mapper keeps verbatim. |

The [mapping file](../../examples/semantic_kernel_import/import/map.json) loads an
[example-local mapper](../../examples/semantic_kernel_import/import/semantic_kernel.py). The field definitions
come from the pinned [function call](https://github.com/microsoft/semantic-kernel/blob/python-1.47.0/python/semantic_kernel/contents/function_call_content.py)
and [function result](https://github.com/microsoft/semantic-kernel/blob/python-1.47.0/python/semantic_kernel/contents/function_result_content.py)
classes.

The SDK has no separate error status on a serialized function result. The mapper sets the span's error status
for version 1.47.0's [kernel invocation diagnostics](https://github.com/microsoft/semantic-kernel/blob/python-1.47.0/python/semantic_kernel/kernel.py)
or a JSON-serializable `metadata.exception` captured on the result item. For custom tool failures, capture
an explicit exception in the result metadata or export a GenAI tool span with an error status.

## Evidence available from the recording

The mapper keeps text and tool evidence in the order recorded in chat history. The standard importer exports
normalized tool and chat spans on a replay clock. Keep the original JSONL for a message-by-message transcript.
Media, provider internals, and timings are outside this example. Record actual side effects and approvals
separately from the conversation, then point the observations map at those fields. A result saying an expense
was paid is a tool response, while a ledger entry is evidence that the payment occurred.
