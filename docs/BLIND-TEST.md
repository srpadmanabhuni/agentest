# Blind test — multi-agent desks vs agentest

Two rounds against frozen agentest builds. Agents are genuine multi-agent desks (local Qwen2.5-7B, nested
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

## Links
- Reference agents (HF): https://huggingface.co/srinivaspadmanabhuni/agentic-ai-reference-agents
- Viewer Space: https://huggingface.co/spaces/srinivaspadmanabhuni/agentic-ai-reference-agents-viewer
- Checklist dataset: https://huggingface.co/datasets/srinivaspadmanabhuni/agentic-ai-test-checklist-110
- agentest v3.3.0 tag: https://github.com/srpadmanabhuni/agentest/releases/tag/v3.3.0
- Verdict cell explanations: [standards/VERDICT-DIFF-3.3.0.md](standards/VERDICT-DIFF-3.3.0.md)
