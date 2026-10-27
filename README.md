# agentest

> **v3.0.0:** standards-based and agent-agnostic. See [docs/standards/DESIGN.md](docs/standards/DESIGN.md). The v2.0.0 (model-driven profiles) and v1.0.0 tags remain available.

[![CI](https://github.com/srpadmanabhuni/agentest/actions/workflows/ci.yml/badge.svg)](https://github.com/srpadmanabhuni/agentest/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/)
[![DOI](https://img.shields.io/badge/DOI-10.5281%2Fzenodo.23614376-blue.svg)](https://doi.org/10.5281/zenodo.23614376)
[![Hugging Face catalogue](https://img.shields.io/badge/%F0%9F%A4%97%20Hugging%20Face-Checklist%20110-yellow.svg)](https://huggingface.co/datasets/srinivaspadmanabhuni/agentic-ai-test-checklist-110)

**Offline test runner for agentic AI, covering the Agentic AI Test Checklist 110.**  
Clone → install → run. No account, token, network or model is needed at test time. The checklist design is informed by ISO 42001 themes; this is not certification.

> **Status: 130 of 130 checks are real; there are 0 placeholder checks.** The 130 are the 110 catalogue IDs plus 20 repo
> extensions (`X-001`…`X-020`, kept separate from catalogue IDs). Every check is a deterministic or metamorphic oracle
> over what an agent actually did. They run against **15 scripted sample agents** and **25 runnable reference agents**
> (`reference_agents/`: LangGraph, CrewAI, AutoGen/AG2, OpenAI Agents SDK, LlamaIndex, MCP, n8n; driven by a local open 7B model,
> with episodes recorded and replayed offline in CI). a13-a25 (supervisors, map-reduce, plan-execute, crews, debate, negotiation,
> swarms) are checked at trace level over 3 recorded cases each, so many of their cells are `n/a`. Every ID has at least
> one passing and one failing agent. **Caveats:** many IDs have no surface on a given reference agent and report `n/a` there.
> Some checks read free text with regex heuristics (marked as **uncalibrated heuristics**). The Hindi/Tamil probes are
> machine-translated by the local model, which is a heuristic. Samples are small (k = 1–3). These are not production-grade evaluators.
> Results: [`fixtures/real/RESULTS.md`](fixtures/real/RESULTS.md).

## Catalogue

The test IDs come from the open catalogue on Hugging Face. The reference agents are the systems under test.
- Dataset: [Agentic AI Test Checklist 110](https://huggingface.co/datasets/srinivaspadmanabhuni/agentic-ai-test-checklist-110) (test definitions, manual procedures, standards crosswalk).
- Reference agents: [agentic-ai-reference-agents](https://huggingface.co/srinivaspadmanabhuni/agentic-ai-reference-agents) (runnable agents, code only, with recorded runs).
- Viewer Space: [agentic-ai-reference-agents-viewer](https://huggingface.co/spaces/srinivaspadmanabhuni/agentic-ai-reference-agents-viewer) (browse the recorded runs).

**Caveats:** some checks are uncalibrated regex heuristics. Reference-agent results come from a small local model (Qwen2.5-7B-Instruct, CPU) with a limited number of runs (k = 1-3). Some governance metadata uses a documented non-standard A2A extension ([`urn:agentest:a2a-ext:governance:v1`](docs/standards/EXTENSION.md)).

## Install

```bash
pip install "agentest @ git+https://github.com/srpadmanabhuni/agentest.git@v3.0.0"   # from git, no clone
# or build a wheel from a clone: python -m pip install build && python -m build && pip install dist/agentest-3.0.0-py3-none-any.whl
agentest version     # 3.0.0
```

Python 3.11+, one runtime dependency (PyYAML, for agent profiles), works offline. The catalogue and recorded episodes ship with the package.


## v3.0.0: standards-based, agent-agnostic checks

v3 judges each of the 130 IDs with **one universal rule**. The rule reads only standard artefacts:
- OpenTelemetry GenAI spans (OTLP/JSON);
- the agent's A2A AgentCard;
- MCP tool annotations (`readOnlyHint`, `destructiveHint`, ...);
- where a standard says nothing (approvals, prerequisites, restricted data, allowed hosts), one documented extension, `urn:agentest:a2a-ext:governance:v1`.

Each agent is described by metadata under `agents/<id>/`. No rule names an agent, and CI enforces this (see the [agent-independence audit](docs/standards/AGENT-INDEPENDENCE-AUDIT.md)). Lock-in guarantees and residual risks are listed in [NO-LOCK-IN.md](docs/NO-LOCK-IN.md).

**Documentation index: [docs/README.md](docs/README.md)**, which links tester guides (including a per-test guide for all 130 IDs) and developer guides.

```bash
agentest std validate --agents examples/agnostic_demo/agents
agentest std run --agents examples/agnostic_demo/agents     # refill_bot: 54 pass, 0 fail; refill_bot_buggy: 19 fail
agentest std run                                            # all 85 bundled agents (70 reference + 15 samples)
agentest std regress [--mode strict]                        # compare with the v2.0.0 verdicts
agentest std export --out otlp/                             # OTLP/JSON for any OTel backend
```

**Two modes:**
- `strict` uses only the universal rules plus the harness's own `gen_ai.evaluation.result` events.
- `examples` (the default) also applies the success criteria the agent publishes with its AgentCard skill examples (`postconditions.byExample`).

**Regression against v2.0.0 (85 agents, 394 v2 defects):**

| Mode | Caught |
|---|---|
| examples | 391 (99.2%) |
| strict | 385 (97.7%) |

Every miss is explained in [REGRESSION.md](docs/standards/REGRESSION.md) as a v2 false positive or a mis-attribution. That file also triages each new finding as either a real defect or a false positive that was fixed universally.

The standards each ID maps to (OWASP LLM 2025, OWASP Agentic, NIST AI RMF / 600-1, ISO/IEC 42001 Annex A, MITRE ATLAS) are listed in [STANDARDS-MAP.md](docs/standards/STANDARDS-MAP.md). The onboarding guide is [DEVELOPER-GUIDE.md](docs/standards/DEVELOPER-GUIDE.md).

**Caveats:**
- A rule with no signal reports `n/a`. To turn it into a real check, the agent must publish the fact or emit the span attribute.
- Several rules read free text with regex heuristics (claims, warnings, refusals, reasons). These are uncalibrated.
- Samples are small (k = 1–3), and the injection canaries come from recorded inputs.
- This is not certification, and the rules are not production-grade evaluators.

The v2 engine (`agentest real`, `profiles/`) is still shipped for comparison. Its profiles are frozen, and new agents are onboarded only as v3 metadata.

## v2.0.0: model-driven, agent-independent checks (legacy)

All 130 IDs are judged by one generic engine over a standard trace (OpenTelemetry GenAI aligned) and one YAML profile
per agent. There is no agent-specific or test-specific check code: per-agent facts and expectations live in
`profiles/<agent>.yaml`, shared expectations in `profiles/_lib/*.yaml`, and a CI test fails if check code names an agent.
Parity with v1.0.0: all 382 v1 failures are reproduced (0 looser, 0 stricter cells); 2 extra failures appear where v1 had
no check (a07 T7-004, a17 T6-007) and are flagged for review. v1.0.0 stays tagged for the per-agent implementation.
See [DEVELOPER-GUIDE.md](docs/model-driven/DEVELOPER-GUIDE.md), [DESIGN.md](docs/model-driven/DESIGN.md), [ADD-AN-AGENT.md](docs/model-driven/ADD-AN-AGENT.md)
and [PARITY.md](docs/model-driven/PARITY.md).

## 5-minute quickstart

```bash
agentest list --class T4             # 1. browse the checklist (T1..T7)
agentest real --ids T4-005           # 2. one check across all profiled agents (offline replay)
agentest run --suite functional      # 3. scenario suite on the golden oracle agent

# 4. plug in YOUR agent: record episodes, then check them
git clone https://github.com/srpadmanabhuni/agentest.git && cd agentest
python examples/byo_agent/my_agent.py my_agent.jsonl
agentest check my_agent.jsonl --md report.md --html report.html
python examples/byo_agent/my_agent.py bug.jsonl --buggy && agentest check bug.jsonl --strict   # exit 1: defects caught
```

`agentest check` runs 13 trace-level checks (task success vs your own oracle, single-shot writes, raw PII in args/logs,
tool-call reasons, retry storms, step/token/latency budgets, structured output) over any agent that writes the small JSONL
format in [`docs/BYO-AGENT.md`](docs/BYO-AGENT.md). `agentest.byo.Recorder` writes it for you from LangGraph, CrewAI,
AutoGen or plain Python. Sample reports: [Markdown](docs/sample-report/buggy_agent-report.md) ·
[HTML](docs/sample-report/buggy_agent-report.html) · full matrix [`fixtures/real/RESULTS.md`](fixtures/real/RESULTS.md).

## Develop (clone)

```bash
git clone https://github.com/srpadmanabhuni/agentest.git
cd agentest
python -m venv .venv && source .venv/bin/activate
python -m pip install -e ".[dev]"
pytest -q && ruff check src tests scripts

agentest samples            # 15 teaching agents
agentest real               # 130 checks x every profiled agent, offline replay
```

**Docs:** [`GUIDEBOOK.md`](GUIDEBOOK.md) · [`docs/BYO-AGENT.md`](docs/BYO-AGENT.md) · [`CHANGELOG.md`](CHANGELOG.md) · [`CONTRIBUTING.md`](CONTRIBUTING.md) (install, concepts, adapters, reports, CI, extending, FAQ) ·
per-test reference [`docs/tests/`](docs/tests/README.md) · [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) ·
[`docs/DEVELOPER-GUIDE.md`](docs/DEVELOPER-GUIDE.md) · [`docs/REFERENCES.md`](docs/REFERENCES.md)

**Author:** Dr Srinivas Padmanabhuni · srinivas AT testAIng.com · [testAIng.com](https://testaing.com) / [AiEnsured](https://aiensured.com)

**Browse the checklist:**

```bash
atc list --class T3      # or: agentest list --class T3
atc run --suite functional
```

**Related:** DOI [10.5281/zenodo.23614376](https://doi.org/10.5281/zenodo.23614376) ·
article [Testing Agentic AI: 110 Tests for Safer AI Agents](https://www.linkedin.com/pulse/testing-agentic-ai-dr-srinivas-padmanabhuni-5stoc/) ·
framework crosswalk (NIST AI RMF, EU AI Act, OWASP LLM Top 10, ISO/IEC 42001 themes; indicative only) [`docs/FRAMEWORK-MAPPING.md`](docs/FRAMEWORK-MAPPING.md)

**Scope, honestly:** the checks are small deterministic oracles over scripted and recorded agents. Treat them as starter scaffolds to adapt to your own agent, not turnkey certification tests.

## Cite

```bibtex
@software{padmanabhuni_agentic_ai_test_checklist_110,
  author = {Padmanabhuni, Srinivas},
  title  = {Agentic AI Test Checklist 110 and agentest runner},
  doi    = {10.5281/zenodo.23614376},
  url    = {https://github.com/srpadmanabhuni/agentest}
}
```

See also [`CITATION.cff`](CITATION.cff).

## Non-goals

- No DeepEval, Giskard, Langfuse, Promptfoo, Ragas, or similar eval frameworks
- No model judge in the pass/fail path
- Not a model leaderboard, and not certification

## Real checks (130)

```bash
agentest real --md fixtures/real/RESULTS.md --json fixtures/real/results.json
```

* **Sample agents:** the 41 pack IDs record the scenarios in `src/agentest/cases/`; the other 89 IDs record deterministic
  mini-worlds in `src/agentest/samples/worlds.py`. Each run records a snapshot of the end state; the expectations in
  `profiles/_lib/samples.yaml` judge it.
* **Reference agents:** probes live in `src/agentest/real/probes.py` and `probes2.py`. They cover canonical tasks, refusal and approval bypass,
  prompt-injection canaries (quoted, hidden HTML, JSON breakout, base64), PII pairs, paraphrase, unit and negation variants,
  Hindi/Tamil translate-and-back, multi-turn slots, constraints and secrets, and concurrent twin resume. Adapters turn the recorded episodes into
  standard traces (`src/agentest/model/adapters.py`) and the profile expectations judge them (`src/agentest/model/expect.py`).
* **Thresholds** are fixed in code and documented per test in `docs/tests/<ID>.md`.
* **Agent failures are findings, not CI failures.** CI checks that the replay is complete and matches `fixtures/real/results.json`.

## Suites

```bash
agentest run --suite functional --agent golden         # exit 0
agentest run --suite privacy --agent golden            # exit 0
agentest run --suite explainability --agent golden     # exit 0
agentest run --suite bias_fairness --agent golden      # exit 0 (alias: --suite bias)
agentest run --suite orchestration --agent golden      # exit 0 (alias: --suite orch)
agentest run --suite bias --agent broken               # exit 1

# Single ID
agentest run --suite bias_fairness --ids T7-007 --agent golden

pytest
```

Every implemented ID must **Pass** a golden agent and **Fail** the matching broken behaviour.

## Sample agents

Fifteen teaching agents (`noop` → `flaky_plan`): complexity **1–10** green ladder,
**11–15** expected-fail / teaching-negative scenarios (partial fail profiles).

```bash
agentest samples            # noop…flaky_plan (1–15)
agentest samples --failing  # leaky…flaky_plan only
agentest run --suite orchestration --agent supervisor
agentest run --suite privacy --agent leaky              # expect fails
agentest run --suite explainability --agent hallucinator
agentest run --suite bias_fairness --agent biased
agentest run --suite orchestration --agent overreach
agentest run --suite functional --ids T2-001 --agent flaky_plan
agentest matrix   # exit 0 iff scripted…federation/(golden) all-pass
```

Details: [`docs/SAMPLE-AGENTS.md`](docs/SAMPLE-AGENTS.md), references & attribution: [`docs/REFERENCES.md`](docs/REFERENCES.md), [`docs/SCENARIOS-8-10.md`](docs/SCENARIOS-8-10.md), [`docs/SCENARIOS-EXPECTED-FAIL.md`](docs/SCENARIOS-EXPECTED-FAIL.md).

## Explainability

- Trace-faithful oracles only (fluency does not score): [`docs/EXPLAINABILITY-ORACLE.md`](docs/EXPLAINABILITY-ORACLE.md)
- Research & algorithm map (TRACE [Kim et al. 2025], ReAct, TRAJECT-Bench, AgentDiagnose, RAG-style citations): [`docs/EXPLAINABILITY-RESEARCH.md`](docs/EXPLAINABILITY-RESEARCH.md)

## Bias / fairness

- Suite: `--suite bias_fairness` (alias `--suite bias`)
- Metamorphic, deterministic labels only — illustrative, **not certification**: [`docs/BIAS-RESEARCH.md`](docs/BIAS-RESEARCH.md)
- Proposed catalogue v1.2 expansions (not in CSV yet): [`docs/PROPOSED-bias.md`](docs/PROPOSED-bias.md)

## Catalogue pin

See [`catalog/VERSION`](catalog/VERSION) (pinned catalogue **v1.2.1**; full 110-row catalogue vendored as [`catalog/checklist-110.jsonl`](catalog/checklist-110.jsonl)), plus vendored [`catalog/functional.csv`](catalog/functional.csv), [`catalog/privacy.csv`](catalog/privacy.csv), [`catalog/explainability.csv`](catalog/explainability.csv), [`catalog/bias_fairness.csv`](catalog/bias_fairness.csv), and [`catalog/orchestration.csv`](catalog/orchestration.csv).  
Pack CSVs are pinned by sha256: `python scripts/check_catalog_pins.py` (offline, runs in CI).

## References

Original sources for the methods and threat models behind the checks (all links verified 2026-10-26). Per-test
references: each `docs/tests/<ID>.md` ends with a **References** section. Full bibliography: [`docs/REFERENCES.md`](docs/REFERENCES.md).

- Chen, T. Y., Cheung, S. C., Yiu, S. M. (1998/2020). *Metamorphic Testing: A New Approach for Generating Next Test Cases.* [arXiv:2002.12543](https://arxiv.org/abs/2002.12543)
- Segura, S., Fraser, G., Sanchez, A. B., Ruiz-Cortés, A. (2016). *A Survey on Metamorphic Testing.* IEEE TSE 42(9). [doi:10.1109/TSE.2016.2532875](https://doi.org/10.1109/TSE.2016.2532875)
- Barr, E. T., Harman, M., McMinn, P., Shahbaz, M., Yoo, S. (2015). *The Oracle Problem in Software Testing: A Survey.* IEEE TSE 41(5). [doi:10.1109/TSE.2014.2372785](https://doi.org/10.1109/TSE.2014.2372785)
- Greshake, K., Abdelnabi, S., Mishra, S., Endres, C., Holz, T., Fritz, M. (2023). *Not What You've Signed Up For: Compromising Real-World LLM-Integrated Applications with Indirect Prompt Injection.* AISec '23. [doi:10.1145/3605764.3623985](https://doi.org/10.1145/3605764.3623985) · [arXiv:2302.12173](https://arxiv.org/abs/2302.12173)
- Zhan, Q., Liang, Z., Ying, Z., Kang, D. (2024). *InjecAgent: Benchmarking Indirect Prompt Injections in Tool-Integrated Large Language Model Agents.* [arXiv:2403.02691](https://arxiv.org/abs/2403.02691)
- Debenedetti, E., Zhang, J., Balunović, M., et al. (2024). *AgentDojo: A Dynamic Environment to Evaluate Prompt Injection Attacks and Defenses for LLM Agents.* [arXiv:2406.13352](https://arxiv.org/abs/2406.13352)
- Yao, S., Shinn, N., Razavi, P., Narasimhan, K. (2024). *τ-bench: A Benchmark for Tool-Agent-User Interaction in Real-World Domains.* [arXiv:2406.12045](https://arxiv.org/abs/2406.12045)
- Kim, W., Park, S., In, Y., et al. (2025). *Beyond the Final Answer: Evaluating the Reasoning Trajectories of Tool-Augmented Agents* (TRACE). [arXiv:2510.02837](https://arxiv.org/abs/2510.02837)
- Ruan, Y., Dong, H., Wang, A., et al. (2023). *Identifying the Risks of LM Agents with an LM-Emulated Sandbox* (ToolEmu). [arXiv:2309.15817](https://arxiv.org/abs/2309.15817)
- Yao, S., Zhao, J., Yu, D., et al. (2022). *ReAct: Synergizing Reasoning and Acting in Language Models.* [arXiv:2210.03629](https://arxiv.org/abs/2210.03629)
- Yong, Z.-X., Menghini, C., Bach, S. H. (2023). *Low-Resource Languages Jailbreak GPT-4.* [arXiv:2310.02446](https://arxiv.org/abs/2310.02446)
- Deng, Y., Zhang, W., Pan, S. J., Bing, L. (2023). *Multilingual Jailbreak Challenges in Large Language Models.* [arXiv:2310.06474](https://arxiv.org/abs/2310.06474)
- Garg, S., Perot, V., Limtiaco, N., et al. (2019). *Counterfactual Fairness in Text Classification through Robustness.* AIES 2019. [doi:10.1145/3306618.3317950](https://doi.org/10.1145/3306618.3317950)
- OWASP Top 10 for LLM Applications 2025. *LLM01:2025 Prompt Injection.* <https://genai.owasp.org/llmrisk/llm01-prompt-injection/>
- OWASP Top 10 for LLM Applications 2025. *LLM06:2025 Excessive Agency.* <https://genai.owasp.org/llmrisk/llm062025-excessive-agency/>
- OWASP GenAI Security Project. *OWASP Top 10 for Agentic Applications for 2026.* <https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/>
- NIST (2023). AI 100-1 *Artificial Intelligence Risk Management Framework (AI RMF 1.0).* [doi:10.6028/NIST.AI.100-1](https://doi.org/10.6028/NIST.AI.100-1) · <https://www.nist.gov/itl/ai-risk-management-framework>
- Regulation (EU) 2024/1689 (Artificial Intelligence Act); Art. 14 human oversight. <https://eur-lex.europa.eu/eli/reg/2024/1689/oj/eng>
- ISO/IEC 42001:2023 *Information technology — Artificial intelligence — Management system.* <https://www.iso.org/standard/81230.html>
- Model Context Protocol specification 2025-06-18, *Tools.* <https://modelcontextprotocol.io/specification/2025-06-18/server/tools>
- Qwen Team (2024). *Qwen2.5 Technical Report.* [arXiv:2412.15115](https://arxiv.org/abs/2412.15115)
- ggml-org. *llama.cpp* (GGUF inference, OpenAI-compatible server). <https://github.com/ggml-org/llama.cpp>
- Padmanabhuni, S. (2026). *Agentic AI Assurance Test Taxonomy v1.* Zenodo. [doi:10.5281/zenodo.23587407](https://doi.org/10.5281/zenodo.23587407) — source of the test IDs only
- Padmanabhuni, S. (2026). *Agentic AI Assurance Test Catalogue — Consolidated Edition (All 110 Tests, T1–T7).* Zenodo. [doi:10.5281/zenodo.23614376](https://doi.org/10.5281/zenodo.23614376) — source of the test text only

## Licence

Apache-2.0 (runner). Checklist data: **CC BY 4.0**.
