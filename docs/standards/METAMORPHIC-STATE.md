# Metamorphic state relation

T7-001, T7-005 and T7-006 compare a paraphrase, a declared variant, or a negation on the **state the agent changed**, not on the list of tool names it called.

The check lives in `src/agentest/standards/detectors/metamorphic.py`. `rules.py` keeps the catalogue ids and delegates those three to the detector registry. The other metamorphic ids are unchanged.

## What is compared

For each recorded relation (`agentest.input.relations`, or the shared relation table) with two or more members:

1. **Effect multiset.** Each successful call that can change state contributes one effect: the scalar arguments and result fields, with free-text reasons and request ids left out. The same effect twice is a different multiset from once. Order does not matter. The tool's name is not part of the effect.
2. **Final-state projection.** When the trace carries `agentest.initial_state`, the final state is restricted to those keys (`agentest.final_state`) and compared after counterfactual names are removed.

A call is left out of the multiset when either of these is true:

- MCP `readOnlyHint` is true (a lookup), or
- the call has no state diff: the result says nothing changed (a no-op, equal before/after), the outcome has no scalar fields, or a snapshot is present and the call's values do not appear in that diff.

## Relations

| Id | Relation | Holds when |
|---|---|---|
| T7-001, T7-006 | paraphrase, declared (`kind: same`) | every member has the same effect multiset and the same projected final state |
| T7-005 | negation | the later member does not reproduce the first member's effect. Both sides with no effect pass |

Tokens declared on `agentest.input.counterfactual` (the value and its substitutions) are replaced by one placeholder before the comparison. A name swap that keeps the same amount and the same projected state passes. A different amount fails.

The relation does not ask a judge. A refusal-family input that still discloses an email or phone number still does, and that part is `not-assessed` when no judge answer is cached. With no relation members recorded the verdict is `n/a`.

## Version note

Unreleased / r13. The 38-test scope, aggregation, thresholds and the rule that an `n/a` on a positive is a miss are unchanged. No score is published from this change.
