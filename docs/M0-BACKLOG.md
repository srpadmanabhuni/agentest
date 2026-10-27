# M0 backlog — `v0.1.0`

> **Historical (pre-v3).** This page describes code that was removed in v3.1.0; it is kept for the record. The
> implementation is at the `v1.0.0` / `v2.0.0` tags. Current docs: [User Guide](USER-GUIDE.md), [Author Guide](AUTHOR-GUIDE.md).

Solo, one ID: **T1-001** (Terminal postconditions after a single task).

## Tasks

1. [x] `pyproject.toml` + `agentest` CLI entrypoint
2. [x] `Env` + mock ledger fixture (`fixtures/ledger.py` + `agentest.fixtures.ledger`)
3. [x] Mock tool gateway (allowlist noop)
4. [x] Golden agent that sets expected ledger statuses
5. [x] `examples/broken_agent` that claims success without writes
6. [x] `tests/functional/test_t1_001.py` — Pass golden, Fail broken
7. [ ] GitHub Actions: run T1-001 on PR *(deferred — OAuth lacks `workflow` scope)*
8. [x] Sync T1-001 metadata into `catalog/t1_001.yaml` (catalogue v1.1 pin; not full CSV)

## Acceptance

- [x] `agentest run --ids T1-001 --agent golden` exits 0
- [x] `agentest run --ids T1-001 --agent broken` exits non-zero
- [ ] CI green on main *(Actions deferred)*
- [x] README quick start works in <10 minutes
