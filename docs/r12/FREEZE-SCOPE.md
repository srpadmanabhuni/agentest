# r12 freeze scope: assessable vs deferred core tests (frozen 2 Nov 2026)

Owner decision, 2 Nov 2026: the 0.95 precision / 0.95 recall bar (two consecutive blind rounds, 0 control false alarms)
applies to the **assessable** subset of the 47 core tests. The **deferred** tests still run on every agent; their n/a
rate, any fails and any planted defects on them are reported separately and openly in every score, and are never folded
into precision or recall. Machine-readable copy: `fixtures/core-assessable.json`. Scorer: `scripts/core_score.py`.

Rules of this freeze:

- This split is written before any r12 scoring and does not change after a blind round is recorded.
- Tests marked *pending re-baseline* became assessable through r12 harness cases added on 2 Nov (empty input, repeat,
  6-turn conversation, units, negation, paraphrase). If one is still n/a on more than one dev desk after the re-baseline,
  it moves to deferred **before** the blind round is frozen, never after.
- Planted defects for the blind round are authored only on assessable tests.

## Assessable (38)

| Test | dev desks n/a today (of 9) | Note |
|---|---|---|
| T1-001 | 0 |  |
| T1-002 | 1 |  |
| T1-003 | 1 |  |
| T1-004 | 0 |  |
| T1-005 | 1 |  |
| T1-006 | 0 |  |
| T1-007 | 9 | pending re-baseline: needs the r12 empty case |
| T1-010 | 0 |  |
| T1-011 | 0 |  |
| T1-013 | 2 |  |
| T1-018 | 0 |  |
| T2-001 | 1 |  |
| T2-002 | 0 |  |
| T2-003 | 0 |  |
| T2-006 | 0 |  |
| T2-007 | 1 |  |
| T2-008 | 1 |  |
| T2-010 | 1 |  |
| T2-013 | 1 |  |
| T2-014 | 0 |  |
| T5-001 | 0 |  |
| T5-002 | 1 |  |
| T5-003 | 0 |  |
| T5-006 | 0 |  |
| T5-012 | 2 |  |
| T6-001 | 1 |  |
| T6-002 | 1 |  |
| T6-003 | 0 |  |
| T6-005 | 0 |  |
| T6-008 | 9 | pending re-baseline: needs the r12 conv6 case |
| T6-010 | 0 |  |
| T6-012 | 1 |  |
| T6-014 | 1 |  |
| T7-001 | 8 | pending re-baseline: needs the r12 paraphrase case |
| T7-005 | 9 | pending re-baseline: needs the r12 negation case |
| T7-006 | 8 | pending re-baseline: needs the r12 paraphrase case |
| T7-008 | 9 | pending re-baseline: needs the r12 repeat case |
| T7-012 | 9 | pending re-baseline: needs the r12 units case |

## Deferred (9)

| Test | dev desks n/a today (of 9) | Reason |
|---|---|---|
| T1-009 | 7 | needs batch/bulk writes; the r12 desks write one case per run (n/a on 7/9 dev desks) |
| T1-014 | 9 | needs an artifact digest asked for or reported; no r12 desk produces artifacts |
| T1-015 | 9 | needs a counter change with a delta argument; no r12 desk tool takes a delta |
| T1-016 | 9 | needs a delete with a soft/hard marker; no r12 desk deletes records |
| T2-009 | 4 | needs parallel/interleaved tool calls; the r12 desks run sequential stages (n/a on 4/9, not reliable) |
| T6-006 | 9 | needs a to-do list with completed items; no r12 desk keeps a to-do list |
| T6-007 | 9 | needs a declared retrieval capability; no r12 desk does retrieval |
| T6-009 | 9 | needs a declared retrieval capability; no r12 desk does retrieval |
| T7-013 | 9 | needs cross-language round-trip/Hinglish relation pairs; the r12 harness adds none |

## Baseline before the re-baseline (2 Nov 2026, judge offline, current r12-core47 rules)

Measured on the 9 existing dev/control recordings (a127, a133, a151-a157; a127 partial r12, a133 pre-r12):

- Assessable: 78/342 cells n/a (23%). 61 of those are on the 7 pending-re-baseline tests, whose cases were not yet recorded.
- Deferred: 74/81 cells n/a (91%), reported as is.
- a133 (control, old staged-desk recording) fires T5-001 'undeclared tools' because its export now carries the rebuilt
  r12 card; this is a recording/card mismatch, cleared by re-recording a133, and is re-checked by the control gate.

Deferred tests are a coverage gap of the r12 reference desks, not a claim that agentest checks them well or badly.
