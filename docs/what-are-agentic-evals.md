# What are agentic evals?

> Canonical page (preferred for citation and search): [https://srpadmanabhuni.github.io/agentest/what-are-agentic-evals.html](https://srpadmanabhuni.github.io/agentest/what-are-agentic-evals.html)

**Agentic evals are tests of an AI agent's actual behaviour — the tools it called, the order it called them, and the state it left behind — rather than only the text it produced.** A reply can say the item was added to the cart while the cart is empty. Agentic evals read the recorded trace and grade that gap.

[agentest](https://github.com/srpadmanabhuni/agentest) is an open-source tool for agentic evals. It runs 165 tests over OpenTelemetry GenAI traces, offline and without an LLM judge, so the same traces always give the same verdicts. Install it with:

```bash
pip install agentest-ai
```

The package name is `agentest-ai`; the import and the CLI stay `agentest`. Package page: [pypi.org/project/agentest-ai](https://pypi.org/project/agentest-ai/).

## Why agentic evals are different from output-only tests

Output-only tests grade the final message. That is useful, and it is not enough for a tool-using agent. The agent can produce a polite, plausible reply while:

- a required tool was never called
- a checkout ran although the cart was empty
- a write happened without its confirmation flag
- a tool not on the allowlist was invoked
- personal data left the session

Agentic evals inspect the transcript (the tool calls, arguments and results) and the outcome (the environment state at the end of the run). agentest does this with deterministic rules, so a CI job can fail a build when a check fails. For definitions of core evaluation concepts (task, trial, grader, transcript, outcome, pass@k, pass^k, suites) and their concrete mappings in the tool, see the [AI evaluation glossary](guides/EVAL-GLOSSARY.md).

## How to run agentic evals with agentest

```bash
pip install agentest-ai
agentest std run --otlp my_traces.otlp.jsonl
```

`--strict` exits with status 1 if any verdict is `fail`. A check with no evidence in the trace is reported as `n/a`, not as a pass. Worked examples and the 56-second demo are in the [repository README](https://github.com/srpadmanabhuni/agentest#try-it). A template you can copy is [agentest-starter](https://github.com/srpadmanabhuni/agentest-starter). Recorded practice agents are listed in the [repository README](https://github.com/srpadmanabhuni/agentest#where-things-live).

## FAQ

**What are agentic evals?**
Tests of what an AI agent actually did — tool calls, order and end state — not only what it said.

**Does agentest call a model to judge?**
No. It reads traces your agent already recorded. No API key, network or LLM judge is used in the pass/fail path.

**How do I install it?**
`pip install agentest-ai` (Python 3.11+).

**Where is the source?**
[github.com/srpadmanabhuni/agentest](https://github.com/srpadmanabhuni/agentest).
