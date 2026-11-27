# Capability suites and regression suites

AiEnsured agentest, an Agentic AI Testing platform, can run the same check IDs in two ways. A **capability suite** is a report: you are still learning which checks fail on traces from real runs, and a low pass rate is expected. A **regression suite** is the short list that has graduated. You run that list with `--strict` so CI exits 1 when one of those checks fails again.

Install:

```bash
pip install agentest-ai
```

Copy [templates/capability.yaml](../../templates/capability.yaml) and [templates/regression.yaml](../../templates/regression.yaml). Both files use the config keys the runner already reads. The `--ids` flag on the command is the suite. For a filled-in regression config wired to the bundled `refill_bot` agent, see [examples/regression_suite/](../../examples/regression_suite/README.md).

## What each suite is for

**Capability suite.** Pass `--config` and a wide `--ids` list. Leave `--strict` off. Write a Markdown or JSON report and read every `fail`. The checks in [templates/capability.yaml](../../templates/capability.yaml) are examples from the [wall of caught failures](../WALL-OF-CAUGHT-FAILURES.md): T1-018, T4-001, T5-009, T6-007 and T7-014. Swap in the IDs that fail on your own traces.

```bash
agentest std run --otlp traces.otlp.jsonl --card agent-card.json --tools tools.json \
  --config templates/capability.yaml \
  --ids T1-018,T4-001,T5-009,T6-007,T7-014 \
  --format md --out capability.md
```

**Regression suite.** Pass `--config`, the graduated IDs, and `--strict`. `--strict` makes `agentest std run` exit 1 when any selected check fails. `--mode strict` is a different flag: it limits which trace fields a check may read. The CI exit code is `--strict`.

The example IDs in [templates/regression.yaml](../../templates/regression.yaml) are T1-018 and T2-001. On the bundled fixed agent `refill_bot` those two checks pass (walkthroughs [1](../walkthroughs/01-verify-before-acting.md) and [3](../walkthroughs/03-claims-success-it-did-not-earn.md)). Replace them with IDs that pass on the trace you fixed.

```bash
agentest std run --agents examples/agnostic_demo/agents --agent refill_bot \
  --config templates/regression.yaml --ids T1-018,T2-001 --strict
```

In CI, point the same flags at your trace and ask for JUnit:

```bash
agentest std run --otlp traces.otlp.jsonl --card agent-card.json --tools tools.json \
  --config templates/regression.yaml --ids T1-018,T2-001 \
  --format junit --out agentest.xml --strict
```

A job that should stay green uses the regression command. A job that is still collecting failures uses the capability command. [CI integration](../developers/CI.md) shows `--strict` with JUnit on a workflow step.

## Keys the config file already accepts

`--config` (or the environment variable `AGENTEST_CONFIG`) loads a YAML or JSON file. The reader applies four keys, documented in the [User Guide](../USER-GUIDE.md) and the [CLI reference](../developers/REFERENCE.md):

| Key | What the runner does with it |
|---|---|
| `disable` | Those IDs are reported as `n/a` with detail `disabled by config`, including when `--ids` also names them. |
| `thresholds` | Overrides `steps`, `tokens`, `seconds`, `tool_calls`, `retries`, `burst` and `success_rate`. Built-in defaults are steps 12, tokens 20000, seconds 600, tool_calls 20, retries 3 and burst 5. `success_rate` defaults to 2/3 when the AgentCard publishes none. |
| `rules_dir` | Imports extra rule modules from that directory, relative to the config file. |
| `scenarios` | Loads extra conformance scenarios from a YAML file in the same shape as the built-in scenarios file. |

A limit published on the AgentCard takes precedence over `thresholds`. Facts about who may call a tool belong on the card, in the governance extension, which the [extension note](../standards/EXTENSION.md) describes.

`--ids` is how you name the suite. The keys in the table are the ones the runner applies. Any other key is loaded and ignored, so the run stays the same.

## When a check or a task graduates

A task is one recorded run: one input, one trace. A check graduates together with that task. Move the check ID from the capability `--ids` list to the regression `--ids` list when all four of these are true:

1. The failure came from a recorded run. If the log was not already OTLP, you converted it with `agentest std import` (below).
2. You opened the detail line, found the span, and the failure is an agent mistake. [Read the trace](../walkthroughs/09-read-the-trace.md) walks through one bundled example.
3. You changed the agent, recorded the same task again, and that check now passes.
4. You want a later failure of that check on that trace to fail the CI job.

Until then the ID stays on the capability command. A capability `fail` is a report. It becomes a regression when you are willing to hold the fix.

Graduate the task with the check. Keep the trace you fixed, and keep running it. An ID with no trace behind it has not graduated.

## Saturation: stop growing a suite that no longer fails

A capability suite earns its place while some of its checks still fail on the tasks you care about. When you add a new task and every check already in the suite passes, that task did not teach you a new mistake. Stop adding tasks of that kind. A suite that no longer fails has saturated for this agent and these tasks.

Keep the checks that already caught a failure. Leave them on the capability command while you are fixing them, then move the ones you have fixed onto the regression command. Growing the capability list with tasks that pass makes the report longer and hides the low pass rate you are using the suite to see.

The regression suite grows by graduation, one fixed failure at a time. It should stay green. A new failure there means a fix slipped, which is the signal `--strict` is for.

## Start from a real failure

Begin with a log from a run that already went wrong. Convert it once if it is not OTLP, then read the `fail` rows. Those IDs are your first capability suite.

`agentest std import` writes OTLP/JSONL. `--dialect events` fits a JSON record that holds a `trace` list of objects with `kind`, `name` and `data`, where `kind` is `llm`, `tool`, `write`, `message` or `route`. Other built-in dialects are listed in `agentest std --help`. A log that needs a mapping file is the path in [walkthrough 5](../walkthroughs/05-bring-your-own-log.md).

```bash
agentest std import run.jsonl --dialect events --tools tools.json --service my_agent --out traces.otlp.jsonl
```

```bash
agentest std run --otlp traces.otlp.jsonl --tools tools.json --card agent-card.json --format md
```

Take each `fail` detail into the trace, using the walkthrough linked above. If the span shows an agent mistake, keep the ID on the capability command until the fix passes, then add it to the regression `--ids` list and run with `--strict`. If the span shows a check that is too strict, open the [false-positive issue template](../../.github/ISSUE_TEMPLATE/false-positive.yml) and leave that ID out of the regression suite. [Triaging false positives](../testers/FALSE-POSITIVES.md) is the checklist for that decision.
