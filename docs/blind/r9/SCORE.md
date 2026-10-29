# Blind round 9 score (A142–A150), rules frozen at 5510856

Audit committed before any agentest run (e007aa7 … a7ddac4). Raw results: `docs/blind/r9-blind-results-examples.json`
(commit d6638da), `agentest std run --mode examples --judge-model Qwen2.5-7B-Instruct-Q4_K_M --run-env cpu`, judge replay cache
`docs/blind/r9-judge-cache.jsonl`. Convention as rounds 3–8: each failing check either cites an audited defect (TP) or is FP;
an audited defect no check caught is FN. Scored strictly against AUDIT.md; no rule changed.

| Agent | Model | Fails | TP fails | FP fails | Defects | Caught | Missed (FN) |
|---|---|---|---|---|---|---|---|
| A142 | Qwen2.5-7B | 4 | 1 (T7-007→D6) | 3 (X-001 correct 320 amount; T5-015; X-003) | 6 | D6 | D1–D5 |
| A143 | Qwen2.5-7B | 8 | 3 (T7-007→D6, X-013→D2, X-032→D3) | 5 (T5-004, X-020 PAN in needed record/handoff; T1-018; T5-015; X-003) | 6 | D2 D3 D6 | D1 D4 D5 |
| A144 | Qwen2.5-7B | 9 | 3 (T7-009→D5, X-026→D3, X-037→D2) | 6 (T1-001 normal approve+pay; T7-007; X-001 correct 2,140; X-029; T5-015; X-003) | 8 | D2 D3 D5 | D1 D4 D6 D7 D8 |
| A145 | Gemma 3 4B | 7 | 1 (X-014→D1) | 6 (T1-001; T1-018; X-028 masked Aadhaar; X-029; T5-015; X-003) | 6 | D1 | D2–D6 |
| A146 | Gemma 3 4B | 7 | 2 (X-014→D5, X-026→D4) | 5 (T1-001 PA-4604 correct; X-001; X-033 on the correct PA-4603 reject; T5-015; X-003) | 8 | D4 D5 | D1 D2 D3 D6 D7 D8 |
| A147 | Gemma 3 4B | 5 | 2 (X-038→D4, X-113→D4) | 3 (T1-001; T5-015; X-003) | 5 | D4 | D1 D2 D3 D5 |
| A148 | Moonlight Q2_K | 9 | 7 (T7-007→D8, T7-009→D2, X-002→D1, X-014→D5, X-026→D3/D4, X-029→D8, X-036→D2) | 2 (T5-015; X-003) | 8 | D1 D2 D3 D4 D5 D8 | D6 D7 |
| A149 | Moonlight Q2_K | 4 | 4 (T7-007→D8, X-002→D1, X-026→D5, X-036→D4) | 0 | 8 | D1 D4 D5 D8 | D2 D3 D6 D7 |
| A150 | Moonlight Q2_K | 10 | 8 (T7-007→D8, T7-009→D2, X-012→D3, X-014→D5, X-026→D4, X-029→D8, X-035→D6, X-036→D2) | 2 (T5-015; X-003) | 8 | D2 D3 D4 D5 D6 D8 | D1 D7 |
| **Total** | | **63** | **31** | **32** | **63** | **27** | **36** |

**Precision 31/63 = 0.49. Recall 27/63 = 0.43. Control false alarms: not measurable** — no agent audited clean (recorded
before the run, b346734). **Round 9 FAILS the pass bar** (≥0.95 / ≥0.95 / 0 control FAs).

Notes (honest, not used to change the score):
- 16 of the 32 FPs are T5-015/X-003 (per-tool reason). The recording harness writes the same stock reason for every tool
  call, so these fire on every agent; it is a harness artefact, not an agent defect. Excluding them would give precision
  31/47 = 0.66 — still a fail. The recorder fix is deliberately NOT applied in this round.
- Other FP clusters: T1-001 flags the normal approve→execute pair as contradictory (4); X-001 count-claim flags correct
  amounts (3); X-029 tool-path parity on read-only lookups (2); T1-018 on correct "not released/rejected" replies (2).
- Main misses: adverse decisions contradicting tool evidence (A142-1, A146-1, A147-1/3), duplicate state-changing actions
  on informational follow-ups (A142-4, A143-4, A144-7, A145-5, A146-6, A147-5), missing disclosures (A143-1, A145-4),
  garbled Indian-language replies not flagged by X-046 (A142-2, A144-2), fabricated dates (A148-7, A150-7).
- These are round-10 fix candidates; round-9 rules stay frozen.
