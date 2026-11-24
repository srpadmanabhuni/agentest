"""Authoring kit for the labelled evaluation set of the opt-in extension packs and the five responsible-AI opt-ins.

RULES OF THE AUTHORING (so that labels are independent of the check code):
  * this package imports only the trace builder (``agentest.standards.packs.synth.Synth``), never ``evaluate``, a rule or a pack module;
  * every scenario carries its label from the moment it is written, derived from the one-sentence spec of the check
    (``catalog/packs/*.jsonl`` ``rule`` field, or the ``rai-additions`` acceptance criteria), not from what any check returns;
  * the label of a scenario is ``defect`` (the spec says the check must FAIL on it) or ``clean`` (the spec says it must not).
"""
from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from agentest.standards.packs.synth import Synth

__all__ = ["Synth", "REG", "case", "V", "TOOLS_STD", "tool", "user_for"]

AUTHOR = "Grok Bot (executor subagent) for srpadmanabhuni, 2026-11-15"
RO = {"readOnlyHint": True, "openWorldHint": False}
W = {"readOnlyHint": False, "destructiveHint": False, "openWorldHint": False}
D = {"readOnlyHint": False, "destructiveHint": True, "openWorldHint": False}
OPEN = {"readOnlyHint": False, "destructiveHint": False, "openWorldHint": True}


def tool(name: str, ann: dict, desc: str = "", props: dict | None = None) -> dict:
    return {"name": name, "description": desc or f"{name.replace('_', ' ')}.", "annotations": ann, "inputSchema": {"type": "object", "properties": props or {}}}


TOOLS_STD = {t["name"]: t for t in [
    tool("lookup_order", RO, "Look up an order by id."), tool("search_kb", RO, "Search the knowledge base."), tool("fetch_record", RO, "Fetch a customer record."),
    tool("read_secret", RO, "Read a configuration secret."), tool("issue_refund", D, "Issue a refund for an order."), tool("update_ticket", W, "Update a support ticket."),
    tool("escalate_to_human", W, "Hand the case to a human agent."), tool("send_note", W, "Send a note to a customer."), tool("approve_loan", W, "Approve a loan application."),
    tool("erase_data", D, "Erase a user's data."), tool("update_profile", W, "Update a customer profile.", props={"user_id": {}, "email": {}}),
    tool("save_memory", W, "Save a note to long-term memory."), tool("web_post", OPEN, "Post data to an external web endpoint."),
    tool("post_public", OPEN, "Publish text publicly."), tool("reverse_refund", D, "Reverse a refund."), tool("revert_ticket", W, "Revert a ticket update."),
]}

# surface variants: ids, amounts, people, phrasing. Scenario i of a pattern uses V[i % len(V)].
V = [
    dict(i=0, oid="ORD-1001", oid2="ORD-1002", tid="TK-101", tid2="TK-102", cid="C-2001", amt=25, amt2=40, name="Asha", email="asha.rao@example.com", phone="415-555-0123", w1="billing", w2="shipping", w3="audit", ask="Please refund order ORD-1001 for 25.", city="Pune"),
    dict(i=1, oid="ORD-2417", oid2="ORD-2418", tid="TK-317", tid2="TK-318", cid="C-3112", amt=120, amt2=75, name="Ravi", email="ravi.k@example.org", phone="212-555-0188", w1="refunds", w2="logistics", w3="compliance", ask="Customer wants ORD-2417 refunded, amount 120.", city="Chennai"),
    dict(i=2, oid="ORD-8120", oid2="ORD-8121", tid="TK-840", tid2="TK-841", cid="C-4420", amt=49.5, amt2=15, name="Meera", email="meera.s@example.net", phone="303-555-0147", w1="payments", w2="dispatch", w3="risk", ask="Refund 49.5 on ORD-8120 please.", city="Kochi"),
    dict(i=3, oid="ORD-3306", oid2="ORD-3307", tid="TK-562", tid2="TK-563", cid="C-5873", amt=310, amt2=200, name="Imran", email="imran.q@example.com", phone="646-555-0161", w1="billing", w2="support", w3="review", ask="Process a refund of 310 for ORD-3306.", city="Delhi"),
    dict(i=4, oid="ORD-5509", oid2="ORD-5510", tid="TK-905", tid2="TK-906", cid="C-6234", amt=75, amt2=30, name="Joy", email="joy.d@example.org", phone="510-555-0199", w1="refunds", w2="shipping", w3="audit", ask="I need ORD-5509 refunded (75).", city="Jaipur"),
    dict(i=5, oid="ORD-7731", oid2="ORD-7732", tid="TK-230", tid2="TK-231", cid="C-7001", amt=18, amt2=60, name="Lena", email="lena.m@example.net", phone="720-555-0112", w1="payments", w2="logistics", w3="compliance", ask="Could you refund ORD-7731 for 18?", city="Goa"),
]


def user_for(v: dict) -> str:
    return v["ask"]


def _specs() -> dict[str, str]:
    from pathlib import Path

    root = Path(__file__).resolve().parents[3]
    out: dict[str, str] = {}
    for f in sorted((root / "catalog" / "packs").glob("*.jsonl")):
        for line in f.read_text(encoding="utf-8").splitlines():
            if line.strip():
                r = json.loads(line)
                out[r["id"]] = r["rule"]
    for line in (root / "catalog" / "rai-additions-v1.4.0.jsonl").read_text(encoding="utf-8").splitlines():
        if line.strip():
            r = json.loads(line)
            out[r["id"]] = f"{r['title']}. {r['acceptance_criteria']}"
    return out


SPEC = _specs()
REG: list[dict] = []


def case(check: str, label: str, name: str, spec: str = "", n: int = 4, kind: str | None = None):
    """Register a scenario pattern. ``fn(v)`` returns ``(gov, docs)`` or ``(gov, docs, tools_patch)``; ``docs`` are Synth objects or OTLP dicts.

    label: ``defect`` or ``clean``; kind: ``realistic`` (default), ``hard_negative`` (clean but close to the defect) or ``near_miss``.
    """
    assert label in ("defect", "clean")

    def deco(fn: Callable[[dict], Any]):
        for i in range(n):
            v = V[i % len(V)]
            out = fn(v)
            gov, docs, patch = (out + ({},))[:3] if len(out) == 2 else out
            docs = [d.build() if hasattr(d, "build") else d for d in docs]
            sid = f"{check}.{label[0]}.{name}.{i}"
            REG.append({"scenario": {"scenario_id": sid, "check_id": check, "gov": gov, "tools_patch": patch, "traces": docs},
                        "label": {"scenario_id": sid, "check_id": check, "label": label, "expected_status": "fail" if label == "defect" else "not-fail",
                                  "kind": kind or ("realistic" if label == "defect" else "negative"), "pattern": name, "variant": i, "spec_clause": spec or SPEC[check],
                                  "provenance": f"written from the spec sentence of {check} before any check was run on it; label = construction intent; author {AUTHOR}"}})
        return fn
    return deco


def dumps(x: Any) -> str:
    return json.dumps(x, ensure_ascii=False, sort_keys=True)
