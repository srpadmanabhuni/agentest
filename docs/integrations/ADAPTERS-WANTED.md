# Framework adapters wanted

**AiEnsured agentest, an Agentic AI Testing platform** checks what an agent actually did, not only what it said. It reads standard artifacts: OpenTelemetry GenAI spans, an A2A agent card and an MCP tool list. An *adapter* is a small, offline example plus a short guide that shows how to get a run from one agent framework into those artifacts (`agentest std import --map`, or live OTLP). No framework is a dependency of agentest.

If you use one of these frameworks, you are the best person to write its page: you know where the run data lives. Enhance and contribute.

| Framework | Status | Where to start |
|---|---|---|
| LangGraph | guide and example on `main` | [integrations/langgraph.md](langgraph.md), `examples/langgraph_import/` |
| CrewAI | guide on `main`; offline example wanted | [integrations/crewai.md](crewai.md), [issue #1](https://github.com/srpadmanabhuni/agentest/issues/1) |
| OpenAI Agents SDK | guide and short offline episode example | [integrations/openai-agents-sdk.md](openai-agents-sdk.md), [issue #4](https://github.com/srpadmanabhuni/agentest/issues/4) |
| AutoGen | guide on `main`; built-in `autogen` dialect | [integrations/autogen.md](autogen.md), [issue #2](https://github.com/srpadmanabhuni/agentest/issues/2) |
| smolagents | guide and example on `main` | [integrations/smolagents.md](smolagents.md), `examples/smolagents_import/`, [issue #111](https://github.com/srpadmanabhuni/agentest/issues/111) |
| n8n | guide on `main`; built-in `n8n` dialect (run-level tool calls only from the native export) | [integrations/n8n.md](n8n.md) |
| MCP | guide on `main` (tools/list + execute_tool spans; agentest does not host a server) | [integrations/mcp.md](mcp.md) |
| Pydantic AI | short offline `all_messages_json()` example; OTLP mapping still wanted | [guide](pydantic-ai.md), [issue #133](https://github.com/srpadmanabhuni/agentest/issues/133) |
| Agno | wanted | [issue #134](https://github.com/srpadmanabhuni/agentest/issues/134) |
| Mastra | wanted | [issue #135](https://github.com/srpadmanabhuni/agentest/issues/135) |
| LlamaIndex | `events` dialect, [guide](llamaindex.md) and [offline example](../../examples/llamaindex_import/) | [issue #231](https://github.com/srpadmanabhuni/agentest/issues/231) |
| Semantic Kernel | guide and example on `main` (`file:semantic_kernel.py` for Python chat history) | [integrations/semantic-kernel.md](semantic-kernel.md), `examples/semantic_kernel_import/`, [issue #232](https://github.com/srpadmanabhuni/agentest/issues/232) |
| Haystack | wanted | [issue #233](https://github.com/srpadmanabhuni/agentest/issues/233) |
| Vercel AI SDK | guide and example on `main` (`file:ai_sdk.py` for recorded UIMessage parts) | [integrations/ai-sdk.md](ai-sdk.md), `examples/ai_sdk_import/`, [issue #234](https://github.com/srpadmanabhuni/agentest/issues/234) |
| Google ADK | guide and example added | [integrations/google-adk.md](google-adk.md), `examples/adk_import/`, [issue #235](https://github.com/srpadmanabhuni/agentest/issues/235) |
| Your framework | open an issue | use the "New test idea" form and name the framework |

## What a good adapter contains

1. `examples/<name>_import/`: a few hand-written, synthetic episodes in the framework's recorded shape, a mapping file, and a README with the two commands (`std import`, then `std run`).
2. `docs/integrations/<name>.md`: a short guide in the same shape as the LangGraph page: how the framework exposes a run, how to record it, how to map it, what is and is not visible.
3. `tests/test_<name>_import.py`: the imported example gives the same verdicts as the equivalent LangGraph example.

Rules: offline, deterministic, no new runtime dependency, no framework import in tests, synthetic ids only, one line in `CHANGELOG.md`. See [CONTRIBUTING.md](../../CONTRIBUTING.md) and the [Author Guide](../AUTHOR-GUIDE.md).

A merged adapter makes you the first co-maintainer candidate for that framework family: see [Help own a check family](../../CONTRIBUTING.md#help-own-a-check-family) and [GOVERNANCE.md](../../GOVERNANCE.md).
