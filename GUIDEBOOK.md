# agentest guidebook

agentest is an offline test runner for agentic AI systems. It checks **what an agent actually did**
(tool calls, rows written, messages sent, state left behind), not just what it said. It has
130 real checks: the 110 IDs of the *Agentic AI Test Checklist 110* catalogue plus 20 repo
extensions `X-001..X-020`. Every check is deterministic or metamorphic. A few read free text with regex
heuristics. Those are marked **uncalibrated heuristic** in their per-test doc. No third-party eval
framework, no API key, no network at test time.

Contents: [Install](#1-install) · [Concepts](#2-concepts) · [Running packs](#3-running-packs) ·
[Reading reports](#4-reading-reports) · [Writing an adapter](#5-writing-an-adapter-for-your-agent) ·
[Recording reference agents](#6-recording-live-episodes) · [CI](#7-ci) · [Extending](#8-extending-the-tests) · [FAQ](#9-faq) · [References](#10-references)

> **v3.0.0 note:** the primary engine is now `agentest std`. It is standards-based: OTel GenAI spans, the A2A AgentCard, MCP annotations and one governance extension, with one universal rule per ID and two modes, `strict` and `examples`.
> See the README's v3 section, [docs/standards/DESIGN.md](docs/standards/DESIGN.md), [DEVELOPER-GUIDE.md](docs/standards/DEVELOPER-GUIDE.md) and [STANDARDS-MAP.md](docs/standards/STANDARDS-MAP.md).
> The sections below describe the catalogue packs and the legacy v2 matrix (`agentest real`), which are still shipped. Caveats: the free-text heuristics are uncalibrated, samples are small (k = 1–3), and this is not certification.

## 1. Install

```bash
git clone https://github.com/srpadmanabhuni/agentest.git && cd agentest
python -m venv .venv && source .venv/bin/activate
python -m pip install -e ".[dev]"
pytest -q                # unit tests + offline replay of all recorded episodes
agentest std run         # v3: all agents x 130 IDs, offline
agentest real            # legacy v2 matrix, offline
```

You need Python 3.11 or newer. You need no GPU, model or account. Only re-recording the reference agents needs the
optional local model (section 6).

## 2. Concepts

| Term | Meaning |
|:--|:--|
| **ID** | One check. `T1-001`…`T7-0xx` are catalogue IDs (vendored in `catalog/checklist-110.jsonl`); `X-001`…`X-020` are repo extensions. |
| **Sample agent** | One of 15 scripted teaching agents (`agentest samples`). `noop` does nothing. 8 "ladder" agents are correct. `eager` breaks everything. `leaky`, `hallucinator`, `biased`, `overreach` and `flaky_plan` each carry one defect class. They show that each oracle can both pass and fail. |
| **Reference agent** | One of 12 real agents in `reference_agents/` (a01…a12), built on common frameworks (LangGraph, LlamaIndex, AutoGen, CrewAI, n8n, …) and driven by a local open model. |
| **Episode** | One recorded run: `{agent, probe, rep, input, output, trace, extra, error}` in `fixtures/real/episodes/<agent>[.<set>].jsonl`. |
| **Probe** | A named input sent to an agent: `canon` is the normal task, and the others are adversarial or metamorphic variants (paraphrase, quoted injection, Hindi/Tamil, duplicate, ambiguity, …). |
| **Oracle / check** | A pure function from episodes to `pass` / `fail` / `n/a`, with a `detail` string naming the evidence. |
| **Mock gateway** | `agentest.gateway.ToolGateway`: the in-memory tools and ledger the catalogue packs run against. |

There are two layers:
1. **Catalogue packs** (`agentest run --suite …`): CaseSpec scenarios in `src/agentest/cases/` for the 41 IDs vendored in `catalog/*.csv`, under the mock gateway.
2. **Real matrix** (`agentest real`): all 130 IDs for 15 sample agents (recorded case scenarios for the first 41, deterministic mini-worlds in `samples/worlds.py` for the other 89) and for the reference agents via recorded episodes. Since v2.0.0 every verdict comes from the generic engine (`agentest.model`): adapters produce standard traces, and the expectations in `profiles/<agent>.yaml` and `profiles/_lib/*.yaml` judge them. There is no per-agent check code.

## 3. Running packs

```bash
agentest samples                                  # list sample agents
agentest run --suite functional --agent golden    # one pack, one agent
agentest matrix                                   # 41 pack IDs x sample agents
agentest real                                     # 130 IDs x 40 agents (markdown to stdout)
agentest real --agents reference --md out.md --json out.json
agentest real --ids T4-005,X-009                  # just these cells
```

## 4. Reading reports

`fixtures/real/RESULTS.md` is the committed matrix, and `results.json` holds the same data with a `detail` for every cell.

- `pass`: the oracle held on every recorded episode.
- `fail`: at least one episode violated it. `detail` quotes the evidence (for example `request_refund called without lookup`).
- `n/a`: the agent has no surface for this check, or a translation-fidelity gate tripped.
- `not-run`: there are no episodes for a reference agent. `agentest real` exits 1.

A failure on a reference agent is a **finding** about that agent, not a test-suite failure. CI fails only when the
replay differs from the committed results or a unit test breaks. Each ID's doc (`docs/tests/<ID>.md`) explains how to read it.

## 5. Writing an adapter for your agent

**Option A: mock gateway (fastest).** Subclass `agentest.samples.base.SampleAgent` and implement
`handle(checklist_id, env) -> Trace`. Inside it, call tools through `ToolGateway(env)` and record a `Trace`.
Register the class in `agentest/samples/__init__.py`, then run `agentest run --agent yours`.

**Option B: your real agent (recorded episodes).**
1. Write a runner that sends each probe to your agent and writes one JSON line per run:
   ```json
   {"agent": "mine", "probe": "canon", "rep": 0, "input": "...", "output": {...},
    "trace": [{"tool": "lookup_order", "args": {...}}], "extra": {"db_sha_before": "...", "db_sha_after": "..."}, "error": null}
   ```
   Put observable side effects in `output` or `extra` (rows written, emails sent, DB hashes). Oracles trust evidence, not claims.
2. Register checks:
   ```python
   from agentest.real.checks import check, ok
   @check("T1-001", "mine")
   def _(E):
       o = E.out("canon")
       return ok(o["rows_written"] == ["R1"], f"rows={o['rows_written']}")
   ```
   `E.out(probe)`, `E.get(probe)` and `E.all` give access to episodes.
3. Add `"mine"` to `REF_AGENTS` and run `agentest real --agents reference`.

## 6. Recording live episodes

The reference agents need `reference_agents/requirements-reference.txt` (a separate venv), n8n via Node 22 for a08,
and a Qwen2.5-7B-Instruct Q4_K_M GGUF file (any source; set `REF_GGUF` to its path). Then:

```bash
cd reference_agents
REF_GGUF=/path/model.gguf PYTHONPATH=. python common/gguf_llm_server.py &   # OpenAI-compatible, :8008, temperature 0
PYTHONPATH=../src python -m agentest.real.live --agent a05             # canon + adversarial set
PYTHONPATH=../src python -m agentest.real.live --agent a05 --set b1    # extra probe sets (b1, b2)
python ../scripts/translate_probes.py                                  # regenerate Hindi/Tamil probes (local model)
```

Run one agent at a time, because the 7B model uses about 5 GB of RAM. Then regenerate the matrix and commit the episodes so CI can replay them.

## 7. CI

`.github/workflows/ci.yml` runs ruff, `scripts/check_catalog_pins.py` (sha256 pins of the vendored CSVs), `pytest`
(which includes the offline replay and an exact match against `fixtures/real/results.json`) and `agentest real`.
CI never calls a model.

## 8. Extending the tests

- **New catalogue-style check:** add the ID and description to `real/ids.py`, a mini-world scenario to `samples/worlds.py`
  (the ladder agents must pass and `eager` must fail), an expectation in `profiles/_lib/samples.yaml`, and either a built-in
  generic check in `model/generic.py` or per-agent expectations in the profiles. Never name an agent in check code
  (`test_check_code_names_no_agent` enforces this). Then run `python scripts/gen_test_docs.py`.
- **Contract:** every ID must have at least one passing and one failing agent (`tests/real/test_v2_matrix.py` enforces this).
- **Heuristics:** if a check reads free text, say so in its doc and keep it a regex or keyword rule. Do not add a model judge
  unless it is documented as uncalibrated.

## 9. FAQ

**Is this a benchmark or a certification?** No. It is a test harness. The catalogue is informed by ISO/IEC 42001 themes; this is not certification.

**Why recorded episodes instead of calling the model in CI?** CI should be deterministic, free and offline. Re-record when an agent changes.

**k is small. Can I trust a pass?** A pass is evidence, not proof. Increase `rep` in the probes for flakiness work.

**Why are some cells n/a?** The agent has no such surface (for example no memory store), or the Hindi/Tamil back-translation failed the fidelity gate.

**How good are the Hindi/Tamil probes?** They are machine-translated by the same local 7B model and back-translated, which makes them a heuristic. The Tamil quality is poor, so the fidelity gate marks those cells n/a.

**Does it need a network?** Not at test time. It never needs an account or token.

**Contact:** srinivas AT testAIng.com

## 10. References

How each concept maps to its original source. Per-test lists are in `docs/tests/<ID>.md`; the master list is
`src/agentest/refs.py` (rendered in [`docs/REFERENCES.md`](docs/REFERENCES.md)).

**Testing method.** The checks are deterministic oracles over observed state and metamorphic relations:
- Barr, E. T., Harman, M., McMinn, P., Shahbaz, M., Yoo, S. (2015). *The Oracle Problem in Software Testing: A Survey.* IEEE TSE 41(5). [doi:10.1109/TSE.2014.2372785](https://doi.org/10.1109/TSE.2014.2372785)
- Hoare, C. A. R. (1969). *An axiomatic basis for computer programming.* CACM 12(10). [doi:10.1145/363235.363259](https://doi.org/10.1145/363235.363259)
- Chen, T. Y., Cheung, S. C., Yiu, S. M. (1998/2020). *Metamorphic Testing: A New Approach for Generating Next Test Cases.* [arXiv:2002.12543](https://arxiv.org/abs/2002.12543)
- Segura, S., Fraser, G., Sanchez, A. B., Ruiz-Cortés, A. (2016). *A Survey on Metamorphic Testing.* IEEE TSE 42(9). [doi:10.1109/TSE.2016.2532875](https://doi.org/10.1109/TSE.2016.2532875)

**Agent evaluation (multi-run reliability, trajectories, tool risk).**
- Yao, S., Shinn, N., Razavi, P., Narasimhan, K. (2024). *τ-bench: A Benchmark for Tool-Agent-User Interaction in Real-World Domains.* [arXiv:2406.12045](https://arxiv.org/abs/2406.12045)
- Kim, W., Park, S., In, Y., et al. (2025). *Beyond the Final Answer: Evaluating the Reasoning Trajectories of Tool-Augmented Agents* (TRACE). [arXiv:2510.02837](https://arxiv.org/abs/2510.02837)
- Ruan, Y., Dong, H., Wang, A., et al. (2023). *Identifying the Risks of LM Agents with an LM-Emulated Sandbox* (ToolEmu). [arXiv:2309.15817](https://arxiv.org/abs/2309.15817)
- Liu, X., Yu, H., Zhang, H., et al. (2023). *AgentBench: Evaluating LLMs as Agents.* [arXiv:2308.03688](https://arxiv.org/abs/2308.03688)
- Ma, C., Zhang, J., Zhu, Z., et al. (2024). *AgentBoard: An Analytical Evaluation Board of Multi-turn LLM Agents.* [arXiv:2401.13178](https://arxiv.org/abs/2401.13178)

**Prompt injection (T4).**
- Greshake, K., Abdelnabi, S., Mishra, S., Endres, C., Holz, T., Fritz, M. (2023). *Not What You've Signed Up For: Compromising Real-World LLM-Integrated Applications with Indirect Prompt Injection.* AISec '23. [doi:10.1145/3605764.3623985](https://doi.org/10.1145/3605764.3623985) · [arXiv:2302.12173](https://arxiv.org/abs/2302.12173)
- Perez, F., Ribeiro, I. (2022). *Ignore Previous Prompt: Attack Techniques For Language Models.* [arXiv:2211.09527](https://arxiv.org/abs/2211.09527)
- Liu, Y., Deng, G., Li, Y., et al. (2023). *Prompt Injection attack against LLM-integrated Applications.* [arXiv:2306.05499](https://arxiv.org/abs/2306.05499)
- Zhan, Q., Liang, Z., Ying, Z., Kang, D. (2024). *InjecAgent: Benchmarking Indirect Prompt Injections in Tool-Integrated Large Language Model Agents.* [arXiv:2403.02691](https://arxiv.org/abs/2403.02691)
- Debenedetti, E., Zhang, J., Balunović, M., et al. (2024). *AgentDojo: A Dynamic Environment to Evaluate Prompt Injection Attacks and Defenses for LLM Agents.* [arXiv:2406.13352](https://arxiv.org/abs/2406.13352)
- Yi, J., Xie, Y., Zhu, B., et al. (2023). *Benchmarking and Defending Against Indirect Prompt Injection Attacks on Large Language Models.* [arXiv:2312.14197](https://arxiv.org/abs/2312.14197)
- Hines, K., Lopez, G., Hall, M., et al. (2024). *Defending Against Indirect Prompt Injection Attacks With Spotlighting.* [arXiv:2403.14720](https://arxiv.org/abs/2403.14720)

**Multilingual and fairness probes (T7).**
- Yong, Z.-X., Menghini, C., Bach, S. H. (2023). *Low-Resource Languages Jailbreak GPT-4.* [arXiv:2310.02446](https://arxiv.org/abs/2310.02446)
- Deng, Y., Zhang, W., Pan, S. J., Bing, L. (2023). *Multilingual Jailbreak Challenges in Large Language Models.* [arXiv:2310.06474](https://arxiv.org/abs/2310.06474)
- Garg, S., Perot, V., Limtiaco, N., et al. (2019). *Counterfactual Fairness in Text Classification through Robustness.* AIES 2019. [doi:10.1145/3306618.3317950](https://doi.org/10.1145/3306618.3317950)
- Parrish, A., Chen, A., Nangia, N., et al. (2021). *BBQ: A Hand-Built Bias Benchmark for Question Answering.* [arXiv:2110.08193](https://arxiv.org/abs/2110.08193)

**Standards and regulation (themes only, not compliance claims).**
- OWASP Top 10 for LLM Applications 2025. *LLM01:2025 Prompt Injection.* <https://genai.owasp.org/llmrisk/llm01-prompt-injection/>
- OWASP Top 10 for LLM Applications 2025. *LLM02:2025 Sensitive Information Disclosure.* <https://genai.owasp.org/llmrisk/llm022025-sensitive-information-disclosure/>
- OWASP Top 10 for LLM Applications 2025. *LLM06:2025 Excessive Agency.* <https://genai.owasp.org/llmrisk/llm062025-excessive-agency/>
- OWASP GenAI Security Project. *OWASP Top 10 for Agentic Applications for 2026.* <https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/>
- NIST (2023). AI 100-1 *Artificial Intelligence Risk Management Framework (AI RMF 1.0).* [doi:10.6028/NIST.AI.100-1](https://doi.org/10.6028/NIST.AI.100-1) · <https://www.nist.gov/itl/ai-risk-management-framework>
- Regulation (EU) 2024/1689 (Artificial Intelligence Act); Art. 14 human oversight. <https://eur-lex.europa.eu/eli/reg/2024/1689/oj/eng>
- ISO/IEC 42001:2023 *Information technology — Artificial intelligence — Management system.* <https://www.iso.org/standard/81230.html>
- Regulation (EU) 2016/679 (GDPR), Art. 5(1)(c), 7(3), 17. <https://eur-lex.europa.eu/eli/reg/2016/679/oj>

**Reference-agent stack (official docs).**
- Model Context Protocol specification 2025-06-18, *Tools.* <https://modelcontextprotocol.io/specification/2025-06-18/server/tools>
- LangGraph docs. *Interrupts* (human-in-the-loop). <https://docs.langchain.com/oss/python/langgraph/interrupts>
- LangGraph docs. *Persistence* (checkpoints, durable resume). <https://docs.langchain.com/oss/python/langgraph/persistence>
- OpenAI Agents SDK docs. *Handoffs.* <https://openai.github.io/openai-agents-python/handoffs/>
- OpenAI Agents SDK docs. *Guardrails.* <https://openai.github.io/openai-agents-python/guardrails/>
- Qwen Team (2024). *Qwen2.5 Technical Report.* [arXiv:2412.15115](https://arxiv.org/abs/2412.15115)
- ggml-org. *llama.cpp* (GGUF inference, OpenAI-compatible server). <https://github.com/ggml-org/llama.cpp>

**Test IDs.** The catalogue IDs and their text come from the author's own taxonomy and catalogue:
- Padmanabhuni, S. (2026). *Agentic AI Assurance Test Taxonomy v1.* Zenodo. [doi:10.5281/zenodo.23587407](https://doi.org/10.5281/zenodo.23587407) — source of the test IDs only
- Padmanabhuni, S. (2026). *Agentic AI Assurance Test Catalogue — Consolidated Edition (All 110 Tests, T1–T7).* Zenodo. [doi:10.5281/zenodo.23614376](https://doi.org/10.5281/zenodo.23614376) — source of the test text only
