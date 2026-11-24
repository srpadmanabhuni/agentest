"""A neutral use-case agent (refund desk) for importer connector round trips: card, MCP tools and governance."""

from __future__ import annotations

from pathlib import Path

from agentest.standards.metadata import Agent

GOV = {"approval": {"required": ["request_refund"]}, "limits": {"max_amount": 500},
       "roles": {"actors": {"billing": ["lookup_order", "request_refund"], "triage": ["lookup_order"]}}}
CARD = {"protocolVersion": "0.3.0", "name": "Refund desk", "description": "handles refunds", "url": "https://agent.invalid/", "version": "1.0.0",
        "capabilities": {"extensions": [{"uri": "urn:agentest:a2a-ext:governance:v1", "params": GOV}]},
        "defaultInputModes": ["text/plain"], "defaultOutputModes": ["text/plain"],
        "skills": [{"id": "refund", "name": "Refund", "description": "refunds an order", "tags": ["support"], "examples": ["Refund order ORD-7"]}]}
TOOLS = {"lookup_order": {"name": "lookup_order", "inputSchema": {"type": "object"}, "annotations": {"readOnlyHint": True}},
         "request_refund": {"name": "request_refund", "inputSchema": {"type": "object"},
                            "annotations": {"readOnlyHint": False, "destructiveHint": True, "idempotentHint": False}}}
OBS = {"final_answer": ["output.final"], "executed": ["output.executed"], "pending": ["output.pending"], "approvals": ["output.approvals"]}


def agent(tmp: Path) -> Agent:
    return Agent("refund_desk", tmp, CARD, TOOLS, GOV)


def is_write(name: str) -> bool:
    return not TOOLS.get(name, {}).get("annotations", {}).get("readOnlyHint", False)


def record(probe: str, rep: int, text: str, trace: list, final: str, executed=(), pending=(), approvals=(), **native) -> dict:
    """One native run record in the shape every dialect shares (input, trace, output)."""
    return {"agent": "refund_desk", "probe": probe, "rep": rep, "input": text, "trace": trace,
            "output": {"final": final, "executed": list(executed), "pending": list(pending), "approvals": list(approvals)}, **native}
