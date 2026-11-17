# agentest roadmap

This is a forward-looking plan, not a commitment. Items may move or change as we learn from real traces. It starts from the current release (v3.3.2) and covers only the open-source checks, dataset, evidence and adapters. Every item follows three rules: it stays zero cost (open-weights models and free tooling only), standards output is test coverage mapping and never a compliance percentage, and only verified control codes from `src/agentest/standards/standards_map.yaml` are used.

Install: `pip install agentest-ai` (until the PyPI release is live, install from the GitHub tag as shown in the README).

## How the roadmap is organised

Two tracks run **in parallel, starting now**. Neither waits for the other.

- **Track A, complete the 130.** Finish the 110-test checklist plus the 20 repo extensions (X-001 to X-020) in offline OpenTelemetry mode, measure them on the reference agents and the train and held-out agents, and keep Hugging Face and GitHub in sync. Versions v3.4 and v3.5.
- **Track B, new check families (in progress now).** Red teaming, privacy, the five responsible-AI additions, and the gap areas (multi-agent, bias, explainability, PHI, data minimisation, consent). Design, scenarios and rules are being built now. They are not gated on Track A finishing, on the PyPI release or on the current measurement milestone. Release version numbers (v4.x) follow the Track A numbering, and each family is released when it passes the same blind gate as every other check.

Gates for every check, in both tracks: blind, label-locked evaluation; no tuning on held-out data; checks stay agent- and framework-agnostic; no check edits test data, specs or locked traces to pass.

## Where we are (v3.3.2)

All 130 checks have a real rule. Each rule is a pure function of recorded OTLP traces, the agent's published metadata (A2A AgentCard, MCP tool list, optional governance extension) and test-side input families. No rule calls the network or a model judge. Every one of the 130 returns pass or fail (not n/a) on at least two GitHub reference agents (`docs/COVERAGE.md`).

Offline OpenTelemetry readiness of the 130, from an audit of `src/agentest/standards/rules.py`:

| Status | Checks | Meaning |
|---|---:|---|
| Offline-ready | 61 | Decided from standard GenAI spans plus AgentCard, MCP and governance metadata. A governance field that is absent gives n/a, never a guess. |
| Offline with extra trace attributes | 53 | Judged offline, but the trace must carry `agentest.*` attributes or spans (approval spans, state-change effects, tool reasons, citations, handoff source, input-family tags, canaries). |
| Needs recorded re-runs | 16 | Judged offline, but the corpus must contain paired or repeated executions recorded beforehand (metamorphic relations, repeats, twin and replay submissions, severity pairs). |
| Needs a model judge | 0 | No rule requires a judge. About 20 rules use text heuristics where a semantic judge would be stronger. |
| Not implemented | 0 | None. T4-016 (image-borne injection) is the thinnest: it reuses the text canary rule and does not inspect image content. |

So the answer to "can all 130 run in offline OpenTelemetry mode" is yes for judging: every check runs from recorded traces plus metadata with no network. A plain production trace is enough for the 61 offline-ready checks only when the agent publishes the metadata they read. The other 69 need richer recordings, which Track A turns into a documented requirement.

## Track A: complete the 130

### v3.4: all 130 decidable offline from OTel recordings

- **Trace attribute profile.** A per-check specification of exactly which spans, attributes, metadata fields and probe inputs each check needs, published next to `docs/standards/EXTENSION.md`, plus a `std` command that reads a trace set and reports, per check, "decidable" or "n/a because attribute X is missing". Size M.
- **Close the 53 attribute-dependent checks.** Document each `agentest.*` attribute against the OTel GenAI conventions (status: Development), prefer standard attributes where one exists, and ship importer and wrapper support that emits the rest for the supported frameworks. Size L.
- **Probe recorder for the 16 re-run checks.** A framework-agnostic recorder that executes the paired and repeated probe inputs once and stores them as ordinary OTLP traces, so judging stays offline and deterministic. Size M to L.
- **Strengthen partial and heuristic checks.** Make T4-016 inspect non-text input parts, publish per-check false-alarm and miss rates for the heuristic checks, and define an optional, off-by-default judge hook that never changes default offline results. Size M.
- **Keep every check decided.** CI keeps `docs/COVERAGE.md` current (`scripts/coverage_table.py --check`) so no check silently becomes always-n/a. Size S.

### v3.5: measured quality, train/test agents, and Hugging Face / GitHub in sync

- **Precision and recall on the reference agents and on the train and held-out agents**, per check, using blind label-locked evaluation. Labels are locked before predictions, held-out batches are never used to tune, and fix work never sees fresh data. Results are published in the repository and Hugging Face docs, not in posts.
- **One agent set on both platforms.** Reconcile the reference-agent set between this repository (`agents/`) and the Hugging Face reference-agents repository, with one documented train, dev and held-out split and one source of truth for agent counts.
- **One version story.** Align the dataset card, reference-agents card and this repository on the release version, the 130-check count, the agent count and the status of the five responsible-AI additions (their rules are already in this repository as opt-in).
- **PyPI release of `agentest-ai`** once the measured-quality gate is met. The upload itself stays with the maintainer. Size S.
- **Golden cases beyond the core set**: pass and fail trace pairs for every remaining assessable rule, built with free, open-weights models only. Size L.

### Adapters and docs (alongside v3.4 and v3.5)

- **smolagents adapter**, the same pattern as the LangGraph one (an importer dialect plus an optional wrapper, no new runtime dependencies). Size S to M.
- **Coverage-mapping JSON**: `agentest std run --format coverage-json` reports the number of mapped tests and the pass/fail count for each control, drawn from `src/agentest/standards/standards_map.yaml` (OWASP LLM and Agentic, NIST AI RMF and AI 600-1, ISO/IEC 42001 Annex A, MITRE ATLAS). Every report carries the disclaimer "test coverage, not a compliance determination". Size S to M.
- **Standards landing pages** under `docs/standards/` (OWASP Agentic, NIST AI RMF, ISO/IEC 42001, and an EU AI Act page only once its mappings are verified), linking to the Hugging Face catalogue files. Size S.
- **PyPI project description** for `agentest-ai`. Size S.
- **Agent playground Space**: drop in a trace and get a scorecard, extending the existing demo and viewer Spaces. Size M.
- **P0 smoke results across agent frameworks**, with a reproducible harness and open-weights models only. Each framework's maintainers get a heads-up before results are published. Size L.
- **Integration docs for the LangChain and CrewAI ecosystems** and **regional positioning pages** (EU, US, APAC). Size M and S.

Already scheduled and tracked separately: the LangGraph flagship integration (`docs/integrations/langgraph.md`, `examples/langgraph_import/`), golden cases for the 38 assessable core tests (Hub config `golden_v2`), and published per-check false-alarm and miss rates.

## Track B: new check families (in progress now)

This is additional open-source check scope on top of the 130. It is **active now, in parallel with Track A**. It does not wait for Track A, for the PyPI release or for the current measurement milestone. Current coverage of the 130 by main topic shows where the gaps are:

| Main topic | Checks in the 130 |
|---|---:|
| Core agent evals | 48 |
| Red teaming and security | 45 |
| Compliance and governance | 15 |
| Privacy | 9 |
| Explainability | 7 |
| Bias and fairness | 3 |
| Data lineage | 3 |
| Multi-agent | 0 |

### Red teaming and privacy (first)

**Red teaming.** Prompt-injection and indirect-injection campaigns, tool-misuse and excessive agency, jailbreak resistance, multi-turn adversarial escalation, and MCP and tool poisoning. This includes an MCP shadow-tool scenario: a mock MCP server offers a look-alike, malicious tool next to the real one, and an assertion checks that the agent calls the legitimate tool.

**Privacy.** PII and PHI leakage in answers, tool arguments, logs and memory; data minimisation; cross-session and cross-user leakage; consent and retention; and secrets exposure. This includes PII injection scenarios (synthetic PII seeded into memory and tool outputs, with an assertion that it does not leak to the model, logs or external calls) and a token and env-var exfiltration scenario extending T4-002.

### Responsible-AI additions

The five additions from the dataset's `rai_additions` config already have rules in this repository, opt-in through `agentest std run --ids` and listed by `agentest list --opt-in`: T1-020 (undo through declared compensation), T1-021 (refusal explanation and escalation route), T3-018 (consent before acting on personal data), T3-019 (handoff to a human that runs and carries context) and T7-017 (persona fairness). Work now: validate them on blind label-locked data, then promote them into the default set.

### Gap families

- **Multi-agent**: handoff integrity, role and permission boundaries between agents, orchestrator conduct, and cross-agent injection.
- **Bias and fairness**: more demographic and persona metamorphic relations beyond the three current checks.
- **Explainability**: explanation-matches-action and reason-quality checks beyond the current seven.
- **PHI, data minimisation and consent**: health-data handling, collecting and passing only what a task needs, and consent capture and withdrawal.

### v4.x release outline (numbering follows Track A)

- **v4.0**: red-teaming and privacy check families, and the five responsible-AI additions promoted into the default set.
- **v4.1**: multi-agent, bias and fairness, explainability, and PHI, minimisation and consent families.
- **Later**: check packs for regulated industries (for example finance and healthcare) once the community is established.

New families use the same offline OpenTelemetry mode, the same trace attribute profile and the same blind gate as Track A. Anything built from client data or client traces stays out of the open repository.

Suggestions are welcome through GitHub issues and discussions.
