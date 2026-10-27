# M4 backlog — `v0.5.0`

> **Historical (pre-v3).** This page describes code that was removed in v3.1.0; it is kept for the record. The
> implementation is at the `v1.0.0` / `v2.0.0` tags. Current docs: [User Guide](../USER-GUIDE.md), [Author Guide](../AUTHOR-GUIDE.md).

**Bias / fairness** pack (3 catalogue IDs) + research note.

## Tasks

1. [x] Fixtures: Hinglish pair, Alex/Priya loan pair, ES malware probe
2. [x] Deterministic labeler (`allow|refuse|abstain`) — no LLM judge
3. [x] CaseSpec for T7-004, T7-007, T7-011
4. [x] CLI `--suite bias_fairness` with alias `--suite bias`
5. [x] pytest Pass golden / Fail broken
6. [x] `docs/BIAS-RESEARCH.md` + `docs/PROPOSED-bias.md`
7. [x] Prior suites (functional, privacy, explainability) still green
8. [ ] GitHub Actions *(deferred — no workflow OAuth scope)*

## IDs

| ID | Status |
|:---|:-------|
| T7-004 | done |
| T7-007 | done |
| T7-011 | done |

## Acceptance

- [x] `agentest run --suite bias_fairness --agent golden` exit 0
- [x] `agentest run --suite bias --agent broken` exit non-zero
- [x] other suites golden exit 0
- [x] research doc present
- [x] pytest green
