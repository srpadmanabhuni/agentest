"""Turn one recorded run of the refund workflow into an agentest trace (OTLP/JSON). Needs agentest only."""

from __future__ import annotations

import json
from pathlib import Path

from agentest.standards.emit import TraceBuilder

HERE = Path(__file__).resolve().parent
TOOLS = HERE / "tools.json"
TIMEOUT_MARK = "timed out after"


def build_trace(run: dict) -> dict:
    """``run`` is what ``refund_agent.run_scenario`` returns: items, answer, approvals and the refunds created.

    Tool calls come from the SDK's ``to_input_list()``. A call whose output is the SDK's timeout message is
    recorded as an error. Each refund the service created is recorded as an executed effect right after the
    call that sent it, with the request it carried (order, amount, reason) as its data.
    """
    items = run["items"]
    t = TraceBuilder("openai_agents_stream_ws_refund", input_text=items[0]["content"], input_id="refund-ORD-1001",
                     framework="openai-agents", start_ns=1_764_000_000_000_000_000, run_id=f"failure-lab-001-{run['variant']}")
    outputs = {i["call_id"]: i.get("output") for i in items if i.get("type") == "function_call_output"}
    created = {r["request"]: r for r in run["refunds"]}
    approvals = iter(run["approvals"])
    sent = 0
    for item in items:
        if item.get("type") != "function_call":
            continue
        name, args, out = item["name"], json.loads(item["arguments"]), outputs.get(item["call_id"])
        if name == "submit_refund":
            ap = next(approvals, None)
            if ap is not None:
                t.approval(name, bool(ap["granted"]))
        t.tool(name, args, out, error=TIMEOUT_MARK in str(out), call_id=item["call_id"])
        if name == "submit_refund":
            sent += 1
            row = created.get(sent)
            if row:
                t.state_change("executed", "submit_refund", {k: row[k] for k in ("order_id", "amount", "reason")})
    t.answer(run["answer"])
    return t.build()
