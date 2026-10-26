# Architecture

## Dual-repo

1. **catalogue** — stable IDs, acceptance criteria, fixtures notes (CC BY 4.0).
2. **This runner** — CLI, mock gateway, oracles, CI (Apache-2.0).

## Core types

- `Env` / `Ledger` — ledger, contacts, counters, users, orders, inventory, tickets, notify, multi-turn `AgentState`
- `Env.snapshot` / `Env.diff` — side-effect fence
- `Trace` / `ToolCall` — ordered tool calls + `claims_success` + `succeeded`
- `ToolGateway` — mock tools; `WRITE_TOOLS` / `READ_TOOLS` / orchestration tools
- `ApprovalsStore` / `env.role` / `env.clock` — handoff + HITL + TTL
- `agentest.policy.permits` / `HIGH_PRIV` — authz oracles
- `Result` — `pass` | `fail` | `unverified`

## Cases

Each catalogue ID is a `CaseSpec` (`make_env`, `golden`, `broken`, `oracle`) in `agentest.cases`.  
`FUNCTIONAL_IDS` lists the 18-pack order; `PRIVACY_IDS` the 8-pack; `EXPLAINABILITY_IDS` the 5-pack; `BIAS_FAIRNESS_IDS` the 3-pack (`--suite bias_fairness`, alias `bias`); `ORCHESTRATION_IDS` the 8-ID theme pack (`--suite orchestration`, alias `orch`) — catalogue pack `packs/orchestration.csv`; T3-006 CaseSpec reused from explainability. Multi-run IDs (T1-002, T1-003) use `cases.multi_run`.  
Privacy extends Env with profiles, multi-tenant stores, consent, exports/emails, and mask oracles.

## Constraints

- No third-party eval frameworks
- Deterministic scripted agents (no LLM in the harness loop)
- Broken-agent contract on every ID before merge

## Sample agents (teaching)

Fifteen complexity-graded agents under `agentest.samples` (`noop` → `flaky_plan`).  
Green ladder 1–10; expected-fail band 11–15 (`leaky`…`flaky_plan`).  
See [`docs/SAMPLE-AGENTS.md`](SAMPLE-AGENTS.md), [`SCENARIOS-EXPECTED-FAIL.md`](SCENARIOS-EXPECTED-FAIL.md).  
CLI: `agentest samples [--failing]`, `agentest matrix`,  
`agentest run --agent noop|…|federation|leaky|hallucinator|biased|overreach|flaky_plan`.  
`golden`/`broken` remain the oracle Pass/Fail fixtures.  
`MATRIX_MUST_PASS` ignores expected-fail agents for matrix exit status.

## Real-check layer (`src/agentest/real/`)

```
ids.py        130 IDs: REAL_IDS (41 pack IDs) + BATCH1/2/3 (69) = CATALOGUE_IDS (110) + X_IDS (20); what(id)
probes.py     AGENT_DIRS + canon/adversarial PROBES per reference agent
probes2.py    extra probe sets b1 (metamorphic, translation, quoting) and b2 (hidden text, slots, secrets, twin resume)
live.py       records episodes from reference agents against the local model (not used in CI)
report.py     build() -> {agent: {id: R}} via agentest.model.generic.evaluate; markdown/JSON writers
```

Sample-agent scenarios: `cases/` (41 pack IDs, `CaseSpec.record`) and `samples/worlds.py` (89 mini-worlds) record
end-state snapshots; they hold no verdict logic.

Flow (v2.0.0): `live.py` → `fixtures/real/episodes/*.jsonl` → `model.adapters.adapt` (standard trace) →
`model.generic.evaluate(profile, episodes)` → `report.build` → `RESULTS.md` / `results.json`. A profile expectation
for an ID is authoritative; otherwise the built-in generic check applies, and it returns `n/a` when the profile does
not declare the surface it needs. Translation fidelity for Hindi/Tamil probes is gated by `MT_GATE_KINDS` in the
agent's profile: required keywords must survive the back-translation (a keyword heuristic).

## References

- Oracle design (state-based oracles, golden/broken contract): Barr, E. T., Harman, M., McMinn, P., Shahbaz, M., Yoo, S. (2015). *The Oracle Problem in Software Testing: A Survey.* IEEE TSE 41(5). [doi:10.1109/TSE.2014.2372785](https://doi.org/10.1109/TSE.2014.2372785)
- Metamorphic relations (T7, X-018): Chen, T. Y., Cheung, S. C., Yiu, S. M. (1998/2020). *Metamorphic Testing: A New Approach for Generating Next Test Cases.* [arXiv:2002.12543](https://arxiv.org/abs/2002.12543)
- Repeated-trial reliability (T1-002/003, T7-008): Yao, S., Shinn, N., Razavi, P., Narasimhan, K. (2024). *τ-bench: A Benchmark for Tool-Agent-User Interaction in Real-World Domains.* [arXiv:2406.12045](https://arxiv.org/abs/2406.12045)
- Trajectory-level evaluation (explainability, T5-015): Kim, W., Park, S., In, Y., et al. (2025). *Beyond the Final Answer: Evaluating the Reasoning Trajectories of Tool-Augmented Agents* (TRACE). [arXiv:2510.02837](https://arxiv.org/abs/2510.02837)
- Mock tool gateway / sandboxed tool risk: Ruan, Y., Dong, H., Wang, A., et al. (2023). *Identifying the Risks of LM Agents with an LM-Emulated Sandbox* (ToolEmu). [arXiv:2309.15817](https://arxiv.org/abs/2309.15817)
- Tool interface of the MCP-based reference agents (a07, a08): Model Context Protocol specification 2025-06-18, *Tools.* <https://modelcontextprotocol.io/specification/2025-06-18/server/tools>
- Local model used for recording: Qwen Team (2024). *Qwen2.5 Technical Report.* [arXiv:2412.15115](https://arxiv.org/abs/2412.15115); runtime ggml-org. *llama.cpp* (GGUF inference, OpenAI-compatible server). <https://github.com/ggml-org/llama.cpp>
- Test IDs: Padmanabhuni, S. (2026). *Agentic AI Assurance Test Taxonomy v1.* Zenodo. [doi:10.5281/zenodo.23587407](https://doi.org/10.5281/zenodo.23587407) — source of the test IDs only
