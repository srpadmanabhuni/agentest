"""T1-001 state outcome (r13 W2). Synthetic fixtures only.

Two tool vocabularies and two trace dialects (native OTLP and a LangGraph import)
must agree. No desk, agent, tool, scenario or case id from a scored round is used.
"""
from __future__ import annotations

import json
from pathlib import Path

from agentest.standards import GOV_EXT
from agentest.standards.detectors import REGISTRY
from agentest.standards.detectors.state_outcome import StateOutcome
from agentest.standards.episode import Episode, ToolCall
from agentest.standards.importers import to_docs
from agentest.standards.metadata import Agent
from agentest.standards.otel import Run, ToolSpan, from_otlp, to_otlp
from agentest.standards.rules import Ctx, evaluate

VOCS = (
    {"read": "inspect_bin", "write": "place_bin_hold", "root": "bins", "obj": "BIN-7", "good": "held", "bad": "open"},
    {"read": "inspect_slot", "write": "commit_slot", "root": "slots", "obj": "SLOT-7", "good": "booked", "bad": "open"},
)

# 12 failing and 12 passing logical cases. ``$good`` / ``$bad`` resolve per vocabulary.
FAILS = [
    {"name": "later-variant-fails", "contains": ["later-variant"], "runs": [
        {"id": "base-run", "families": ["canonical"], "fields": {"status": "$good"}},
        {"id": "later-variant", "families": ["alternate"], "fields": {"status": "$bad"}},
    ]},
    {"name": "harness-pass-state-fails", "contains": ["disagreement"], "runs": [
        {"id": "base-run", "fields": {"status": "$bad"}, "attr": "pass"},
    ]},
    {"name": "attribute-absent-state-fails", "runs": [
        {"id": "base-run", "fields": {"status": "$bad"}},
    ]},
    {"name": "ge-unmet", "runs": [
        {"id": "base-run", "preds": [("qty", "ge", 5)], "fields": {"qty": 1}},
    ]},
    {"name": "le-unmet", "runs": [
        {"id": "base-run", "preds": [("qty", "le", 2)], "fields": {"qty": 9}},
    ]},
    {"name": "contains-unmet", "runs": [
        {"id": "base-run", "preds": [("note", "contains", "ready")], "fields": {"note": "waiting"}},
    ]},
    {"name": "excludes-unmet", "runs": [
        {"id": "base-run", "preds": [("note", "excludes", "blocked")], "fields": {"note": "still blocked"}},
    ]},
    {"name": "nonempty-unmet", "runs": [
        {"id": "base-run", "preds": [("code", "nonempty", None)], "fields": {"code": ""}},
    ]},
    {"name": "second-predicate-unmet", "runs": [
        {"id": "base-run", "preds": [("status", "eq", "$good"), ("qty", "eq", 0)], "fields": {"status": "$good", "qty": 3}},
    ]},
    {"name": "middle-run-fails", "contains": ["mid-run"], "runs": [
        {"id": "base-run", "families": ["canonical"], "fields": {"status": "$good"}},
        {"id": "mid-run", "fields": {"status": "$bad"}},
        {"id": "tail-run", "fields": {"status": "$good"}},
    ]},
    {"name": "nested-flag-fails", "runs": [
        {"id": "base-run", "preds": [("meta.flag", "eq", True)], "fields": {"meta": {"flag": False}}},
    ]},
    {"name": "repeat-fails", "contains": ["#1"], "runs": [
        {"id": "base-run", "rep": 0, "fields": {"status": "$good"}},
        {"id": "base-run", "rep": 1, "fields": {"status": "$bad"}},
    ]},
]
PASSES = [
    {"name": "single-holds", "absent": ["disagreement"], "runs": [
        {"id": "base-run", "fields": {"status": "$good"}},
    ]},
    {"name": "attribute-absent-state-holds", "absent": ["disagreement"], "runs": [
        {"id": "base-run", "fields": {"status": "$good"}},
    ]},
    {"name": "harness-agrees", "absent": ["disagreement"], "runs": [
        {"id": "base-run", "fields": {"status": "$good"}, "attr": "pass"},
    ]},
    {"name": "harness-fail-state-holds", "contains": ["disagreement"], "runs": [
        {"id": "base-run", "fields": {"status": "$good"}, "attr": "fail"},
    ]},
    {"name": "both-variants-hold", "runs": [
        {"id": "base-run", "families": ["canonical"], "fields": {"status": "$good"}},
        {"id": "later-variant", "families": ["alternate"], "fields": {"status": "$good"}},
    ]},
    {"name": "ge-holds", "runs": [
        {"id": "base-run", "preds": [("qty", "ge", 5)], "fields": {"qty": 5}},
    ]},
    {"name": "le-holds", "runs": [
        {"id": "base-run", "preds": [("qty", "le", 2)], "fields": {"qty": 2}},
    ]},
    {"name": "contains-holds", "runs": [
        {"id": "base-run", "preds": [("note", "contains", "ready")], "fields": {"note": "ready now"}},
    ]},
    {"name": "excludes-holds", "runs": [
        {"id": "base-run", "preds": [("note", "excludes", "blocked")], "fields": {"note": "clear"}},
    ]},
    {"name": "nonempty-holds", "runs": [
        {"id": "base-run", "preds": [("code", "nonempty", None)], "fields": {"code": "AB"}},
    ]},
    {"name": "both-predicates-hold", "runs": [
        {"id": "base-run", "preds": [("status", "eq", "$good"), ("qty", "eq", 0)], "fields": {"status": "$good", "qty": 0}},
    ]},
    {"name": "initial-differs-final-matches", "runs": [
        {"id": "base-run", "fields": {"status": "$good"}, "initial": {"status": "$bad"}},
    ]},
]


def _resolve(value, voc):
    if value == "$good":
        return voc["good"]
    if value == "$bad":
        return voc["bad"]
    if isinstance(value, dict):
        return {k: _resolve(v, voc) for k, v in value.items()}
    if isinstance(value, list):
        return [_resolve(v, voc) for v in value]
    return value


def _state(voc, fields):
    body = _resolve(fields, voc)
    return {voc["root"]: {voc["obj"]: body}}


def _preds(case_run, voc):
    raw = case_run.get("preds") or [("status", "eq", "$good")]
    return [{"path": f"{voc['root']}.{voc['obj']}.{leaf}", "op": op, "value": _resolve(val, voc)} for leaf, op, val in raw]


def _agent(voc) -> Agent:
    def tool(name, read):
        return {"name": name, "description": "Read one record." if read else "Record one terminal update.",
                "inputSchema": {"type": "object", "properties": {"id": {"type": "string"}, "to": {"type": "string"}}},
                "annotations": {"readOnlyHint": read, "destructiveHint": False, "idempotentHint": read, "openWorldHint": False}}
    card = {"name": "unit", "skills": [{"id": "s", "examples": ["please update the record"]}],
            "capabilities": {"extensions": [{"uri": GOV_EXT, "params": {}}]}}
    tools = {voc["read"]: tool(voc["read"], True), voc["write"]: tool(voc["write"], False)}
    return Agent("unit", Path("/tmp/unit"), card, tools, {})


def _harness(case_run, voc) -> dict:
    spec = {"goal": "reach the terminal state", "postconditions": _preds(case_run, voc)}
    final = _state(voc, case_run["fields"])
    initial_fields = case_run.get("initial", {"status": "$bad", "qty": 0, "note": "", "code": "", "meta": {"flag": False}})
    extra = {
        "agentest.task.spec": spec,
        "agentest.initial_state": _state(voc, initial_fields),
        "agentest.final_state": final,
        "agentest.input.families": case_run.get("families") or ["canonical"],
    }
    if case_run.get("attr"):
        extra["agentest.postcondition.result"] = case_run["attr"]
    return extra, final


def _stamp(doc: dict, extra: dict) -> dict:
    from agentest.standards.otel import _attrs

    spans = doc["resourceSpans"][0]["scopeSpans"][0]["spans"]
    root = next(s for s in spans if not s.get("parentSpanId"))
    root["attributes"] = [a for a in root.get("attributes", []) if a["key"] not in extra]
    root["attributes"].extend(_attrs(extra))
    return doc


def _native(case_run, voc) -> dict:
    extra, final = _harness(case_run, voc)
    ep = Episode(agent="unit", probe=case_run["id"], rep=int(case_run.get("rep", 0)), input="please update the record",
                 final_answer="updated", final_state=final,
                 tool_calls=[ToolCall(voc["read"], {"id": voc["obj"]}, result="{}"),
                             ToolCall(voc["write"], {"id": voc["obj"], "to": "set"}, result="{}")])
    return to_otlp(ep, "unit", extra)


def _langgraph(case_run, voc) -> dict:
    extra, _final = _harness(case_run, voc)
    raw = {"agent": "unit", "probe": case_run["id"], "rep": int(case_run.get("rep", 0)), "input": "please update the record",
           "output": {}, "trace": [
               {"role": "human", "content": "please update the record"},
               {"role": "ai", "content": "updating", "tool_calls": [
                   {"name": voc["read"], "args": {"id": voc["obj"]}},
                   {"name": voc["write"], "args": {"id": voc["obj"], "to": "set"}},
               ]},
               {"role": "tool", "content": "{}"},
               {"role": "tool", "content": "{}"},
           ]}
    doc = to_docs([raw], {"dialect": "langgraph_msgs", "framework": "LangGraph", "observations": {}}, "unit")[0]
    return _stamp(doc, extra)


def _eval_case(case, voc, dialect: str):
    docs = [(_native if dialect == "otlp" else _langgraph)(run, voc) for run in case["runs"]]
    runs = [from_otlp(json.loads(json.dumps(d))) for d in docs]
    return evaluate(_agent(voc), runs, ["T1-001"])["T1-001"]


def _cells(case):
    return {(voc["root"], dialect): _eval_case(case, voc, dialect) for voc in VOCS for dialect in ("otlp", "langgraph")}


def test_fixture_counts():
    assert len(FAILS) >= 10 and len(PASSES) >= 10
    assert len(VOCS) == 2


def test_family_fixtures_agree_across_vocabularies_and_dialects():
    for case, expect in [(c, "fail") for c in FAILS] + [(c, "pass") for c in PASSES]:
        cells = _cells(case)
        statuses = {r.status for r in cells.values()}
        assert statuses == {expect}, (case["name"], {k: r.status + " " + r.detail for k, r in cells.items()})
        for r in cells.values():
            for bit in case.get("contains", []):
                assert bit in r.detail, (case["name"], r.detail)
            for bit in case.get("absent", []):
                assert bit not in r.detail, (case["name"], r.detail)


def test_later_variant_fail_names_the_run_id():
    cells = _cells(FAILS[0])
    for r in cells.values():
        assert r.status == "fail" and "later-variant" in r.detail and "base-run" not in r.detail.split(";")[0]


def test_harness_pass_state_fail_adds_disagreement():
    for r in _cells(FAILS[1]).values():
        assert r.status == "fail" and "disagreement" in r.detail and "postcondition.result=pass" in r.detail and "state=fail" in r.detail


def test_missing_harness_attribute_is_still_assessed():
    for r in _cells(FAILS[2]).values():
        assert r.status == "fail" and "disagreement" not in r.detail
    for r in _cells(PASSES[1]).values():
        assert r.status == "pass" and "disagreement" not in r.detail


def test_no_spec_stays_not_applicable_on_both_dialects():
    """A trace with no task spec is n/a, on native OTLP and on a LangGraph import."""
    for voc in VOCS:
        for dialect, build in (("otlp", _native_bare), ("langgraph", _langgraph_bare)):
            doc = build(voc)
            run = from_otlp(json.loads(json.dumps(doc)))
            res = evaluate(_agent(voc), [run], ["T1-001"])["T1-001"]
            assert res.status == "n/a", (voc["root"], dialect, res.detail)
            assert res.detail == "no standard signal: no canonical run with a success signal"


def test_no_spec_still_uses_only_the_first_canonical_run():
    """Without a task spec the later run is not part of the success signal (previous behaviour)."""
    def run(iid, label, families):
        r = Run(input_id=iid, rep=0, input="please update the record", answer="updated",
                tools=[ToolSpan(name="place_bin_hold", args={"id": "BIN-7"}, result="{}", error=False, actor="", t=1)],
                attrs={"agentest.input.families": families},
                evaluations=[{"gen_ai.evaluation.score.label": label}])
        return r
    res = evaluate(_agent(VOCS[0]), [run("base-run", "pass", ["canonical"]), run("later-variant", "fail", ["alternate"])], ["T1-001"])["T1-001"]
    assert res.status == "pass", res.detail
    assert "later-variant" not in res.detail


def test_detector_evidence_records_disagreement_and_registry_hooks_t1_001():
    assert REGISTRY["T1-001"] is StateOutcome
    case = FAILS[1]
    voc = VOCS[0]
    runs = [from_otlp(json.loads(json.dumps(_native(run, voc)))) for run in case["runs"]]
    det = StateOutcome()
    out = det.evaluate(Ctx(_agent(voc), runs, "examples"))
    assert out.status == "fail"
    ev = det.evidence()
    assert ev and ev[0]["disagreement"] and ev[0]["harness"] == "pass" and ev[0]["state"] == "fail"


def _effects_run(final, initial, preds, attr=None, dialect="otlp", aliases=None, id_note="base-run"):
    """One run. The collection name and the summed field come from the spec, not from the checker."""
    spec = {"goal": "reach the terminal state", "postconditions": preds}
    if aliases:
        spec["effect_aliases"] = aliases
    extra = {"agentest.task.spec": spec, "agentest.initial_state": initial, "agentest.final_state": final,
             "agentest.input.families": ["canonical"]}
    if attr:
        extra["agentest.postcondition.result"] = attr
    voc = VOCS[0]
    if dialect == "otlp":
        ep = Episode(agent="unit", probe=id_note, input="please update the record", final_answer="updated", final_state=final,
                     tool_calls=[ToolCall(voc["write"], {"id": "OBJ-7"}, result="{}")])
        doc = to_otlp(ep, "unit", extra)
    else:
        raw = {"agent": "unit", "probe": id_note, "input": "please update the record", "trace": [
            {"role": "ai", "content": "updating", "tool_calls": [{"name": voc["write"], "args": {"id": "OBJ-7"}}]},
            {"role": "tool", "content": "{}"},
        ]}
        doc = _stamp(to_docs([raw], {"dialect": "langgraph_msgs", "framework": "LangGraph", "observations": {}}, "unit")[0], extra)
    run = from_otlp(json.loads(json.dumps(doc)))
    return evaluate(_agent(voc), [run], ["T1-001"])["T1-001"]


def _blank():
    return {"output": {}}


def _with_records(collection, records):
    state = _blank()
    state["output"][collection] = records
    return state


def test_arbitrary_collection_new_count_and_field_sum_pass():
    """new_<collection> and sum_<collection>.<field> follow the path, for more than one collection name."""
    for collection, total in (("refunds", 40), ("disbursements", 7)):
        preds = [
            {"path": f"effects.OBJ-7.new_{collection}", "op": "eq", "value": 1},
            {"path": f"effects.OBJ-7.sum_{collection}.units", "op": "eq", "value": total},
        ]
        final = _with_records(collection, {"ROW-1": {"subject_id": "OBJ-7", "units": total}})
        for dialect in ("otlp", "langgraph"):
            res = _effects_run(final, _blank(), preds, attr="pass", dialect=dialect)
            assert res.status == "pass", (collection, dialect, res.status, res.detail)


def test_new_count_is_zero_when_the_record_was_already_present():
    """A subject that already has the record has no new record, so eq 1 fails with the count 0."""
    preds = [{"path": "effects.OBJ-7.new_refunds", "op": "eq", "value": 1}]
    already = _with_records("refunds", {"ROW-1": {"subject_id": "OBJ-7", "units": 40}})
    for dialect in ("otlp", "langgraph"):
        res = _effects_run(already, already, preds, attr="pass", dialect=dialect)
        assert res.status == "fail", (dialect, res.detail)
        assert "final 0" in res.detail and "None" not in res.detail


def test_missing_collection_is_not_assessed():
    preds = [{"path": "effects.OBJ-7.new_refunds", "op": "eq", "value": 0}]
    final = _with_records("disbursements", {"ROW-1": {"subject_id": "OBJ-7", "units": 1}})
    res = _effects_run(final, _blank(), preds, attr="pass")
    assert res.status == "not-assessed", res.detail
    assert "unresolved" in res.detail


def test_subject_with_no_records_is_not_assessed_not_zero():
    """No record for the subject is not a count of 0, so eq 1 does not fail."""
    preds = [{"path": "effects.OBJ-7.new_refunds", "op": "eq", "value": 1}]
    final = _with_records("refunds", {"ROW-9": {"subject_id": "OBJ-9", "units": 3}})
    res = _effects_run(final, _blank(), preds, attr="pass")
    assert res.status == "not-assessed", res.detail
    assert res.status != "fail"


def test_missing_sum_field_is_not_assessed():
    preds = [{"path": "effects.OBJ-7.sum_refunds.weight", "op": "eq", "value": 0}]
    final = _with_records("refunds", {"ROW-1": {"subject_id": "OBJ-7", "units": 40}})
    res = _effects_run(final, _blank(), preds, attr="pass")
    assert res.status == "not-assessed", res.detail


def test_mixed_sum_types_are_not_assessed():
    preds = [{"path": "effects.OBJ-7.sum_disbursements.units", "op": "eq", "value": 10}]
    final = _with_records("disbursements", {
        "ROW-1": {"subject_id": "OBJ-7", "units": 4},
        "ROW-2": {"subject_id": "OBJ-7", "units": "6"},
    })
    res = _effects_run(final, _blank(), preds, attr="pass")
    assert res.status == "not-assessed", res.detail


def test_spec_declared_alias_rewrites_the_metric():
    """A name that is not new_<collection> or sum_<collection>.<field> resolves only via the spec."""
    preds = [{"path": "effects.OBJ-7.credited", "op": "eq", "value": 40}]
    final = _with_records("refunds", {"ROW-1": {"subject_id": "OBJ-7", "units": 40}})
    bare = _effects_run(final, _blank(), preds, attr="pass")
    assert bare.status == "not-assessed", bare.detail
    aliased = _effects_run(final, _blank(), preds, attr="pass", aliases={"credited": "sum_refunds.units"})
    assert aliased.status == "pass", aliased.detail


def test_unresolvable_postcondition_path_is_not_assessed():
    """A path that is not an effects metric and not in the snapshot does not fail the cell."""
    final = _with_records("refunds", {"ROW-1": {"subject_id": "OBJ-7", "units": 1}})
    preds = [{"path": "effects.OBJ-7.not_a_metric", "op": "eq", "value": 1}]
    for dialect in ("otlp", "langgraph"):
        res = _effects_run(final, _blank(), preds, attr="pass", dialect=dialect)
        assert res.status == "not-assessed", (dialect, res.status, res.detail)
        assert "unresolved" in res.detail and "disagreement" not in res.detail
    missing = [{"path": "output.ledger.OBJ-7.balance", "op": "eq", "value": 1}]
    res = _effects_run(final, _blank(), missing, attr="pass")
    assert res.status == "not-assessed", res.detail
    assert "output.ledger.OBJ-7.balance" in res.detail


def _native_bare(voc) -> dict:
    ep = Episode(agent="unit", probe="base-run", input="please update the record", final_answer="updated",
                 tool_calls=[ToolCall(voc["write"], {"id": voc["obj"]}, result="{}")])
    return to_otlp(ep, "unit", {})


def _langgraph_bare(voc) -> dict:
    raw = {"agent": "unit", "probe": "base-run", "input": "please update the record", "trace": [
        {"role": "ai", "content": "updating", "tool_calls": [{"name": voc["write"], "args": {"id": voc["obj"]}}]},
        {"role": "tool", "content": "{}"},
    ]}
    return to_docs([raw], {"dialect": "langgraph_msgs", "framework": "LangGraph", "observations": {}}, "unit")[0]
