"""r12-prep Fix 7: pre-scoring trace integrity validator (synthetic exports only; no agent of any round)."""
import json

from agentest.standards import integrity as V
from agentest.standards import trust

KEY = b"test-key-not-a-harness-key"
TOOLS = {"tools": [{"name": "look_up", "inputSchema": {"type": "object"}, "annotations": {"readOnlyHint": True}},
                   {"name": "do_write", "inputSchema": {"type": "object"}, "annotations": {"readOnlyHint": False}}]}


def _a(k, v):
    return {"key": k, "value": {"intValue": str(v)} if isinstance(v, int) else {"stringValue": v}}


def _doc(tid="t1", writes=True, change=True, root_final=True, orphan=False):
    root = {"traceId": tid, "spanId": "r", "parentSpanId": "", "name": "invoke_agent x", "startTimeUnixNano": "1", "endTimeUnixNano": "9",
            "attributes": [_a("gen_ai.operation.name", "invoke_agent"), _a("gen_ai.input.messages", "[]"), _a("gen_ai.output.messages", "[]")]
            + ([_a("agentest.final_state", "{}")] if root_final else [])}
    spans = [root]
    calls = [("c1", "look_up")] + ([("c2", "do_write")] if writes else [])
    for cid, name in calls:
        spans.append({"traceId": tid, "spanId": cid, "parentSpanId": "zz" if orphan else "r", "name": f"execute_tool {name}",
                      "startTimeUnixNano": "2", "endTimeUnixNano": "3",
                      "attributes": [_a("gen_ai.operation.name", "execute_tool"), _a("gen_ai.tool.name", name), _a("gen_ai.tool.call.id", cid),
                                     _a("gen_ai.tool.call.arguments", "{}"), _a("gen_ai.tool.call.result", "ok")],
                      "events": [{"name": "agentest.state_change", "timeUnixNano": "3", "attributes": []}] if (name == "do_write" and change) else []})
    d = {"resourceSpans": [{"resource": {"attributes": [_a("service.name", "x")]}, "scopeSpans": [{"scope": {"name": "s"}, "spans": spans}]}]}
    return trust.sign(d, KEY), calls


def _write(tmp, docs, traffic=True, extra_line=None):
    ad = tmp / "agent"
    (ad / "traces").mkdir(parents=True)
    (ad / "tools.json").write_text(json.dumps(TOOLS))
    (ad / "agent-card.json").write_text(json.dumps({"name": "x"}))
    lines = [json.dumps(d) for d, _ in docs] + ([extra_line] if extra_line else [])
    (ad / "traces" / "x.otlp.jsonl").write_text("\n".join(lines) + "\n")
    if traffic:
        (ad / "traffic").mkdir()
        recs = [trust.traffic_record(KEY, d["resourceSpans"][0]["scopeSpans"][0]["spans"][0]["traceId"], cid, n, "{}", "ok") for d, c in docs for cid, n in c]
        (ad / "traffic" / "calls.jsonl").write_text("\n".join(json.dumps(r) for r in recs) + "\n")
    return ad


def test_clean_export_is_ok(tmp_path):
    r = V.check_agent(_write(tmp_path, [_doc()]), KEY)
    assert r["status"] == "OK", r


def test_missing_traffic_is_refused(tmp_path):
    r = V.check_agent(_write(tmp_path, [_doc()], traffic=False), KEY)
    assert r["status"] == "ERROR" and any("no intercepted tool traffic" in e for e in r["errors"])
    assert V.check_agent(tmp_path / "agent", KEY, allow_unsigned=True, allow_no_traffic=True)["status"] != "ERROR"


def test_unsigned_and_tampered(tmp_path):
    d, c = _doc()
    d["resourceSpans"][0]["scopeSpans"][0]["spans"][0]["name"] = "edited"
    r = V.check_agent(_write(tmp_path, [(d, c)]), KEY)
    assert any("bad signature" in e for e in r["errors"])


def test_no_state_transitions_at_all(tmp_path):
    r = V.check_agent(_write(tmp_path, [_doc("t1", change=False), _doc("t2", change=False)]), KEY)
    assert any("no agentest.state_change event at all" in e for e in r["errors"])


def test_one_idempotent_run_is_only_a_warning(tmp_path):
    r = V.check_agent(_write(tmp_path, [_doc("t1"), _doc("t2", change=False)]), KEY)
    assert r["status"] == "WARN"


def test_truncated_line_and_incomplete_root(tmp_path):
    good = _doc("t1")
    r = V.check_agent(_write(tmp_path, [good], extra_line='{"resourceSpans": [{"scopeSpans": [{"spans": [{"traceId"'), KEY)
    assert any("truncated" in e for e in r["errors"])
    r2 = V.check_agent(_write(tmp_path / "b", [_doc("t2", root_final=False)]), KEY)
    assert any("root span lacks" in e for e in r2["errors"])


def test_orphan_spans(tmp_path):
    r = V.check_agent(_write(tmp_path, [_doc(orphan=True)]), KEY)
    assert any("parent is missing" in e for e in r["errors"])


def test_cli_exit_codes(tmp_path, capsys):
    _write(tmp_path, [_doc()])
    kf = tmp_path / "k"
    kf.write_bytes(KEY)
    assert V.main([str(tmp_path), "--trace-key-file", str(kf)]) == 0
    assert V.main([str(tmp_path / "nope")]) == 2


def _with_root(doc, extra):
    d, calls = doc
    d = json.loads(json.dumps(d))
    root = d["resourceSpans"][0]["scopeSpans"][0]["spans"][0]
    root["attributes"] += [_a(k, v) for k, v in extra.items()]
    for s in d["resourceSpans"][0]["scopeSpans"][0]["spans"][1:]:
        s["attributes"].append(_a("agentest.tool.status", "ok"))
    d["resourceSpans"][0]["resource"]["attributes"] = [a for a in d["resourceSpans"][0]["resource"]["attributes"] if not a["key"].startswith("agentest.trace")]
    return trust.sign(d, KEY), calls


def test_r12_schema_requires_task_spec_and_final_state(tmp_path):
    ad = _write(tmp_path, [_doc()])
    assert V.check_agent(ad, KEY)["status"] == "OK"  # v1 unchanged
    r = V.check_agent(ad, KEY, schema="r12")
    assert r["status"] == "ERROR" and any("agentest.task.spec" in e for e in r["errors"])


def test_r12_schema_bad_spec_and_missing_final_state(tmp_path):
    (tmp_path / "a").mkdir(); (tmp_path / "b").mkdir(); (tmp_path / "c").mkdir()
    bad = V.check_agent(_write(tmp_path / "a", [_with_root(_doc(), {"agentest.task.spec": '{"postconditions": []}'})]), KEY, schema="r12")
    assert bad["status"] == "ERROR" and any("goal" in e for e in bad["errors"])
    nofs = V.check_agent(_write(tmp_path / "b", [_with_root(_doc(root_final=False), {"agentest.task.spec": '{"goal": "g", "postconditions": []}'})]), KEY, schema="r12")
    assert nofs["status"] == "ERROR" and any("agentest.final_state" in e for e in nofs["errors"])
    ok = V.check_agent(_write(tmp_path / "c", [_with_root(_doc(), {"agentest.task.spec": '{"goal": "g", "postconditions": []}',
                                                                   "agentest.initial_state": "{}", "agentest.user.language": "en"})]), KEY, schema="r12")
    assert ok["status"] == "OK", ok
