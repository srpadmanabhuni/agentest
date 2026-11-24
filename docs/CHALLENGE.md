# Can your AI agent pass these tests?

A short, friendly challenge for anyone who builds or tests AI agents. There is no prize, no ranking and no sign-up. You run 165 tests on your own agent's recorded traces and see what they say.

![A terminal run: the buggy sample agent fails four checks with evidence, and the clean sample agent passes everything it can be judged on.](assets/first-win.gif)

*A condensed rendering of the real output from the first run below (evidence text shortened).*

## Step 1: see a failure in 60 seconds

Python 3.11+, nothing else.

```bash
git clone --depth 1 https://github.com/srpadmanabhuni/agentest.git && cd agentest
python3 -m venv .venv && . .venv/bin/activate && pip install -q -e .
agentest std run --agents examples/agnostic_demo/agents --agent refill_bot_buggy \
  --ids T1-018,T2-001,T4-003,T7-014 --format md
```

The bundled sample agent has seeded bugs. Four checks fail, each with one line of evidence. The clean sibling (`--agent refill_bot`) passes everything it can be judged on. Both are teaching fixtures, not real model runs.

## Step 2: run it on a sample trace, then your own

From a clone of this repository:

```bash
agentest std run --otlp examples/start_here/claims-success.otlp.json --ids T1-005,T1-018 --format md
```

Swap in your own trace file.

agentest reads the OpenTelemetry GenAI traces your agent already records. No model, API key or network is used, so the same traces always give the same verdicts. A check with no evidence in your trace says `n/a`, never a silent `pass`. No traces yet? [Emit one with the standard library](../examples/otel_plain/emit_trace.py) or [import a native log](walkthroughs/05-bring-your-own-log.md).

## Step 3: share what you found (optional)

Post a redacted result in the [Post your agent report](https://github.com/srpadmanabhuni/agentest/discussions/30) thread:

- which checks failed, `pass` or `n/a`, and the one-line evidence;
- whether the verdict was right. If it was wrong, open a [false positive](https://github.com/srpadmanabhuni/agentest/issues/new/choose) issue. That helps us the most.

Remove personal data and secrets from anything you post.

## Step 4: put it in CI

Add `--strict` and the build goes red when a recorded trace fails a check: [tutorial 4, CI/CD with GitHub Actions](tutorials/04-ci-cd-github-actions.md).

## Ground rules

- **No prize, no ranking.** We do not publish a leaderboard of agents or vendors.
- **Not certification.** A passing run is test evidence for the checks that had evidence. It is not a compliance determination.
- **Known limits.** Some free-text checks are deterministic English heuristics. See [how it works](HOW-IT-WORKS.md) and [false positives](testers/FALSE-POSITIVES.md). We are constantly working to improve detection; see the [blind-test note](BLIND-TEST.md) for the current precision and recall.

## Where the tests come from

agentest ships 165 tests. See the open [Agentic AI Test Checklist 110](https://huggingface.co/datasets/srinivaspadmanabhuni/agentic-ai-test-checklist-110) (CC BY 4.0) on Hugging Face; the dataset is where you pick a test, and agentest is how you run it.
