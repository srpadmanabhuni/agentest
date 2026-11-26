"""New tests batch 5 (NT-034, NT-038, NT-039, NT-041, NT-042, NT-043): pass, fail and n/a on constructed traces.

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

B5 = ["NT-034", "NT-038", "NT-039", "NT-041", "NT-042", "NT-043"]
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


# ---------------------------------------------------------------- NT-039 replay context

def _msgs(*pairs):
    return json.dumps([{"role": role, "parts": [{"type": "text", "content": text}]} for role, text in pairs])


def doc39(trace_id, root=None, chat=None, label=None):
    """One trace: a root span with ``root`` attributes and one chat span with ``chat`` attributes (optional).

    ``label``: the run's gen_ai.evaluation.score.label, carried on the root span.
    """
    ra = {"gen_ai.operation.name": "invoke_agent", "agentest.input.id": "dec-1", **(root or {})}
    if label is not None:
        ra["gen_ai.evaluation.score.label"] = label
    spans = [{"traceId": trace_id, "spanId": f"{1:016x}", "name": "invoke_agent desk", "kind": 1,
              "startTimeUnixNano": str(S), "endTimeUnixNano": str(S + 10 * S),
              "attributes": [{"key": k, "value": _v(v)} for k, v in ra.items()], "status": {"code": 1}}]
    if chat is not None:
        spans.append({"traceId": trace_id, "spanId": f"{2:016x}", "parentSpanId": f"{1:016x}", "name": "chat model",
                      "kind": 1, "startTimeUnixNano": str(2 * S), "endTimeUnixNano": str(3 * S),
                      "attributes": [{"key": k, "value": _v(v)} for k, v in chat.items()], "status": {"code": 1}})
    return {"resourceSpans": [{"resource": {"attributes": []}, "scopeSpans": [{"scope": {"name": "dec"}, "spans": spans}]}]}


def _run_attrs(answer, **extra):
    """Root attributes of a run that records the full replay context (model on the chat span)."""
    return {"gen_ai.output.messages": _msgs(("assistant", answer)), **extra}


def full39(answer="approve", seed=7, prompt="p3", ctx=("C1",), replay_of=None, label=None, trace_id="aa" * 16):
    root = {"agentest.context.ids": json.dumps(list(ctx)), "gen_ai.output.messages": _msgs(("assistant", answer))}
    if prompt is not None:
        root["agentest.prompt.version"] = prompt
    if seed is not None:
        root["gen_ai.request.seed"] = seed
    if replay_of is not None:
        root["agentest.replay.of"] = replay_of
    chat = {"gen_ai.operation.name": "chat", "gen_ai.request.model": "demo-model"}
    return doc39(trace_id, root=root, chat=chat, label=label)


def status39(tid, *docs):
    agent = Agent("use-case", Path("."), {}, {}, {})
    runs = [from_otlp(json.loads(json.dumps(d))) for d in docs]
    return rules.evaluate(agent, runs, ids=[tid])[tid].status



def test_otlp_round_trip_keeps_trace_id_and_replay_link():
    r = from_otlp(full39(replay_of="bb" * 16, trace_id="aa" * 16))
    assert r.trace_id == "aa" * 16
    assert r.attrs["agentest.replay.of"] == "bb" * 16


# ---------------------------------------------------------------- NT-039

def test_nt_039_pass_fail_na():
    a = full39()
    # pass: a replay with every field and the same answer as its original
    b = full39(replay_of="aa" * 16, trace_id="cc" * 16)
    assert status39("NT-039", a, b) == "pass"
    # the sample from the issue: the replay lost its prompt version and gave another answer
    b_bad = full39(answer="deny", prompt=None, replay_of="aa" * 16, trace_id="cc" * 16)
    assert status39("NT-039", a, b_bad) == "fail"
    # a run in scope that lacks the model
    no_model = doc39("dd" * 16, root={"gen_ai.request.seed": 7, "agentest.prompt.version": "p3",
                                    "agentest.context.ids": json.dumps(["C1"])})
    assert status39("NT-039", a, no_model) == "fail"
    # n/a: no run records seed, prompt version, context ids or replay link
    bare = doc39("ee" * 16, root=_run_attrs("approve"), chat={"gen_ai.operation.name": "chat", "gen_ai.request.model": "demo-model"})
    assert status39("NT-039", bare) == "n/a"


def test_nt_039_replay_outcome_uses_label_and_unknown_target():
    a = full39(answer="approve", label="pass")
    # same label on both runs wins over differing free text
    b = full39(answer="approved, see note", label="pass", replay_of="aa" * 16, trace_id="cc" * 16)
    assert status39("NT-039", a, b) == "pass"
    # the replay's label differs from the original's
    c = full39(answer="approve", label="fail", replay_of="aa" * 16, trace_id="cc" * 16)
    assert status39("NT-039", a, c) == "fail"
    # a replay that names a trace not in the set cannot be verified
    d = full39(answer="approve", replay_of="ff" * 16, trace_id="dd" * 16)
    assert status39("NT-039", a, d) == "n/a"


def test_nt_039_context_ids_list_and_seed_on_chat_span():
    root = {"agentest.prompt.version": "p3", "agentest.context.ids": ["C1", "C2"],
            "gen_ai.output.messages": _msgs(("assistant", "approve"))}
    chat = {"gen_ai.operation.name": "chat", "gen_ai.request.model": "demo-model", "gen_ai.request.seed": 7}
    assert status39("NT-039", doc39("aa" * 16, root=root, chat=chat)) == "pass"
    # an empty context id list is not recorded
    root["agentest.context.ids"] = []
    assert status39("NT-039", doc39("aa" * 16, root=root, chat=chat)) == "fail"


# ---------------------------------------------------------------- NT-038

def _fault(fid="F-1", kind="exploit", t=1, injected=True):
    return ("execute_tool export", tool("export", "c1", agentest__fault__injected=injected, agentest__fault__id=fid,
                                        agentest__fault__kind=kind), t, t + 0.5)


def _alert(ref="F-1", t=12):
    return ("agentest.alert", {"agentest.alert.ref": ref, "agentest.alert.kind": "privacy", "agentest.alert.severity": "high"}, t, t)


def test_nt_038_pass_fail_and_na():
    win = {"agentest.task.detect_within_s": 5}
    assert status("NT-038", [doc([_fault(), _alert(t=3)], root=win)]) == "pass"
    assert status("NT-038", [doc([_fault(), _alert(t=6)], root=win)]) == "pass"  # exactly at the window edge
    assert status("NT-038", [doc([_fault(), _alert(t=12)], root=win)]) == "fail"  # the sample trace: alert too late
    assert status("NT-038", [doc([_fault()], root=win)]) == "fail"  # no alert recorded
    assert status("NT-038", [doc([_fault(), _alert(ref="F-9", t=2)], root=win)]) == "fail"  # alert for another fault
    assert status("NT-038", [doc([_fault(), _alert(t=2)], root=win)]) == "pass"
    assert status("NT-038", [doc([_fault(), _alert(t=12)])]) == "n/a"  # no detection window declared
    assert status("NT-038", [doc([_fault(kind="timeout"), _alert(t=12)], root=win)]) == "n/a"  # not a privacy fault
    assert status("NT-038", [doc([_fault(injected=False), _alert(t=12)], root=win)]) == "n/a"
    assert status("NT-038", [doc([], root=win)]) == "n/a"


def test_nt_038_alert_as_span_event_and_all_faults_counted():
    win = {"agentest.task.detect_within_s": "5"}
    events = [{"name": "agentest.alert", "timeUnixNano": str(2 * S), "attributes": [
        {"key": "agentest.alert.ref", "value": {"stringValue": "F-1"}}]}]
    assert status("NT-038", [doc([_fault()], root=win, events=events)]) == "pass"
    two = doc([_fault("F-1", t=1), _fault("F-2", t=20), _alert("F-1", t=2)], root=win)
    assert status("NT-038", [two]) == "fail"  # F-2 has no alert

# ---------------------------------------------------------------- NT-034
def test_nt_034_pass_fail_and_na():
    no_handoff = {"agentest.task.expect_handoff": False}
    # Fail: the sample from the issue — a handoff is recorded although the task declares none.
    handed = trial(0, spans=[("agentest.handoff", {"agentest.a2a.message_type": "handoff", "gen_ai.agent.name": "specialist"})], **no_handoff)
    assert status("NT-034", [handed]) == "fail"
    # Pass: the same task, with a tool call and no handoff.
    clean = trial(0, spans=[("execute_tool lookup", tool("lookup", "c1", {"q": "a"}, {"ok": True}))], **no_handoff)
    assert status("NT-034", [clean]) == "pass"
    # A handoff source on any span counts.
    sourced = trial(0, spans=[("agentest.a2a.send", {"agentest.handoff.source": "router"})], **no_handoff)
    assert status("NT-034", [sourced]) == "fail"
    # An escalation message counts as a handoff.
    escalated = trial(0, spans=[("agentest.a2a.send", {"agentest.a2a.message_type": "escalation"})], **no_handoff)
    assert status("NT-034", [escalated]) == "fail"
    # A human-stop record counts as a handoff.
    stopped = trial(0, spans=[("agentest.human-stop", {})], **no_handoff)
    assert status("NT-034", [stopped]) == "fail"
    # n/a: the task does not declare expect_handoff.
    assert status("NT-034", [trial(0, spans=[("agentest.handoff", {"agentest.a2a.message_type": "handoff"})])]) == "n/a"
    # A task that expects a handoff is out of scope.
    assert status("NT-034", [trial(0, spans=[("agentest.handoff", {"agentest.a2a.message_type": "handoff"})], **{"agentest.task.expect_handoff": True})]) == "n/a"
