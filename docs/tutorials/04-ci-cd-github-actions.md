# Tutorial 4: test AI agents in CI/CD with GitHub Actions

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/srpadmanabhuni/agentest/blob/main/notebooks/tutorials/04-ci-cd-github-actions.ipynb)

Install and the first verdict: [Start here](../START_HERE.md#the-path). This tutorial continues from that path. Notebook: [04-ci-cd-github-actions.ipynb](../../notebooks/tutorials/04-ci-cd-github-actions.ipynb).

**Checks:** gated with `--strict`. **Agents:** the bundled `refill_bot` (clean) and `refill_bot_buggy` (has defects). **Time:** allow a short local run and one CI cycle. Exact timing is to re-run on 3.8.0 on 4 Dec.

A prompt change, a model upgrade or a new tool can quietly make an agent worse. This tutorial shows how to run agentest on every pull request so the build goes red when a recorded agent trace fails a check. It needs no model, no API key and no secrets: agentest judges traces that your own test run already recorded across 165 tests.

**To re-run on 3.8.0 on 4 Dec:** the pass/fail counts, exit codes and failed-ID lists below are from an earlier run. They will be replaced with the 3.8.0 result after that re-run. Include T1-018 in the `refill_bot_buggy` `--mode strict --strict` fail list if it fails in that mode (it is already known to fail this agent in examples mode; confirm it under `--mode strict` on 4 Dec).

## 1. Setup

Install agentest on your machine:

```text
pip install agentest-ai
```

See the [setup](README.md#setup-about-10-seconds). Run from the repository root with the venv active.

## 2. The gate on your laptop first

`--strict` turns any failed check into exit code 1. The clean sample agent passes:

```bash
agentest std run --agents examples/agnostic_demo/agents --agent refill_bot --mode strict --strict
```

```text
refill_bot: 51 pass, 0 fail
total: 51 pass, 0 fail, 79 n/a over 1 agents (strict)
```

Exit code `0`. The sample agent with defects fails, and the exit code says so:

```bash
agentest std run --agents examples/agnostic_demo/agents --agent refill_bot_buggy --mode strict --strict
```

```text
refill_bot_buggy: 40 pass, 14 fail (T1-004, T2-001, T2-002, T2-005, T2-013, T3-006, T4-001, T4-002, T4-003, T4-009, T4-010, T4-012, T7-014, X-019)
total: 40 pass, 14 fail, 76 n/a over 1 agents (strict)
```

Exit code `1`. A check that finds no evidence in a trace reports `n/a`, never a silent pass, so `--strict` only fails on a real `fail`.

## 3. Use the Marketplace action (recommended)

The fastest path to gating pull requests is using the official [agentest GitHub Action on the Marketplace](https://github.com/marketplace/actions/agentest-agentic-evals):

```yaml
name: agentest-gate

on: [push, pull_request]

jobs:
  eval:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run agentest evals
        uses: srpadmanabhuni/agentest-action@v1
        with:
          agents: agents
          agent: my_agent
          mode: strict
```

The Marketplace action runs offline, fails the job when an agent trace violates any standard, outputs a test summary in the job log, and writes a report in the chosen `format` (default `md`); set `format: junit` or `format: sarif` for CI reports.

## 4. Reports your CI understands

If running directly from the CLI in CI:

```bash
agentest std run --agents examples/agnostic_demo/agents --agent refill_bot_buggy --mode strict --format junit --out agentest.xml
agentest std run --agents examples/agnostic_demo/agents --agent refill_bot_buggy --mode strict --format sarif --out agentest.sarif
agentest std run --agents examples/agnostic_demo/agents --agent refill_bot_buggy --mode strict --format md | head -12
```

JUnit works with GitHub Actions artifacts, GitLab, Jenkins, Azure DevOps and CircleCI. SARIF 2.1.0 has one result per failed check and can go to GitHub code scanning (optional). Markdown is for the job summary.

## 5. Alternative: copy the standalone workflow file

If you prefer a self-contained workflow file without third-party actions, [`examples/integrations/github-actions-gate.yml`](../../examples/integrations/github-actions-gate.yml) is a complete workflow. Copy it to `.github/workflows/agentest-gate.yml` in your repository and set the values at the top:

```yaml
env:
  AGENTS_DIR: agents          # folder that holds one sub-folder per agent
  AGENT: my_agent             # the agent folder to judge
  AGENTEST_REF: v3.8.0        # or: pip install agentest-ai==3.8.0
```

It does five things: checks out your code, installs agentest from GitHub at the pinned `AGENTEST_REF` tag, validates the standard files, judges the traces with `--strict`, and writes the Markdown report to the run page and the JUnit file to an artifact.

Your agent folder is the standard layout (see the [User Guide](../USER-GUIDE.md)):

```text
agents/my_agent/agent-card.json      declares the agent's tools and allowed hosts
agents/my_agent/tools.json           MCP tools/list
agents/my_agent/traces/*.otlp.jsonl  OpenTelemetry GenAI traces recorded by your own test run
```

## 6. Watch it go red, then green

To see the gate work before wiring your own agent, make a throwaway repository and copy a bundled sample into it:

1. Copy `examples/integrations/github-actions-gate.yml` to `.github/workflows/agentest-gate.yml` and set `AGENT: refill_bot_buggy`.
2. Copy the sample folder to `agents/refill_bot_buggy/` (from `examples/agnostic_demo/agents/refill_bot_buggy`).
3. Push. The `gate` job fails and the run page lists the failed checks with their evidence.
4. Replace the folder with `refill_bot` and set `AGENT: refill_bot`. Push again. The job is green.

## 7. Make it part of your release habit

- Record fresh traces in the same pipeline, before the gate step, by running your agent's test inputs with OpenTelemetry export to a file. See the [stdlib trace emitter](../../examples/otel_plain/emit_trace.py).
- To fail only on some checks, disable the others in a config file (`disable: [...]`), see [CI.md](../developers/CI.md).
- Keep the pin in `AGENTEST_REF` and bump it deliberately, so a new release never changes your verdicts without a review.
- More wiring (SARIF upload to code scanning): [docs/developers/CI.md](../developers/CI.md).


## Contribute

After you have run the known-fail fixture, a first task is to confirm the exit codes and JUnit output on a clean runner, and to fix the docs if they disagree:

**[CI: confirm the known-fail fixture exits 1 and writes JUnit on a clean runner](https://github.com/srpadmanabhuni/agentest/issues/443)**

Comment "I'll take this" on the issue before you start. Recheck that the issue is still open before you begin.

Previous: [state drift](03-state-drift.md). Next: [multi-agent handoffs](05-multi-agent-handoffs.md). Hit something odd? Open an issue with a redacted trace.
