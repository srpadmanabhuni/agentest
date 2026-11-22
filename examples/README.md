# Examples

Every example runs offline from a clone: Python 3.11+, no API key, no model, no network. Set up once:

```bash
git clone --depth 1 https://github.com/srpadmanabhuni/agentest.git && cd agentest
python3 -m venv .venv && . .venv/bin/activate && pip install -q -e .
```

| Folder | What it shows | Run |
|---|---|---|
| [`start_here/`](start_here/) | One trace where the agent claims success it did not earn | see [Start here](../docs/START_HERE.md) |
| [`agnostic_demo/`](agnostic_demo/) | A buggy and a clean sample agent: four caught bugs, then a clean pass | `agentest std run --agents examples/agnostic_demo/agents --agent refill_bot_buggy --ids T1-018,T2-001,T4-003,T7-014 --format md` |
| [`first_trace/`](first_trace/) | A three-span hand-written OTLP/JSON trace: a write without its confirmation flag | see its [README](first_trace/README.md) |
| [`otel_plain/`](otel_plain/) | Emit an OpenTelemetry GenAI trace with the standard library, plus an A2A AgentCard and MCP tools list | `python examples/otel_plain/emit_trace.py` |
| [`langgraph_import/`](langgraph_import/) | Import LangGraph / LangChain message lists | `python examples/langgraph_import/test_langgraph.py` |
| [`smolagents_import/`](smolagents_import/) | Import smolagents memory steps; same verdicts as the LangGraph example | see its [README](smolagents_import/README.md) |
| [`adk_import/`](adk_import/) | Import recorded Google ADK events with a local adapter; representative fixtures | see its [README](adk_import/README.md) |
| [`build_your_own/`](build_your_own/) | Write your first check | `python examples/build_your_own/my_first_check.py examples/first_trace/trace.otlp.json examples/first_trace/tools.json` |
| [`course/`](course/) | A 45-minute class exercise: plan, review and run agent tests with the checklist | see its [README](course/README.md) |
| [`colab_quickstart.ipynb`](colab_quickstart.ipynb) | The before-and-after walkthrough in a browser | [Open in Colab](https://colab.research.google.com/github/srpadmanabhuni/agentest/blob/main/examples/colab_quickstart.ipynb) or `python examples/colab_quickstart.py` |
| [`integrations/`](integrations/) | Use the checklist dataset inside other eval tools, and a CI gate workflow | see its [README](integrations/README.md) |

Framework pages: [LangGraph](../docs/integrations/langgraph.md), [Google ADK](../docs/integrations/google-adk.md), [CrewAI](../docs/integrations/crewai.md), [OpenAI Agents SDK](../docs/integrations/openai-agents-sdk.md), [AutoGen](../docs/integrations/autogen.md), [smolagents](../docs/integrations/smolagents.md), [n8n](../docs/integrations/n8n.md), [MCP](../docs/integrations/mcp.md). Want an adapter that is not here? See [adapters wanted](../docs/integrations/ADAPTERS-WANTED.md).
