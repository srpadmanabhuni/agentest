# Expected-fail scenarios (complexity 11–15)

> **Historical (pre-v3).** This page describes code that was removed in v3.1.0; it is kept for the record. The
> implementation is at the `v1.0.0` / `v2.0.0` tags. Current docs: [User Guide](../USER-GUIDE.md), [Author Guide](../AUTHOR-GUIDE.md).

Teaching-negative agents. Each is **partial fail** by design: enough PASS that
learners see functional competence, enough FAIL that a suite’s oracles visibly
catch the anti-pattern. Implementation: `play_selective` in
`samples/playbook.py` — golden playbook everywhere except a documented
`FAIL_IDS` set (those call `CaseSpec.broken`).

They are listed in `MATRIX_EXPECTED_FAIL` and **excluded** from
`MATRIX_MUST_PASS`. `agentest matrix` exit code ignores their failures.

## 11. `leaky` — privacy anti-pattern

**FAIL_IDS:** all `PRIVACY_IDS`  
**Teaches:** soft-delete vs hard-delete, verify-before-disclose, tenant fences,
PII in tool args / email body, post-revoke share, paraphrase leakage.

```bash
agentest run --suite privacy --agent leaky          # expect all FAIL
agentest run --suite functional --agent leaky       # expect all PASS
```

## 12. `hallucinator` — explainability anti-pattern

**FAIL_IDS:** all `EXPLAINABILITY_IDS`  
**Teaches:** `api_success` without `db.write`, invented `cited_steps`, missing
tool `reason`, silent `memory.read`, explanation that names tools never called.

Note: `T3-006` is also listed under the orchestration suite, so the matrix
counts that CaseSpec twice when both suites run.

```bash
agentest run --suite explainability --agent hallucinator
```

## 13. `biased` — fairness anti-pattern

**FAIL_IDS:** all `BIAS_FAIRNESS_IDS`  
**Teaches:** metamorphic label skew (Hinglish / Spanish asymmetry, demographic
flip) while other suites stay green.

```bash
agentest run --suite bias_fairness --agent biased
```

## 14. `overreach` — orchestration / authz anti-pattern

**FAIL_IDS:** all `ORCHESTRATION_IDS`  
**Teaches:** trust handover prose, ambient authority, skip HITL, replay
single-use approval, ignore session TTL / role downgrade.

```bash
agentest run --suite orchestration --agent overreach
```

## 15. `flaky_plan` — planning / handoff half-done

**FAIL_IDS:** `T2-001`, `T2-003`, `T2-009`, `T2-013`, `T6-006`, `T2-004`, `T3-010`  
**Teaches:** skipping DEPENDS_ON / `todo.plan`, wrong tool order, incomplete
todo repair, disbursing without plan, replaying approval. Deterministic — not
a random flake; “flaky” here means the *plan* is incomplete.

```bash
agentest run --suite functional --ids T2-001,T6-006 --agent flaky_plan
agentest run --suite orchestration --ids T2-004,T3-010 --agent flaky_plan
```

## Matrix expectation (illustrative)

| Agent | cx | Approx. matrix |
|:------|---:|:---------------|
| `leaky` | 11 | **34/42** pass (8 privacy fails) |
| `hallucinator` | 12 | **36/42** pass (5 explain + T3-006 double-count → 6 fails) |
| `biased` | 13 | **39/42** pass (3 bias fails) |
| `overreach` | 14 | **33/42** pass (8 orch + T3-006 double-count → 9 fails) |
| `flaky_plan` | 15 | **35/42** pass (7 planning fails) |

Exact numbers: `agentest matrix --json`.
