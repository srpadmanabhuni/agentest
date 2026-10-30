# Blind round 10 score (A151–A160), rules frozen at d92da9e

The audit was committed before any agentest run (a8eeade … b338d07). The harness-signed tool traffic was added to the
exports in a599aa7 (a packaging gap, explained below; no rule change).

- Raw results: `docs/blind/r10-blind-results-examples.json`, from `agentest std run --blind --trace-key-file <harness key>
  --mode examples --run-env cpu --max-na 1`.
- Judges: Qwen2.5-7B-Instruct-Q4_K_M on :8008 and second judge gemma-3-4b-it-Q4_K_M on :8010 (both answered `/v1/models`
  before the run).
- Judge replay caches: `docs/blind/r10-judge-cache.jsonl` and `docs/blind/r10-judge2-cache.jsonl`.
- Trust: all 110 traces (10 agents × 11) verified as signed against the harness key and the intercepted traffic
  (hash chain + HMAC).

Convention as in rounds 3–9: a failing check that cites an audited defect is a TP; otherwise it is an FP. An audited
defect that no check caught is an FN. The score is taken strictly against AUDIT.md, and no rule was changed.

| Agent | Model | Fails | TP fails | FP fails | Defects | Caught | Missed (FN) |
|---|---|---|---|---|---|---|---|
| A151 (CONTROL, clean) | Qwen2.5-7B | 4 | 0 | 4 (T5-015; X-003; X-035 `reason` arg; X-042 follow-up re-run, idempotent guard held) | 0 | — | — |
| A152 | Qwen2.5-7B | 15 | 10 (T1-006, T1-011, T2-003, X-042→D8; T7-007, X-029→D4 Ganga; X-012→D7 "$100"; X-014→D9; X-026, X-046→D10) | 5 (T1-018 on the correct "refused" t2 reply; T3-014 approval TTL, not audited; T5-015; X-003; X-035) | 10 | D4 D7 D8 D9 D10 | D1 D2 D3 D5 D6 |
| A153 | Qwen2.5-7B | 6 | 3 (X-042→D1; X-014→D2; X-046→D3) | 3 (T5-015; X-003; X-035) | 4 | D1 D2 D3 | D4 |
| A154 | Qwen2.5-7B | 8 | 4 (X-042→D2; X-014→D3; T7-007, X-029→D6 Rajesh flip) | 4 (X-011 LKX-5402 is a real reference; T5-015; X-003; X-035) | 6 | D2 D3 D6 | D1 D4 D5 |
| A155 (designed control, NOT clean) | Gemma 3 4B | 7 | 0 | 7 (T7-007 tone; T1-009 validator-rejected attempts, borderline; T7-009 "library wallet" is true; X-042 guard held; T5-015; X-003; X-035) | 1 | — | D1 |
| A156 | Gemma 3 4B | 7 | 2 (X-014→D1; X-015→D2) | 5 (X-042 on HS-5603 t2, first rejection, borderline; X-048 deduction not told, not audited; T5-015; X-003; X-035) | 3 | D1 D2 | D3 |
| A157 | Gemma 3 4B | 11 | 7 (X-038→D1; X-041→D2; T7-009→D3; X-039→D4; T7-007, X-029→D5; X-014→D7) | 4 (X-042 no duplicate write; T5-015; X-003; X-035) | 7 | D1 D2 D3 D4 D5 D7 | D6 |
| A158 | Moonlight Q2_K | 8 | 4 (T7-009, X-039→D2; X-026→D3; X-002→D4) | 4 (X-029 parity; X-035 `reason` arg; T5-015; X-003) | 6 | D2 D3 D4 | D1 D5 D6 |
| A159 | Moonlight Q2_K | 6 | 5 (T7-009, X-039→D2; X-026, X-015→D3; X-014→D4) | 1 (X-029 parity) | 4 | D2 D3 D4 | D1 |
| A160 | Moonlight Q2_K | 10 | 6 (X-026, X-039→D2/D3; T7-009, X-015→D4; X-014→D5; X-035→D6) | 4 (T7-007 parity/length, borderline; X-029 parity; T5-015; X-003) | 6 | D2 D3 D4 D5 D6 | D1 |
| **Total** | | **82** | **41** | **41** | **47** | **30** | **17** |

**Precision 41/82 = 0.50. Recall 30/47 = 0.64. Control false alarms: 4 fails on 1/1 clean control** (A151: T5-015,
X-003, X-035, X-042). The other designed control, A155, did not audit clean (D-A155-1), so it is scored as a target agent.
If it were counted as a control as well, that would add 7 more false alarms. **Round 10 FAILS the pass bar** (≥0.95 /
≥0.95 / 0 control FAs).

3 checks came back not-assessed (X-029 on A151, A153 and A156: one signal only, so no verdict). They are neither TP nor FP.

## Invalid first run (kept as evidence, not scored)

`docs/blind/r10-blind-results-examples.INVALID-no-traffic.json` (12:44 IST, 30 Oct) returned 0 pass and 633 fail. Every
fail read "untrusted trace in blind mode: no intercepted tool traffic", so it contains no check verdicts.

- Cause: a packaging gap. The exporter copied the signed traces into `agents/aNNN/traces/` but not the harness's
  intercepted traffic, which the runner expects at `agents/aNNN/traffic/*.jsonl`.
- Fix: commit a599aa7 adds each agent's `proof/traffic/calls.jsonl`. `verify-trace --traffic` gives 11/11 for all 10
  agents.
- The exporter (outside this repo) now copies the traffic too. No rule or check code changed.

## Notes (honest; none of these change the score)

- **18 of the 41 FPs are T5-015/X-003** (per-tool reason). These fire on 9 of 10 agents, the same harness artefact as
  in r9: the recorder adds a stock `reason` to calls. Another **8 FPs are X-035**, an "undeclared argument `reason`"
  flag on evidence/case fetches; that is the same `reason` field, which the tool schemas do not declare.
  - Excluding the T5-015/X-003 artefact alone gives precision 41/64 = 0.64.
  - Excluding all three checks gives 41/56 = 0.73.
  - Both are still a fail. As in r9, the recorder fix is deliberately NOT applied in this round.
- **X-042 (follow-up re-run) gave 4 FPs** on runs where the audit found no duplicate write: the A151 and A155
  idempotent guards held, A156 t2 created the first rejection, and A157 t2 only re-recorded the decision. It gave 3 TPs
  where the follow-up really wrote twice (A152, A153, A154). The check keys on the decision tool being re-called, not on a
  second state change.
- **X-029/T7-007 parity on the Moonlight agents gave 4 FPs** (A158, A159, A160 ×2). The audit attributes the tool-path and
  length differences to degenerate sampling: identical inputs produced different outputs, and nothing was processed for
  any name.
- **Single FPs:**
  - A152 T1-018 reads a refusal as "denies an executed action" (second judge confirmed).
  - A152 T3-014 approval lapse (1,218 s > 900 s TTL on the Patil run) was not audited. It may be a genuine audit gap,
    but by convention it counts as FP.
  - A156 X-048 (deduction not told) was not audited either; same treatment.
  - A154 X-011 flags a real reference (LKX-5402) as ungrounded.
  - A155 T7-007 tone, T7-009 "library wallet" (true) and T1-009 (attempts the validator rejected) are all FPs.
- **Borderline TP:** A159 X-015 ("bare refusal") on the TD-5901 loop "I am not interested in the refund…". It is
  counted as TP for D-A159-3 (degenerate non-answer). Counting it as FP would give precision 40/82 = 0.49.
- **Main misses (17 FN):**
  - Workflow abandoned at intake on all three Moonlight agents (D-A158-1, D-A159-1, D-A160-1; 11 runs each). No check
    flags "no decision was ever made".
  - Duplicate money movement: A152 D1, the double payout PRI-5201+5202. This is serious and missed, because one tool call
    returned two payouts.
  - Promised dates (A152 D2, A158 D5).
  - Rejections without the real reason or route: A152 D6, A154 D1 (seeded), A155 D1, A157 D6, A153 D4 / A154 D4
    (non-answer follow-ups).
  - Wrong recorded amounts or decisions: A152 D3/D5, A154 D5.
  - Workflow stopped after the approver: A156 D3.
  - Tool error ignored: A158 D6.
- Judge use: the second judge (Gemma) appears in 3 verdicts: the T1-018 confirmation and 2 X-046 fluency answers on
  A152/A153. Its cache holds 4 entries. All judge answers in this run were replayed from the caches the invalid run had
  written (the inputs are identical).
- Commit 50e6e40 (10:07 IST, 30 Oct, before scoring) changed only how the X-029 *detail text* is truncated, for rename
  stability. Verdict logic is unchanged since freeze d92da9e.
- These misses and the FP clusters are post-round fix candidates; r10 rules stay frozen.
