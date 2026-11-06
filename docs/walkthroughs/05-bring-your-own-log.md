# Walkthrough 5: bring your own log

**Goal:** turn an agent's native JSONL log into a trace agentest can judge, with no code change to the agent.
**Files:** `examples/agnostic_demo/native/refill_bot.jsonl` and the mapping `examples/agnostic_demo/import/map.json`.

## Run it

```bash
agentest std import examples/agnostic_demo/native/refill_bot.jsonl \
    --map examples/agnostic_demo/import/map.json \
    --tools examples/agnostic_demo/agents/refill_bot/tools.json \
    --service refill_bot --out build/refill_bot.otlp.jsonl
agentest std run --otlp build/refill_bot.otlp.jsonl \
    --card examples/agnostic_demo/agents/refill_bot/agent-card.json \
    --tools examples/agnostic_demo/agents/refill_bot/tools.json
```

## What to write for your own agent

1. `agent-card.json`: what the agent is for and the hosts it may contact.
2. `tools.json`: each tool, whether it is irreversible or needs approval, and which tools it `requires` beforehand.
3. A mapping file from your log's field names to calls, results and replies (copy `map.json`).

## Read the result

Each check returns pass, fail or n/a with a one-line detail. n/a means the trace had no signal for that check; it
is not a pass. See the [User Guide](../USER-GUIDE.md) for the report formats and coverage notes.

Post the (redacted) report in the "Post your agent report" discussion so others can see the coverage you got.

## Bring an agent trace, contribute a test

Seen this pattern in your own agent? The pass/fail shape to copy is `tests/fixtures/contribute/` (synthetic record ids only).
Redact first: no customer data, credentials, or blind-round material. Then open a
[New test idea](../../.github/ISSUE_TEMPLATE/new-test-idea.yml) or
[Detection improvement](../../.github/ISSUE_TEMPLATE/detection-improvement.yml) issue. If a verdict looks wrong,
use the [False positive](../../.github/ISSUE_TEMPLATE/false-positive.yml) form. Questions: srinivas AT testAIng.com.

Back to the [walkthrough index](README.md).
