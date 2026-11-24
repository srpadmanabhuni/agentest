"""New tests batch 5 (NT-041, NT-042, NT-043): pass, fail and n/a on constructed traces.

Traces are OTLP/JSON documents read through ``from_otlp``. Names are neutral.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from agentest.standards import rules
from agentest.standards.catalog import new_tests
from agentest.standards.metadata import Agent
from agentest.standards.otel import from_otlp

B5 = ["NT-041", "NT-042", "NT-043"]
S = 1_000_000_000


def _v(x):
    if isinstance(x, bool):
        return {"boolValue": x}
    if isinstance(x, int):
        return {"intValue": str(x)}
    if isinstance(x, list) and all(isinstance(y, str) for y in x):
        return {"arrayValue": {"values": [{"stringValue": y} for y in x]}}
    return {"stringValue": x if isinstance(x, str) else json.dumps(x)}


def doc(spans, root=None, rep=0, events=None):
    ra = {"gen_ai.operation.name": "invoke_agent", "agentest.input.id": "uc-1", "agentest.run.rep": rep, **(root or {})}
    root_span = {"traceId": f"{rep + 1:032x}", "spanId": f"{rep + 1:016x}", "name": "invoke_agent desk", "kind": 1,
                 "startTimeUnixNano": str((rep + 1) * S), "endTimeUnixNano": str((rep + 1) * S + 1000 * S),
                 "attributes": [{"key": k, "value": _v(v)} for k, v in ra.items()], "status": {"code": 1}}
    if events:
        root_span["events"] = events
    out = [root_span]
    for i, sp in enumerate(spans):
        name, attrs = sp[0], sp[1]
        t0, t1 = (sp[2], sp[3]) if len(sp) > 2 else (i + 1, i + 1.5)
        err = len(sp) > 4 and sp[4]
        out.append({"traceId": root_span["traceId"], "spanId": f"{rep + 1:08x}{i + 2:08x}", "parentSpanId": root_span["spanId"],
                    "name": name, "kind": 1, "startTimeUnixNano": str(int(root_span["startTimeUnixNano"]) + int(t0 * S)),
                    "endTimeUnixNano": str(int(root_span["startTimeUnixNano"]) + int(t1 * S)),
                    "attributes": [{"key": k, "value": _v(v)} for k, v in attrs.items()],
                    "status": {"code": 2 if err else 1}})
    return {"resourceSpans": [{"resource": {"attributes": []}, "scopeSpans": [{"scope": {"name": "uc"}, "spans": out}]}]}


def tool(name, cid, args=None, result=None, **attrs):
    a = {"gen_ai.operation.name": "execute_tool", "gen_ai.tool.name": name, "gen_ai.tool.call.id": cid,
         "gen_ai.tool.call.arguments": json.dumps(args or {}), "gen_ai.tool.call.result": json.dumps(result) if not isinstance(result, str) else result}
    a.update({k.replace("__", "."): v for k, v in attrs.items()})
    return a


def ev(label):
    return [{"name": "gen_ai.evaluation.result", "timeUnixNano": "1", "attributes": [
        {"key": "gen_ai.evaluation.score.label", "value": {"stringValue": label}}]}]


def change(kind, ref):
    return ("agentest.environment.change", {"agentest.environment.change.kind": kind, "agentest.environment.change.ref": ref})


def status(tid, docs, gov=None, card=None):
    agent = Agent("use-case", Path("."), card or {"skills": []}, {}, gov or {})
    runs = [from_otlp(json.loads(json.dumps(d))) for d in docs]
    return rules.evaluate(agent, runs, ids=[tid])[tid].status


def both(tid, docs, gov=None, card=None):
    agent = Agent("use-case", Path("."), card or {"skills": []}, {}, gov or {})
    runs = [from_otlp(json.loads(json.dumps(d))) for d in docs]
    return rules.evaluate(agent, runs, ids=[tid, "T1-003"], mode="examples")


START = {"ready": True}


def trial(rep, state=START, spans=None, **root):
    attrs = {"agentest.task.id": "book", **root}
    if state is not None:
        attrs["agentest.task.initial_state"] = state
    return doc(spans or [], root=attrs, rep=rep)


# ---------------------------------------------------------------- catalogue

def test_b5_rows_present_and_wording():
    rows = {k: v for k, v in new_tests().items() if v["batch"] == "b5"}
    assert sorted(rows) == B5
    text = json.dumps(rows)
    assert not re.search(r"\b[A-Z]\d-\d{3}\b", text)
    assert all(r["class_id"] == "NT" and r["trace_attributes"] for r in rows.values())


def test_b5_not_in_default_set():
    res = rules.evaluate(Agent("use-case", Path("."), {}, {}, {}), [from_otlp(doc([]))])
    assert not set(B5) & set(res)


# ---------------------------------------------------------------- NT-041

def test_nt_041_pass_fail_and_na():
    clean = [trial(0, spans=[change("write", "art-1")]), trial(1, spans=[change("write", "art-2")])]
    assert status("NT-041", clean) == "pass"
    leaked = [trial(0, spans=[change("write", "art-1")]), trial(1, spans=[change("read", "art-1")])]
    assert status("NT-041", leaked) == "fail"
    # A kind left blank on a later trial still counts as reading an artefact an earlier trial wrote.
    blank = [trial(0, spans=[change("write", "art-1")]), trial(1, spans=[("agentest.environment.change", {"agentest.environment.change.ref": "art-1"})])]
    assert status("NT-041", blank) == "fail"
    # A later write of a new artefact is not a read of the earlier one.
    assert status("NT-041", [trial(0, spans=[change("write", "art-1")]), trial(1, spans=[change("write", "art-9")])]) == "pass"
    # The same trial may read what it wrote.
    assert status("NT-041", [trial(0, spans=[change("write", "art-1"), change("read", "art-1")])]) == "pass"
    assert status("NT-041", [trial(0, state={"ready": True}), trial(1, state={"ready": False})]) == "fail"
    assert status("NT-041", [trial(0), trial(1, state=None)]) == "fail"
    assert status("NT-041", [doc([], root={"agentest.task.id": "book"}, rep=0), doc([], root={"agentest.task.id": "book"}, rep=1)]) == "n/a"


# ---------------------------------------------------------------- NT-042

def _skill(k=2, examples=None):
    skill = {"id": "book", "name": "Book", "description": "Book a desk", "tags": ["desk"], "consistency_required": {"k": k}}
    if examples is not None:
        skill["examples"] = examples
    return {"skills": [skill]}


def test_nt_042_all_trials_gate_and_na():
    passed = [doc([], root={"agentest.task.id": "book"}, rep=i, events=ev("pass")) for i in range(2)]
    assert status("NT-042", passed, card=_skill(2)) == "pass"
    mixed = [doc([], root={"agentest.task.id": "book"}, rep=0, events=ev("pass")),
             doc([], root={"agentest.task.id": "book"}, rep=1, events=ev("fail"))]
    assert status("NT-042", mixed, card=_skill(2)) == "fail"
    assert status("NT-042", passed[:1], card=_skill(2)) == "fail"  # fewer than k trials
    assert status("NT-042", passed) == "n/a"
    assert status("NT-042", passed, card={"skills": [{"id": "book", "name": "Book", "description": "d", "tags": [], "consistency_required": True}]}) == "n/a"
    # Linked by the skill example when the task id is different.
    by_example = [doc([], root={"gen_ai.input.messages": json.dumps([{"role": "user", "parts": [{"type": "text", "content": "Book a desk"}]}])},
                      rep=i, events=ev("pass")) for i in range(2)]
    assert status("NT-042", by_example, card=_skill(2, examples=["Book a desk"])) == "pass"


def test_nt_042_complements_the_rate_threshold():
    """Two of three trials pass: the rate threshold holds and the all-trials gate does not."""
    docs = [doc([], root={"agentest.task.id": "book"}, rep=i, events=ev("pass" if i < 2 else "fail")) for i in range(3)]
    res = both("NT-042", docs, card=_skill(3))
    assert res["T1-003"].status == "pass"
    assert res["NT-042"].status == "fail"


# ---------------------------------------------------------------- NT-043

def task_root(**budget):
    root = {"agentest.task.id": "book"}
    root.update(budget)
    return root


def test_nt_043_errors_repeats_and_na():
    ok_calls = [doc([("execute_tool lookup", tool("lookup", "c1", {"q": "a"}, {"ok": True}))], root=task_root(**{"agentest.task.budget.tool_errors": 1, "agentest.task.budget.repeat_calls": 1}), rep=0)]
    assert status("NT-043", ok_calls) == "pass"
    errored = [doc([("execute_tool lookup", tool("lookup", "c1", {"q": "a"}, {"ok": False}, error__type="rejected"))],
                   root=task_root(**{"agentest.task.budget.tool_errors": 0}), rep=0)]
    assert status("NT-043", errored) == "fail"
    invalid = [doc([("execute_tool lookup", tool("lookup", "c1", {"q": "a"}, {"error": {"code": -32602, "message": "bad"}}))],
                   root=task_root(**{"agentest.task.budget.tool_errors": 0}), rep=0)]
    assert status("NT-043", invalid) == "fail"
    # The same call in two trials is one repeat, over a budget of 0.
    repeated = [
        doc([("execute_tool lookup", tool("lookup", "c1", {"q": "a"}, {"ok": True}))], root=task_root(**{"agentest.task.budget.repeat_calls": 0}), rep=0),
        doc([("execute_tool lookup", tool("lookup", "c1", {"q": "a"}, {"ok": True}))], root=task_root(**{"agentest.task.budget.repeat_calls": 0}), rep=1),
    ]
    assert status("NT-043", repeated) == "fail"
    allowed = [
        doc([("execute_tool lookup", tool("lookup", "c1", {"q": "a"}, {"ok": True}))], root=task_root(**{"agentest.task.budget.repeat_calls": 1}), rep=0),
        doc([("execute_tool lookup", tool("lookup", "c1", {"q": "a"}, {"ok": True}))], root=task_root(**{"agentest.task.budget.repeat_calls": 1}), rep=1),
    ]
    assert status("NT-043", allowed) == "pass"
    # A repeat budget does not count tool errors, and an error budget does not count repeats.
    errors_only = [doc([
        ("execute_tool lookup", tool("lookup", "c1", {"q": "a"}, {"ok": True})),
        ("execute_tool lookup", tool("lookup", "c2", {"q": "a"}, {"ok": True})),
    ], root=task_root(**{"agentest.task.budget.tool_errors": 0}), rep=0)]
    assert status("NT-043", errors_only) == "pass"
    assert status("NT-043", [doc([("execute_tool lookup", tool("lookup", "c1", {"q": "a"}, {"ok": True}))], root={"agentest.task.id": "book"}, rep=0)]) == "n/a"
