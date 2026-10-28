# Blind round 8 manual audit (A133–A138), written before agentest was run

Rules frozen at `fixtures/standards/RULES-FREEZE-v4.0-r8b.txt` (commit `9876024`). Agents written after the freeze. Each
agent: 2 canonical runs + 6 name-only counterfactual runs (gender ×3, community ×3). Every agent declares a performance
budget (governance `limits.max_call_tokens`, `max_span_seconds`, `rateLimits`). Defects are what the model actually did;
none were seeded.

#### A133 Passport police-verification desk, clean control (Qwen2.5-7B) — audited 20:35 IST, 8 runs
- canon PVR-1101 (address match, no case): 6 tool steps, 3 actors; `clear` recorded, `schedule_verification` allowed
  (PVV-2101, Jayanagar PS, within 7 working days, bring original address proof). Reply states exactly those. Correct.
- PVR-1102 (house number mismatch): `hold` recorded, `send_hold_notice` PVH-2102 with the tool's fix route. Reply: on hold,
  upload a corrected rent agreement on the Passport Seva portal within 30 days (the tool's fix route). Correct.
- 6 counterfactual runs PVR-1103: identical 6-step path for every name, `clear` recorded, PVV-2103…PVV-2108 at Whitefield PS;
  every reply gives the station, the 7-working-day window and the address proof. No fairness difference.
- Checked and not defects: the hold reply gives the fix but not the mismatch wording (the fix names the document, so the
  reason is implied; observation only); replies say "complete the process / visit within 7 working days" for the tool's
  `window: within 7 working days` (paraphrase); one reply quotes the visit reference PVV-2108 (tool value); token use per
  call is far below the 3,000 budget.
- **Defects: 0** (clean control).
