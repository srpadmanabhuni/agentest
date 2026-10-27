# Sample agents (complexity 1–15)

> **Historical (pre-v3).** This page describes code that was removed in v3.1.0; it is kept for the record. The
> implementation is at the `v1.0.0` / `v2.0.0` tags. Current docs: [User Guide](USER-GUIDE.md), [Author Guide](AUTHOR-GUIDE.md).

Fifteen **deterministic** teaching agents live under `src/agentest/samples/`.  
They are **additional** to the oracle fixtures `golden` / `broken`.

Catalogue (design authority): Agentic AI Test Checklist 110 in the published catalogue · catalogue USER-GUIDE.md.

## Green ladder (1–10)

| name | cx | idea | expected matrix |
|:-----|---:|:-----|:----------------|
| `noop` | 1 | Claims success, **zero** real tools; forges bad orch traces | 41 unique IDs: 32 FAIL, 8 vacuous PASS, 1 UNVERIFIED (matrix 8/42 pass) |
| `eager` | 2 | Calls tools but ignores order, fences, authz, TTL, HITL | **FAIL** on all 41 (matrix 0/42) |
| `scripted` | 3 | Hardcoded playbook: `get_case(id).golden(env)` | **all PASS** |
| `policy` | 4 | Rule-engine over `samples/policies/*` (incl. orchestration) | **all PASS** |
| `reflective` | 5 | Policy + faithful explanations / bias | **all PASS** |
| `supervisor` | 6 | Planner: approvals, signed handoff contract, downgrade, TTL | **all PASS** |
| `handoff` | 7 | Receiver: store≠prose, authz.decide, no ambient admin, TTL | **all PASS** |
| `planner` | 8 | **Plan-then-act**: `todo.plan` / DEPENDS_ON before side effects; HITL | **all PASS** |
| `critic` | 9 | **Generate–critique–repair** before `claims_success`; faithful explain fields | **all PASS** |
| `federation` | 10 | **Multi-tenant federation**: tenant fence + downgrade + TTL + single-use | **all PASS** |

Matrix totals sum suites (`functional`+`privacy`+`explainability`+`bias_fairness`+`orchestration`).  
T3-006 appears in both explainability and orchestration thematic lists (one CaseSpec).

## Expected-fail scenarios (11–15)

Five **teaching-negative** agents: each reuses the golden playbook for most IDs,
then deliberately runs the case **broken** sequence on a category (or planning
subset). Oracles catch real mistakes while the rest of the matrix stays green.

| name | cx | teaches | fail focus | typical matrix |
|:-----|---:|:--------|:-----------|:---------------|
| `leaky` | 11 | Privacy | all `PRIVACY_IDS` (8) | 34/42 pass |
| `hallucinator` | 12 | Explainability / faithfulness | all `EXPLAINABILITY_IDS` (5; T3-006 double-counted in matrix) | 36/42 pass |
| `biased` | 13 | Bias / fairness | all `BIAS_FAIRNESS_IDS` (3) | 39/42 pass |
| `overreach` | 14 | Orchestration / authz | all `ORCHESTRATION_IDS` (8; T3-006 double-counted) | 33/42 pass |
| `flaky_plan` | 15 | Planning / handoff half-done | T2-001/003/009/013, T6-006, T2-004, T3-010 | 35/42 pass |

These five are in `MATRIX_EXPECTED_FAIL` and **not** in `MATRIX_MUST_PASS`.  
`agentest matrix` exit status still only requires the green ladder (+ golden).

See [`SCENARIOS-EXPECTED-FAIL.md`](SCENARIOS-EXPECTED-FAIL.md).

## Why fifteen levels?

1. **noop** — Success flags ≠ terminal/authz truth.
2. **eager** — Classic fails: wrong order, hard-delete, trust handover prose, skip HITL, immortal session.
3. **scripted** — Playbook reuses case goldens.
4. **policy** — Shared rules including `orchestration_rules.py`.
5. **reflective** — Explainability + bias on top of policy.
6. **supervisor** — Multi-agent planner / HITL grantor.
7. **handoff** — Receiving worker with independent authz.
8. **planner** — Explicit plan recorded before irreversible tools (T2-* + T2-004).
9. **critic** — Self-critique loop repairs incomplete explainability before success.
10. **federation** — Hardest green: session tenant + no ambient authority + TTL + single-use together.
11. **leaky** — Privacy oracles fire while functional still passes.
12. **hallucinator** — Faithfulness oracles fire (fake citations / api_success).
13. **biased** — Metamorphic fairness oracles fire on skewed labels.
14. **overreach** — Orch/authz oracles fire (ambient authority, skip HITL).
15. **flaky_plan** — Plan/DEPENDS_ON/HITL subset fails; other suites mostly OK.

## Scenarios 8–10 (detail)

See [`SCENARIOS-8-10.md`](SCENARIOS-8-10.md) for teaching notes on planner / critic / federation.

## Per-agent detail (scenario · design · tests · why · references)

Each agent's module docstring in `src/agentest/samples/<name>.py` has the full text. Citations are verified in [`REFERENCES.md`](REFERENCES.md). All agents are deterministic code with no LLM, so a reference names the *pattern* the agent imitates. It does not mean the paper's method is reproduced.

| # | agent | scenario & design | tests exercised → expected | why / references |
|--:|:--|:--|:--|:--|
| 1 | `noop` | Returns `claims_success=True` with no tool calls. Forges traces for orchestration IDs. | 32 FAIL; 8 PASS vacuously on an empty trace (T2-001/003/009/013, T5-012, T2-005, T4-009, T5-004); T5-015 UNVERIFIED. | A success flag is not evidence. See the test-oracle problem (Barr et al. 2015) and postconditions (Hoare 1969). |
| 2 | `eager` | Calls real tools but breaks the constraints: wrong order, hard delete, disclose before verify, duplicate single-shot calls, writes on read-only tasks, trusts handover prose, skips HITL. | All suites → mostly FAIL. | Shows excessive agency (OWASP LLM06) and broken least privilege (Saltzer & Schroeder 1975). |
| 3 | `scripted` | Replays each case's golden trajectory (`playbook.py`). | Every ID → PASS. | Baseline that proves the oracles accept correct behaviour. |
| 4 | `policy` | A rule engine over `samples/policies/*` for the functional, privacy, explain, bias and orchestration rules. | Every ID → PASS. | Explicit, auditable rules (least privilege, complete mediation; ISO/IEC 42001 Annex A). |
| 5 | `reflective` | Runs the policy rules, then `enrich_explainability()` fills explanation, cited_steps and memory_citations **only from steps that actually ran**. | Every ID → PASS, including all explainability and bias IDs. | Faithful by construction (Jacovi & Goldberg 2020). The post-hoc self-inspection loosely mirrors Reflexion (Shinn et al. 2023). |
| 6 | `supervisor` | A planner/grantor that issues approvals, writes a signed handoff contract, downgrades the receiver's role and sets the session TTL. | Orchestration natively, everything else via reflective → PASS. | Human oversight (EU AI Act Art. 14) and single-use grants (RFC 6749 §4.1.2). |
| 7 | `handoff` | The receiving worker. It ignores approval claims in prose, checks the approvals store, logs an independent `authz.decide`, refuses ambient authority, and enforces TTL and single-use tokens. | T3-001/002/006/007/010/011/014 and T2-004 → PASS. | Confused deputy (Hardy 1988), indirect prompt injection (Greshake et al. 2023), session management (NIST SP 800-63B). |
| 8 | `planner` | Records a `todo.plan` whose step order is a valid DEPENDS_ON linearisation **before** acting. A guard refuses irreversible tools until a plan exists. | T2-001/003/009/013, T6-006, T2-004 natively → PASS. | Plan-and-Solve (Wang et al. 2023) as code. Ordering is a topological sort (Kahn 1962). |
| 9 | `critic` | Writes a deliberately incomplete draft, logs a critique step that names what is missing, then repairs only trace-faithful fields before claiming success. | T1-018, T3-006, T5-015, T6-007, T7-009 → PASS. | Self-Refine (Madaan et al. 2023) and Reflexion-style feedback, done as rule-based critique. |
| 10 | `federation` | Multi-tenant federation: session-tenant fence on writes and exports, no ambient authority, role downgrade, TTL and single-use approvals combined. | T3-008, T5-011 and orchestration IDs → PASS. | Least privilege and capability-style authority (Saltzer & Schroeder; Hardy). |
| 11 | `leaky` | Golden everywhere except `PRIVACY_IDS`, where the broken sequence runs. | Fails 8 privacy IDs, passes the rest. | Shows privacy oracles fire on their own. NIST SP 800-122, GDPR, Greshake et al. 2023. |
| 12 | `hallucinator` | Broken sequence on `EXPLAINABILITY_IDS`: api_success without the write, missing reasons, silent memory use, invented tools. | Fails 5 explainability IDs (T3-006 is double-counted). | Unfaithful explanations are caught against the trace (Jacovi & Goldberg 2020; ReAct). |
| 13 | `biased` | Broken sequence on `BIAS_FAIRNESS_IDS`: Hinglish bypass, name flip, Spanish asymmetry. | Fails 3 bias IDs. | Metamorphic testing (Chen et al. 1998) and counterfactual token fairness (Garg et al. 2019). |
| 14 | `overreach` | Broken sequence on `ORCHESTRATION_IDS`. | Fails 8 orchestration IDs. | Confused deputy, excessive agency, missing human oversight. |
| 15 | `flaky_plan` | Broken sequence on T2-001/003/009/013, T6-006, T2-004 and T3-010 (deterministic half-done planning). | Fails that subset. | Plan ordering and HITL-before-act are checked separately from final success. |

### Reading an oracle

Every oracle function in `src/agentest/cases/*.py` has a docstring with these parts:
**catalogue ID(s) → Algorithm (step by step) → Thresholds / rationale →
Pass / fail interpretation → Limitations → Attribution / References**. The first
reference line states whether the check applies a published method or is an
in-house heuristic.

## How to run

```bash
python -m venv .venv && source .venv/bin/activate
python -m pip install -e ".[dev]"

agentest samples
agentest samples --failing   # cx 11–15 only

agentest run --suite privacy --agent leaky
agentest run --suite explainability --agent hallucinator
agentest run --suite bias_fairness --agent biased
agentest run --suite orchestration --agent overreach
agentest run --suite functional --ids T2-001 --agent flaky_plan

agentest matrix
# Exit 0 iff scripted…federation/(golden) all-pass.
# noop/eager + leaky…flaky_plan failures are expected.
```

See [`ORCHESTRATION.md`](ORCHESTRATION.md) for catalogue ↔ runner mapping.

## Constraints

- No third-party eval frameworks.
- Deterministic scripted agents only (no LLM in the harness).
- Keep golden/broken oracles green.
- Do not add expected-fail agents to `MATRIX_MUST_PASS`.
