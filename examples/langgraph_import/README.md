# LangGraph flagship example (`expense_bot`)

Offline, synthetic episodes in the LangGraph / LangChain message-list shape. No live
graph runtime, no model, no network. Package dependency for scoring remains PyYAML only.
`agentest-ai` is not on PyPI; from a clone, `pip install -r requirements.txt` is enough to run the script below.

## Layout

| Path | Role |
|---|---|
| `native/expense_bot.jsonl` | Four hand-written message-list episodes (`canon`, `social`, `empty`) |
| `import/map.json` | `langgraph_msgs` dialect + observation / label mapping |
| `agents/expense_bot/` | Agent Card, MCP-style `tools.json`, pre-imported OTLP JSONL |
| `test_langgraph.py` | Flagship script: import → run checks → print a short sample report |

## Quick run

```bash
# from the repo root, with agentest on PYTHONPATH or installed editable
python examples/langgraph_import/test_langgraph.py
```

Equivalent CLI:

```bash
agentest std import examples/langgraph_import/native/expense_bot.jsonl \
  --map examples/langgraph_import/import/map.json \
  --tools examples/langgraph_import/agents/expense_bot/tools.json \
  --service expense_bot --out build/expense_bot.otlp.jsonl
agentest std run --otlp build/expense_bot.otlp.jsonl \
  --card examples/langgraph_import/agents/expense_bot/agent-card.json \
  --tools examples/langgraph_import/agents/expense_bot/tools.json
```

Instrumentation guide (how to emit OTLP from a real LangGraph app):
[`docs/integrations/langgraph.md`](../../docs/integrations/langgraph.md).

## Contribute

*Bring an agent trace, contribute a test.* If a check misfires on your own recorded
LangGraph run, open a detection issue with the anonymised OTLP (or message-list) episode
and the catalogue id — see [CONTRIBUTING.md](../../CONTRIBUTING.md).
