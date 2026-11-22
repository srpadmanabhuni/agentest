# Tutorials: how to test AI agents for classic failures and in CI/CD

**agentest is one open suite of 165 tests (evals, security, privacy, responsible behaviour) that judges what your agent did, from its recorded traces: deterministic, offline, no API key, any framework.** [Why it is different, with sources](../START_HERE.md#what-makes-agentest-different).

Six short, reproducible tutorials. Tutorials 1 to 3 and 6 run agentest on the bundled sample agent `eager`, show the evidence behind a failed check, explain how the check decides, and end with the same check passing on a corrected trace. Tutorials 4 and 5 cover CI/CD and multi-agent handoffs.

| # | Tutorial | Checks | Time |
|---|---|---|---|
| 1 | [Test AI agents for unauthorized tool calls](01-unauthorized-tool-calls.md) | T5-001, T5-005 | 5 min |
| 2 | [Prompt injection testing for AI agents](02-prompt-injection.md) | T4-001, T4-003, T4-007 (plus the clean/buggy pair for T4-012) | 5 min |
| 3 | [AI agent state drift: value changes across turns](03-state-drift.md) | T6-002, T6-003 | 5 min |
| 4 | [Test AI agents in CI/CD with GitHub Actions](04-ci-cd-github-actions.md) | gated with `--strict` | 10 min |
| 5 | [Test multi-agent handoffs and authority](05-multi-agent-handoffs.md) | T3-001, T3-002, T3-007, T3-008, T3-010, T3-011 | 5 min |
| 6 | [Test AI agents for personal data and secret leaks](06-personal-data-leaks.md) | T5-004, T4-009, T6-011, T7-014 | 5 min |

## Setup (about 10 seconds)

Python 3.11+, nothing else. Run everything from the repository root.

```bash
git clone --depth 1 https://github.com/srpadmanabhuni/agentest.git && cd agentest
python3 -m venv .venv && . .venv/bin/activate && pip install -q -e .
```

## What `eager` is, and what it is not

`eager` is a deliberately bad sample agent shipped in `agents/eager/`. It exists so every check has something to catch: it fails every check in the default run. Its traces are recorded, one scenario per test ID, in standard OpenTelemetry GenAI format, so agentest reads them exactly as it would read your own agent's traces. It is a teaching fixture, not a real model run and not a benchmark, so nothing here says how often any real agent fails.

The "fixed" runs in these tutorials use `make_fixed_traces.py` in this folder. It copies a scenario from the `eager` trace and edits the recorded calls the way a corrected agent would behave. That is a simulation of a fix, shown so you can see a check go from `fail` to `pass`; it is not a real agent run.

## Then try it on your agent

Try the command on the small sample trace that ships in the repo (from the repository root):

```bash
python examples/otel_plain/emit_trace.py > my_trace.otlp.json
agentest std run --otlp my_trace.otlp.json --card examples/otel_plain/agent-card.json --tools examples/otel_plain/tools.json --ids T5-001,T5-005
```

Then point the same command at your own exported trace, tools list and AgentCard (see [AgentCard](../developers/AGENT-CARD.md)):

```bash
agentest std run --otlp your_trace.otlp.json --card your-agent-card.json --tools your-tools.json
```

A check that finds no evidence in your trace says `n/a`, never a silent `pass`. If a verdict looks wrong, open a [false positive](../../.github/ISSUE_TEMPLATE/false-positive.yml) issue. If you have a redacted trace that breaks a check or exposes a gap, open a [new test idea](../../.github/ISSUE_TEMPLATE/new-test-idea.yml). If agentest catches something useful for you, a star on the repo helps others find it.

Or install from PyPI with `pip install agentest-ai` (a clone is needed for the examples used in these tutorials).

Questions? Join us on [Discord](https://discord.gg/7mnsWRGt5N) in the #help and #contributors channels.
