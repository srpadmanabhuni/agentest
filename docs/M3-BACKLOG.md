# M3 backlog — `v0.4.0`

> **Historical (pre-v3).** This page describes code that was removed in v3.1.0; it is kept for the record. The
> implementation is at the `v1.0.0` / `v2.0.0` tags. Current docs: [User Guide](USER-GUIDE.md), [Author Guide](AUTHOR-GUIDE.md).

**Explainability** pack (5 catalogue IDs) + research map.

## Tasks

1. [x] Extend types (`ToolCall.meta`, Trace `api_success` / `memory_citations` / `explanation` / `cited_steps`)
2. [x] Extend Env (`authz_log`, `memory`, `memory_reads`, `db_ok`)
3. [x] Gateway: `reason=` / `meta=` on calls; `db.write`, `refund`, `memory.read`
4. [x] CaseSpec for T1-018, T3-006, T5-015, T6-007, T7-009
5. [x] CLI `--suite explainability`
6. [x] pytest Pass golden / Fail broken
7. [x] `docs/EXPLAINABILITY-RESEARCH.md` + oracle “Related research” section
8. [x] Functional + privacy regression green
9. [ ] GitHub Actions *(deferred — no workflow OAuth scope)*

## IDs

| ID | Status |
|:---|:-------|
| T1-018 | done |
| T3-006 | done |
| T5-015 | done |
| T6-007 | done |
| T7-009 | done |

## Acceptance

- [x] `agentest run --suite explainability --agent golden` exit 0
- [x] `agentest run --suite explainability --agent broken` exit non-zero
- [x] functional + privacy golden exit 0
- [x] research doc with per-ID table
- [x] pytest green
