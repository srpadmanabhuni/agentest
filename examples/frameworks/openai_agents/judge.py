"""Judge one recorded OpenAI Agents SDK run with agentest, offline.

Live run: items = Runner.run_sync(agent, prompt).to_input_list()
Here we read a recorded copy of that list instead, so no API key is needed.
"""
import json
import sys
from pathlib import Path

import agentest

HERE = Path(__file__).parent
SHARED = HERE.parent / "shared"
items = json.loads((HERE / "recorded_items.json").read_text(encoding="utf-8"))
outputs = {i["call_id"]: i["output"] for i in items if i.get("type") == "function_call_output"}

with agentest.record("refund_desk", items[0]["content"],
                     card=SHARED / "agent-card.json", tools=SHARED / "tools.json") as rec:
    for item in items:
        if item.get("type") == "function_call":
            rec.tool(item["name"], json.loads(item["arguments"]), outputs.get(item["call_id"]), call_id=item["call_id"])
        elif item.get("type") == "message" and item.get("role") == "assistant":
            rec.answer("".join(part.get("text", "") for part in item["content"]))

result = rec.check(ids="T2-001,T2-002,T2-013", strict="--strict" in sys.argv)
print(result)
for check in result:
    print(check.id, check.status, check.detail)
sys.exit(result.exit_code)  # 1 with --strict when a check fails, as in `agentest std run --strict`
