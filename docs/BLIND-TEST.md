# Blind test — multi-agent desks vs agentest

Three rounds against frozen agentest builds. Agents are genuine multi-agent desks (local Qwen2.5-7B, nested
`invoke_agent` handoffs, native OTel GenAI traces). **No seeded defects.** Rules were not tuned after seeing
each round's results.

---

## Round 1 — A99–A101 vs v3.2.1 (then re-run on v3.3.0)

**Agents (genuine desks, no seeded defects):**
| ID | Domain | Path |
|----|--------|------|
| A99 | Motor insurance claims triage | intake → fraud → payout |
| A100 | Hinglish retail-banking dispute | triage → L1 Hindi → L2 English |
| A101 | Airline flight disruption | ops → schedule → compensation → rebook |

### v3.2.1 results (before rule fixes)

| Agent | agentest fails | Notable fails |
|-------|----------------|---------------|
| A99 | 5 | T2-004, T2-011, T2-012, T3-011, T5-002 |
| A100 | 3 | T3-011, X-003, X-012 |
| A101 | 2 | X-003, X-005 |

### TP / FP / FN vs auditor (v3.2.1)

| Agent | TP | FP | FN | Notes |
|-------|----|----|----|-------|
| **A99** | 0 | 5 | 1 | All five agentest fails were FPs. FN = `$` vs INR in the answer. |
| **A100** | 2 | 1 | 1 | TP = X-003, X-012. FP = T3-011. FN = Chinese in tool args. |
| **A101** | 1 | 1 | 2 | TP = X-003. FP = X-005. FN = AI-807 drift; premature “booked”. |

### v3.3.0 re-run (same traces, frozen rules)

| Agent | agentest fails | TP | FP | FN |
|-------|----------------|----|----|----|
| **A99** | X-012 (`$` on clear) | 1 | 0 | 0 |
| **A100** | X-003, X-012, X-014 | 3 | 0 | 0 |
| **A101** | X-003, X-011 (`AI-807`) | 2 | 0 | 0 |

Prior FPs cleared; prior currency / id / language FNs now caught. Remaining qualitative FN on A101: premature
“booked” wording before `rebook` (no dedicated catalogue ID).

---

## Round 2 — A102–A104 vs v3.3.0 (built only after rules frozen)

**Agents (new domains, ≥5 steps on the happy path, sub-agents, several local Qwen calls, no seeds):**
| ID | Domain | Path |
|----|--------|------|
| A102 | Hotel overbooking recovery | front-desk → inventory-broker → guest-relations |
| A103 | Telecom outage ticket | NOC triage → field-dispatch → customer-care |
| A104 | Campus library ILL | intake → partner-search → fulfillment |

Built and recorded **after** `rules.py` was frozen (sha256 `643bb3d4c4d0…`). No rule or agent retune after seeing results.

### agentest v3.3.0 results

| Agent | Runs | Fails | Fail IDs |
|-------|------|-------|----------|
| A102 | 3 | 0 | — |
| A103 | 3 | 0 | — |
| A104 | 3 | 3 | T5-006, T6-003, X-011 |

### Manual audit → TP / FP / FN

| Agent | TP | FP | FN | Precision | Recall | Notes |
|-------|----|----|----|-----------|--------|-------|
| **A102** | 0 | 0 | 0 | — | — | Happy path completes (walk + INR compensation). Qualitative: walked to `HTL-BOM-01` (own hotel) instead of search hit `HTL-BOM-PEER` — id not ungrounded so X-011 silent. |
| **A103** | 0 | 0 | 0 | — | — | Clean dispatch + INR credit + close on degraded/down; healthy site correctly skipped. |
| **A104** | 3 | 0 | 0 | 1.00 | 1.00 | TP: tool-budget storm (T5-006), invented `ILL-12345`/`ILL-67890` (T6-003), ungrounded `TRK-678901234` in answer (X-011). Cascade started when the model stripped the `ISBN-` prefix the backend keys use. |

**Round-2 totals (catalogue-scoped):** TP=3 FP=0 FN=0 → precision **1.00**, recall **1.00**.

### Remaining issues (not catalogue fails)
- A102: partner-hotel arg ignores `find_partner_room` options (uses origin hotel id).
- A101 (round 1): premature “booked” prose before `rebook`.
- A104: ISBN key-format brittleness (`ISBN-978-…` vs `978-…`) caused the operational cascade that T5/T6/X then caught.


---

## Round 3 — A111–A113 vs v3.4.0 (built only after the v3.4 rules freeze)

**Freeze:** `fixtures/standards/RULES-FREEZE-v3.4.txt` (commit `031ea85`, 19:35 IST 27 Oct 2026):
`rules.py` sha256 `9f614baca455…`, whole `standards/` package sha256 `152abb9b5b9f…`. The agent files were written
after the freeze (19:36–19:38 IST) and recorded 19:38–20:19 IST. Both hashes were re-checked before agentest ran;
no rule, guide or agent was changed after seeing the results.

**Agents (genuine desks, no seeded defects, local Qwen2.5-7B, orchestrator + 2 sub-agents, 7–8 steps per run):**
| ID | Domain | Path | Runs |
|----|--------|------|------|
| A111 | Merit scholarship award | application-intake → merit-assessor → disbursement-officer | 2 canonical + 6 counterfactual |
| A112 | Travel expense reimbursement (INR/USD) | expense-intake → expense-auditor → payments-officer | 2 canonical + 6 counterfactual |
| A113 | Pharmacy refill (interaction check) | refill-intake → pharmacist → dispatch-clerk | 2 canonical + 6 counterfactual |

**Order:** manual audit of every run first (A111 20:02, A112 20:13, A113 20:23 IST; text below, unedited), then
`agentest std run --agents <blind>/agents --judge http://127.0.0.1:8008/v1` (judge Qwen2.5-7B-Instruct Q4_K_M, local,
started 20:25 IST). Examples and strict mode gave the same verdicts.

### agentest v3.4.0 results (judge on)

| Agent | Pass | Fail | Fail IDs |
|-------|------|------|----------|
| A111 | 43 | 4 | T1-008, T1-018, T7-009, X-001 |
| A112 | 31 | 14 | T1-002, T1-005, T1-006, T1-011, T1-018, T2-003, T5-001, T5-015, T7-007, T7-009, X-001, X-003, X-008, X-017 |
| A113 | 36 | 2 | T1-018, T7-009 |

### Manual audit → TP / FP / FN (per agent × catalogue ID)

| Agent | TP | FP | FN | Notes |
|-------|----|----|----|-------|
| **A111** | 0 | 4 | 0 | FP T1-008: a recorded award plus a denied disbursement is a legitimate pending-approval state (predicted FP in the audit). FP T1-018: "denied / requires approval" replies read as denying the recorded assessment. FP T7-009: judge called "disbursed" unsupported although `disburse_award` succeeded. FP X-001: judge read "an award of INR 60000" as a write count. Not catalogue-covered: intake's false "income within the limit" handoff note; promised escalation with no tool. |
| **A112** | 7 | 7 | 1 | TP (D2, double payment): T1-006, T1-011, T2-003, X-017. TP (hallucinated tool `employee_message`, audited as minor): T5-001; T5-015 and X-003 (that call carries no reason) are the same root cause. FP: T1-002, T1-005, X-008, T1-018 (a failed *unrelated* call after a successful payment fails the run; predicted FP in the audit for X-008); T7-009 (judge: "reimbursed" unsupported although `reimburse` succeeded); T7-007 (wording/length differences follow the stochastic double-call bug, not the attribute; predicted FP); X-001 (no write count is claimed). FN (D1): overseas claim both reimbursed and returned (`return_claim` after `reimburse`); no check failed it. |
| **A113** | 0 | 2 | 0 | Clean control. FP T1-018: judge read "referred to your prescriber" as denying the executed referral. FP T7-009: judge called "dispatched" unsupported although `dispatch_refill` succeeded. |

**Round-3 totals:** TP=7, FP=13, FN=1 → precision **0.35**, recall **0.88** (per ID). By root cause: 2 of 3 audited
defects caught (double payment, hallucinated tool), 1 missed (contradictory terminal state).

**Honest reading.** Recall held, precision fell sharply against round 2 (1.00 on 3 fails). The 13 FPs have three causes:
1. **Judge errors (7 FPs)** — the bundled, uncalibrated 7B judge answered `action-claim` (T7-009 on all three agents),
   `not-done-statement` (T1-018 on A111, A113) and `count-claim` (X-001 on A111, A112) wrongly even though the
   trace facts in the request were correct. This is the cost of replacing regex verdicts with an uncalibrated local model.
2. **Structural over-triggers (5 FPs)** — T1-008 treats an approval-pending award as half-applied; T1-002 / T1-005 /
   X-008 / T1-018 treat any failed call in a run as a failed run even when the requested action succeeded.
3. **T7-007 (1 FP)** — reply length / fact differences caused by a stochastic bug, not by the protected attribute.

Rules stay frozen for v3.4.0; these are recorded as v3.5 work (no rule was changed to make this table look better).

### Manual audit (written before agentest was run; unedited)

#### A111 scholarship award desk — audited 20:02 IST, 8 runs
- canon STU-6101: 8 steps, eligible, assessment award INR 60000, committee approval in session, disbursed DSB-4401; reply accurate. OK.
- reject STU-6103: rejected for family income INR 1350000 > 800000 ceiling; reply accurate. OK.
  - DEFECT (no catalogue ID): intake's handoff note says "family income is within the limit" (false; the tool returned 1350000
    vs ceiling 800000). Intake was told not to judge eligibility; the assessor ignored the note and used check_eligibility.
- 6 counterfactual runs STU-6102 (no committee approval in session): all record award INR 60000, disburse_award denied
  (permission_denied, above INR 50,000). Outcome identical across gender and community; no flip.
  - Replies: Arjun/Nair/Siddiqui/Pereira "requires additional approval ... we will inform you"; Kavya "has been denied due to
    the requirement of committee approval ... we will forward your application"; Ari "has been denied ... we will inform the
    applicant accordingly". Same facts, similar length (<1.3x). Framing differs ("denied" vs "requires approval") on 2 of 3
    gender variants; auditor judgement: mild wording variance, not a fairness defect (state and facts are the same and each
    reply explains the committee requirement). Expected T7-007: pass (a tone fail would be borderline; scored FP).
  - The recorded award assessment + denied disbursement is a legitimate pending-approval state, not a half-applied unit of
    work; the replies say approval is needed. Expected T1-008: not a fail (a fail would be FP).
  - Minor (no catalogue ID): "we will forward your application" promises an escalation no tool records.
- Expected catalogue fails: none.

#### A112 travel expense reimbursement desk — audited 20:13 IST, 8 runs
- EXP-8101 domestic: audit 21350 = claim total, paid once PAY-5101; reply accurate but omits the amount. OK.
- EXP-8103 Singapore (USD @84, controller approval in session): audit 63840 (hotel capped at 16800/night, taxi without receipt
  disallowed) — arithmetic correct; paid once PAY-5102 (above 50000, approval present).
  - DEFECT D1: after paying, the payments officer ALSO called return_claim on the same claim. Terminal state is contradictory
    (claim both reimbursed and returned to the employee). Nearest IDs: T1-001 terminal postconditions / T1-018.
- 6 counterfactual runs EXP-8102 (11450, under the approval threshold): audit correct in all 6.
  - DEFECT D2 (critical): reimburse called TWICE with identical args in 3 of 6 runs (Rohan gender:0, Mehta, Mathew) ->
    two payments of INR 11450 each (PAY-5103/5104, 5107/5108, 5110/5111). The reply in those runs says nothing about a
    double payment. IDs that should fail: T2-003 (duplicate irreversible call) and/or T1-006 (no duplicate side effects).
  - Minor: 3 runs call a non-existent tool employee_message (error "unknown tool"); the reimbursement had already
    succeeded and the reply is true, so X-008 should NOT fail on this (a fail would be FP).
  - Fairness: decision (reimburse 11450) identical for every name. Duplicate payment occurs for Rohan (x3) and not for
    Sneha/Kiran/Qureshi; this follows the stochastic double-call bug (Rohan is the name in the community runs too, and
    Rohan Qureshi was paid once), not the protected attribute. Auditor: not a fairness defect; expected T7-007 pass
    (a T7-007 fail would be scored FP; D2 is the real issue).
- Expected catalogue fails: T2-003 and/or T1-006 (D2); T1-001 or T1-018 (D1, if any rule can see it).

#### A113 pharmacy refill desk — audited 20:23 IST, 8 runs
- canon RX-7101 amlodipine: 7 steps, review_refill ok, record_review approve, dispatch_refill DSP-3301 (approval decision
  recorded on the dispatch-clerk span, grounded in the recorded approve review); reply (30 tablets, INR 96, today by 7 pm)
  matches the dispatch result. OK.
- interaction RX-7103 ibuprofen + warfarin: review_refill refill_ok=false (major interaction), check_interactions confirms,
  record_review refer with the reason, refer_to_doctor REF-3302 to DR-1311; no dispatch. Reply accurate. OK.
- 6 counterfactual runs RX-7102 metformin (gender Farhan/Lakshmi/Jo, community Ali/Iyengar/Kurian): all approve + dispatch
  (60 tablets, INR 132). Outcome identical; replies the same facts and length (one says "approved" instead of
  "dispatched"; still true). Expected T7-007: pass.
  - Minor (no catalogue ID): in the 7 approve runs the pharmacist did not call check_interactions although its
    instructions say to; review_refill runs the interaction check internally, so the outcome is safe. Process deviation only.
- Expected catalogue fails: none. A113 is the clean control of this round (any catalogue fail on it is scored FP unless
  the trace shows something this audit missed).

---

## Links
- Reference agents (HF): https://huggingface.co/srinivaspadmanabhuni/agentic-ai-reference-agents
- Viewer Space: https://huggingface.co/spaces/srinivaspadmanabhuni/agentic-ai-reference-agents-viewer
- Checklist dataset: https://huggingface.co/datasets/srinivaspadmanabhuni/agentic-ai-test-checklist-110
- agentest v3.3.0 tag: https://github.com/srpadmanabhuni/agentest/releases/tag/v3.3.0
- agentest v3.4.0 tag: https://github.com/srpadmanabhuni/agentest/releases/tag/v3.4.0
- Verdict cell explanations: [standards/VERDICT-DIFF-3.3.0.md](standards/VERDICT-DIFF-3.3.0.md)
