# Judge a LangChain or LangGraph run in Python

**AiEnsured agentest, an Agentic AI Testing platform** judges what an agent did: its tool calls, their order and their results. This page takes one LangChain or LangGraph run, turns it into an agentest trace with `agentest.record()`, and judges it. It runs offline from a recorded copy of the run, so you need no LangChain or LangGraph install, no API key and no network.

Python 3.11 or newer:

```bash
pip install agentest-ai
```

## 1. Run the example

The script and its recorded run are in [`examples/frameworks/langgraph/`](../../examples/frameworks/langgraph/). From a clone of the repository:

```bash
python examples/frameworks/langgraph/judge.py
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

Get the run from LangChain or LangGraph:

```python
from langchain_core.messages import messages_to_dict

state = graph.invoke({"messages": [("user", "Refund order A-1001, it arrived broken.")]})
messages = messages_to_dict(state["messages"])  # the shape in recorded_messages.json
```

Then map it to agentest calls. The example does exactly this in about 15 lines:

| LangChain message (`messages_to_dict`) | agentest call |
|---|---|
| first `human` message `data.content` | the run's input (`agentest.record(service, input_text)`) |
| `ai` message `data.tool_calls[]` (`name`, `args`, `id`) | `rec.tool(name, args, result, call_id=id)` |
| `tool` message `data.content`, matched on `data.tool_call_id` | the `result` of that tool call |
| last `ai` message with text `data.content` | `rec.answer(text)` |

Change three things for your agent:

1. Write your own `agent-card.json` and `tools.json` (start from [`examples/frameworks/shared/`](../../examples/frameworks/shared/)). The card holds the rules, such as prerequisites; the tools file says which tools change state.
2. Drop `ids=` from `rec.check()` to run all 165 tests, not just the three order checks.
3. To keep the trace, call `rec.write("run.otlp.jsonl")` and judge it later with `agentest std run --otlp run.otlp.jsonl --card agent-card.json --tools tools.json`.

For whole folders of recorded message lists, the built-in `langgraph_msgs` import dialect does the same mapping from the command line: see [How to test LangGraph agents](langgraph.md).

## Tell us what it caught or missed

Ran it on your own LangChain or LangGraph agent? Share what agentest caught, or what it missed, in the [Show and tell thread](https://github.com/srpadmanabhuni/agentest/discussions/265). A redacted trace of a miss is the most useful thing you can send.
