# Developer guide (v3.0.0): onboard an agent with zero test changes

You never write a test. You publish metadata and recorded runs; the same 130 universal rules judge every agent.

## 1. Publish metadata

```
agents/my_agent/
  agent-card.json   A2A AgentCard (+ governance extension, optional)
  tools.json        MCP tools/list: name, description, inputSchema, annotations
  adapter.json      {"dialect": "events" | "openai_agents" | "langgraph_msgs" | ... | "file:adapter.py", "observations": {...}, "episodes": "runs.jsonl"}
  inputs.json       {"inputs": {"canon": {"families": ["canonical"]}, ...}, "relations": [...], "canaries": [...]}
  runs.jsonl        recorded episodes (or emit OTLP/JSON directly)
```

Use the shared input names (`canon`, `faq`, `empty`, `pii_base`/`pii_para`, `social`, `b1_quote`, `refuse_en`/`refuse_es`, …;
see `agentest.standards.inputs.BY_NAME`) and they get families automatically. `agentest std gen --agent my_agent` proposes
new inputs from your skill examples and tool schemas.

## 2. Worked example: the agnostic demo

`examples/agnostic_demo/refill_agent.py` is a plain-Python pharmacy agent that logs in its own text format
(`CALL`, `RESULT`, `SAY`). It is onboarded with:

* `agents/refill_bot/agent-card.json` — skill + examples, governance: `approval.required=[place_refill]`,
  `prerequisites.place_refill=[verify_identity]`, `disclosureTools=[lookup_patient]`, `recipients.allow`;
* `agents/refill_bot/tools.json` — 5 MCP tools; `check_rx`, `lookup_patient`, `verify_identity` are `readOnlyHint: true`;
* `agents/refill_bot/adapter.py` — 19 lines that map the text log to tool calls and messages (no verdicts).

```bash
python examples/agnostic_demo/refill_agent.py                      # re-record (deterministic)
agentest std validate --agents examples/agnostic_demo/agents
agentest std run --agents examples/agnostic_demo/agents            # refill_bot: 54 pass, 0 fail
                                                                   # refill_bot_buggy: 19 fail (T1-004, T2-001, T2-005, T3-001, T4-009, T7-014, ...)
agentest std export --agents examples/agnostic_demo/agents --out otlp/   # OTLP/JSON for any OTel backend
```

No file under `src/` or `tests/` changed to onboard it; `tests/test_standards_guard.py` would fail if one named it.
`examples/model_driven/agents/expense_bot` is a second example using the built-in `langgraph_msgs` dialect.

## 3. Read results

`pass` — the rule held on every run; `fail` — the detail names the run and evidence; `n/a` — your metadata or traces
carry no signal for that ID (e.g. no approval facts → approval IDs are n/a). To turn an n/a into a real check, publish
the fact (governance extension) or emit the span attribute; never add a per-agent rule.

## 4. Modes and regression

`--mode strict` ignores your published postconditions. `agentest std regress` compares with the v2.0.0 baseline.
