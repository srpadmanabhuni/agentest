# r12 pool freeze readiness (6 Nov 2026 ~13:15 IST)

Prep-docs only. Blind agents a161–a170 are untouched. No plant authoring, no checker tuning, no private score publish.

## Status: FREEZE-READY (gate PASS)

Authoritative control-gate + measure run finished **2026-11-06 11:55 IST** after:

- a153 re-record DONE 11:28 IST
- a151 re-record 11:28–11:54 IST with the X-004 handoff-once harness
  (`tool_loop` stop-after-successful-handoff in `common/runtime.py`;
  `handoff_tool` required-field error with no `handoff` key in `common/staged_desk.py`)

### Gate (private)

| Check | Result |
|---|---|
| Control core fires (a127 / a133 / a151 / a155) | **0** |
| Control non-core fires | **0** |
| Seeded-dev assessable n/a (a152–a154, a156, a157) | **0/190 = 0.0%** (bar ≤25%) |
| Overall assessable n/a (all 9 desks) | **1/342 = 0.3%** |
| Remaining assessable n/a | **T2-008 ×1** somewhere on a151 |
| Core-47 n/a (all desks) | 80/423 = 18.9% |
| RESULT | **PASS** |

### Exact local file refs (box paths; do not invent numbers)

| Artifact | Path |
|---|---|
| Summary | `/workspace/r12/rebase/sum.chain-a153-a151/night4.summary.txt` |
| Measure text | `/workspace/r12/rebase/measure.chain-a153-a151.out` |
| Measure JSON | `/workspace/r12/rebase/measure.chain-a153-a151.json` |
| Gate text | `/workspace/r12/rebase/gate.chain-a153-a151.out` |
| Gate JSON | `/workspace/r12/rebase/gate.chain-a153-a151.json` |
| Daytime aliases (byte-identical copies) | `/workspace/r12/rebase/measure.day6.{out,json}`, `gate.day6.{out,json}`, `sum.day6/` |

Pool used for the gate: `rebase/pool-day3.json` (examples mode).

## Scope (unchanged)

Assessable vs deferred split is already frozen in [`FREEZE-SCOPE.md`](./FREEZE-SCOPE.md)
(38 assessable / 9 deferred; machine copy `fixtures/core-assessable.json`). That deferred list
does **not** change after a blind round is recorded. Plants for the blind round are authored only
on assessable tests, and only after this freeze.

## Schedule (targets)

| Milestone | Target |
|---|---|
| Pool freeze | ~10 Nov 2026 |
| Blind score (a161–a170) | ~13 Nov 2026 |

## Rules during freeze prep

- Do **not** merge `r12-core47` to `main` for this freeze alone.
- Do **not** change checkers to chase scores.
- Do **not** tune on, re-record, or inspect blind agents a161–a170.
- Do **not** publish private scores.
- Box RAM is often ~3–5 GB available; model re-records need MemAvailable ≥ ~7.5 GB (Qwen) / ≥ ~5.1 GB (Gemma). Gate is already PASS — no re-record required for freeze readiness.

## Notes

- Single remaining assessable n/a cell is T2-008 on a151 (overall 1/342). Not a control fire.
- X-004 harness fix is in the live refagents tree and was present for the a151 re-record; verified still present on 6 Nov daytime.
- Earlier night5 PASS (0 core / X-004 ×1 on a151) is superseded for freeze purposes by this post-X-004 chain PASS (0 core / 0 non-core).
