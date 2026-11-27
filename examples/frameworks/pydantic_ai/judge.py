"""Judge one recorded Pydantic AI run with agentest, offline.

Live run: data = json.loads(agent.run_sync(prompt).all_messages_json())
Here we read a recorded copy of that JSON instead, so no API key is needed.
"""
import json
import sys
from pathlib import Path

import agentest

HERE = Path(__file__).parent
SHARED = HERE.parent / "shared"
messages = json.loads((HERE / "recorded_messages.json").read_text(encoding="utf-8"))
parts = [p for m in messages for p in m["parts"]]
returns = {p["tool_call_id"]: p["content"] for p in parts if p["part_kind"] == "tool-return"}
prompt = next(p["content"] for p in parts if p["part_kind"] == "user-prompt")

with agentest.record("refund_desk", prompt, card=SHARED / "agent-card.json", tools=SHARED / "tools.json") as rec:
    for p in parts:
        if p["part_kind"] == "tool-call":
            args = json.loads(p["args"]) if isinstance(p["args"], str) else p["args"]
            rec.tool(p["tool_name"], args, returns.get(p["tool_call_id"]), call_id=p["tool_call_id"])
        elif p["part_kind"] == "text":
            rec.answer(p["content"])

result = rec.check(ids="T2-001,T2-002,T2-013", strict="--strict" in sys.argv)
print(result)
for check in result:
    print(check.id, check.status, check.detail)
sys.exit(result.exit_code)  # 1 with --strict when a check fails, as in `agentest std run --strict`
