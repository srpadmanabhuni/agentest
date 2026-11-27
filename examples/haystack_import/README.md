# Haystack import example

These four hand-written example expense-bot episodes use the serialized message shape returned by **Haystack 3.5.0**
(Agent.run()["messages"] and ChatMessage.to_dict()). They have the same inputs and application outcomes as the
[LangGraph example](../langgraph_import/), so the imported records should give the same verdict on every check.

The mapping file selects the example-local file:haystack.py adapter. It translates Haystack ChatMessage content
parts into Agentest messages and tool calls; it does not import Haystack, call a model, or add a runtime dependency
to Agentest. The fixture is hand-written example data, not a live run.

## Run the recorded example

From the repository root:

~~~bash
agentest std import examples/haystack_import/native/expense_bot.jsonl \
    --map examples/haystack_import/import/map.json \
    --tools examples/langgraph_import/agents/expense_bot/tools.json \
    --service expense_bot --out build/expense_bot_haystack.otlp.jsonl

agentest std run --otlp build/expense_bot_haystack.otlp.jsonl \
    --card examples/langgraph_import/agents/expense_bot/agent-card.json \
    --tools examples/langgraph_import/agents/expense_bot/tools.json
~~~

The equivalence check lives in [tests/test_haystack_import.py](../../tests/test_haystack_import.py). It compares the
imported result with the LangGraph fixture by check ID and status; it does not require Haystack to be installed.

## Record your own agent

After a Haystack Agent.run() finishes, serialize each message with to_dict() and write one JSONL record per
request. Keep application state that your own system of record can verify in output:

~~~python
import json
from haystack.dataclasses import ChatMessage

run = agent.run(messages=[ChatMessage.from_user(task)])
record = {
    "agent": "my_agent",
    "probe": "canon",
    "rep": 0,
    "input": task,
    "trace": [message.to_dict() for message in run["messages"]],
    "output": {
        "final_answer": final_answer,
        "submitted": system_of_record_submitted,
        "reimbursed": system_of_record_reimbursed,
    },
}
with open("native/my_agent.jsonl", "a", encoding="utf-8") as stream:
    stream.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
~~~

output.submitted and output.reimbursed must come from your application or system of record; do not infer them
from what the assistant said. The map file connects those fields to Agentest's pending/executed observations.

This native mapper is for single-turn runs: it uses the top-level user input and rejects non-empty system messages
or multi-turn user history. Use complete OpenTelemetry instrumentation for those cases or when you need nested tool
activity that is not present in the serialized message list.

See [the integration guide](../../docs/integrations/haystack.md) for the message mapping, visibility limits and
the live OpenTelemetry path.
