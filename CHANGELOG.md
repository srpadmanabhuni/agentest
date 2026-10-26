# Changelog

All notable changes. Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow [SemVer](https://semver.org/).

## [2.0.0] - 2026-10-27

Model-driven release: one generic engine judges all 130 IDs from the standard trace and the agent profile.
There is no agent-specific or test-specific check code. The v1 implementation stays available at tag `v1.0.0`.

### Added
- Model-driven, agent-independent checks (`agentest.model`, `agentest model run|parity|convert|generate|validate`):
  - standard trace format (`src/agentest/model/trace.schema.json` + dataclasses) aligned with the OpenTelemetry GenAI semantic conventions;
  - adapters for OpenAI Agents SDK, LangGraph (message list and node logs), AutoGen AgentChat, CrewAI, n8n, MCP-based agents, LlamaIndex and the in-process sample agents;
  - one YAML profile per agent in `profiles/` describing tools and their read/write type, approval-required actions, recipients, limits, sensitive fields, languages, capabilities, observations, probe roles, success criteria and per-ID expectations;
  - profile expectations: sandboxed `lambda E: ...` expressions (`model/expr.py`, `model/expect.py`), shared libraries in `profiles/_lib/` via `extends:`, per-agent `defs:`; an expectation is authoritative over the built-in generic check;
  - `profiles/_lib/samples.yaml`: the 41 pack-case oracles and 89 mini-world checks as expectations over recorded end-state snapshots (method notes kept in `expect_notes`);
  - pluggable adapters (`adapter: file:adapter.py`) and `examples/agnostic_demo/`;
  - deterministic generator of metamorphic and adversarial inputs from a profile;
  - `docs/model-driven/` (DEVELOPER-GUIDE, DESIGN, ADD-AN-AGENT, PARITY) and `scripts/loc_table.py`;
  - CI test `test_check_code_names_no_agent`: check code may not name an agent;
  - reference agents a26 onwards (profiles and recorded episodes; generic coverage only, no v1 baseline).

### Changed
- `agentest real`, `agentest check` and the packs are judged by the generic engine. Parity with v1.0.0 (40 agents x 130 IDs):
  382/382 v1 failures reproduced exactly, 1970 passes reproduced, 0 looser and 0 stricter cells, 60 cells with wording-only
  detail changes, 60 cells v1 left `n/a` now judged (58 pass, 2 fail). See `docs/model-driven/PARITY.md`.
- Sample scenarios (`cases/`, `samples/worlds.py`) only record end states; they contain no verdict logic.
- a08 (n8n) adapter: run-level tool calls with results are exposed as `final_state.run_tool_calls`.
- Per-test docs (`docs/tests/`) show the expectations that judge each ID.

### Removed
- v1 per-agent check modules: `real/checks.py`, `checks2.py`, `checks3.py`, `real/samples.py`, `real/synth.py`, `oracles/`
  and the per-case oracle functions. Use tag `v1.0.0` for that implementation.

### Findings (new in v2, to review)
- a07 T7-004: refusal differs across languages (English probe discloses customer emails).
- a17 T6-007: retrieval answers carry no citation in cases `case1`, `case2`.

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
