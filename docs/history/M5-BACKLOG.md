# M5 backlog — `v0.7.0a0` orchestration

> **Historical (pre-v3).** This page describes code that was removed in v3.1.0; it is kept for the record. The
> implementation is at the `v1.0.0` / `v2.0.0` tags. Current docs: [User Guide](../USER-GUIDE.md), [Author Guide](../AUTHOR-GUIDE.md).

**Orchestration** runner theme pack (8 catalogue IDs) + sample agents 6–7.

catalogue pack: `packs/orchestration.csv`.

## Tasks

1. [x] Sync `catalog/orchestration.csv` from the published catalogue packs
2. [x] Env + gateway: approvals store, actor/role, clock/TTL, handover notes, HIGH_PRIV tools
3. [x] `agentest.policy.permits` helper
4. [x] CaseSpec for T3-001, T3-002, T3-007, T3-010, T3-011, T3-014, T2-004
5. [x] Suite `--suite orchestration` / alias `orch` (includes T3-006 by reference)
6. [x] Sample agents `supervisor` (6) + `handoff` (7)
7. [x] Policy/reflective/scripted pass new IDs; noop/eager teach-fail
8. [x] pytest + CI golden orchestration + matrix
9. [x] `docs/ORCHESTRATION.md` + SAMPLE-AGENTS / ARCHITECTURE / README updates

## IDs

| ID | Status |
|:---|:-------|
| T3-001 | done (new) |
| T3-002 | done (new) |
| T3-006 | reused (explainability) |
| T3-007 | done (new) |
| T3-010 | done (new) |
| T3-011 | done (new) |
| T3-014 | done (new) |
| T2-004 | done (new) |

## Acceptance

- [x] `agentest run --suite orchestration --agent golden` exit 0
- [x] `agentest run --suite orchestration --agent broken` exit non-zero
- [x] `agentest samples` lists 7 agents
- [x] matrix: supervisor + handoff + scripted/policy/reflective/golden all-pass
- [x] prior suites still green
