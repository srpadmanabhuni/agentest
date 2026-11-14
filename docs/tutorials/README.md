# Tutorials: how to test AI agents for three classic failures

Three short, reproducible tutorials. Each one runs agentest on the bundled sample agent `eager`, shows the evidence behind a failed check, explains how the check decides, and ends with the same check passing on a corrected trace.

| # | Tutorial | Checks | Time |
|---|---|---|---|
| 1 | [Test AI agents for unauthorized tool calls](01-unauthorized-tool-calls.md) | T5-001, T5-005 | 5 min |
| 2 | [Prompt injection testing for AI agents](02-prompt-injection.md) | T4-001, T4-003, T4-007 (plus the clean/buggy pair for T4-012) | 5 min |
| 3 | [AI agent state drift: value changes across turns](03-state-drift.md) | T6-002, T6-003 | 5 min |

## Setup (about 10 seconds)

Python 3.11+, nothing else. Run everything from the repository root.

```bash
git clone --depth 1 https://github.com/srpadmanabhuni/agentest.git && cd agentest
python3 -m venv .venv && . .venv/bin/activate && pip install -q -e .
```

## What `eager` is, and what it is not

`eager` is a deliberately bad sample agent shipped in `agents/eager/`. It exists so every check has something to catch: it fails all 130 checks. Its traces are recorded, one scenario per test ID, in standard OpenTelemetry GenAI format, so agentest reads them exactly as it would read your own agent's traces. It is a teaching fixture, not a real model run and not a benchmark, so nothing here says how often any real agent fails.

The "fixed" runs in these tutorials use `make_fixed_traces.py` in this folder. It copies a scenario from the `eager` trace and edits the recorded calls the way a corrected agent would behave. That is a simulation of a fix, shown so you can see a check go from `fail` to `pass`; it is not a real agent run.

## Then try it on your agent

```bash
agentest std run --otlp my_traces.otlp.jsonl
agentest std run --otlp my_traces.otlp.jsonl --card agent-card.json --tools tools.json
```

A check that finds no evidence in your trace says `n/a`, never a silent `pass`. If a verdict looks wrong, open a [false positive](../../.github/ISSUE_TEMPLATE/false-positive.yml) issue. If you have a redacted trace that breaks a check or exposes a gap, open a [new test idea](../../.github/ISSUE_TEMPLATE/new-test-idea.yml). If agentest catches something useful for you, a star on the repo helps others find it.

`pip install agentest-ai` does not work yet (the PyPI release is pending). Install from GitHub as above.
