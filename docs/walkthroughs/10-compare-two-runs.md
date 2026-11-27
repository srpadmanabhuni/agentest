# Compare two saved runs with `std diff`

When you fix an agent and re-run checks, you want to see which checks moved from `fail` to `pass`—and fail CI if anything newly broke. `agentest std diff OLD.json NEW.json` compares two saved `agentest std run --format json` files check by check.

Install from PyPI, then run the commands below from the repository root so the bundled traces exist on disk:

```bash
pip install agentest-ai
```

## Save two JSON reports

Run the buggy and fixed `refill_bot` traces in [examples/agnostic_demo/](../../examples/agnostic_demo/agents/refill_bot/agent-card.json) through `--otlp` so both reports use the same `otlp_agent` key:

```bash
mkdir -p build
agentest std run \
  --otlp examples/agnostic_demo/agents/refill_bot_buggy/traces/refill_bot_buggy.otlp.jsonl \
  --card examples/agnostic_demo/agents/refill_bot_buggy/agent-card.json \
  --tools examples/agnostic_demo/agents/refill_bot_buggy/tools.json \
  --ids T1-018,T2-001,T4-003,T7-014 \
  --format json --out build/old.json

agentest std run \
  --otlp examples/agnostic_demo/agents/refill_bot/traces/refill_bot.otlp.jsonl \
  --card examples/agnostic_demo/agents/refill_bot/agent-card.json \
  --tools examples/agnostic_demo/agents/refill_bot/tools.json \
  --ids T1-018,T2-001,T4-003,T7-014 \
  --format json --out build/new.json
```

## Diff the two reports

```bash
agentest std diff build/old.json build/new.json
```

Output:

```text
newly failing: 0
newly passing: 4

otlp_agent
  T1-018  fail -> pass
  T2-001  fail -> pass
  T4-003  fail -> pass
  T7-014  fail -> pass
```

Only checks whose status changed are printed; unchanged checks are omitted so regressions stand out.

## Catch regressions with `--fail-on-new-fail`

In CI, pass `--fail-on-new-fail` when comparing the current run against your saved baseline. With `--fail-on-new-fail`, `agentest std diff` exits `1` whenever any check's new status becomes `fail` (and `0` otherwise). Reversing the two files above shows a regression:

```bash
agentest std diff build/new.json build/old.json --fail-on-new-fail
```

```text
newly failing: 4
newly passing: 0

otlp_agent
  T1-018  pass -> fail
  T2-001  pass -> fail
  T4-003  pass -> fail
  T7-014  pass -> fail
```

Because four checks became `fail`, the command exits with status `1`.

See [Reading the report](../READING-THE-REPORT.md) for the verdict JSON format, or return to the [walkthrough index](README.md).
