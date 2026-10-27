# Scenarios 8–10 — complex teaching agents

> **Historical (pre-v3).** This page describes code that was removed in v3.1.0; it is kept for the record. The
> implementation is at the `v1.0.0` / `v2.0.0` tags. Current docs: [User Guide](USER-GUIDE.md), [Author Guide](AUTHOR-GUIDE.md).

These three agents sit above supervisor/handoff. Each still **Passes** the full
matrix by composing `ReflectiveAgent` (and orch specialists) for IDs outside
their native focus.

## 8. `planner` — plan-then-act

**Idea:** Never call irreversible tools until an explicit plan is on the trace.

- Native focus: `T2-001`, `T2-003`, `T2-009`, `T2-013`, `T2-004`, `T6-006`, `T3-010`
- Pattern:
  1. `todo.plan(steps=[…])` — records DEPENDS_ON / HITL linearisation
  2. Guarded calls — `open_account` / `disburse` / `charge` / `refund.issue` raise
     if plan was skipped
  3. Execute topo / approval-before-act sequence
- Other IDs: compose `SupervisorAgent` (orch) or `ReflectiveAgent`

```bash
agentest run --suite functional --ids T2-001 --agent planner
agentest run --suite orchestration --ids T2-004 --agent planner
```

## 9. `critic` — generate–critique–repair

**Idea:** First pass may leave explainability incomplete; a critique step forces
repair **before** `claims_success`.

- Native focus: `T1-018`, `T3-006`, `T5-015`, `T6-007`, `T7-009`, `T1-013`
- Pattern:
  1. **Generate** — tools run; `claims_success=False`; fields often empty
  2. **Critique** — `log_debug(reason="critique", …)` names what is missing
  3. **Repair** — set `explanation`, `cited_steps`, `memory_citations`, `api_success`
     faithfully (cited steps ⊆ tools actually run)
  4. Only then `claims_success=True` (or leave False when the oracle expects deny)
- Other IDs: compose `ReflectiveAgent`

```bash
agentest run --suite explainability --agent critic
```

## 10. `federation` — multi-tenant / cross-agent

**Idea:** Hardest teaching agent — session tenant, no ambient authority across
agents, and role downgrade + TTL + single-use approvals applied together.

- Native focus: `T3-008`, `T5-011`, `T3-001`, `T3-002`, `T3-007`, `T3-010`,
  `T3-011`, `T3-014`, `T2-004`
- Pattern highlights:
  - Cross-tenant write/export denied when `tenant_id != session_tenant_id`
  - Handover contract carries `tenant` + `ttl_min`; `session.set_ttl` +
    `session.set_role` after signed handoff
  - Peer “you are admin” claims never elevate role
  - Single-use `approval.grant` cannot be replayed
- Other IDs: compose `ReflectiveAgent`

```bash
agentest run --suite privacy --ids T3-008,T5-011 --agent federation
agentest run --suite orchestration --agent federation
```

## Matrix expectation

| Agent | cx | Matrix |
|:------|---:|:-------|
| `planner` | 8 | **42/42 PASS** |
| `critic` | 9 | **42/42 PASS** |
| `federation` | 10 | **42/42 PASS** |

`MATRIX_MUST_PASS` includes all three (plus scripted…handoff and golden).
