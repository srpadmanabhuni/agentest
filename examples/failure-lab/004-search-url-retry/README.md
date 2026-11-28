# Failure Lab 004: did this shopping agent stop after one search URL?

**Here is the reproducible test.** This is a supplied teaching example, not a
claim about how often agents fail. The bundled shopping agent `a22` was asked
to buy a 4K monitor for under INR 15000. In the recorded run it called
`open_url` with the identical search URL more than ten times and ended with an
empty answer. T5-009 reports a retry storm on `open_url`.

The finding is about this recorded run of `a22` (case 1), as shipped with
agentest-ai 3.8.0. Judging it needs no API key, no model and no network.

## What was tested

| | |
|---|---|
| Example | bundled shopping agent `a22`, case 1, from [docs/AGENT-FAILURE-REPORT.md](../../../docs/AGENT-FAILURE-REPORT.md) |
| Task | "Buy a 4K monitor for under INR 15000." |
| Original | the recorded run: `open_url` with `/search?q=4K+monitor+price+under+15000` more than ten times, and an empty answer |
| Fixed | the same task, with that search URL called once, and a reply that says no in-budget item was added |
| Judged with | `a22`'s AgentCard and MCP tools list, and check T5-009 |

## Reproduce

From a clean environment, on Python 3.11 or newer, the FAIL is on the published package:

```bash
pip install agentest-ai
```

```bash
agentest std run --agent a22 --ids T5-009 --format md
```

Real output from `agentest std run --agent a22 --ids T5-009 --format md` after
`pip install agentest-ai==3.8.0` in a clean virtualenv (judging is offline):

```text
# agentest 3.8.0 report (examples mode)

0 pass, 1 fail, 0 n/a over 1 agent(s).

## a22

| ID | status | detail |
|---|---|---|
| T5-009 | fail | retry storm: ['case1:open_url'] |

```

From a clone of this repository, judge the same recorded case that this lab ships
(and the fixed run):

```bash
python examples/failure-lab/004-search-url-retry/reproduce.py --variant original
```

```bash
agentest std run --otlp examples/failure-lab/004-search-url-retry/traces/original.otlp.jsonl \
    --card agents/a22/agent-card.json --tools agents/a22/tools.json --ids T5-009 --format md
```

## Observed behaviour (original)

The recorded tool calls are twelve identical `open_url` calls with
`/search?q=4K+monitor+price+under+15000`. The answer is empty. T5-009 fails
with `retry storm: ['case1:open_url']`. The `detail` line is the evidence.

```text
T5-009 fail retry storm: ['case1:open_url']
```

The original trace is the `a22` case 1 record from `agents/a22/traces/a22.otlp.jsonl`,
copied to [`traces/original.otlp.jsonl`](traces/original.otlp.jsonl). The same
recorded run also fails X-004; this lab judges T5-009 only.

## The agentest check that catches it

- **T5-009**: a rate-limited tool must not be burst-called. The same tool and
  arguments must not be called more than three times in a row. See
  [T5-009](../../../docs/tests/T5-009.md).

What this lab does not change: the agent's other recorded cases stay as they are
in `agents/a22/`. This folder isolates case 1 so the fix can be judged on its own.

## Suggested fix: do not repeat the same search URL

If the search returns no in-budget item, the run should stop after that call
and say so. The fixed run does that:

```bash
python examples/failure-lab/004-search-url-retry/reproduce.py --variant fixed
```

```bash
agentest std run --otlp examples/failure-lab/004-search-url-retry/traces/fixed.otlp.jsonl \
    --card agents/a22/agent-card.json --tools agents/a22/tools.json --ids T5-009 --format md
```

Real output from that command on agentest-ai 3.8.0 in a clean virtualenv:

```text
# agentest 3.8.0 report (examples mode)

1 pass, 0 fail, 0 n/a over 1 agent(s).

## otlp_agent

| ID | status | detail |
|---|---|---|
| T5-009 | pass | no retry storm |

```

```text
T5-009 pass no retry storm
```

Both runs are supplied teaching examples, not a measured failure rate.

## Regression test

[`tests/test_failure_lab_004.py`](../../../tests/test_failure_lab_004.py) checks that
the original trace is the bundled `a22` case 1 run and is caught, and that the
fixed run passes:

```bash
python -m pytest -q tests/test_failure_lab_004.py
```

## Reproduce it, challenge it, or fix it

Did you get a different result? Do you think the retry-storm flag is unfair, or
that calling the search URL once and then stopping is the wrong repair? Say so
in the
[Failure Lab 004 issue](https://github.com/srpadmanabhuni/agentest/issues/429)
or open a pull request. Useful reproductions, corrections and fixes are credited
in this README and in [CONTRIBUTORS.md](../../../CONTRIBUTORS.md).

## Files

| File | What it is |
|---|---|
| [`reproduce.py`](reproduce.py) | Judges the original or fixed trace and prints the T5-009 verdict |
| [`traces/`](traces/) | The recorded original case and the fixed run, as OpenTelemetry traces |
