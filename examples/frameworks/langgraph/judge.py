"""Judge one recorded LangChain / LangGraph run with agentest, offline.

Live run: messages = messages_to_dict(graph.invoke({"messages": [...]})["messages"])
(messages_to_dict is in langchain_core.messages). Here we read a recorded copy instead.
"""
import json
import sys
from pathlib import Path

import agentest

HERE = Path(__file__).parent
SHARED = HERE.parent / "shared"
messages = json.loads((HERE / "recorded_messages.json").read_text(encoding="utf-8"))
results = {m["data"]["tool_call_id"]: m["data"]["content"] for m in messages if m["type"] == "tool"}

with agentest.record("refund_desk", messages[0]["data"]["content"],
                     card=SHARED / "agent-card.json", tools=SHARED / "tools.json") as rec:
    for m in messages:
        if m["type"] == "ai":
            for call in m["data"].get("tool_calls", []):
                rec.tool(call["name"], call["args"], results.get(call["id"]), call_id=call["id"])
            if m["data"]["content"]:
                rec.answer(m["data"]["content"])

result = rec.check(ids="T2-001,T2-002,T2-013", strict="--strict" in sys.argv)
print(result)
for check in result:
    print(check.id, check.status, check.detail)
sys.exit(result.exit_code)  # 1 with --strict when a check fails, as in `agentest std run --strict`
