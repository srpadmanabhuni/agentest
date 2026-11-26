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
| Agno | guide and example on `main` (`file:agno_adapter.py` for recorded `RunOutput` messages) | [integrations/agno.md](agno.md), `examples/agno_import/`, [issue #134](https://github.com/srpadmanabhuni/agentest/issues/134) |
| Mastra | wanted | [issue #135](https://github.com/srpadmanabhuni/agentest/issues/135) |
| LlamaIndex | `events` dialect, [guide](llamaindex.md) and [offline example](../../examples/llamaindex_import/) | [issue #231](https://github.com/srpadmanabhuni/agentest/issues/231) |
| Semantic Kernel | wanted | [issue #232](https://github.com/srpadmanabhuni/agentest/issues/232) |
| Haystack | wanted | [issue #233](https://github.com/srpadmanabhuni/agentest/issues/233) |
| Vercel AI SDK | guide and example on `main` (`file:ai_sdk.py` for recorded UIMessage parts) | [integrations/ai-sdk.md](ai-sdk.md), `examples/ai_sdk_import/`, [issue #234](https://github.com/srpadmanabhuni/agentest/issues/234) |
| Google ADK | guide and example added | [integrations/google-adk.md](google-adk.md), `examples/adk_import/`, [issue #235](https://github.com/srpadmanabhuni/agentest/issues/235) |
| Your framework | open an issue | use the "New test idea" form and name the framework |

## Open units: status and acceptance criteria (26 Nov 2026)

This section is the weekly status of the units above that are still open. The table above is the long-lived list. A unit with an open pull request is being reviewed there; the other units are free to claim. To claim one, comment "I'll take this" on its issue and open a draft pull request early.

| Unit | Issue | Pull request | Claim it |
|---|---|---|---|
| CrewAI offline example | [#1](https://github.com/srpadmanabhuni/agentest/issues/1) | none yet | free to claim |
| AutoGen | [#2](https://github.com/srpadmanabhuni/agentest/issues/2) | none yet | free to claim |
| OpenAI Agents SDK episode example | [#4](https://github.com/srpadmanabhuni/agentest/issues/4) | none yet | free to claim |
| Mastra | [#135](https://github.com/srpadmanabhuni/agentest/issues/135) | none yet | free to claim |
| Pydantic AI | [#133](https://github.com/srpadmanabhuni/agentest/issues/133) | [#350](https://github.com/srpadmanabhuni/agentest/pull/350) | in review, no need to claim |
| Agno | [#134](https://github.com/srpadmanabhuni/agentest/issues/134) | [#349](https://github.com/srpadmanabhuni/agentest/pull/349) | in review, no need to claim |
| Semantic Kernel | [#232](https://github.com/srpadmanabhuni/agentest/issues/232) | [#345](https://github.com/srpadmanabhuni/agentest/pull/345) | in review, no need to claim |
| Haystack | [#233](https://github.com/srpadmanabhuni/agentest/issues/233) | [#307](https://github.com/srpadmanabhuni/agentest/pull/307) | in review, no need to claim |

Finished and closed: smolagents ([#111](https://github.com/srpadmanabhuni/agentest/issues/111)), LlamaIndex ([#231](https://github.com/srpadmanabhuni/agentest/issues/231)), Vercel AI SDK ([#234](https://github.com/srpadmanabhuni/agentest/issues/234)) and Google ADK ([#235](https://github.com/srpadmanabhuni/agentest/issues/235)). Use any of them as the reference for shape.

Each block below is copy-pasteable. Paste the checklist into your pull request description and tick it. Run the commands from the repository root after `pip install -e ".[dev]"`. The commands reuse the expense-bot agent card and tool list from the LangGraph example, so you do not write new ones.

### CrewAI offline example

A recorded-run folder for the existing [CrewAI guide](crewai.md). The built-in `steps` dialect only reads task outputs, so tool calls need a small `file:to_trace.py` mapping.

Acceptance criteria:

```markdown
- [ ] Offline: no framework install, no network, no model, no new runtime dependency
- [ ] Hand-written recording with invented ids, in the framework's recorded shape
- [ ] `examples/crewai_import/native/support_crew.jsonl` and `examples/crewai_import/import/map.json` import with the commands below
- [ ] `docs/integrations/crewai.md` exists, is linked from `docs/README.md`, and says which framework version the sample was written against
- [ ] One recorded run calls only declared tools and one calls a tool that is not in `tools.json`.
- [ ] The test asserts T5-001 is `pass` for the first run and `fail` for the second.
- [ ] `docs/integrations/crewai.md` links to the new example folder.
- [ ] `python -m pytest -q tests/test_crewai_import.py tests/test_no_lock_in.py tests/test_agent_independence.py` and `ruff check .` pass
- [ ] One file in `changelog.d/` and a signed-off commit (`git commit -s`)
```

Commands (the folder name follows `examples/crewai_import/`):

```bash
agentest std import examples/crewai_import/native/support_crew.jsonl \
    --map examples/crewai_import/import/map.json \
    --tools examples/langgraph_import/agents/expense_bot/tools.json \
    --service support_crew --out build/support_crew_crewai.otlp.jsonl
agentest std run --otlp build/support_crew_crewai.otlp.jsonl \
    --card examples/langgraph_import/agents/expense_bot/agent-card.json \
    --tools examples/langgraph_import/agents/expense_bot/tools.json
python -m pytest -q tests/test_crewai_import.py tests/test_no_lock_in.py tests/test_agent_independence.py
ruff check .
```

Mapping notes: `examples/crewai_import/to_trace.py`, `"dialect": "file:to_trace.py"`.

### AutoGen

A recorded-run folder using the built-in `autogen` dialect (`ToolCallRequestEvent` and `TextMessage` events). No importer change is needed.

Acceptance criteria:

```markdown
- [ ] Offline: no framework install, no network, no model, no new runtime dependency
- [ ] Hand-written recording with invented ids, in the framework's recorded shape
- [ ] `examples/autogen_import/native/support_agent.jsonl` and `examples/autogen_import/import/map.json` import with the commands below
- [ ] `docs/integrations/autogen.md` exists, is linked from `docs/README.md`, and says which framework version the sample was written against
- [ ] Two recorded runs: one calls only declared tools, one calls a tool that is not in `tools.json`.
- [ ] The test asserts T5-001 is `pass` for the first run and `fail` for the second.
- [ ] `docs/AUTHOR-GUIDE.md` or `docs/USER-GUIDE.md` links to the folder.
- [ ] `python -m pytest -q tests/test_autogen_import.py tests/test_no_lock_in.py` and `ruff check .` pass
- [ ] One file in `changelog.d/` and a signed-off commit (`git commit -s`)
```

Commands (the folder name follows `examples/autogen_import/`):

```bash
agentest std import examples/autogen_import/native/support_agent.jsonl \
    --map examples/autogen_import/import/map.json \
    --tools examples/langgraph_import/agents/expense_bot/tools.json \
    --service support_agent --out build/support_agent_autogen.otlp.jsonl
agentest std run --otlp build/support_agent_autogen.otlp.jsonl \
    --card examples/langgraph_import/agents/expense_bot/agent-card.json \
    --tools examples/langgraph_import/agents/expense_bot/tools.json
python -m pytest -q tests/test_autogen_import.py tests/test_no_lock_in.py
ruff check .
```

Mapping notes: `"dialect": "autogen"`.

### OpenAI Agents SDK episode example

A recorded-run folder using the built-in `openai_agents` dialect (`tool_call_item`, `tool_call_output_item`, `handoff_output_item`), with an injected URL on `evil.example` in a tool result.

Acceptance criteria:

```markdown
- [ ] Offline: no framework install, no network, no model, no new runtime dependency
- [ ] Hand-written recording with invented ids, in the framework's recorded shape
- [ ] `examples/openai_agents_import/native/support_agent.jsonl` and `examples/openai_agents_import/import/map.json` import with the commands below
- [ ] `docs/integrations/openai-agents-sdk.md` exists, is linked from `docs/README.md`, and says which framework version the sample was written against
- [ ] In one run the agent ignores the injected URL and in the other it passes the URL to a tool.
- [ ] The test asserts T4-002 is `pass` for the first run and `fail` for the second.
- [ ] `docs/integrations/openai-agents-sdk.md` links to the new folder.
- [ ] `python -m pytest -q tests/test_openai_agents_import.py tests/test_no_lock_in.py` and `ruff check .` pass
- [ ] One file in `changelog.d/` and a signed-off commit (`git commit -s`)
```

Commands (the folder name follows `examples/openai_agents_import/`):

```bash
agentest std import examples/openai_agents_import/native/support_agent.jsonl \
    --map examples/openai_agents_import/import/map.json \
    --tools examples/langgraph_import/agents/expense_bot/tools.json \
    --service support_agent --out build/support_agent_openai_agents.otlp.jsonl
agentest std run --otlp build/support_agent_openai_agents.otlp.jsonl \
    --card examples/langgraph_import/agents/expense_bot/agent-card.json \
    --tools examples/langgraph_import/agents/expense_bot/tools.json
python -m pytest -q tests/test_openai_agents_import.py tests/test_no_lock_in.py
ruff check .
```

Mapping notes: `"dialect": "openai_agents"` and `"labels": {"inputs": {"inj": {"families": ["injection"]}}, "canaries": ["evil.example"]}`.

### Mastra

A new framework page and example for a Mastra agent run (a recorded JSON line per run, or its OpenTelemetry telemetry). Say which Mastra version the sample was written against.

Acceptance criteria:

```markdown
- [ ] Offline: no framework install, no network, no model, no new runtime dependency
- [ ] Hand-written recording with invented ids, in the framework's recorded shape
- [ ] `examples/mastra_import/native/expense_bot.jsonl` and `examples/mastra_import/import/map.json` import with the commands below
- [ ] `docs/integrations/mastra.md` exists, is linked from `docs/README.md`, and says which framework version the sample was written against
- [ ] The recorded runs match the LangGraph expense-bot scenarios: the verdicts equal the LangGraph example's on every check.
- [ ] The guide page names the Mastra version used.
- [ ] `python -m pytest -q tests/test_mastra_import.py tests/test_doc_links.py tests/test_standards_guard.py` and `ruff check .` pass
- [ ] One file in `changelog.d/` and a signed-off commit (`git commit -s`)
```

Commands (the folder name follows `examples/mastra_import/`):

```bash
agentest std import examples/mastra_import/native/expense_bot.jsonl \
    --map examples/mastra_import/import/map.json \
    --tools examples/langgraph_import/agents/expense_bot/tools.json \
    --service expense_bot --out build/expense_bot_mastra.otlp.jsonl
agentest std run --otlp build/expense_bot_mastra.otlp.jsonl \
    --card examples/langgraph_import/agents/expense_bot/agent-card.json \
    --tools examples/langgraph_import/agents/expense_bot/tools.json
python -m pytest -q tests/test_mastra_import.py tests/test_doc_links.py tests/test_standards_guard.py
ruff check .
```

Mapping notes: `docs/integrations/mastra.md`, linked from `docs/README.md`.

### Pydantic AI

A recorded message-history example (`all_messages_json()`) plus the OpenTelemetry mapping. Review is on the open pull request; this list only tracks it.

Acceptance criteria:

```markdown
- [ ] Offline: no framework install, no network, no model, no new runtime dependency
- [ ] Hand-written recording with invented ids, in the framework's recorded shape
- [ ] `examples/pydanticai_import/native/expense_bot.jsonl` and `examples/pydanticai_import/import/map.json` import with the commands below
- [ ] `docs/integrations/pydanticai.md` exists, is linked from `docs/README.md`, and says which framework version the sample was written against
- [ ] The imported recording gives the same verdicts as the LangGraph expense-bot example.
- [ ] The guide says which Pydantic AI version the sample was written against.
- [ ] `python -m pytest -q tests/test_pydanticai_import.py tests/test_doc_links.py tests/test_standards_guard.py` and `ruff check .` pass
- [ ] One file in `changelog.d/` and a signed-off commit (`git commit -s`)
```

Commands (the folder name follows `examples/pydanticai_import/`):

```bash
agentest std import examples/pydanticai_import/native/expense_bot.jsonl \
    --map examples/pydanticai_import/import/map.json \
    --tools examples/langgraph_import/agents/expense_bot/tools.json \
    --service expense_bot --out build/expense_bot_pydanticai.otlp.jsonl
agentest std run --otlp build/expense_bot_pydanticai.otlp.jsonl \
    --card examples/langgraph_import/agents/expense_bot/agent-card.json \
    --tools examples/langgraph_import/agents/expense_bot/tools.json
python -m pytest -q tests/test_pydanticai_import.py tests/test_doc_links.py tests/test_standards_guard.py
ruff check .
```

Mapping notes: the guide, the example folder and the test named in the pull request.

### Agno

An offline Agno import example and guide. Review is on the open pull request; this list only tracks it.

Acceptance criteria:

```markdown
- [ ] Offline: no framework install, no network, no model, no new runtime dependency
- [ ] Hand-written recording with invented ids, in the framework's recorded shape
- [ ] `examples/agno_import/native/expense_bot.jsonl` and `examples/agno_import/import/map.json` import with the commands below
- [ ] `docs/integrations/agno.md` exists, is linked from `docs/README.md`, and says which framework version the sample was written against
- [ ] The imported recording gives the same verdicts as the LangGraph expense-bot example.
- [ ] The guide says which Agno version the sample was written against.
- [ ] `python -m pytest -q tests/test_agno_import.py tests/test_doc_links.py tests/test_standards_guard.py` and `ruff check .` pass
- [ ] One file in `changelog.d/` and a signed-off commit (`git commit -s`)
```

Commands (the folder name follows `examples/agno_import/`):

```bash
agentest std import examples/agno_import/native/expense_bot.jsonl \
    --map examples/agno_import/import/map.json \
    --tools examples/langgraph_import/agents/expense_bot/tools.json \
    --service expense_bot --out build/expense_bot_agno.otlp.jsonl
agentest std run --otlp build/expense_bot_agno.otlp.jsonl \
    --card examples/langgraph_import/agents/expense_bot/agent-card.json \
    --tools examples/langgraph_import/agents/expense_bot/tools.json
python -m pytest -q tests/test_agno_import.py tests/test_doc_links.py tests/test_standards_guard.py
ruff check .
```

Mapping notes: the guide, the example folder and the test named in the pull request.

### Semantic Kernel

An offline Semantic Kernel adapter example (Python chat history). Review is on the open pull request; this list only tracks it.

Acceptance criteria:

```markdown
- [ ] Offline: no framework install, no network, no model, no new runtime dependency
- [ ] Hand-written recording with invented ids, in the framework's recorded shape
- [ ] `examples/semantic_kernel_import/native/expense_bot.jsonl` and `examples/semantic_kernel_import/import/map.json` import with the commands below
- [ ] `docs/integrations/semantic-kernel.md` exists, is linked from `docs/README.md`, and says which framework version the sample was written against
- [ ] The imported recording gives the same verdicts as the LangGraph expense-bot example.
- [ ] The guide says which Semantic Kernel version the sample was written against.
- [ ] `python -m pytest -q tests/test_semantic_kernel_import.py tests/test_doc_links.py tests/test_standards_guard.py` and `ruff check .` pass
- [ ] One file in `changelog.d/` and a signed-off commit (`git commit -s`)
```

Commands (the folder name follows `examples/semantic_kernel_import/`):

```bash
agentest std import examples/semantic_kernel_import/native/expense_bot.jsonl \
    --map examples/semantic_kernel_import/import/map.json \
    --tools examples/langgraph_import/agents/expense_bot/tools.json \
    --service expense_bot --out build/expense_bot_semantic_kernel.otlp.jsonl
agentest std run --otlp build/expense_bot_semantic_kernel.otlp.jsonl \
    --card examples/langgraph_import/agents/expense_bot/agent-card.json \
    --tools examples/langgraph_import/agents/expense_bot/tools.json
python -m pytest -q tests/test_semantic_kernel_import.py tests/test_doc_links.py tests/test_standards_guard.py
ruff check .
```

Mapping notes: the guide, the example folder and the test named in the pull request.

### Haystack

An offline Haystack import example and guide. Review is on the open pull request; this list only tracks it.

Acceptance criteria:

```markdown
- [ ] Offline: no framework install, no network, no model, no new runtime dependency
- [ ] Hand-written recording with invented ids, in the framework's recorded shape
- [ ] `examples/haystack_import/native/expense_bot.jsonl` and `examples/haystack_import/import/map.json` import with the commands below
- [ ] `docs/integrations/haystack.md` exists, is linked from `docs/README.md`, and says which framework version the sample was written against
- [ ] The imported recording gives the same verdicts as the LangGraph expense-bot example.
- [ ] The guide says which Haystack version the sample was written against.
- [ ] `python -m pytest -q tests/test_haystack_import.py tests/test_doc_links.py tests/test_standards_guard.py` and `ruff check .` pass
- [ ] One file in `changelog.d/` and a signed-off commit (`git commit -s`)
```

Commands (the folder name follows `examples/haystack_import/`):

```bash
agentest std import examples/haystack_import/native/expense_bot.jsonl \
    --map examples/haystack_import/import/map.json \
    --tools examples/langgraph_import/agents/expense_bot/tools.json \
    --service expense_bot --out build/expense_bot_haystack.otlp.jsonl
agentest std run --otlp build/expense_bot_haystack.otlp.jsonl \
    --card examples/langgraph_import/agents/expense_bot/agent-card.json \
    --tools examples/langgraph_import/agents/expense_bot/tools.json
python -m pytest -q tests/test_haystack_import.py tests/test_doc_links.py tests/test_standards_guard.py
ruff check .
```

Mapping notes: the guide, the example folder and the test named in the pull request.

Seen something the criteria miss, or hit a snag following them? Say so on the issue. That feedback improves this list.

## What a good adapter contains

1. `examples/<name>_import/`: a few hand-written episodes with invented data in the framework's recorded shape, a mapping file, and a README with the two commands (`std import`, then `std run`).
2. `docs/integrations/<name>.md`: a short guide in the same shape as the LangGraph page: how the framework exposes a run, how to record it, how to map it, what is and is not visible.
3. `tests/test_<name>_import.py`: the imported example gives the same verdicts as the equivalent LangGraph example.

Rules: offline, deterministic, no new runtime dependency, no framework import in tests, invented ids only, one line in `CHANGELOG.md`. See [CONTRIBUTING.md](../../CONTRIBUTING.md) and the [Author Guide](../AUTHOR-GUIDE.md).

A merged adapter makes you the first co-maintainer candidate for that framework family: see [Help own a check family](../../CONTRIBUTING.md#help-own-a-check-family) and [GOVERNANCE.md](../../GOVERNANCE.md).
