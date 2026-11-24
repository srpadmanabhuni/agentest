"""Shared harness for the extension-pack tests: build an Agent, round-trip synthetic OTLP through the reader, evaluate by ID."""
from __future__ import annotations

import json
from pathlib import Path

from agentest.standards import GOV_EXT
from agentest.standards.metadata import Agent
from agentest.standards.otel import from_otlp
from agentest.standards.packs.synth import Synth
from agentest.standards.rules import evaluate

W = {"readOnlyHint": False, "destructiveHint": False}
D = {"readOnlyHint": False, "destructiveHint": True}
RO = {"readOnlyHint": True}
CLOSED = {"readOnlyHint": False, "destructiveHint": False, "openWorldHint": False}
OPEN = {"readOnlyHint": False, "destructiveHint": False, "openWorldHint": True}


def tool(name, ann, desc="", props=None):
    return {"name": name, "description": desc or name, "annotations": ann,
            "inputSchema": {"type": "object", "properties": props or {}}}


TOOLS = {t["name"]: t for t in [
    tool("lookup_order", RO), tool("issue_refund", D), tool("update_ticket", W), tool("escalate_to_human", W),
    tool("send_note", W), tool("read_secret", RO), tool("web_post", OPEN), tool("save_memory", CLOSED),
    tool("erase_data", D), tool("search_kb", RO), tool("approve_loan", W),
    tool("update_profile", CLOSED, props={"user_id": {}, "email": {}}), tool("fetch_record", RO), tool("post_public", OPEN),
]}


def agent(gov: dict | None = None, tools: dict | None = None) -> Agent:
    params = dict(gov or {})
    card = {"name": "unit", "skills": [], "capabilities": {"extensions": [{"uri": GOV_EXT, "params": params}] if gov is not None else []}}
    return Agent("unit", Path("/tmp/unit"), card, TOOLS if tools is None else tools, params if gov is not None else {})


def runs(*docs):
    return [from_otlp(json.loads(json.dumps(d))) for d in docs]


def status(a: Agent, docs, tid: str) -> str:
    return evaluate(a, runs(*docs), ids=[tid])[tid].status


def run_case(tid: str, case: dict) -> None:
    """case: gov (spec for pass/fail), fail/clean (callables returning a list of docs), optional na (callable) and na_gov."""
    gov = case.get("gov", {})
    assert status(agent(gov, case.get("fail_tools", case.get("tools"))), case["fail"](), tid) == "fail", f"{tid}: seeded defect not caught"
    assert status(agent(gov, case.get("clean_tools", case.get("tools"))), case["clean"](), tid) == "pass", f"{tid}: clean control flagged"
    if "na" in case:
        na_agent = agent(case.get("na_gov", gov), case.get("na_tools", case.get("tools")))
        assert status(na_agent, case["na"](), tid) == "n/a", f"{tid}: missing observable must be n/a, not a verdict"


def one(fn):
    """Wrap a single-trace builder into the list form."""
    return lambda: [fn().build()]


__all__ = ["Synth", "agent", "runs", "status", "run_case", "one", "TOOLS", "W", "D", "RO", "CLOSED", "OPEN", "tool"]
