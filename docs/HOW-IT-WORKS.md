# How agentest works, coverage and non-goals

Moved from the README. What each check reads, the two modes, per-release coverage on the 98 reference agents, caveats and non-goals.

## What makes agentest different

- **Offline and deterministic.** Judging needs no account, API key, network or model, and no LLM judge sits in the pass/fail path. The same traces give the same verdicts on every run.
- **Works on what your agent already recorded.** agentest does not run or wrap your agent. It reads OpenTelemetry GenAI traces after the fact (OTLP/JSON, JSONL or protobuf files), can receive them over OTLP/HTTP (`agentest std serve`), and can convert native framework logs (`agentest std import`).
- **Agent- and framework-agnostic.** No rule names an agent, tool or vendor. Rules read standard evidence such as MCP tool annotations, call arguments, tool results and span status. A CI test renames every agent and tool and fails if any verdict changes ([agent-independence audit](standards/AGENT-INDEPENDENCE-AUDIT.md)).
- **Built on open protocols.** OpenTelemetry GenAI semantic conventions (pinned version), the A2A AgentCard and MCP `tools/list` annotations. Your agent never imports agentest ([No lock-in](NO-LOCK-IN.md)).
- **130 checks with public IDs.** 110 come from the open Agentic AI Test Checklist 110 on Hugging Face; 20 are repo extensions (`X-001`…`X-020`). Every ID has its own page ([per-ID test pages](tests/README.md)).
- **Evidence for every verdict, and an honest `n/a`.** Each result carries a `detail` line naming the run and the evidence. When a trace has no signal for a check, the verdict is `n/a`, never a silent pass.
- **CI- and pytest-ready.** JUnit, SARIF, versioned JSON, HTML, Markdown, CSV and OTel `gen_ai.evaluation.result` events; `--strict` exits 1 on any `fail`; a pytest template ships in `templates/`.
- **Small and extensible.** One runtime dependency (PyYAML). Disable IDs or tune thresholds in a config file, or add rules from a `rules_dir` or an entry-point plugin without forking.

**Guides:** [User Guide](USER-GUIDE.md) (install, quickstart, CLI, config, outputs, CI) ·
[Author Guide](AUTHOR-GUIDE.md) (new rules, scenarios, adapters, extension fields, reference agents, guards) ·
[Getting started](GETTING-STARTED.md) · [Why agentest: testers](guides/WHY-AGENTEST-FOR-TESTERS.md) · [Why agentest: developers](guides/WHY-AGENTEST-FOR-DEVELOPERS.md) · [Documentation index](README.md) · [FAQ](FAQ.md) · [Framework (4 pillars)](FRAMEWORK.md) · [Overlaps and gaps](OVERLAPS-AND-GAPS.md) · [Coverage](COVERAGE.md) · [CHANGELOG](../CHANGELOG.md)


## How it works

Each ID is judged by **one universal rule** that reads only:
- OpenTelemetry GenAI spans (OTLP/JSON or OTLP/protobuf, semantic conventions pinned in
  [semconv.yaml](../src/agentest/standards/semconv.yaml), with older versions and common instrumentation styles mapped);
- the agent's A2A AgentCard;
- MCP tool schemas and annotations (`readOnlyHint`, `destructiveHint`, ...);
- where no standard says it (approvals, prerequisites, compensations, roles, tenancy, allowed hosts, approval TTLs),
  one documented, optional extension, [`urn:agentest:a2a-ext:governance:v1`](standards/EXTENSION.md), with a
  [JSON Schema](../src/agentest/standards/schemas/governance-extension.schema.json).

An agent is a folder with exactly `agent-card.json`, `tools.json` and `traces/`. No rule names an agent, a tool or a
vendor; there are no per-agent profiles. CI enforces this with the
[agent-independence audit](standards/AGENT-INDEPENDENCE-AUDIT.md) (static scan, rename/mutation test over every
agent, traces-only onboarding) and the [no-lock-in checks](NO-LOCK-IN.md). Traces come in from files, from any
OTLP exporter via `agentest std serve`, or from native framework logs via `agentest std import`; verdicts go out as
JSON, JUnit, SARIF, HTML, Markdown, CSV or OTel `gen_ai.evaluation.result` events (`--emit-otlp`).

**Two modes:** `strict` reads only the standard fields and the extension; `examples` (the default) also uses the
success criteria the agent publishes with its AgentCard skill examples.

## Coverage on the reference agents

Every one of the 130 IDs is now decided (pass or fail, not `n/a`) on at least one of the 98 reference agents, in both
modes. The table counts, for each bucket, how many IDs are decided on that many agents.

| Release | Mode | 0 agents | 1-9 | 10-49 | 50-69 | 70+ |
|---|---|---:|---:|---:|---:|---:|
| v3.0.0 (a01-a70) | strict | 37 | 50 | 16 | 23 | 4 |
| v3.0.0 (a01-a70) | examples | 37 | 50 | 12 | 23 | 8 |
| v3.1.0 (a01-a81) | strict | 0 | 84 | 17 | 16 | 13 |
| v3.1.0 (a01-a81) | examples | 0 | 84 | 14 | 15 | 17 |
| v3.2.0 (a01-a98) | strict | 0 | 73 | 20 | 17 | 20 |
| v3.2.0 (a01-a98) | examples | 0 | 73 | 17 | 16 | 24 |
| v3.3.0 (a01-a98) | strict | 0 | 72 | 20 | 15 | 23 |
| v3.3.0 (a01-a98) | examples | 0 | 72 | 17 | 14 | 27 |
| v3.3.1 (a01-a98) | strict | 0 | 72 | 20 | 15 | 23 |
| v3.3.1 (a01-a98) | examples | 0 | 72 | 17 | 14 | 27 |
| v3.3.2 (a01-a98) | strict | 0 | 72 | 20 | 15 | 23 |
| v3.3.2 (a01-a98) | examples | 0 | 72 | 17 | 14 | 27 |

Being decided is not the same as being shown both ways. In examples mode every ID now has both a passing and a
failing agent (0 one-sided, was 68 at v3.1.1); [docs/COVERAGE.md](COVERAGE.md) lists the pass/fail split per ID.

The full per-ID table is [docs/COVERAGE.md](COVERAGE.md), generated by `scripts/coverage_table.py` and checked in
CI; `scripts/check_versions.py` fails CI if the current-release rows above drift from it. The standards each ID maps to (OWASP LLM 2025, OWASP Agentic, NIST AI RMF / 600-1, ISO/IEC 42001 Annex A,
MITRE ATLAS) are in [STANDARDS-MAP.md](standards/STANDARDS-MAP.md).

**Caveats:**
- A rule with no signal reports `n/a`, never `pass`. To turn it into a real check, the agent must emit the span
  attribute or publish the fact.
- Several rules read free text with English regex heuristics (claims, warnings, refusals, corrections). They are
  deterministic but uncalibrated; see [false positives](testers/FALSE-POSITIVES.md).
- Reference-agent traces come from a small local model (Qwen2.5-7B-Instruct GGUF, CPU) with k = 1-3 runs per input.
- This is not certification, and the rules are not production-grade evaluators.


## Non-goals

- Not an LLM-judge eval framework, and no third-party eval framework as a dependency
- No model judge in the pass/fail path
- Not a model leaderboard, and not certification

## Catalogue pin

See [`catalog/VERSION`](../catalog/VERSION) (pinned catalogue **v1.3.1**; full 110-row catalogue vendored as [`catalog/checklist-110.jsonl`](../catalog/checklist-110.jsonl)), plus vendored [`catalog/functional.csv`](../catalog/functional.csv), [`catalog/privacy.csv`](../catalog/privacy.csv), [`catalog/explainability.csv`](../catalog/explainability.csv), [`catalog/bias_fairness.csv`](../catalog/bias_fairness.csv), and [`catalog/orchestration.csv`](../catalog/orchestration.csv).  
Pack CSVs are pinned by sha256: `python scripts/check_catalog_pins.py` (offline, runs in CI).
