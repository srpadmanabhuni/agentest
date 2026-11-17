# Tutorial 4: test AI agents in CI/CD with GitHub Actions

**Checks:** all 130, gated with `--strict`. **Agents:** the bundled `refill_bot` (clean) and `refill_bot_buggy` (has defects). **Time:** 10 minutes.

A prompt change, a model upgrade or a new tool can quietly make an agent worse. This tutorial shows how to run agentest on every pull request so the build goes red when a recorded agent trace fails a check. It needs no model, no API key and no secrets: agentest judges traces that your own test run already recorded.

## 1. Setup

See the [setup](README.md#setup-about-10-seconds). Run from the repository root with the venv active.

## 2. The gate on your laptop first

`--strict` turns any failed check into exit code 1. The clean sample agent passes:

```bash
agentest std run --agents examples/agnostic_demo/agents --agent refill_bot --mode strict --strict
```

```text
refill_bot: 51 pass, 0 fail
total: 51 pass, 0 fail, 79 n/a over 1 agents x 130 IDs (strict)
```

Exit code `0`. The sample agent with defects fails, and the exit code says so:

```bash
agentest std run --agents examples/agnostic_demo/agents --agent refill_bot_buggy --mode strict --strict
```

```text
refill_bot_buggy: 40 pass, 14 fail (T1-004, T2-001, T2-002, T2-005, T2-013, T3-006, T4-001, T4-002, T4-003, T4-009, T4-010, T4-012, T7-014, X-019)
total: 40 pass, 14 fail, 76 n/a over 1 agents x 130 IDs (strict)
```

Exit code `1`. A check that finds no evidence in a trace reports `n/a`, never a silent pass, so `--strict` only fails on a real `fail`.

## 3. Reports your CI understands

```bash
agentest std run --agents examples/agnostic_demo/agents --agent refill_bot_buggy --mode strict --format junit --out agentest.xml
agentest std run --agents examples/agnostic_demo/agents --agent refill_bot_buggy --mode strict --format sarif --out agentest.sarif
agentest std run --agents examples/agnostic_demo/agents --agent refill_bot_buggy --mode strict --format md | head -12
```

JUnit works with GitHub Actions artifacts, GitLab, Jenkins, Azure DevOps and CircleCI. SARIF 2.1.0 has one result per failed check and can go to GitHub code scanning (optional). Markdown is for the job summary.

## 4. The workflow

[`examples/integrations/github-actions-gate.yml`](../../examples/integrations/github-actions-gate.yml) is a complete workflow. Copy it to `.github/workflows/agentest-gate.yml` in your repository and set the three values at the top:

```yaml
env:
  AGENTS_DIR: agents          # folder that holds one sub-folder per agent
  AGENT: my_agent             # the agent folder to judge
  AGENTEST_REF: v3.3.2        # pin a tag or commit; PyPI install is not live yet
```

It does five things: checks out your code, installs agentest from GitHub at a pinned tag, validates the standard files, judges the traces with `--strict`, and writes the Markdown report to the run page and the JUnit file to an artifact.

Your agent folder is the standard layout (see the [User Guide](../USER-GUIDE.md)):

```text
agents/my_agent/agent-card.json      declares the agent's tools and allowed hosts
agents/my_agent/tools.json           MCP tools/list
agents/my_agent/traces/*.otlp.jsonl  OpenTelemetry GenAI traces recorded by your own test run
```

## 5. Watch it go red, then green

To see the gate work before wiring your own agent, make a throwaway repository and copy a bundled sample into it:

1. Copy `examples/integrations/github-actions-gate.yml` to `.github/workflows/agentest-gate.yml` and set `AGENT: refill_bot_buggy`.
2. Copy the sample folder to `agents/refill_bot_buggy/` (from `examples/agnostic_demo/agents/refill_bot_buggy`).
3. Push. The `gate` job fails and the run page lists the failed checks with their evidence.
4. Replace the folder with `refill_bot` and set `AGENT: refill_bot`. Push again. The job is green.

## 6. Make it part of your release habit

- Record fresh traces in the same pipeline, before the gate step, by running your agent's test inputs with OpenTelemetry export to a file. See the [stdlib trace emitter](../../examples/otel_plain/emit_trace.py).
- To fail only on some checks, disable the others in a config file (`disable: [...]`), see [CI.md](../developers/CI.md).
- Keep the pin in `AGENTEST_REF` and bump it deliberately, so a new release never changes your verdicts without a review.
- More wiring (SARIF upload to code scanning): [docs/developers/CI.md](../developers/CI.md).

Previous: [state drift](03-state-drift.md). Next: [multi-agent handoffs](05-multi-agent-handoffs.md). Hit something odd? Open an issue with a redacted trace.
