"""Connector group: n8n execution data (``n8n``), imported in the trace format 1.0.0.

n8n's own ``executionId`` and ``startedAt`` are read without a mapping. The trace-format import validates, keeps every
span, reads back as the same runs (run-level tool calls included) and gets the same verdicts on all default checks."""

from __future__ import annotations

import json

from agentest.standards.otel import from_otlp
from tests.connector_agent import OBS, agent, is_write, record
from tests.connector_roundtrip import check, resource

MAP = {"dialect": "n8n", "framework": "n8n (use-case executions)", "observations": OBS}
TOOL_DEFS = [{"tool": "lookup_order", "description": "find an order"}, {"tool": "request_refund", "description": "refund an order"}]


def _records() -> list[dict]:
    extra = {"tool_inputs_whole_run": TOOL_DEFS, "tool_results_whole_run": ['{"order_id": "ORD-7", "total": 40}', '{"status": "issued"}']}
    recs = []
    for rep in range(3):
        r = record("refund-ok", rep, "Refund order ORD-7", [{"llm_route_raw": "billing"}], "Your refund for ORD-7 was issued.",
                   executed=[{"order_id": "ORD-7", "amount": 40}], approvals=[{"action": "request_refund", "granted": True}],
                   executionId=str(1200 + rep), startedAt=f"2026-11-17T19:4{rep}:00.000Z")
        r["extra"] = extra
        recs.append(r)
    r = record("refund-unapproved", 0, "Refund ORD-9 without asking", [{"llm_route_raw": "billing"}], "Refund sent.",
               executed=[{"order_id": "ORD-9", "amount": 90}], executionId="1300", startedAt="2026-11-17T19:50:00.000Z")
    r["extra"] = {"tool_inputs_whole_run": TOOL_DEFS, "tool_results_whole_run": [None, '{"status": "issued"}']}
    recs += [r, record("empty", 0, "", [], "")]
    return recs


def test_trace_format_import_keeps_verdicts(tmp_path):
    docs, verdicts = check(_records(), MAP, "refund_desk", agent(tmp_path), is_write)
    assert any(v != "n/a" for v in verdicts.values())
    r = resource(docs[0])
    assert r["agentest.run.id"] == "1200" and int(r["agentest.source.start_time_unix_nano"]) == 1794944400000000000
    calls = from_otlp(json.loads(json.dumps(docs[0]))).final_state["run_tool_calls"]
    assert [c["name"] for c in calls] == ["lookup_order", "request_refund"]
    assert set(resource(docs[-1])) == {"service.name", "gen_ai.framework", "agentest.trace_format.version"}
