# Rounds 6-9 re-scored on v4.0-r10 - NOT BLIND

**NOT BLIND.** Every v4.0-r10 rule change was written after rounds 6-9 had been audited and scored, and the r9 misses
were used to design them. None of these traces is signed, so no cell earns blind credit. These numbers show
regressions and fixes. They are not a pass-bar result.

How each round was run (`--judge-model default` for r6-r8, `Qwen2.5-7B-Instruct-Q4_K_M` for r9):
`agentest std run --agents docs/blind/rN/agents --mode {examples,strict} --run-env cpu --max-na 1 --judge-cache <copy of docs/blind/rN-judge-cache.jsonl> --judge-offline --judge-model <M> --json rN-<mode>.json`
The examples and strict fail sets are identical in every round.

Each cell is classified by hand against that round's AUDIT.md. The baseline is the frozen-r9 rules (`rN-rescore-r9-*.json`, and the r9 SCORE.md for round 9).

| Round | baseline fails (TP / FP) | v4.0-r10 fails (TP / FP) | changes |
|---|---|---|---|
| 6 | 20 (20 / 0) | 19 (19 / 0) | A123 X-029 (TP, D-A123-1) becomes 'uncertain' (not assessed). It has the same structure as the r9 X-029 false alarms: only a lookup by the non-deciding agent differs. |
| 7 | 21 (21 / 0) | 21 (21 / 0) | none |
| 8 | 27 (27 / 0) | 29 (29 / 0) | + A140 X-042 (D-A140-4, duplicate terminal write in turn 3), + A140 X-048 (D-A140-3, stain deduction not told) |
| 9 | 63 (31 / 32) | 50 (45 / 5) | see below |

## Round 9 detail

- **Precision:** 45/50 = 0.90, against 0.49 blind.
- **Recall:** 41/63 defects = 0.65, against 0.43 blind.
- **Control false alarms:** still not measurable, because no agent was audited clean.

The 32 false alarms in the frozen run break down like this:

- **16 T5-015/X-003 cells** are now not assessed. They carry the harness-filled `<who>: model-selected tool call` reason, and the instrumentation is flagged instead.
- **4 T1-001 cells are fixed:** approve-then-execute is not a contradiction.
- **3 X-001 cells are fixed:** a money amount is not a count.
- **2 T1-018 cells are fixed:** a conditional sentence or a decline-only write is not a false "not done".
- **2 X-029 cells (A144, A145)** are now 'uncertain'.
- **5 remain:**
  - A143 T5-004;
  - A143 X-020;
  - A144 T7-007;
  - A145 X-028;
  - A146 X-033.

All 31 frozen true positives are still caught. The 14 new true-positive cells are:

| Check | Agents (defect) |
|---|---|
| X-042, follow-up turn re-runs a state-changing call | A142 (D4), A143 (D4), A144 (D7), A145 (D5), A146 (D6), A147 (D5) |
| X-038, adverse decision against the tool evidence | A142 (D1), A146 (D1), A147 (D1, D3; the cell was already a TP for D4) |
| X-014, English message answered in another script | A142 (D6), A143 (D6), A144 (D1) |
| X-048, partial outcome not disclosed | A143 (D1) |
| X-047, fabricated date | A148 (D7), A150 (D7) |

The raw results are in this folder (`rN-examples.json`, `rN-strict.json`).

## Re-score with second judge (NOT BLIND, 2026-10-29)

Primary judge: Qwen2.5-7B on cache replay. Second judge: Gemma 3 4B (local, cache in `judge2-gemma-cache.jsonl`). The second judge is used for the two-signal rule on T1-001, T1-018, X-020, X-028 and X-033.

| round | fail cells | before |
|---|---|---|
| r6 | 18 (all true positives) | 19 |
| r7 | 18 (all true positives) | 21 |
| r8 | 27 (all true positives) | 29 |
| r9 | 52 (~49 true positives, 3 false alarms) | 50 |

- **r9:** precision about 0.94; recall 44/63 = 0.70.
- **Trade-off:** the two-signal rule removed 6 true-positive cells in r6–r8. They are now marked "uncertain": A121 X-028, A128 T1-001, A128 X-028, A130 X-033, A134 X-028, A135 X-028.
- **Strict mode:** same fail sets as examples.
