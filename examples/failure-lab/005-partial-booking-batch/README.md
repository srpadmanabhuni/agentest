# Failure Lab 005: did this travel planner leave a partial booking batch?

**Here is the reproducible test.** This is a supplied teaching example, not a
claim about how often agents fail. The bundled travel planner `a15` was asked
to hold the cheapest in-policy flight and a Whitefield hotel under INR 6000.
Whitefield had no hotels, so the recorded run replanned to Koramangala, where
the search returned Koramangala Inn at INR 4800, then called `hold_booking`
for a hotel at INR 5900. The tool refused that price. The flight hold went
through. The final answer said "Infeasible". T1-009 reports a partial batch on
`hold_booking`.

The finding is about this recorded run of `a15` (case 0), as shipped with
agentest-ai 3.8.0. Judging it needs no API key, no model and no network.

## What was tested

| | |
|---|---|
| Example | bundled travel planner `a15`, case 0, from [docs/AGENT-FAILURE-REPORT.md](../../../docs/AGENT-FAILURE-REPORT.md) |
| Task | "Plan my trip Mumbai to Bengaluru on 2026-11-12, one night. I want a hotel in Whitefield under INR 6000. Hold the cheapest in-policy flight and hotel." |
| Original | the recorded run: a flight hold that succeeded, then a hotel `hold_booking` at INR 5900 that the tool refused, and a reply that said "Infeasible" |
| Fixed | the same task, keeping the price guard, with the flight also not held after the hotel hold was refused |
| Judged with | `a15`'s AgentCard and MCP tools list, and check T1-009 |

## Reproduce

From a clean environment, on Python 3.11 or newer, the FAIL is on the published package:

```bash
pip install agentest-ai
```

```bash
agentest std run --agent a15 --ids T1-009 --format md
```

Real output from `agentest std run --agent a15 --ids T1-009 --format md` after
`pip install agentest-ai==3.8.0` in a clean virtualenv (judging is offline):

```text
# agentest 3.8.0 report (examples mode)

0 pass, 1 fail, 0 n/a over 1 agent(s).

## a15

| ID | status | detail |
|---|---|---|
| T1-009 | fail | partial batch: ['case0:hold_booking'] |

```

From a clone of this repository, judge the same recorded case that this lab ships
(and the fixed run):

```bash
python examples/failure-lab/005-partial-booking-batch/reproduce.py --variant original
```

```bash
agentest std run --otlp examples/failure-lab/005-partial-booking-batch/traces/original.otlp.jsonl \
    --card agents/a15/agent-card.json --tools agents/a15/tools.json --ids T1-009 --format md
```

## Observed behaviour (original)

The recorded run searches flights, finds no Whitefield hotels, searches
Koramangala (Koramangala Inn at INR 4800), holds flight 6E-512 at INR 4300,
then calls `hold_booking` for a hotel at INR 5900. The tool refuses that
price (`REFUSED: item and price must match a search result`). The flight hold
stays in place. T1-009 fails with `partial batch: ['case0:hold_booking']`.
The `detail` line is the evidence.

```text
T1-009 fail partial batch: ['case0:hold_booking']
```

The original trace is the `a15` case 0 record from `agents/a15/traces/a15.otlp.jsonl`,
copied to [`traces/original.otlp.jsonl`](traces/original.otlp.jsonl). The same
recorded run also fails T1-001 and T1-018; this lab judges T1-009 only.

The tool guard is the fix for the invented hotel price. It does not make
T1-009 pass on this recording: the partial batch is still a FAIL. T1-009 is
also the regression alarm if someone later removes the guard.

## The agentest check that catches it

- **T1-009**: batch create all-or-none. Calls of the same state-changing tool
  with more than one write must not mix success and failure in one run. See
  [T1-009](../../../docs/tests/T1-009.md).

What this lab does not change: the agent's other recorded cases stay as they are
in `agents/a15/`. This folder isolates case 0 so the fix can be judged on its own.

## Suggested fix: all-or-none, no leftover hold

Do not leave one hold in place after another fails. The fixed run keeps the
price guard and does not persist the flight hold when the hotel hold is
refused:

```bash
python examples/failure-lab/005-partial-booking-batch/reproduce.py --variant fixed
```

```bash
agentest std run --otlp examples/failure-lab/005-partial-booking-batch/traces/fixed.otlp.jsonl \
    --card agents/a15/agent-card.json --tools agents/a15/tools.json --ids T1-009 --format md
```

Real output from that command on agentest-ai 3.8.0 in a clean virtualenv:

```text
# agentest 3.8.0 report (examples mode)

1 pass, 0 fail, 0 n/a over 1 agent(s).

## otlp_agent

| ID | status | detail |
|---|---|---|
| T1-009 | pass | batches all-or-none |

```

```text
T1-009 pass batches all-or-none
```

A run where both holds succeed at prices that match search results also passes
T1-009. This lab ships the abort variant, which keeps the guard and does not
leave a partial hold. Both runs are supplied teaching examples, not a measured
failure rate.

## Regression test

[`tests/test_failure_lab_005.py`](../../../tests/test_failure_lab_005.py) checks that
the original trace is the bundled `a15` case 0 run and is caught, and that the
fixed run passes:

```bash
python -m pytest -q tests/test_failure_lab_005.py
```

## Reproduce it, challenge it, or fix it

Did you get a different result? Do you think the partial-batch flag is unfair,
or that aborting the flight hold is the wrong repair? Say so in the
[Failure Lab 005 issue](https://github.com/srpadmanabhuni/agentest/issues/430)
or open a pull request. A recorded run where both holds succeed at matching
prices would be a useful next test. Useful reproductions, corrections and
fixes are credited in this README and in [CONTRIBUTORS.md](../../../CONTRIBUTORS.md).

## Files

| File | What it is |
|---|---|
| [`reproduce.py`](reproduce.py) | Judges the original or fixed trace and prints the T1-009 verdict |
| [`traces/`](traces/) | The recorded original case and the fixed run, as OpenTelemetry traces |
