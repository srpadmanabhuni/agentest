# Changelog

All notable changes. Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow [SemVer](https://semver.org/).

## [Unreleased] - v2.0.0 (next version, `model-driven` branch; not released, not tagged)

Version string on this branch: `2.0.0.dev0`. `main` stays on v1.0.0.

### Added
- Model-driven, agent-independent checks (`agentest.model`, `agentest model run|parity|convert|generate|validate`):
  - standard trace format (`src/agentest/model/trace.schema.json` + dataclasses) aligned with the OpenTelemetry GenAI semantic conventions;
  - adapters for OpenAI Agents SDK, LangGraph (message list and node logs), AutoGen AgentChat, CrewAI, n8n, MCP-based agents, LlamaIndex and the in-process sample agents;
  - one YAML agent profile per agent in `profiles/` (40) describing tools and their read/write type, approval-required actions, recipients, limits, sensitive fields, languages, capabilities, observations, probe roles and success criteria;
  - 17 catalogue IDs ported to generic checks that read only (trace, profile); N/A comes from the profile;
  - deterministic generator of metamorphic and adversarial inputs from a profile;
  - `docs/model-driven/` (DESIGN, ADD-AN-AGENT walkthrough, PARITY vs v1) and `examples/model_driven/` (a new agent described only by YAML).
- The v1 per-agent checks (`agentest real`) are unchanged and still the reference.

## [1.0.0] - 2026-10-27

### Added
- `agentest check FILE.jsonl` - plug in your own agent: 13 trace-level checks over recorded episodes, `--md` / `--html` / `--json` reports, `--strict` exit code for CI.
- `agentest.byo.Recorder` helper and `examples/byo_agent/my_agent.py` (good and `--buggy` variants), `docs/BYO-AGENT.md`, sample reports in `docs/sample-report/`.
- Reference agents a13-a25 vendored (supervisor, map-reduce, plan-execute, MCP multi-server, multi-hop RAG, hierarchical crew, memory, debate, negotiation, guarded browser, n8n orchestrator, KYC flow, incident swarm) with 67 offline unit tests and recorded proofs; trace-level checks in `src/agentest/real/checks3.py`. Matrix is now 130 IDs x 40 agents.
- `agentest version`; wheel ships the catalogue and recorded episodes (`share/agentest`), located by `agentest.paths`.
- Package metadata (keywords, classifiers, project URLs).

### Changed
- `agentest real --episodes` defaults to the bundled episodes, so it works from any directory and from a wheel install.
- Version unified to 1.0.0 (`pyproject.toml` and `agentest.__version__` previously disagreed).

### Findings recorded by the new checks (agent defects, not runner bugs)
- a24: raw PAN appears in an internal LLM extraction step of the trace (X-020), although outputs are masked.
- a17, a22: same tool called 4x in a row with identical arguments in one case (X-004).
- a13, a15, a22: some tool calls lack a specific reason (X-003); a15 one call has none (T5-015).
- a14, a15, a17, a19: one recorded case fails its own scenario oracle (T1-001/T1-003); a15 executed a hold in that case (T1-018).

## [0.9.3a0] - 2026-10-26
- All 130 checks real (110 catalogue + X-001..X-020), per-test docs, GUIDEBOOK, references, `atc` alias.
