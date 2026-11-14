# Why agentest matters for developers

**Audience:** engineers who build AI agents and agentic apps (LangGraph and other frameworks, tool-calling loops, MCP servers, multi-agent handoffs).

**Owner:** agentest is owned by **Dr Srinivas Padmanabhuni** / **AiEnsured** (testAIng.com).  
**Repo:** https://github.com/srpadmanabhuni/agentest  
**Catalogue:** [Agentic AI Test Checklist 110](https://huggingface.co/datasets/srinivaspadmanabhuni/agentic-ai-test-checklist-110)

---

## What makes agentest different

- **Offline and deterministic.** Judging needs no account, API key, network or model, and no LLM judge sits in the pass/fail path. The same traces give the same verdicts on every run.
- **Works on what your agent already recorded.** agentest does not run or wrap your agent. It reads OpenTelemetry GenAI traces after the fact (OTLP/JSON, JSONL or protobuf files), can receive them over OTLP/HTTP (`agentest std serve`), and can convert native framework logs (`agentest std import`).
- **Agent- and framework-agnostic.** No rule names an agent, tool or vendor. Rules read standard evidence such as MCP tool annotations, call arguments, tool results and span status. A CI test renames every agent and tool and fails if any verdict changes ([agent-independence audit](../../docs/standards/AGENT-INDEPENDENCE-AUDIT.md)).
- **Built on open protocols.** OpenTelemetry GenAI semantic conventions (pinned version), the A2A AgentCard and MCP `tools/list` annotations. Your agent never imports agentest ([No lock-in](../../docs/NO-LOCK-IN.md)).
- **130 checks with public IDs.** 110 come from the open Agentic AI Test Checklist 110 on Hugging Face; 20 are repo extensions (`X-001`…`X-020`). Every ID has its own page ([per-ID test pages](../../docs/tests/README.md)).
- **Evidence for every verdict, and an honest `n/a`.** Each result carries a `detail` line naming the run and the evidence. When a trace has no signal for a check, the verdict is `n/a`, never a silent pass.
- **CI- and pytest-ready.** JUnit, SARIF, versioned JSON, HTML, Markdown, CSV and OTel `gen_ai.evaluation.result` events; `--strict` exits 1 on any `fail`; a pytest template ships in `templates/`.
- **Small and extensible.** One runtime dependency (PyYAML). Disable IDs or tune thresholds in a config file, or add rules from a `rules_dir` or an entry-point plugin without forking.

---

## Why agent testing is different for builders

Shipping an agent is not the same as shipping a pure function. Four properties change how you test:

1. **Non-determinism.** Model sampling and planner choices mean two runs of the same graph can take different tool paths. Flaky “assert exact reply text” tests either fail randomly or are so loose they catch nothing.
2. **Tool calls.** Correctness lives in the call graph: which tools ran, in what order, with what arguments, and whether writes were gated. That graph belongs in telemetry, not only in logs you eyeball.
3. **Multi-turn state.** Session memory, slots, and early constraints must survive later turns. A green unit test on a single node does not prove the conversation still respects “max $50” or “verify before disclose.”
4. **Side effects.** Your agent may create tickets, send email, place refills, or call payment APIs. Regressions show up as durable wrong state — often after the chat reply looked fine.

agentest addresses that by judging **recorded OpenTelemetry GenAI traces** (optionally with an A2A AgentCard and MCP `tools.json`). It returns `pass` / `fail` / `n/a` for **130** checks (the open **110** checklist IDs plus **20** `X-*` extensions). The judge is offline and deterministic: no account, token, network, or model in the pass/fail path. Your agent **never imports agentest**; instrumentation is plain OpenTelemetry.

Rules are **agent-agnostic**: no rule hard-codes an agent name, tool name, or vendor. An agent folder is just `agent-card.json`, `tools.json`, and `traces/`. CI in the project enforces that independence (see `docs/NO-LOCK-IN.md` and the agent-independence audit).

---

## Failures you can catch before users do

Concrete classes, grounded in the catalogue and the bundled `refill_bot_buggy` demo / walkthroughs:

| Failure class | Developer symptom | Checks to watch |
|---|---|---|
| **Duplicate actions** | Double refill, double charge, duplicate ticket create | T2-003; T1-006 for re-run idempotency |
| **Wrong outcomes** | UI says “done” while the write failed or never ran | T1-002, T1-018 |
| **Ignored constraints** | Spend/recipient rules from turn 1 broken later | T6-001, T6-008 |
| **Tool misuse** | Write before `verify_identity`; call outside the allowlist | T2-001, T2-005, T5-001 |
| **Ungrounded values** | Reply invents a currency amount or code not seen in tools/input | X-012 |

The README documents the demo summary as **refill_bot: 55 pass, 0 fail** and **refill_bot_buggy: 41 pass, 16 fail**. The Colab / `examples/colab_quickstart.py` path also shows a minimal temporary repair (insert verification before dependent calls) and re-runs so you can see two checks flip while other seeded defects remain. That is a teaching demo, not a pass-rate claim and not certification.

LangGraph is the flagship framework example on `main`: recorded message lists under `examples/langgraph_import/`, import dialect `langgraph_msgs`, and `docs/integrations/langgraph.md`. Other dialects (`openai_agents`, `autogen`, `n8n`, …) exist for recorded logs when you are not emitting OTLP yet.

---

## How agentest fits a developer workflow

- **CI gate.** Record traces in the pipeline (or commit fixtures), then run `agentest std run … --format junit --out agentest.xml --strict`. `--strict` fails the job on any `fail` verdict. SARIF upload is optional (`docs/developers/CI.md`). Works with any JUnit consumer (GitHub Actions, GitLab, Jenkins, Azure DevOps, CircleCI).
- **pytest.** Develop against the same CLI or invoke the packaged command from tests. The repo’s own CI runs `ruff` and `python -m pytest -q`, including no-lock-in and agent-independence tests. For LangGraph-shaped episodes, copy `templates/test_langgraph.py` and point `AGENTEST_LG_*` paths at your recordings (`templates/README.md`).
- **LangGraph / OTel traces.** Prefer live GenAI spans: root `invoke_agent`, child `execute_tool` with `gen_ai.tool.name` and call arguments/results (`docs/developers/INSTRUMENTING.md`). Or import message lists:

```bash
agentest std import examples/langgraph_import/native/expense_bot.jsonl \
  --map examples/langgraph_import/import/map.json \
  --tools examples/langgraph_import/agents/expense_bot/tools.json \
  --service expense_bot --out build/expense_bot.otlp.jsonl
agentest std run --otlp build/expense_bot.otlp.jsonl \
  --card examples/langgraph_import/agents/expense_bot/agent-card.json \
  --tools examples/langgraph_import/agents/expense_bot/tools.json
```

- **Agent-agnostic onboarding.** Start traces-only (`examples/otel_plain/`), then add a card and tools list when you need governance and allowlist checks. Override locally with config (`disable`, thresholds) or a `rules_dir` / entry-point plugin without forking the engine (`docs/NO-LOCK-IN.md`).

Outputs: JSON (`agentest.verdicts/1`), JUnit, SARIF, HTML, Markdown, CSV, and optional OTel `gen_ai.evaluation.result` events (`--emit-otlp`).

---

## Five-minute quickstart (verified commands)

Aligned with the current `main` README. Python **3.11+**. The distribution name is `agentest-ai`, but **it is not on PyPI** — install from git or a clone. Judging needs only PyYAML.

**Clone demo (recommended starting point)**

```bash
git clone --depth 1 https://github.com/srpadmanabhuni/agentest.git
cd agentest
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
python examples/colab_quickstart.py
```

**Install the CLI without the examples tree**

```bash
pip install "git+https://github.com/srpadmanabhuni/agentest.git"   # from git, not PyPI
agentest version
agentest std run --agent a14
agentest std run --agent a14 --format html --out report.html
```

**Dev install + self-check**

```bash
git clone https://github.com/srpadmanabhuni/agentest.git && cd agentest
python -m venv .venv && . .venv/bin/activate && pip install -e ".[dev]"
ruff check . && python -m pytest -q
agentest std validate --agents examples/agnostic_demo/agents
agentest std run --agents examples/agnostic_demo/agents
```

**Own OTLP file**

```bash
python examples/otel_plain/emit_trace.py > build/trace.otlp.json
agentest std run --otlp build/trace.otlp.json \
  --card examples/otel_plain/agent-card.json --tools examples/otel_plain/tools.json
```

---

## Links, contribution, and stars

- GitHub: https://github.com/srpadmanabhuni/agentest  
- Checklist 110: https://huggingface.co/datasets/srinivaspadmanabhuni/agentic-ai-test-checklist-110  
- Getting started: `docs/GETTING-STARTED.md` · CI: `docs/developers/CI.md` · Instrumenting: `docs/developers/INSTRUMENTING.md` · LangGraph: `docs/integrations/langgraph.md`  
- Contribute: `CONTRIBUTING.md` · Discussions · issue forms for wrong verdicts  
- Labels: `good first issue`, `detection`

If the runner saves you time in CI, please **star** the repository and consider contributing a recorded failing case from your own agent (sanitised traces only). Theme on `main`: *bring an agent trace, contribute a test.*

---

## Honest limits

- **Not a model leaderboard and not certification.** Catalogue design is informed by ISO/IEC 42001 themes; that is not a certificate for your product.
- **You must emit (or import) useful traces.** Missing GenAI attributes → `n/a`. agentest will not invent evidence.
- **Heuristic text rules** (English regex over claims/refusals) are deterministic but uncalibrated. Expect triage; file false positives with a minimal OTLP repro.
- **OTel GenAI semantic conventions are still evolving.** agentest pins versions in `semconv.yaml` and maps common aliases; attribute renames upstream may need a migration.
- **Optional governance fields** (`urn:agentest:a2a-ext:governance:v1`) are documented extensions, not a ratified A2A standard. Without them, related checks return `n/a`.
- **No framework SDK lock-in — and no free lunch.** agentest does not depend on LangGraph, CrewAI, AutoGen, and so on; those stay your dependencies. You still own correct instrumentation or a faithful import mapping.
- **Reference agents** use a small local model with limited runs. Use them as fixtures and examples, not as proof of production quality.

---

*agentest — offline, deterministic testing for AI agents. Owned by Dr Srinivas Padmanabhuni / AiEnsured.*
