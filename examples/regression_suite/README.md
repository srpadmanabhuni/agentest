# Regression suite example

A ready-to-copy config filled in from [templates/regression.yaml](../../templates/regression.yaml) for the bundled `refill_bot` agent in [examples/agnostic_demo/](../agnostic_demo/agents/refill_bot/agent-card.json).

Install agentest first:

```bash
pip install agentest-ai
```

## Run from the repository root

```bash
agentest std run --agents examples/agnostic_demo/agents --agent refill_bot \
  --config examples/regression_suite/regression.yaml \
  --ids T1-018,T2-001,T2-005,T4-009,T7-014 --strict
```

Observed output:

```text
refill_bot: 5 pass, 0 fail
total: 5 pass, 0 fail, 0 n/a over 1 agents x 5 IDs (examples)
```

If you point the same command at `refill_bot_buggy` instead of `refill_bot`, the run fails and exits `1` because `--strict` turns any check failure into a non-zero exit code.

## Adapting it to your own agent

1. Copy `examples/regression_suite/regression.yaml` into your repository.
2. Replace `--agents ... --agent refill_bot` with your own OTLP traces (`--otlp traces.otlp.jsonl --card agent-card.json --tools tools.json`).
3. List the check IDs that already pass on your fixed traces under `--ids`, and adjust `thresholds` to match your agent's normal step, tool-call, and success-rate limits.
4. Keep `disable: []` so every graduated check can fail CI; only add an ID to `disable` temporarily if you intentionally waive it while fixing a known issue.

See [Capability suites and regression suites](../../docs/guides/CAPABILITY-AND-REGRESSION-SUITES.md) for how checks graduate from a capability report to a `--strict` regression gate.
