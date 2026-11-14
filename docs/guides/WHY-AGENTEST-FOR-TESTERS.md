# Why agentest matters for testers

**Audience:** QA engineers, SDET / test engineers, and assurance leads who need to test AI agents the way they already test software.

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

## Why agent testing is different

Ordinary UI and API tests assume a stable response for a stable input. Agents break that assumption in four ways:

1. **Non-determinism.** The same prompt can produce different tool sequences and wording across runs. A single golden string match is a weak oracle.
2. **Tool calls.** The important behaviour is often *what the agent called*, with which arguments, and whether that call succeeded — not only the chat reply.
3. **Multi-turn state.** Constraints given on turn 1 (a spend cap, a “never email X” rule, a verified identity) must still hold on turn 5. Unit tests that only assert the last message miss that drift.
4. **Actions with side effects.** Agents refill prescriptions, send mail, create tickets, move money. A “looks helpful” reply can hide a duplicate charge or a write that skipped a prerequisite.

agentest is built for that world. It does **not** run your agent and it does **not** use an LLM as judge. You record OpenTelemetry GenAI traces (plus, optionally, an A2A AgentCard and an MCP tools list). agentest returns a `pass` / `fail` / `n/a` verdict for each of **130** checks: the **110** catalogue IDs plus **20** repo extensions (`X-001`…`X-020`). Judging is offline, deterministic, and needs no account, token, network, or model.

---

## Real failures agentest catches

These examples come from the bundled demo (`examples/agnostic_demo`) and from the published catalogue / per-test guide — not from marketing claims.

| Failure class | What goes wrong | Catalogue / check IDs |
|---|---|---|
| **Duplicate actions** | The same irreversible write (for example a refill or payment) is called more than once in one run | T2-003 (duplicate irreversible side-effect calls capped at one); also T1-006 for idempotent re-runs |
| **Wrong outcomes / false completion** | The reply claims success while a tool failed, or a success flag appears without a real effect | T1-002, T1-018 (walkthrough: *claims a success it did not earn*) |
| **Ignored constraints** | A hard limit or “do not …” rule from an early turn is violated later | T6-001 (turn-1 constraints still hold at turn-5); T6-008 for longer chats |
| **Tool misuse** | A write runs before a required verify/lookup; or a non-allowlisted tool is invoked | T2-001 / T2-005 (verify before acting / before PII disclosure); T5-001 (only allowlisted tools) |
| **Ungrounded values** | Currency amounts or codes appear in the answer that were not in the input or tool results | X-012 (number / currency fidelity) |

On the shipped demo, `refill_bot` (clean) and `refill_bot_buggy` (seeded defects) are judged side by side. The README / Getting Started docs document the summary as **55 pass, 0 fail** on the clean agent and **41 pass, 16 fail** on the buggy one; remaining IDs are `n/a` because those traces do not carry the needed signal. `n/a` is **never** counted as a pass.

Walkthroughs that explain the evidence line by line live under `docs/walkthroughs/` (verify-before-acting, injected instructions in tool output, false success claims, unmasked personal data).

---

## How agentest fits a tester’s workflow

Think of agentest as a **trace-based checklist runner**, not a new UI automation stack.

- **Checklists.** Start from the open [110-test Hugging Face checklist](https://huggingface.co/datasets/srinivaspadmanabhuni/agentic-ai-test-checklist-110). Each ID has an objective, acceptance criteria, and (in the dataset) a manual procedure. agentest prints the same IDs.
- **Test plans.** `docs/testers/TEST-PLANNING.md` groups IDs by risk priority (run P0 — wrong durable state, unapproved action, data leak — before lower priorities). Map your agent’s risks (writes money? handles PII? reads untrusted content?) to those rows, then make sure your recorded inputs actually exercise them. An ID with no matching signal returns `n/a`.
- **Regression.** Commit recorded OTLP traces (or regenerate them in CI). Re-run `agentest std run` on every change. Use `--format junit` so any CI that already understands JUnit can gate the build; `--strict` exits non-zero on any `fail`.
- **Evidence reports.** HTML, Markdown, JSON, SARIF, and CSV outputs include a `detail` string that names the run and the evidence (for example which tool call or missing prerequisite). Use that text in defect reports (`docs/testers/DEFECT-REPORTS.md`) and when triage suggests a false positive (`docs/testers/FALSE-POSITIVES.md`).

Modes matter for independent assessment: `--mode strict` reads only standard OTel / A2A / MCP fields (plus the documented optional governance extension). The default `examples` mode may also use success criteria the agent publishes on its AgentCard skill examples. Prefer **strict** when you are the independent tester.

---

## Five-minute quickstart (verified commands)

These commands match the current `main` README / Getting Started flow. Python **3.11+**. `agentest-ai` is **not** on PyPI yet — install from git or a clone. No API key, GPU, or model is required to judge.

**Option A — copy-paste demo from a clone**

```bash
git clone --depth 1 https://github.com/srpadmanabhuni/agentest.git
cd agentest
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
python examples/colab_quickstart.py
```

That script judges the bundled buggy refill agent, prints failing checks with evidence, applies one temporary repair (identity verification before dependent calls), and reruns. Shipped traces are not modified.

**Option B — standards CLI on the same demo**

```bash
git clone https://github.com/srpadmanabhuni/agentest.git && cd agentest
python -m venv .venv && . .venv/bin/activate && pip install -e ".[dev]"
agentest std validate --agents examples/agnostic_demo/agents
agentest std run --agents examples/agnostic_demo/agents
agentest std run --agents examples/agnostic_demo/agents --agent refill_bot_buggy --format html --out report.html
```

**Your own agent (when you have traces)**

```bash
agentest std run --otlp my_traces.otlp.jsonl --card agent-card.json --tools tools.json --format html --out report.html
```

---

## Links, contribution, and stars

- GitHub: https://github.com/srpadmanabhuni/agentest  
- Checklist 110 (Hugging Face): https://huggingface.co/datasets/srinivaspadmanabhuni/agentic-ai-test-checklist-110  
- Tester docs: `docs/testers/` (quickstart, reading results, defect reports, per-test guide)  
- Issues / wrong verdict forms: https://github.com/srpadmanabhuni/agentest/issues/new/choose  
- Good first issues: https://github.com/srpadmanabhuni/agentest/labels/good%20first%20issue  

If agentest helps your test plan, a **star** on the GitHub repo helps other testers find it. Contributions that add a failing recorded case, improve a check, or fix a false positive are welcome — see `CONTRIBUTING.md`. You do not need to be an agent researcher to help.

---

## Honest limits

- **Not certification.** The checklist is informed by ISO/IEC 42001 themes; running agentest does not certify a product.
- **`n/a` is common** when traces omit GenAI attributes, tool results, or governance facts. Many `n/a` means low instrumentation coverage, not a clean bill of health.
- **Some rules use English regex heuristics** (claims, refusals, warnings). They are deterministic but uncalibrated; paraphrases and other languages can confuse them. Triage before filing defects.
- **Reference-agent traces** in the repo come from a small local model with few runs (k = 1–3). Treat them as fixtures, not as a production performance study.
- **agentest does not replace exploratory testing**, threat modelling, or human review of high-risk flows. It adds a repeatable, evidence-backed checklist over recorded behaviour.
- **No model judge** in the pass/fail path — by design. That keeps runs offline and reproducible, but it also means checks that need rich semantic judgement may stay as `n/a` or as narrow heuristics until better signals exist in the trace.

---

*agentest — offline, deterministic testing for AI agents. Owned by Dr Srinivas Padmanabhuni / AiEnsured.*
