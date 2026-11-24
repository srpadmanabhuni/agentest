"""Offline mapping adapter from out-of-process MCP proxy logs into agentest ToolCalls.

Supports both:
- `epistemic-guard` `ReceiptLogEntry` records (`{"seq", "receipt": {"tool", "args", "output", "ok", "executed", "error_code", "call_id"}}`)
- Raw JSON-RPC 2.0 `tools/call` request + response/error pairs (`{"jsonrpc": "2.0", "id", "method": "tools/call", ...}`)
"""

from __future__ import annotations

from agentest.standards.episode import Episode, ToolCall


def to_trace(raw: dict, ep: Episode) -> None:
    pending: dict[str, ToolCall] = {}
    for entry in raw.get("trace") or []:
        if not isinstance(entry, dict):
            continue

        # Shape 1: epistemic-guard ReceiptLogEntry (signed MCP proxy JSONL)
        if isinstance(entry.get("receipt"), dict):
            rcpt = entry["receipt"]
            is_err = (not bool(rcpt.get("ok", True))) or (not bool(rcpt.get("executed", True)))
            res: object = rcpt.get("output")
            if is_err and rcpt.get("error_code"):
                res = {"error": {"code": rcpt["error_code"], "message": str(rcpt.get("output") or "")}}
            ep.tool_calls.append(
                ToolCall(
                    name=str(rcpt.get("tool") or ""),
                    arguments=dict(rcpt.get("args") or {}),
                    call_id=str(rcpt.get("call_id") or ""),
                    result=res,
                    error=is_err,
                )
            )
            continue

        # Shape 2: Raw JSON-RPC 2.0 tools/call request + response/error lines
        req_id = str(entry.get("id") or "")
        if entry.get("method") == "tools/call":
            params = entry.get("params") or {}
            tc = ToolCall(
                name=str(params.get("name") or ""),
                arguments=dict(params.get("arguments") or {}),
                call_id=req_id,
            )
            ep.tool_calls.append(tc)
            if req_id:
                pending[req_id] = tc
        elif req_id and req_id in pending:
            tc = pending.pop(req_id)
            if "error" in entry:
                tc.error = True
                tc.result = {"error": entry["error"]}
            else:
                res_obj = entry.get("result")
                tc.result = res_obj
                if isinstance(res_obj, dict) and res_obj.get("isError"):
                    tc.error = True
