# Asserting end state, not just the tool call

**Short answer:** agentest judges what is in the recorded run. A tool call that ran is not proof the effect landed. To grade the final browser or page state separately from the tool call, you need three things in the same run: (1) the tool call, (2) a later read of the state, recorded in the trace, and (3) a postcondition that compares that read against the expected end state.

## The cart example

User: "Add the wireless headphones to my cart."

The agent calls `add_to_cart`, then reads the cart back, then says "Done — the headphones are in your cart." If the add silently failed, the later read is what catches it:

1. **The tool call happened.** The trace shows `add_to_cart` ran. On its own, that proves only that the call was made.
2. **A later read of the state is in the trace.** The agent reads the cart back (a `get_cart` call, or a read of the cart page) after the add. That read's result is recorded as the run's end state, `agentest.final_state` — for example:

   ```json
   {"cart": {"items": []}}
   ```

3. **A postcondition compares that read.** Publish the expected end state as `postconditions` in the AgentCard governance extension (`urn:agentest:a2a-ext:governance:v1`):

   ```json
   "postconditions": {
     "byExample": [
       {
         "example": "Add the wireless headphones to my cart.",
         "criteria": [
           {"path": "cart.items", "op": "nonempty"},
           {"path": "cart.items.0.name", "op": "contains", "value": "headphones"}
         ]
       }
     ]
   }
   ```

   Adapt the paths and values to the shape of your own `final_state` — the paths above assume the end state is `{"cart": {"items": [...]}}`, with each item having a `name`.

With the empty cart above, both criteria fail: `cart.items` is empty, so there is no `cart.items.0.name`. If the reply still claims success, [T1-002](../tests/T1-002.md) and [T1-018](../tests/T1-018.md) fail the run as a false completion — a success claim with unmet postconditions. [T1-001](../tests/T1-001.md) judges the first canonical run against the same postconditions.

If there is no later read in the trace, there is nothing to compare: agentest can see that the add call ran, but it cannot see whether the item is in the cart. Record the read. To see, run by run, which criteria applied and what value was observed at each path, use:

```bash
agentest std postconditions --agents <agents-dir> --agent <agent>
```

Validate the card first with `agentest std validate`, which rejects a malformed criterion (unknown `op`, missing `path`, or a missing `value` where one is required).

agentest does not read a page screenshot or snapshot on its own. It reads the end state your harness records as `agentest.final_state` (see [TRACE-FORMAT.md](../TRACE-FORMAT.md)). If your harness already produces a page snapshot, record the values you want judged from it in `final_state`. Passing a raw snapshot in as the end state is not a supported input today; if you need it, open a follow-on issue.

## Vague goals: what is the end state compared against?

User: "Get me a good monitor."

agentest compares the end state against the postconditions **you** wrote — not against an inferred idea of "good". There is no built-in notion of a good monitor, a good price, or a good size. If you do not write down what "good" means in checkable terms, agentest cannot grade it.

Pin "good" down in `byExample`, keyed by the request text. For example, if "good" means at least 27 inches, IPS, and at most $300 in your test, write exactly that (adapt the paths to your `final_state`):

```json
"postconditions": {
  "byExample": [
    {
      "example": "Get me a good monitor.",
      "criteria": [
        {"path": "cart.items.0.size_inches", "op": "ge", "value": 27},
        {"path": "cart.items.0.panel", "op": "contains", "value": "IPS"},
        {"path": "cart.items.0.price", "op": "le", "value": 300}
      ]
    }
  ],
  "default": [
    {"path": "cart.items", "op": "nonempty"}
  ]
}
```

Keep `default` for invariants that must hold on every request. A request-specific end state belongs in `byExample`, not in `default`: a `default` that expects a particular monitor would also be applied to unrelated requests ("What are your opening hours?"), where it cannot hold.

Two things to watch:

- `byExample` matches the recorded input text, not the input id. A paraphrase ("Find me a nice monitor") does not match the example above; it falls through to `default`. Add a `byExample` row for each wording you test, or keep the fallback `default` partial.
- Criteria on one example are all required. There is no "one of these values" operator. If the same request may correctly end in more than one state, write only the conditions that hold in every acceptable ending.

If you cannot state what "good" means in checkable terms, narrow the test request until you can, or judge the outcome in your own harness and emit a `gen_ai.evaluation.result` event on the trace. In `--mode strict`, published postconditions are ignored and only those events are used as the success signal.

## Further reading

- [Tutorial 7: writing expected outcomes for your own agent](../tutorials/07-writing-expected-outcomes.md) — postconditions, `byExample`/`byInput`/`default`, open-ended requests, and testing the criteria themselves.
- [TRACE-FORMAT.md](../TRACE-FORMAT.md) — how to emit `agentest.final_state`.
- [EXTENSION.md](../standards/EXTENSION.md) and [AGENT-CARD.md](../developers/AGENT-CARD.md) — the postcondition fields.
- [T1-001](../tests/T1-001.md), [T1-002](../tests/T1-002.md), [T1-018](../tests/T1-018.md) — the checks that apply postconditions.
- [Reading the report](../READING-THE-REPORT.md) — how to read a false-completion `fail` in the report.
