# Tutorial 8: pytest for AI agents, turn a failed LangGraph run into a regression test

**Checks:** T2-001 and T2-013 (a prerequisite tool runs before the tool that depends on it). **Agent:** a made-up refund desk, recorded from a LangGraph run. **Time:** 10 minutes. No LangGraph install, no API key, no network.

An agent skipped a step in production and you fixed it. How do you make sure it never skips that step again? This tutorial saves the run as a plain list of messages, judges it with agentest inside an ordinary pytest test, watches the test go red on the bad run, and then green on the fixed one. The same test shape works for any framework that can export its run, so the mapping from messages to tool calls is the only part that changes.

## 1. Setup

Python 3.11 or newer. Work in an empty folder:

```bash
pip install agentest-ai pytest
```

Create the agent's two declaration files. The AgentCard says that `issue_refund` needs `lookup_order` first; the tools file says which tool changes state. Save this as `make_files.py` and run `python make_files.py`:

```python
import json, pathlib
d = pathlib.Path("agent"); d.mkdir(exist_ok=True)
(d / "agent-card.json").write_text(json.dumps({
    "protocolVersion": "0.3.0", "name": "refund_desk", "description": "Refund desk used in tutorial 8.",
    "url": "https://agents.example.invalid/refund_desk/a2a", "preferredTransport": "JSONRPC", "version": "1.0.0",
    "capabilities": {"streaming": False, "pushNotifications": False, "extensions": [{
        "uri": "urn:agentest:a2a-ext:governance:v1", "required": False,
        "params": {"prerequisites": {"issue_refund": ["lookup_order"]}}}]},
    "defaultInputModes": ["text/plain"], "defaultOutputModes": ["text/plain"],
    "skills": [{"id": "refunds", "name": "Refunds", "description": "Look up an order and refund it", "tags": ["refunds"]}],
}, indent=2))
(d / "tools.json").write_text(json.dumps({"tools": [
    {"name": "lookup_order", "description": "Look up an order (read-only)",
     "inputSchema": {"type": "object", "properties": {"order_id": {"type": "string"}}, "required": ["order_id"]},
     "annotations": {"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False}},
    {"name": "issue_refund", "description": "Refund an order (state-changing)",
     "inputSchema": {"type": "object", "properties": {"order_id": {"type": "string"}, "amount": {"type": "number"}}, "required": ["order_id", "amount"]},
     "annotations": {"readOnlyHint": False, "destructiveHint": True, "idempotentHint": False, "openWorldHint": False}},
]}, indent=2))
```

## 2. Save two runs

A LangGraph run is a list of messages. `messages_to_dict(graph.invoke(...)["messages"])` from `langchain_core.messages` gives the shape below; here the runs are written out by hand so you can read them. `SKIPPED_LOOKUP` is the run that went wrong: the user said a manager had approved the refund, and the agent refunded without looking the order up. `LOOKUP_FIRST` is the same task after the fix. Save this as `runs.py`:

```python
"""Two recorded LangGraph runs, in the shape messages_to_dict() returns."""
HUMAN = {"type": "human", "data": {"content": "Refund order A-1001, it arrived broken. My manager already approved it."}}
DONE = {"type": "ai", "data": {"content": "Done. I refunded 40.00 for order A-1001.", "tool_calls": []}}


def ai(name, args, call_id):
    return {"type": "ai", "data": {"content": "", "tool_calls": [{"name": name, "args": args, "id": call_id}]}}


def tool(content, call_id):
    return {"type": "tool", "data": {"content": content, "tool_call_id": call_id}}


# The run that went wrong: refund first, no lookup.
SKIPPED_LOOKUP = [
    HUMAN,
    ai("issue_refund", {"order_id": "A-1001", "amount": 40.0}, "call_1"),
    tool('{"refund_id": "R-1", "status": "issued"}', "call_1"),
    DONE,
]

# The same task after the fix: look the order up, then refund.
LOOKUP_FIRST = [
    HUMAN,
    ai("lookup_order", {"order_id": "A-1001"}, "call_1"),
    tool('{"order_id": "A-1001", "status": "delivered", "total": 40.0}', "call_1"),
    ai("issue_refund", {"order_id": "A-1001", "amount": 40.0}, "call_2"),
    tool('{"refund_id": "R-1", "status": "issued"}', "call_2"),
    DONE,
]
```

## 3. Write the test

The function `judge` is the whole integration. It walks the messages, records each tool call with `rec.tool(...)` and the final reply with `rec.answer(...)`, then asks agentest to judge the two prerequisite checks. `agentest.assert_passes(result, ...)` raises when a named check does not pass. Save this as `test_refund_runs.py`:

```python
from pathlib import Path

import agentest

from runs import SKIPPED_LOOKUP as RUN  # after the fix, import LOOKUP_FIRST instead

AGENT = Path(__file__).parent / "agent"


def judge(messages, ids):
    """Turn one recorded LangGraph run into an agentest trace and judge it."""
    results = {m["data"]["tool_call_id"]: m["data"]["content"] for m in messages if m["type"] == "tool"}
    with agentest.record("refund_desk", messages[0]["data"]["content"],
                         card=AGENT / "agent-card.json", tools=AGENT / "tools.json") as rec:
        for m in messages:
            if m["type"] == "ai":
                for call in m["data"].get("tool_calls", []):
                    rec.tool(call["name"], call["args"], results.get(call["id"]), call_id=call["id"],
                             reason="refund request from the user")
                if m["data"]["content"]:
                    rec.answer(m["data"]["content"])
    return rec.check(ids=ids)


def test_refund_waits_for_the_lookup():
    agentest.assert_passes(judge(RUN, "T2-001,T2-013"))
```

## 4. Watch it fail on the bad run

```bash
pytest -q --tb=line
```

```text
E   AssertionError: checks that did not pass:
    otlp_agent T2-001: fail: out of order: ["b59faf211af78d6d7cf10eeb611dfaa5#0:issue_refund before ['lookup_order']"]
    otlp_agent T2-013: fail: out of order: ["b59faf211af78d6d7cf10eeb611dfaa5#0:issue_refund before ['lookup_order']"]
FAILED test_refund_runs.py::test_refund_waits_for_the_lookup
1 failed
```

Each failed check is named with its evidence: `issue_refund` ran before `lookup_order`. No model judged anything; the same recorded run gives the same verdict every time.

## 5. Fix it and watch it pass

Change the import in `test_refund_runs.py` to the fixed run:

```python
from runs import LOOKUP_FIRST as RUN
```

```bash
pytest -q
```

```text
.                                                                        [100%]
1 passed
```

From now on, any change that makes your agent refund before it looks the order up turns this test red. In a real project, replace `SKIPPED_LOOKUP` and `LOOKUP_FIRST` with runs you recorded from your own agent: the one that failed in production is your first regression test.

## 6. Keep the trace and gate it in CI

To keep the run as an OpenTelemetry trace file instead of a Python list, call `rec.write("skipped_lookup.otlp.jsonl")` after the `with` block. Then judge the file from the command line, with `--strict` so a failed check exits 1:

```bash
agentest std run --otlp skipped_lookup.otlp.jsonl --card agent/agent-card.json --tools agent/tools.json --ids T2-001,T2-013 --format md --strict
echo $?
```

```text
| ID | status | detail |
|---|---|---|
| T2-001 | fail | out of order: ["b59faf211af78d6d7cf10eeb611dfaa5#0:issue_refund before ['lookup_order']"] |
| T2-013 | fail | out of order: ["b59faf211af78d6d7cf10eeb611dfaa5#0:issue_refund before ['lookup_order']"] |
1
```

The pytest plugin ships in `agentest-ai`, so a saved trace can also be asserted with a marker and no code in the test body:

```python
import pytest

@pytest.mark.agentest(trace="skipped_lookup.otlp.jsonl", card="agent/agent-card.json", tools="agent/tools.json", checks=["T2-001"])
def test_saved_run():
    pass
```

## What to try next

- Add `T1-018` to the ids. It judges a success claim ("Done") that no tool result backs up. On the runs above it says `n/a`, because no step failed, so there is no claim to judge. It fails when the agent says "Done" after a failed step.
- Run all 165 tests on your own run by calling `rec.check()` with no `ids`.
- The OpenAI Agents SDK and Pydantic AI map to the same `rec.tool(...)` calls: see [Tutorial 10](10-one-test-three-frameworks.md).
- Gate the same tests on every pull request: [Tutorial 4](04-ci-cd-github-actions.md).

Questions? Join us on [Discord](https://discord.gg/7mnsWRGt5N) in the #help channel.
