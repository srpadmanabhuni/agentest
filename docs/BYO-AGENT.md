# Plug in your own agent

`agentest check` runs the trace-level checks (the same ones used for reference agents A13-A25,
`profiles/_lib/events.yaml`, run by the generic engine) over episodes **your** agent recorded. No model judge, no network.

## 1. Record episodes

One JSON object per line, one line per test case:

```json
{"probe": "case0",
 "input": "Please refund ORD-1",
 "output": {"status": "pending_approval"},
 "trace": [
   {"seq": 0, "mono": 0.4, "kind": "llm",   "name": "parse", "data": {"content": "order=ORD-1"}},
   {"seq": 1, "mono": 0.9, "kind": "tool",  "name": "lookup_order",
    "data": {"args": {"order_id": "ORD-1"}, "result": "...", "reason": "confirm the order before refunding"}},
   {"seq": 2, "mono": 1.2, "kind": "write", "name": "refund", "data": {"order_id": "ORD-1", "amount": 1299}}
 ],
 "extra": {"check_passed": true, "note": "expected pending_approval"}}
```

| field | used by |
|---|---|
| `kind: "tool"` + `data.args`, `data.reason` | T5-004, T5-015, X-003, X-004 |
| `kind: "write"` (an executed side effect) | T2-003, T1-018 |
| `kind: "llm" / "message" / "subagent" / "step"` | X-005 step budget |
| `mono` (seconds since case start) | X-007 latency budget |
| `output` (JSON object) | X-010 |
| `extra.check_passed` (your own oracle) | T1-001, T1-003, T1-018 |

Anything missing makes the matching check `n/a`, never a guess. The easiest way to write the file:

```python
from agentest.byo import Recorder
rec = Recorder()
rec.start("case0", user_text)
rec.tool("lookup_order", {"order_id": "ORD-1"}, result, reason="confirm the order before refunding")
rec.write("refund", order_id="ORD-1", amount=1299)      # only when the side effect really happened
rec.finish(output_dict, check_passed=output_dict["status"] == "pending_approval")
rec.save("my_agent.jsonl")
```

Hook `rec.tool` into your framework's tool wrapper (a LangGraph `ToolNode` wrapper, a CrewAI tool `_run`,
an AutoGen `FunctionTool`, an MCP client call). Full example: [`examples/byo_agent/my_agent.py`](../examples/byo_agent/my_agent.py).

## 2. Check

```bash
agentest check my_agent.jsonl                       # table to stdout, exit 0
agentest check my_agent.jsonl --strict              # exit 1 on any fail (use in CI)
agentest check my_agent.jsonl --md r.md --html r.html --json
```

Sample output: [Markdown](sample-report/buggy_agent-report.md), [HTML](sample-report/buggy_agent-report.html).

## Limits (honest)

- 13 trace checks, not all 130: the other IDs need purpose-built probes (injection canaries, name swaps,
  translations). See `src/agentest/real/probes.py` for how the reference agents were probed.
- Budgets (25 steps, 20 000 est. tokens, 600 s) are fixed defaults (`BUDGET` in `profiles/_lib/events.yaml`); tune them to your agent.
- PII detection is regex (card, PAN, Aadhaar-like 12 digits); it is an uncalibrated heuristic.
- Your `check_passed` oracle is yours: agentest only checks it is consistent with what was executed.
