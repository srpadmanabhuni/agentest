"""Unit tests for Phase 1 New tests batch 1 (NT-001..NT-009, opt-in).

Constructed use case traces only (OTLP dicts read through ``from_otlp``, plus hand-built ``Run`` objects); neutral tool
names, no agent or framework names. Each check has pass, fail and n/a cases. No network, no model.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from agentest.standards import GOV_EXT
from agentest.standards.catalog import ALL_IDS, new_tests
from agentest.standards.metadata import Agent
from agentest.standards.otel import Run, ToolSpan, from_otlp
from agentest.standards.rules import evaluate

B1 = [f"NT-00{i}" for i in range(1, 10)]
RO = {"readOnlyHint": True}
W = {"readOnlyHint": False, "destructiveHint": False}
TOOLS = {
    "lookup": {"name": "lookup", "annotations": RO, "description": "Read a record."},
    "search": {"name": "search", "annotations": RO, "description": "Search records."},
    "update_record": {"name": "update_record", "annotations": W, "description": "Update a record."},
    "send_note": {"name": "send_note", "annotations": W, "description": "Send a note."},
    "open_page": {"name": "open_page", "annotations": RO, "description": "Read a web page."},
    "get_order": {"name": "get_order", "annotations": RO, "description": "Read an order from an API."},
}


def _agent(tools=None) -> Agent:
    card = {"name": "unit-b1", "skills": [], "capabilities": {"extensions": [{"uri": GOV_EXT, "params": {}}]}}
    return Agent("unit-b1", Path("/tmp/unit-b1"), card, tools or TOOLS, {})


def _v(x):
    if isinstance(x, bool):
        return {"boolValue": x}
    if isinstance(x, int):
        return {"intValue": str(x)}
    if isinstance(x, float):
        return {"doubleValue": x}
    return {"stringValue": x if isinstance(x, str) else json.dumps(x)}


def _otlp(spans, *, root=None, answer="Done.", dur_ns=5_000_000_000, input_id="task-1", rep=0):
    """``spans``: list of (name, attrs) in start order, children of one root span. Root lasts ``dur_ns``."""
    ra = {"gen_ai.operation.name": "invoke_agent", "gen_ai.agent.name": "desk",
          "gen_ai.input.messages": json.dumps([{"role": "user", "parts": [{"type": "text", "content": "Please help."}]}]),
          "gen_ai.output.messages": json.dumps([{"role": "assistant", "parts": [{"type": "text", "content": answer}]}]),
          "gen_ai.conversation.id": f"{input_id}#{rep}", "agentest.input.id": input_id, "agentest.run.rep": rep, **(root or {})}
    out = [{"traceId": "ab" * 16, "spanId": f"{1:016x}", "parentSpanId": "", "name": "invoke_agent desk", "kind": 1,
            "startTimeUnixNano": "1000", "endTimeUnixNano": str(1000 + dur_ns),
            "attributes": [{"key": k, "value": _v(v)} for k, v in ra.items() if v is not None], "status": {"code": 1}}]
    for i, (name, a) in enumerate(spans, start=1):
        out.append({"traceId": "ab" * 16, "spanId": f"{i + 1:016x}", "parentSpanId": f"{1:016x}", "name": name, "kind": 1,
                    "startTimeUnixNano": str(2000 + 100 * i), "endTimeUnixNano": str(2050 + 100 * i),
                    "attributes": [{"key": k, "value": _v(v)} for k, v in a.items() if v is not None],
                    "status": {"code": 2 if a.get("error.type") else 1}})
    return {"resourceSpans": [{"resource": {"attributes": [{"key": "service.name", "value": {"stringValue": "desk"}}]},
                               "scopeSpans": [{"scope": {"name": "unit"}, "spans": out}]}]}


def _tool(name, args=None, result=None, **attrs):
    a = {"gen_ai.operation.name": "execute_tool", "gen_ai.tool.name": name, "gen_ai.tool.call.id": f"c-{name}",
         "gen_ai.tool.call.arguments": json.dumps(args or {}),
         "gen_ai.tool.call.result": result if isinstance(result, str) or result is None else json.dumps(result)}
    a.update(attrs)
    return (f"execute_tool {name}", a)


def _chat(inp, out, **attrs):
    return ("chat model", {"gen_ai.operation.name": "chat", "gen_ai.usage.input_tokens": inp, "gen_ai.usage.output_tokens": out, **attrs})


def _run(spans, **kw) -> Run:
    return from_otlp(_otlp(spans, **kw))


def _st(runs, tid, agent=None):
    if isinstance(runs, Run):
        runs = [runs]
    return evaluate(agent or _agent(), runs, ids=[tid])[tid].status


# ---------------------------------------------------------------- registry

def test_b1_rows_and_rules_registered_and_opt_in():
    rows = new_tests()
    assert [i for i in rows if rows[i]["batch"] == "b1"] == B1
    assert not set(B1) & set(ALL_IDS)
    res = evaluate(_agent(), [_run([_tool("lookup", result={"ok": 1})])])  # default set
    assert not any(k.startswith("NT-") for k in res)
    for i in B1:
        assert rows[i]["class_id"] == "NT" and rows[i]["trace_attributes"]


def test_otlp_round_trip_keeps_new_test_attributes():
    r = _run([_tool("open_page", result={"price": "12.50"}, **{"agentest.tool.kind": "page_snapshot", "agentest.step.expected_tool": "open_page"})],
             root={"agentest.task.budget.latency_s": 10, "agentest.task.allowed_actions": ["update_record"]})
    assert r.attrs["agentest.task.budget.latency_s"] == 10
    assert json.loads(r.attrs["agentest.task.allowed_actions"]) == ["update_record"]
    tool = next(s for s in r.spans if s["name"] == "execute_tool open_page")
    assert tool["attrs"]["agentest.tool.kind"] == "page_snapshot" and tool["attrs"]["agentest.step.expected_tool"] == "open_page"
    assert r.tools[0].attrs["agentest.tool.kind"] == "page_snapshot"


def test_every_b1_check_is_na_without_its_attributes():
    r = _run([_tool("lookup", result={"ok": 1}), _chat(10, 5)])
    for i in B1:
        assert _st(r, i) == "n/a", i


# ---------------------------------------------------------------- NT-001 latency budget

def test_nt_001_latency_within_budget_pass():
    rs = [_run([_tool("lookup")], root={"agentest.task.budget.latency_s": 10}, dur_ns=d * 1_000_000_000, rep=i)
          for i, d in enumerate((4, 6, 30))]  # median 6 s <= 10 s even with one slow run
    assert _st(rs, "NT-001") == "pass"


def test_nt_001_latency_over_budget_fail():
    rs = [_run([_tool("lookup")], root={"agentest.task.budget.latency_s": 5}, dur_ns=d * 1_000_000_000, rep=i)
          for i, d in enumerate((4, 8, 9))]
    assert _st(rs, "NT-001") == "fail"


def test_nt_001_tasks_judged_separately_by_task_id():
    rs = [_run([_tool("lookup")], root={"agentest.task.budget.latency_s": 10, "agentest.task.id": t}, dur_ns=d * 1_000_000_000,
               input_id=f"in-{i}") for i, (t, d) in enumerate((("a", 4), ("a", 5), ("b", 20)))]
    assert _st(rs, "NT-001") == "fail"  # task b is over budget
    assert _st(rs[:2], "NT-001") == "pass"


def test_nt_001_no_budget_na():
    assert _st(_run([_tool("lookup")], dur_ns=99 * 1_000_000_000), "NT-001") == "n/a"


def test_nt_001_reads_hand_built_runs():
    r = Run(input_id="t", rep=0, input="x", answer="y", duration_s=3.0, attrs={"agentest.task.budget.latency_s": 2})
    assert _st(r, "NT-001") == "fail"


# ---------------------------------------------------------------- NT-002 token / cost budget

def test_nt_002_tokens_and_cost_within_budget_pass():
    r = _run([_chat(300, 100, **{"agentest.usage.cost": 0.01}), _tool("lookup"), _chat(400, 100, **{"agentest.usage.cost": 0.02})],
             root={"agentest.task.budget.tokens": 1000, "agentest.task.budget.cost": 0.05})
    assert _st(r, "NT-002") == "pass"


def test_nt_002_tokens_over_budget_fail():
    r = _run([_chat(800, 300), _chat(500, 200)], root={"agentest.task.budget.tokens": 1000})
    assert _st(r, "NT-002") == "fail"


def test_nt_002_cost_over_budget_fail():
    r = _run([_chat(10, 10, **{"agentest.usage.cost": 0.2})], root={"agentest.task.budget.tokens": 1000, "agentest.task.budget.cost": 0.1})
    assert _st(r, "NT-002") == "fail"


def test_nt_002_root_totals_not_double_counted():
    r = _run([_chat(400, 100)], root={"agentest.task.budget.tokens": 600, "gen_ai.usage.input_tokens": 400, "gen_ai.usage.output_tokens": 100})
    assert _st(r, "NT-002") == "pass"


def test_nt_002_na_without_usage_or_budget():
    assert _st(_run([_tool("lookup")], root={"agentest.task.budget.tokens": 1000}), "NT-002") == "n/a"
    assert _st(_run([_chat(10, 10)]), "NT-002") == "n/a"


# ---------------------------------------------------------------- NT-003 autonomy ratio

HUMAN = ("agentest.human_input", {"agentest.human_input.kind": "confirm"})


def test_nt_003_ratio_matches_declared_level_pass():
    # 4 tool steps, one after a human-input span: 3/4 = 0.75
    r = _run([_tool("lookup"), _tool("search"), HUMAN, _tool("update_record"), _tool("lookup")],
             root={"agentest.task.autonomy_level": 0.75})
    assert _st(r, "NT-003") == "pass"


def test_nt_003_step_flag_and_percentage_level_fail():
    r = _run([_tool("lookup", **{"agentest.step.human_input": True}), _tool("search", **{"agentest.step.human_input": True}),
              _tool("update_record")], root={"agentest.task.autonomy_level": 90})
    assert _st(r, "NT-003") == "fail"  # 1/3 autonomous vs declared 90 %


def test_nt_003_tolerance_widens_the_band():
    spans = [_tool("lookup"), HUMAN, _tool("search"), _tool("update_record")]  # 2/3
    assert _st(_run(spans, root={"agentest.task.autonomy_level": 0.8}), "NT-003") == "fail"
    assert _st(_run(spans, root={"agentest.task.autonomy_level": 0.8, "agentest.task.autonomy_tolerance": 0.2}), "NT-003") == "pass"


def test_nt_003_na_without_level_or_steps():
    assert _st(_run([_tool("lookup"), HUMAN]), "NT-003") == "n/a"
    assert _st(_run([HUMAN], root={"agentest.task.autonomy_level": 1.0}), "NT-003") == "n/a"


# ---------------------------------------------------------------- NT-004 expected tool per step

def test_nt_004_expected_or_acceptable_tool_pass():
    r = _run([_tool("lookup", **{"agentest.step.expected_tool": "lookup"}),
              _tool("search", **{"agentest.step.expected_tool": "lookup", "agentest.step.acceptable_tools": ["search"]}),
              _tool("send_note")])  # unlabelled step is not judged
    assert _st(r, "NT-004") == "pass"


def test_nt_004_wrong_tool_fail():
    r = _run([_tool("lookup", **{"agentest.step.expected_tool": "lookup"}),
              _tool("send_note", **{"agentest.step.expected_tool": "update_record", "agentest.step.acceptable_tools": "lookup, search"})])
    assert _st(r, "NT-004") == "fail"


def test_nt_004_no_labels_na():
    assert _st(_run([_tool("lookup"), _tool("send_note")]), "NT-004") == "n/a"


def test_nt_004_hand_built_tool_spans():
    t = ToolSpan("search", {}, "{}", False, "", 1, attrs={"agentest.step.expected_tool": "lookup"})
    assert _st(Run(input_id="t", rep=0, input="", answer="", tools=[t]), "NT-004") == "fail"


# ---------------------------------------------------------------- NT-005 goal relevance

ALLOWED = {"agentest.task.allowed_actions": ["update_record"]}


def test_nt_005_writes_in_allowed_set_pass():
    r = _run([_tool("lookup"), _tool("update_record", {"id": "R-1"}, {"ok": True})], root=ALLOWED)
    assert _st(r, "NT-005") == "pass"


def test_nt_005_off_goal_write_fail():
    r = _run([_tool("update_record", {"id": "R-1"}, {"ok": True}), _tool("send_note", {"to": "x"}, {"ok": True})], root=ALLOWED)
    assert _st(r, "NT-005") == "fail"


def test_nt_005_failed_write_and_attack_runs_not_judged():
    failed = _run([_tool("update_record"), _tool("send_note", **{"error.type": "denied"})], root=ALLOWED)
    assert _st(failed, "NT-005") == "pass"
    attack = _run([_tool("send_note", result={"ok": True})], root={**ALLOWED, "agentest.input.attack": True})
    assert _st(attack, "NT-005") == "n/a"


def test_nt_005_na_without_declaration_or_writes():
    assert _st(_run([_tool("send_note")]), "NT-005") == "n/a"
    assert _st(_run([_tool("lookup")], root=ALLOWED), "NT-005") == "n/a"


# ---------------------------------------------------------------- NT-006 page extraction

SNAP = {"agentest.tool.kind": "page_snapshot"}
PAGE = {"title": "Desk lamp", "price": "24.99", "stock": {"count": 3}}


def test_nt_006_extracted_values_match_page_pass():
    r = _run([_tool("open_page", {"url": "https://shop.example/lamp"}, PAGE, **SNAP)],
             answer=json.dumps({"title": "desk lamp", "price": 24.99, "count": 3}))
    assert _st(r, "NT-006") == "pass"


def test_nt_006_wrong_value_fail():
    r = _run([_tool("open_page", result=PAGE, **SNAP)], answer=json.dumps({"title": "Desk lamp", "price": "19.99"}))
    assert _st(r, "NT-006") == "fail"


def test_nt_006_invented_field_fail():
    r = _run([_tool("open_page", result=PAGE, **SNAP)], answer=json.dumps({"title": "Desk lamp", "rating": "4.5"}))
    assert _st(r, "NT-006") == "fail"


def test_nt_006_declared_field_missing_fail_and_structured_attr():
    r = _run([_tool("open_page", result=PAGE, **SNAP)], answer="Here it is.",
             root={"agentest.task.extracted": ["title", "price"], "agentest.output.structured": {"title": "Desk lamp"}})
    assert _st(r, "NT-006") == "fail"


def test_nt_006_na_without_snapshot_or_structured_output():
    assert _st(_run([_tool("open_page", result=PAGE)], answer=json.dumps({"title": "Desk lamp"})), "NT-006") == "n/a"
    assert _st(_run([_tool("open_page", result=PAGE, **SNAP)], answer="The lamp costs 24.99."), "NT-006") == "n/a"


# ---------------------------------------------------------------- NT-007 click target

def _click(want, got, name="ui.click"):
    return (name, {"agentest.ui.action": "click", "agentest.ui.expected_element_id": want, "agentest.ui.element_id": got})


def test_nt_007_click_on_intended_element_pass():
    assert _st(_run([_click("btn-buy", "btn-buy"), _click("link-cart", "link-cart")]), "NT-007") == "pass"


def test_nt_007_mis_click_fail():
    assert _st(_run([_click("btn-buy", "btn-buy"), _click("btn-buy", "btn-wishlist")]), "NT-007") == "fail"


def test_nt_007_click_on_tool_span_fail():
    r = _run([_tool("click", {"selector": "#x"}, {"ok": True}, **{"agentest.ui.action": "click",
                                                                  "agentest.ui.expected_element_id": "a", "agentest.ui.element_id": "b"})])
    assert _st(r, "NT-007") == "fail"


def test_nt_007_na_without_intended_or_recorded_element():
    assert _st(_run([_click(None, "btn-buy"), _click("btn-buy", None)]), "NT-007") == "n/a"


# ---------------------------------------------------------------- NT-008 form filling

def _form(fid, *, action="fill", values=None, errors=None, step=None):
    return ("ui.form", {"agentest.form.id": fid, "agentest.form.action": action,
                        "agentest.form.values": values, "agentest.form.validation_errors": errors, "agentest.form.step": step})


EXP = {"agentest.task.expected_form": {"signup": {"email": "a@example.org", "zip": "560001"}}}


def test_nt_008_error_corrected_and_values_match_pass():
    r = _run([_form("signup", action="submit", values={"email": "a@example.org", "zip": "5600"}, errors=["zip: 6 digits"]),
              _form("signup", action="submit", values={"email": "a@example.org", "zip": "560001"})], root=EXP)
    assert _st(r, "NT-008") == "pass"


def test_nt_008_final_submit_wrong_value_fail():
    r = _run([_form("signup", action="submit", values={"email": "b@example.org", "zip": "560001"})], root=EXP)
    assert _st(r, "NT-008") == "fail"


def test_nt_008_uncorrected_validation_error_fail():
    r = _run([_form("signup", action="submit", values={"zip": "1"}, errors=["zip: 6 digits"])])
    assert _st(r, "NT-008") == "fail"


def test_nt_008_expected_form_never_submitted_fail():
    r = _run([_form("signup", values={"email": "a@example.org"})], root=EXP)
    assert _st(r, "NT-008") == "fail"


def test_nt_008_multi_step_form_order_and_completeness():
    ok_steps = [_form("claim", step=1), _form("claim", step=2), _form("claim", step=2), _form("claim", action="submit", step=3, values={"amt": 5})]
    assert _st(_run(ok_steps, root={"agentest.task.form_steps": {"claim": 3}}), "NT-008") == "pass"
    skipped = [_form("claim", step=1), _form("claim", action="submit", step=3, values={"amt": 5})]
    assert _st(_run(skipped), "NT-008") == "fail"
    short = [_form("claim", step=1), _form("claim", action="submit", step=2, values={"amt": 5})]
    assert _st(_run(short, root={"agentest.task.form_steps": {"claim": 3}}), "NT-008") == "fail"
    back = [_form("claim", step=1), _form("claim", step=2), _form("claim", step=1), _form("claim", action="submit", step=2)]
    assert _st(_run(back), "NT-008") == "fail"


def test_nt_008_na_without_forms():
    assert _st(_run([_tool("lookup"), _click("a", "a")]), "NT-008") == "n/a"


# ---------------------------------------------------------------- NT-009 API response mapping

MAP = {"agentest.task.output_mapping": {"status": {"tool": "get_order", "path": "order.status"},
                                        "total": {"tool": "get_order", "path": "order.lines.0.amount"}}}
ORDER = {"order": {"status": "SHIPPED", "lines": [{"amount": 42.5}]}}


def test_nt_009_fields_mapped_from_response_pass():
    r = _run([_tool("get_order", {"id": "O-1"}, ORDER)], root=MAP, answer=json.dumps({"status": "shipped", "total": "42.50"}))
    assert _st(r, "NT-009") == "pass"


def test_nt_009_wrong_mapping_fail():
    r = _run([_tool("get_order", {"id": "O-1"}, ORDER)], root=MAP, answer=json.dumps({"status": "DELIVERED", "total": 42.5}))
    assert _st(r, "NT-009") == "fail"


def test_nt_009_partial_response_flagged_not_used_pass():
    r = _run([_tool("get_order", {"id": "O-1"}, {"order": {"status": "SHIPPED"}}, **{"agentest.api.response_status": "partial"})],
             root={**MAP, "agentest.output.flagged": ["get_order"]}, answer=json.dumps({"status": None, "total": None}))
    assert _st(r, "NT-009") == "pass"


def test_nt_009_partial_or_malformed_response_used_fail():
    used = _run([_tool("get_order", {"id": "O-1"}, ORDER, **{"agentest.api.response_status": "partial"})],
                root=MAP, answer=json.dumps({"status": "SHIPPED", "total": 42.5}))
    assert _st(used, "NT-009") == "fail"
    silent = _run([_tool("get_order", {"id": "O-1"}, "<html>502 Bad Gateway</html>")], root=MAP, answer=json.dumps({"status": None}))
    assert _st(silent, "NT-009") == "fail"  # unparsable response not flagged


def test_nt_009_later_good_response_is_used():
    r = _run([_tool("get_order", {"id": "O-1"}, "{bad", **{"agentest.api.response_status": "malformed"}),
              _tool("get_order", {"id": "O-1"}, ORDER)], root=MAP, answer=json.dumps({"status": "SHIPPED", "total": 42.5}))
    assert _st(r, "NT-009") == "pass"


@pytest.mark.parametrize("root,answer,spans", [
    ({}, json.dumps({"status": "SHIPPED"}), [_tool("get_order", result=ORDER)]),  # no mapping
    (MAP, "It shipped.", [_tool("get_order", result=ORDER)]),  # no structured output
    (MAP, json.dumps({"status": "SHIPPED"}), [_tool("lookup", result=ORDER)]),  # source API not called
])
def test_nt_009_na(root, answer, spans):
    assert _st(_run(spans, root=root, answer=answer), "NT-009") == "n/a"
