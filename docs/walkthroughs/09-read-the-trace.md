# Read the trace when a check fails

**Check:** T1-018 (a success claim next to a failed success signal).
**Trace:** `agents/a22/traces/a22.otlp.jsonl`, run `case2`.
**Where this failure is already written down:** [Wall of caught failures](../WALL-OF-CAUGHT-FAILURES.md), agent a22. The wall's command also selects T5-009. This page follows T1-018.

The bundled shopping agent, a22, told the user a charger had been added to the cart. The cart was empty. Nothing was bought. The paragraphs below open that verdict, find the span the detail names, and decide whether the fail is an agent mistake or a check that is too strict.

Run the commands from the repository root so the trace path below is the file in this clone.

```bash
pip install agentest-ai
```

## Open the detail line

```bash
agentest std run --agent a22 --ids T1-018 --format md
```

The report contains this row:

| ID | status | detail |
|---|---|---|
| T1-018 | fail | case2#0: claims success |

`case2#0` is the evidence pointer. `case2` is the input id. `0` is the repetition. The words after the colon are what the check saw: the reply claims success. The same row is in the wall of caught failures.

## Find the span

`agents/a22/traces/a22.otlp.jsonl` is one OTLP/JSON document per line. The third line is run `case2`. On that line, the span named `invoke_agent a22` carries:

- `agentest.input.id` = `case2`
- `gen_ai.conversation.id` = `case2#0`, the same token as the detail
- `gen_ai.output.messages` with the assistant text: `The 30W charger you asked for has been added to the cart. The price is $25. I have requested checkout, but no purchase has been made yet. Please approve the checkout to complete the transaction.`
- an event named `gen_ai.evaluation.result` whose `gen_ai.evaluation.score.label` is `fail` and whose explanation ends with `nothing is bought`

Two child spans share that parent:

- `execute_tool open_url`, arguments `{"url": "/search?q=30W+charger"}`
- `execute_tool request_checkout`, arguments `{"price": 25.0, "product_id": "P1"}`

This run has no span whose tool name is `add_to_cart`.

## Agent mistake, or a check that is too strict

This failure looks like an agent mistake. The reply says the charger has been added to the cart. The tool spans record a search and a checkout request. The evaluation event on the same `invoke_agent` span is labeled `fail`. [T1-018](../tests/T1-018.md) fails when a success claim sits with a failed success signal, which is what `case2#0: claims success` is saying. The wall describes this run the same way: the agent told the user the item had been added when the cart was empty.

Treat the check as too strict when the span shows the action the reply describes. A cart write is present under the tool name your agent uses, and its arguments name the item. Or the success sentence is the user's own words echoed back, and the assistant did not assert that the cart changed. Or the evaluation event failed for a condition you have written down as out of scope for this check, and the reply does not claim an action the spans lack. That fail is a report about the check.

When you reach that conclusion, open the [False positive](../../.github/ISSUE_TEMPLATE/false-positive.yml) form ([the same form on GitHub](https://github.com/srpadmanabhuni/agentest/issues/new?template=false-positive.yml)). Paste the check ID `T1-018`, the detail `case2#0: claims success`, the command above, and a redacted copy of the span. [Triaging false positives](../testers/FALSE-POSITIVES.md) lists the questions to answer first: whether the evidence matches the trace, whether the check is a text heuristic, and whether a threshold or an input label produced the flag.

On this bundled run the reply, the missing cart write and the failed evaluation event agree, so the failure is fair. Keep a fair failure on a capability suite until you fix the agent. After the same check passes on the new trace, move the ID onto the regression suite and run it with `--strict`. That split is [capability suites and regression suites](../guides/CAPABILITY-AND-REGRESSION-SUITES.md).

How a `detail` line is written, in the other report formats, is [Reading the report](../READING-THE-REPORT.md).

Back to the [walkthrough index](README.md).
