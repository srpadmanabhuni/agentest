# Blind test — multi-agent desks vs agentest

Two rounds against frozen agentest builds. Agents are genuine multi-agent desks (local Qwen2.5-7B, nested
`invoke_agent` handoffs, native OTel GenAI traces). **No seeded defects.** Rules were not tuned after seeing
each round's results.

These are our current measured results; we are constantly working to improve precision and recall, and we update this page as new held-out measurements land.

## How these figures are counted

Two kinds of miss appear below:

- **Catalogue-scoped false negative (FN):** an auditor-found defect that maps to a catalogue check ID, and that agentest
  did not flag. These fill the FN column and are the recall denominator in each totals line.
- **Unlabelled miss:** an auditor-found defect that has no catalogue check ID yet, so no current check can produce a
  verdict for it. These are shown in the *Unlabelled* column and listed under [Unlabelled misses](#unlabelled-misses-no-catalogue-check-id),
  so they stay visible, but they are **not** in the catalogue-scoped recall denominator.

Recall is reported in two parts: the catalogue-scoped figure (defects an existing check could catch) and the number of
unlabelled misses (real issues no existing check covers). Neither is hidden inside the other. When an unlabelled miss
later gets a catalogue check ID, it moves into the catalogue-scoped FN column and recall is recomputed.

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

| Agent | TP | FP | FN | Unlabelled | Notes |
|-------|----|----|----|------------|-------|
| **A99** | 0 | 5 | 1 | 0 | All five agentest fails were FPs. FN = `$` vs INR in the answer. |
| **A100** | 2 | 1 | 1 | 0 | TP = X-003, X-012. FP = T3-011. FN = Chinese in tool args. |
| **A101** | 1 | 1 | 1 | 1 | TP = X-003. FP = X-005. FN = AI-807 drift. Unlabelled = premature “booked”. |

FN here counts only auditor defects that map to a catalogue check ID; the premature “booked” miss had none, so it is
in the *Unlabelled* column rather than the FN column.

### v3.3.0 re-run (same traces, frozen rules)

| Agent | agentest fails | TP | FP | FN | Unlabelled |
|-------|----------------|----|----|----|------------|
| **A99** | X-012 (`$` on clear) | 1 | 0 | 0 | 0 |
| **A100** | X-003, X-012, X-014 | 3 | 0 | 0 | 0 |
| **A101** | X-003, X-011 (`AI-807`) | 2 | 0 | 0 | 1 |

Prior FPs cleared; prior currency / id / language FNs now caught. Remaining qualitative miss on A101: premature
“booked” wording before `rebook` (no dedicated catalogue ID), reported in the *Unlabelled* column.

**v3.3.0 totals (catalogue-scoped):** TP=6 FP=0 FN=0 → precision **1.00**, recall **1.00** over catalogue defects.
**Unlabelled misses: 1** (A101 premature “booked” wording).

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

| Agent | TP | FP | FN | Precision | Recall | Unlabelled | Notes |
|-------|----|----|----|-----------|--------|------------|-------|
| **A102** | 0 | 0 | 0 | — | — | 1 | Happy path completes (walk + INR compensation). Qualitative: walked to `HTL-BOM-01` (own hotel) instead of search hit `HTL-BOM-PEER` — id not ungrounded so X-011 silent, and no catalogue ID covers it. |
| **A103** | 0 | 0 | 0 | — | — | 0 | Clean dispatch + INR credit + close on degraded/down; healthy site correctly skipped. |
| **A104** | 3 | 0 | 0 | 1.00 | 1.00 | 0 | TP: tool-budget storm (T5-006), invented `ILL-12345`/`ILL-67890` (T6-003), ungrounded `TRK-678901234` in answer (X-011). Cascade started when the model stripped the `ISBN-` prefix the backend keys use. |

**Round-2 totals (catalogue-scoped):** TP=3 FP=0 FN=0 → precision **1.00**, recall **1.00** over catalogue defects.
**Unlabelled misses: 1** (A102 partner-hotel argument).

These are our current measured results; we are constantly working to improve precision and recall, and we update this page as new held-out measurements land.

### Unlabelled misses (no catalogue check ID)

These are real auditor-found issues, listed so they are not lost. No catalogue check covers them yet, so they are
outside the catalogue-scoped precision and recall above and are counted separately in the *Unlabelled* column.
- A102: partner-hotel arg ignores `find_partner_room` options (uses origin hotel id).
- A101 (round 1): premature “booked” prose before `rebook`.

For completeness, A104's ISBN key-format brittleness (`ISBN-978-…` vs `978-…`) is not an unlabelled miss: it started
the cascade that T5-006, T6-003 and X-011 correctly flagged, so it is already inside the catalogue-scoped TP count.

---

## Links
- Reference agents (HF): https://huggingface.co/srinivaspadmanabhuni/agentic-ai-reference-agents
- Viewer Space: https://huggingface.co/spaces/srinivaspadmanabhuni/agentic-ai-reference-agents-viewer
- Checklist dataset: https://huggingface.co/datasets/srinivaspadmanabhuni/agentic-ai-test-checklist-110
- agentest v3.3.0 tag: https://github.com/srpadmanabhuni/agentest/releases/tag/v3.3.0
- Verdict cell explanations: [standards/VERDICT-DIFF-3.3.0.md](standards/VERDICT-DIFF-3.3.0.md)
