# r12-prep Phase 1 (Fixes 5, 7, 8) - NOT part of the round 11 rules

Branch `r12-prep` off `r11-rules` (freeze ref edee9cc + RULES_FREEZE.md f303498). Round 11 is scored from `r11-rules`, never from here.

## Fix 5 - shared helpers: `agentest.standards.textnorm`

`find_amounts` / `money_values` / `amount_grounded` / `is_zero_amount` / `parse_number` / `to_number`;
`fold` / `strip_punct` / `tokens` / `has_token` / `same_token` / `contains_any` / `scripts`.
Handles `INR 3,50,000`, `350000 rupees`, `Rs 350000/-`, `₹3.5 lakh`, `2.5 lakhs`, `1 crore`, `1.5cr`, `$1.2k`, `USD 1,200.00`,
`500 रुपये`, `500 ரூபாய்`, Devanagari digits `₹ ३,५०,०००`, zero amounts (`Rs. 0`, `₹0.`, "zero rupees", "nil"); IDs (`AB-1234`)
and dates (`2026/10/30`) are not amounts; `5L` = 5 lakh but `5 L` is 5; `examiners.` == `Examiners`, `re-examiners` != `examiners`,
`स्वीकृत।` matches `स्वीकृत`, full-width text folds to ASCII. Tests: tests/test_r12_textnorm.py.

### Migrated now (no verdict change)
- `_num`: rules.py defined it **three times** (L2438 loose `float(x.replace(",",""))`, L2781 loose `float(str(v)...)`,
  L5572 strict + round(2)). Python rebinds the name, so only the last was ever in effect for all 11 rules that call it
  (T1-002, T1-005, T1-015, T2-010, T6-001, T7-009, X-012, X-013, X-027, X-031, X-054). The two dead copies are removed
  and `_num` is now `textnorm.to_number` (identical semantics). Control gate and full suite unchanged.

### Inventory - own number/currency or token regex, candidates to migrate under the r12 freeze
| Helper in rules.py | Rules affected | Migration | Expected behaviour change |
|---|---|---|---|
| `NUM_RX` (prefix-only currency) via `_grounded` | X-012, X-013, T1-002, T1-005, T7-009 | `find_amounts(money_only=True)` | **More** amounts checked: suffix currency (`350000 rupees`), lakh/crore scales, `$1.2k` -> new grounding fails possible, and fewer false "ungrounded" when the source writes the same value in another format |
| `CURRENCY_SYM_RX` / `_currency_tokens` | X-012 | `find_amounts` currency field | currency words in Indian languages count as tokens |
| `_FACT_NUM_RX`, `_reply_facts`, `_cf_sig` | T7-007 | `find_amounts` + `tokens` | scale words normalised: "3.5 lakh" vs "350000" compare equal across counterfactual pairs (fewer FPs) |
| `num_rx` in `_t6_002` | T6-002 | `find_amounts` | IDs/dates no longer read as numbers |
| `_count_written`, `MONEY_STEMS` | X-001 | `find_amounts` + `has_token` | currency word stems shared |
| `_result_quantities`, `_ungrounded_quantities`, `_credit_kind_mismatch` | X-031 | `find_amounts` | lakh/crore and Indian grouping |
| `_plain_num`, `_numeric_fields` | X-038 | `to_number` | none expected |
| `_num_set`, `_tool_facts`, `_x_054` | X-048, X-054 | `find_amounts`, `is_zero_amount` | zero-amount handling unified (r11 already special-cases it) |
| `_x_047`, `_x_051`, `_x_030`, `_scheduled_as_done`, `_t2_010`, `_constraint_check`, `_counter_pairs` | X-047, X-051, X-030, X-027, T2-010, T6-001, T1-015 | `to_number` / `find_amounts` | minor |
| punctuation strips `.strip(".,;:'\"")`, `.rstrip(".,;")` | T1-002 (`_denied_objects`), T6-007, X-001, T6-012 (`_correction`) | `strip_punct` / `same_token` | any script's punctuation (। « ») stripped, not only ASCII |
| tokenisers `_tokens`, `_words`, `_has_denial`, `_failed_action_claims`, `_final_money_claims`, `_embedded_tokens` | T6-001, X-038, X-045; T2-011, T3-004, T7-009, X-025-X-053 (20 rules via `_words`); T1-002, T1-005, T1-008 | `tokens` / `has_token` | NFKC + casefold: full-width and ligature forms match |

Each migration is a rules change: do it on r12-prep only, then run the control gate and the dev re-score before the r12 freeze.

## Fix 7 - pre-scoring integrity validator
See TRACE_SCHEMA.md. Catches round 10 run 1 on all 10 agents; passes the fixed export.

## Fix 8 - clean-control gate: `scripts/control_gate.py`
Pool (fixtures/controls/pool.json): audited-clean controls of scored rounds only - r7 A127, r8 A133, r10 A151; offline judge-cache replay.
Excluded: A118, A122, A155 (audits found defects), A113/A115/A116 (not bundled), any r11 agent (unscored), TRAIL / Who&When.

Today (examples and strict, identical): **FAIL - 4 checks fire, all on r10 A151** (the same 4 FAs as r10 SCORE.md):
- T5-015 and X-003: "same reason for 2 different tools" (reason-specificity heuristic; 93/124 calls ok)
- X-035: `reason` argument not declared in the tool's inputSchema (agent passes an extra arg) - arguably a real schema
  violation; needs a decision whether an extra optional arg is misuse
- X-042: idempotent follow-up re-run flagged as duplicated side effect although the guard held ("already processed")
A127 and A133: 0 fire. 1 not-assessed on A151 (X-029, single signal).
