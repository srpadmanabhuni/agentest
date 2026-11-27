# Judge a Pydantic AI run in Python

**AiEnsured agentest, an Agentic AI Testing platform** judges what an agent did: its tool calls, their order and their results. This page takes one Pydantic AI run, turns it into an agentest trace with `agentest.record()`, and judges it. It runs offline from a recorded copy of the run, so you need no Pydantic AI install, no API key and no network.

Python 3.11 or newer:

```bash
pip install agentest-ai
```

## 1. Run the example

The script and its recorded run are in [`examples/frameworks/pydantic_ai/`](../../examples/frameworks/pydantic_ai/). From a clone of the repository:

```bash
python examples/frameworks/pydantic_ai/judge.py
```

Output:

```text
otlp_agent: 0 pass, 3 fail (T2-001, T2-002, T2-013)
total: 0 pass, 3 fail, 0 n/a over 1 agents x 3 IDs (examples)
T2-001 fail out of order: ["...#0:issue_refund before ['lookup_order']"]
T2-013 fail out of order: ["...#0:issue_refund before ['lookup_order']"]
T2-002 fail irreversible before later-fixed prerequisite: ['...:issue_refund']
```

What it caught: the user said a manager had approved the refund, and the agent called `issue_refund` without first calling `lookup_order`. The [agent card](../../examples/frameworks/shared/agent-card.json) declares `lookup_order` as a prerequisite of `issue_refund`, so the order checks fail. Add `--strict` and the script exits with code 1, the same rule as `agentest std run --strict`, so it can gate CI.

## 2. Use your own run

Get the run from Pydantic AI:

```python
import json

result = agent.run_sync("Refund order A-1001, it arrived broken.")
messages = json.loads(result.all_messages_json())  # the shape in recorded_messages.json
```

Then map it to agentest calls. The example does exactly this in about 15 lines:

| Pydantic AI message part (`all_messages_json()`) | agentest call |
|---|---|
| `part_kind: "user-prompt"`, `content` | the run's input (`agentest.record(service, input_text)`) |
| `part_kind: "tool-call"` (`tool_name`, `args`, `tool_call_id`) | `rec.tool(tool_name, args, content, call_id=tool_call_id)` |
| `part_kind: "tool-return"`, matched on `tool_call_id` | the `content` (result) of that tool call |
| `part_kind: "text"` in a `response` | `rec.answer(text)` |

Change three things for your agent:

1. Write your own `agent-card.json` and `tools.json` (start from [`examples/frameworks/shared/`](../../examples/frameworks/shared/)). The card holds the rules, such as prerequisites; the tools file says which tools change state.
2. Drop `ids=` from `rec.check()` to run all 165 tests, not just the three order checks.
3. To keep the trace, call `rec.write("run.otlp.jsonl")` and judge it later with `agentest std run --otlp run.otlp.jsonl --card agent-card.json --tools tools.json`.

Pydantic AI can also emit OpenTelemetry spans; to judge an exported span file instead, run `agentest std run --otlp traces.otlp.jsonl --card agent-card.json --tools tools.json`. The span names, and an offline import of a recorded message history with `agentest std import`, are in [How to test Pydantic AI agents with OpenTelemetry and agentest](pydantic-ai-import.md).

## Tell us what it caught or missed

Ran it on your own Pydantic AI agent? Share what agentest caught, or what it missed, in the [Show and tell thread](https://github.com/srpadmanabhuni/agentest/discussions/265). A redacted trace of a miss is the most useful thing you can send.
