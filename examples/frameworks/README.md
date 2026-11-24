# Export a run and judge it: framework examples

Each folder turns one recorded framework run into an agentest trace with `agentest.record()` and judges it. All run offline from a recorded copy of the run: no framework install, no API key, no network.

```bash
pip install agentest-ai
python examples/frameworks/langgraph/judge.py
```

| Folder | Framework | Recorded shape | Guide |
|---|---|---|---|
| [`langgraph/`](langgraph/) | LangChain / LangGraph | `messages_to_dict(state["messages"])` | [guide](../../docs/integrations/langgraph-record.md) |
| [`openai_agents/`](openai_agents/) | OpenAI Agents SDK | `result.to_input_list()` | [guide](../../docs/integrations/openai-agents-sdk-record.md) |
| [`pydantic_ai/`](pydantic_ai/) | Pydantic AI | `result.all_messages_json()` | [guide](../../docs/integrations/pydantic-ai.md) |

[`shared/`](shared/) holds the agent card and tools list all three use: a made-up refund desk where `lookup_order` must come before `issue_refund`. Each recorded run skips that lookup, so the order checks (T2-001, T2-002, T2-013) fail. Add `--strict` to exit 1 on a failure.

For LlamaIndex, see the [LlamaIndex import example](../llamaindex_import/).
