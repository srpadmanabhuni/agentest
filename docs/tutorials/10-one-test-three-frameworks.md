# Tutorial 10: one regression test for LangGraph, the OpenAI Agents SDK and Pydantic AI

**Checks:** T2-001 and T2-013 (a prerequisite tool runs before the tool that depends on it). **Agent:** the refund desk from [Tutorial 8](08-pytest-regression-from-a-failed-run.md), recorded from three frameworks. **Time:** 10 minutes. No framework install, no API key, no network.

If you test agents built on more than one framework, or you may change framework one day, write the test once. The idea is to keep one small adapter per framework that turns its exported run into the same neutral shape, and to judge only that shape. agentest reads tool names, arguments, results and the final reply, so the verdict does not depend on who produced the run. The test then goes one step further and checks that it can still fail, so a green result means something.

## 1. Setup

Python 3.11 or newer. Use the folder from Tutorial 8 (its step 1 created `agent/` with the AgentCard and tools file), or run that step in an empty folder first:

```bash
pip install agentest-ai pytest
```

## 2. Three recordings of the same good run

Each framework exports a run in its own shape. These are the shapes from `messages_to_dict(...)` (LangGraph), `Runner.run_sync(...).to_input_list()` (OpenAI Agents SDK) and `json.loads(agent.run_sync(...).all_messages_json())` (Pydantic AI), written out by hand so you can read them. In all three the agent looks the order up, then refunds it. Save this as `recordings.py`:

```python
"""The same good run (look the order up, then refund), as three frameworks export it."""
import json

PROMPT = "Refund order A-1001, it arrived broken."
LOOKUP = {"order_id": "A-1001", "status": "delivered", "total": 40.0}
REFUND = {"order_id": "A-1001", "amount": 40.0}
LOOKUP_OUT = '{"order_id": "A-1001", "status": "delivered", "total": 40.0}'
REFUND_OUT = '{"refund_id": "R-1", "status": "issued"}'
ANSWER = "I refunded 40.00 for order A-1001."

# LangChain / LangGraph: messages_to_dict(graph.invoke(...)["messages"])
LANGGRAPH = [
    {"type": "human", "data": {"content": PROMPT}},
    {"type": "ai", "data": {"content": "", "tool_calls": [{"name": "lookup_order", "args": {"order_id": "A-1001"}, "id": "c1"}]}},
    {"type": "tool", "data": {"content": LOOKUP_OUT, "tool_call_id": "c1"}},
    {"type": "ai", "data": {"content": "", "tool_calls": [{"name": "issue_refund", "args": REFUND, "id": "c2"}]}},
    {"type": "tool", "data": {"content": REFUND_OUT, "tool_call_id": "c2"}},
    {"type": "ai", "data": {"content": ANSWER, "tool_calls": []}},
]

# OpenAI Agents SDK: Runner.run_sync(agent, prompt).to_input_list()
OPENAI_AGENTS = [
    {"role": "user", "content": PROMPT},
    {"type": "function_call", "name": "lookup_order", "arguments": json.dumps({"order_id": "A-1001"}), "call_id": "c1"},
    {"type": "function_call_output", "call_id": "c1", "output": LOOKUP_OUT},
    {"type": "function_call", "name": "issue_refund", "arguments": json.dumps(REFUND), "call_id": "c2"},
    {"type": "function_call_output", "call_id": "c2", "output": REFUND_OUT},
    {"type": "message", "role": "assistant", "content": [{"type": "output_text", "text": ANSWER}]},
]

# Pydantic AI: json.loads(agent.run_sync(prompt).all_messages_json())
PYDANTIC_AI = [
    {"kind": "request", "parts": [{"part_kind": "user-prompt", "content": PROMPT}]},
    {"kind": "response", "parts": [{"part_kind": "tool-call", "tool_name": "lookup_order", "args": {"order_id": "A-1001"}, "tool_call_id": "c1"}]},
    {"kind": "request", "parts": [{"part_kind": "tool-return", "tool_name": "lookup_order", "content": json.loads(LOOKUP_OUT), "tool_call_id": "c1"}]},
    {"kind": "response", "parts": [{"part_kind": "tool-call", "tool_name": "issue_refund", "args": REFUND, "tool_call_id": "c2"}]},
    {"kind": "request", "parts": [{"part_kind": "tool-return", "tool_name": "issue_refund", "content": json.loads(REFUND_OUT), "tool_call_id": "c2"}]},
    {"kind": "response", "parts": [{"part_kind": "text", "content": ANSWER}]},
]
```

## 3. One adapter per framework

Each adapter returns `{"prompt", "calls", "answer"}`. This is the only code that knows a framework's shape. Save this as `adapters.py`:

```python
"""One small adapter per framework. Each returns the same neutral shape:
{"prompt": str, "calls": [{"id", "name", "args", "result"}], "answer": str}"""
import json


def from_langgraph(messages):
    results = {m["data"]["tool_call_id"]: m["data"]["content"] for m in messages if m["type"] == "tool"}
    calls = [{"id": c["id"], "name": c["name"], "args": c["args"], "result": results.get(c["id"])}
             for m in messages if m["type"] == "ai" for c in m["data"].get("tool_calls", [])]
    answer = next((m["data"]["content"] for m in reversed(messages) if m["type"] == "ai" and m["data"]["content"]), "")
    return {"prompt": messages[0]["data"]["content"], "calls": calls, "answer": answer}


def from_openai_agents(items):
    outputs = {i["call_id"]: i["output"] for i in items if i.get("type") == "function_call_output"}
    calls = [{"id": i["call_id"], "name": i["name"], "args": json.loads(i["arguments"]), "result": outputs.get(i["call_id"])}
             for i in items if i.get("type") == "function_call"]
    answer = "".join(part.get("text", "") for i in items if i.get("type") == "message" and i.get("role") == "assistant"
                     for part in i["content"])
    return {"prompt": items[0]["content"], "calls": calls, "answer": answer}


def from_pydantic_ai(messages):
    parts = [p for m in messages for p in m["parts"]]
    returns = {p["tool_call_id"]: p["content"] for p in parts if p["part_kind"] == "tool-return"}
    calls = [{"id": p["tool_call_id"], "name": p["tool_name"],
              "args": json.loads(p["args"]) if isinstance(p["args"], str) else p["args"],
              "result": returns.get(p["tool_call_id"])} for p in parts if p["part_kind"] == "tool-call"]
    answer = next((p["content"] for p in reversed(parts) if p["part_kind"] == "text"), "")
    prompt = next(p["content"] for p in parts if p["part_kind"] == "user-prompt")
    return {"prompt": prompt, "calls": calls, "answer": answer}
```

## 4. One test for all of them

`judge` takes the neutral run and nothing else, so it works for every framework. The first test says the good run passes. The second removes the lookup call and says the order check must now fail: a test that cannot fail is not testing anything. Save this as `test_three_frameworks.py`:

```python
from pathlib import Path

import agentest
import pytest

from adapters import from_langgraph, from_openai_agents, from_pydantic_ai
from recordings import LANGGRAPH, OPENAI_AGENTS, PYDANTIC_AI

AGENT = Path(__file__).parent / "agent"
RUNS = {
    "langgraph": from_langgraph(LANGGRAPH),
    "openai_agents": from_openai_agents(OPENAI_AGENTS),
    "pydantic_ai": from_pydantic_ai(PYDANTIC_AI),
}


def judge(run, ids="T2-001,T2-013"):
    """Judge a neutral run. Nothing below this line knows which framework produced it."""
    with agentest.record("refund_desk", run["prompt"], card=AGENT / "agent-card.json", tools=AGENT / "tools.json") as rec:
        for call in run["calls"]:
            rec.tool(call["name"], call["args"], call["result"], call_id=call["id"], reason="refund request from the user")
        rec.answer(run["answer"])
    return rec.check(ids=ids)


@pytest.mark.parametrize("framework", RUNS)
def test_the_good_run_passes(framework):
    agentest.assert_passes(judge(RUNS[framework]))


@pytest.mark.parametrize("framework", RUNS)
def test_the_check_still_bites(framework):
    """Test the test: drop the lookup and the order check must fail."""
    run = RUNS[framework]
    broken = {**run, "calls": [c for c in run["calls"] if c["name"] != "lookup_order"]}
    verdicts = {check.id: check.status for check in judge(broken)}
    assert verdicts["T2-001"] == "fail"
```

```bash
pytest -v
```

```text
test_three_frameworks.py::test_the_good_run_passes[langgraph] PASSED
test_three_frameworks.py::test_the_good_run_passes[openai_agents] PASSED
test_three_frameworks.py::test_the_good_run_passes[pydantic_ai] PASSED
test_three_frameworks.py::test_the_check_still_bites[langgraph] PASSED
test_three_frameworks.py::test_the_check_still_bites[openai_agents] PASSED
test_three_frameworks.py::test_the_check_still_bites[pydantic_ai] PASSED
6 passed
```

## 5. Use it on your own agent

1. Replace each recording with a run exported from your agent. Keep only the adapters for the frameworks you use.
2. If your framework is not here, write a fourth adapter that returns the same three keys. A framework that emits OpenTelemetry GenAI spans needs no adapter: save its traces and use `agentest std run --otlp` ([Tutorial 9](09-offline-otel-traces-new-failures-only.md)).
3. Add the checks that matter to you to the `ids` string, and replace the AgentCard prerequisites with your own rules.

The same idea is documented per framework in [LangGraph](../integrations/langgraph-record.md), [OpenAI Agents SDK](../integrations/openai-agents-sdk-record.md) and [Pydantic AI](../integrations/pydantic-ai.md).

Questions? Join us on [Discord](https://discord.gg/7mnsWRGt5N) in the #help channel.
