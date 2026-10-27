# M1 backlog — `v0.2.0`

> **Historical (pre-v3).** This page describes code that was removed in v3.1.0; it is kept for the record. The
> implementation is at the `v1.0.0` / `v2.0.0` tags. Current docs: [User Guide](../USER-GUIDE.md), [Author Guide](../AUTHOR-GUIDE.md).

Full **functional** pack (18 catalogue IDs).

## Tasks

1. [x] Extend Env (snapshot/diff, counters, users, orders/inventory, notify, multi-turn state)
2. [x] Expand ToolGateway + WRITE/READ classification
3. [x] Case registry with per-ID golden / broken / oracle
4. [x] Multi-run harness for T1-002 / T1-003
5. [x] CLI: `--suite functional` runs all 18; `--ids` still works
6. [x] Parametrized pytest Pass golden / Fail broken
7. [ ] GitHub Actions *(still deferred — no workflow OAuth scope)*

## IDs

| ID | Status |
|:---|:-------|
| T1-001 | done (M0) |
| T1-002 | done |
| T1-003 | done |
| T1-004 | done |
| T1-005 | done |
| T1-007 | done |
| T1-009 | done |
| T1-011 | done |
| T1-013 | done |
| T1-015 | done |
| T2-001 | done |
| T2-003 | done |
| T2-009 | done |
| T2-013 | done |
| T5-012 | done |
| T6-003 | done |
| T6-006 | done |
| T6-010 | done |

## Acceptance

- [x] `agentest run --suite functional --agent golden` exit 0
- [x] `agentest run --suite functional --agent broken` exit non-zero (all FAIL)
- [x] pytest functional suite green
