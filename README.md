# agentest

> **v3.2.0** (coverage release: A82-A98 fixed and seeded-defect agents; 0 one-sided IDs). **v3.1.1** (patch on v3.1.0: stricter guard, OTel `schemaUrl` and retry handling, optional official protobuf
> decoder, real-SDK conformance test, a snapshot of every verdict). **v3.1.0:** every one of the 130 checks is a universal rule over standard artifacts (OpenTelemetry GenAI traces,
> the A2A AgentCard, MCP tool annotations). The legacy v2 engine and its per-agent YAML profiles are removed; the
> `v2.0.0` and `v1.0.0` tags keep that history. See the [CHANGELOG](CHANGELOG.md) for the migration note.

[![CI](https://github.com/srpadmanabhuni/agentest/actions/workflows/ci.yml/badge.svg)](https://github.com/srpadmanabhuni/agentest/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/)
[![DOI](https://img.shields.io/badge/DOI-10.5281%2Fzenodo.23614376-blue.svg)](https://doi.org/10.5281/zenodo.23614376)
[![Hugging Face catalogue](https://img.shields.io/badge/%F0%9F%A4%97%20Hugging%20Face-Checklist%20110-yellow.svg)](https://huggingface.co/datasets/srinivaspadmanabhuni/agentic-ai-test-checklist-110)

**Offline, deterministic test runner for agentic AI, covering the Agentic AI Test Checklist 110.**
Give it an agent's OTel GenAI traces (plus, optionally, its A2A AgentCard and MCP tools list) and it returns a
`pass` / `fail` / `n/a` verdict for each of 130 checks: the 110 catalogue IDs plus 20 repo extensions (`X-001`…`X-020`).
No account, token, network or model is needed to judge. The checklist design is informed by ISO 42001 themes; this is
not certification.

**Guides:** [User Guide](docs/USER-GUIDE.md) (install, quickstart, CLI, config, outputs, CI) ·
[Author Guide](docs/AUTHOR-GUIDE.md) (new rules, scenarios, adapters, extension fields, reference agents, guards) ·
[Documentation index](docs/README.md) · [Coverage](docs/COVERAGE.md) · [CHANGELOG](CHANGELOG.md)

## Catalogue

The test IDs come from the open catalogue on Hugging Face. The reference agents are the systems under test.
- Dataset: [Agentic AI Test Checklist 110](https://huggingface.co/datasets/srinivaspadmanabhuni/agentic-ai-test-checklist-110) (test definitions, manual procedures, standards crosswalk).
- Reference agents: [agentic-ai-reference-agents](https://huggingface.co/srinivaspadmanabhuni/agentic-ai-reference-agents) (runnable agents, code only, with recorded runs).
- Viewer Space: [agentic-ai-reference-agents-viewer](https://huggingface.co/spaces/srinivaspadmanabhuni/agentic-ai-reference-agents-viewer) (browse the recorded runs).

**Caveats:** some checks are uncalibrated regex heuristics. Reference-agent results come from a small local model (Qwen2.5-7B-Instruct, CPU) with a limited number of runs (k = 1-3). Some governance metadata uses a documented non-standard A2A extension ([`urn:agentest:a2a-ext:governance:v1`](docs/standards/EXTENSION.md)).

## Install

```bash
pip install "agentest @ git+https://github.com/srpadmanabhuni/agentest.git@v3.2.0"   # from git, no clone
agentest version     # 3.1.1
```

or from a fresh clone: `git clone https://github.com/srpadmanabhuni/agentest.git && cd agentest && pip install -e ".[dev]"`.
Python 3.11+, one runtime dependency (PyYAML), works offline. The catalogue and the bundled agents' standard files
ship with the package.

## Quickstart

```bash
agentest std validate --agents examples/agnostic_demo/agents
agentest std run --agents examples/agnostic_demo/agents     # refill_bot: 54 pass, 0 fail; refill_bot_buggy: 19 fail
agentest std run --otlp my_traces.otlp.jsonl --card agent-card.json --tools tools.json   # your own agent
agentest std run                                            # all 113 bundled agents (98 reference + 15 samples)
agentest std run --format junit --out agentest.xml --strict # CI gate (also json, sarif, html, md, csv)
```

## How it works

Each ID is judged by **one universal rule** that reads only:
- OpenTelemetry GenAI spans (OTLP/JSON or OTLP/protobuf, semantic conventions pinned in
  [semconv.yaml](src/agentest/standards/semconv.yaml), with older versions and common instrumentation styles mapped);
- the agent's A2A AgentCard;
- MCP tool schemas and annotations (`readOnlyHint`, `destructiveHint`, ...);
- where no standard says it (approvals, prerequisites, compensations, roles, tenancy, allowed hosts, approval TTLs),
  one documented, optional extension, [`urn:agentest:a2a-ext:governance:v1`](docs/standards/EXTENSION.md), with a
  [JSON Schema](src/agentest/standards/schemas/governance-extension.schema.json).

An agent is a folder with exactly `agent-card.json`, `tools.json` and `traces/`. No rule names an agent, a tool or a
vendor; there are no per-agent profiles. CI enforces this with the
[agent-independence audit](docs/standards/AGENT-INDEPENDENCE-AUDIT.md) (static scan, rename/mutation test over every
agent, traces-only onboarding) and the [no-lock-in checks](docs/NO-LOCK-IN.md). Traces come in from files, from any
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

Being decided is not the same as being shown both ways. In examples mode every ID now has both a passing and a
failing agent (0 one-sided, was 68 at v3.1.1); [docs/COVERAGE.md](docs/COVERAGE.md) lists the pass/fail split per ID.

The full per-ID table is [docs/COVERAGE.md](docs/COVERAGE.md), generated by `scripts/coverage_table.py` and checked in
CI. The standards each ID maps to (OWASP LLM 2025, OWASP Agentic, NIST AI RMF / 600-1, ISO/IEC 42001 Annex A,
MITRE ATLAS) are in [STANDARDS-MAP.md](docs/standards/STANDARDS-MAP.md).

**Caveats:**
- A rule with no signal reports `n/a`, never `pass`. To turn it into a real check, the agent must emit the span
  attribute or publish the fact.
- Several rules read free text with English regex heuristics (claims, warnings, refusals, corrections). They are
  deterministic but uncalibrated; see [false positives](docs/testers/FALSE-POSITIVES.md).
- Reference-agent traces come from a small local model (Qwen2.5-7B-Instruct GGUF, CPU) with k = 1-3 runs per input.
- This is not certification, and the rules are not production-grade evaluators.

## Develop

```bash
git clone https://github.com/srpadmanabhuni/agentest.git && cd agentest
python -m venv .venv && . .venv/bin/activate && pip install -e ".[dev]"
ruff check . && python -m pytest -q
python scripts/coverage_table.py --check
```

**Author:** Dr Srinivas Padmanabhuni · srinivas AT testAIng.com · [testAIng.com](https://testaing.com) / [AiEnsured](https://aiensured.com)

**Related:** DOI [10.5281/zenodo.23614376](https://doi.org/10.5281/zenodo.23614376) ·
article [Testing Agentic AI: 110 Tests for Safer AI Agents](https://www.linkedin.com/pulse/testing-agentic-ai-dr-srinivas-padmanabhuni-5stoc/) ·
framework crosswalk (NIST AI RMF, EU AI Act, OWASP LLM Top 10, ISO/IEC 42001 themes; indicative only) [`docs/FRAMEWORK-MAPPING.md`](docs/FRAMEWORK-MAPPING.md)

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
