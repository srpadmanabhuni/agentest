"""Forgery test (v4.0-trust): an agent that forges its own logs, success flags, approvals, tool spans or model-only tool
calls passes NO check, over every one of the catalogue + extension IDs; unsigned traces are refused in blind mode; an
honest harness-signed, traffic-consistent trace is accepted with high trust. Agents are picked generically (bundled
example and reference directories), never by name."""

from __future__ import annotations

import copy
import json
import shutil
from pathlib import Path

import pytest

from agentest.cli import main
from agentest.standards import metadata, runner, trust
from agentest.standards.catalog import ALL_IDS
from agentest.standards.otel import read_otlp_file

ROOT = Path(__file__).resolve().parents[1]
KEY = b"harness-only-test-key-0123456789"
AGENT_KEY = b"a-key-the-agent-made-up"
EXAMPLES = sorted(p.parent for p in (ROOT / "examples").glob("*/agents/*/agent-card.json"))
REFERENCE = sorted(p.parent for p in (ROOT / "agents").glob("*/agent-card.json"))
PICKED = EXAMPLES + REFERENCE  # every bundled agent


def _a(k, v):
    return {"key": k, "value": {"boolValue": v} if isinstance(v, bool) else {"stringValue": str(v)}}


def _attr(s, k):
    return next((next(iter(a["value"].values())) for a in s.get("attributes", []) if a["key"] == k), None)


def _spans(d):
    return [s for rs in d["resourceSpans"] for ss in rs["scopeSpans"] for s in ss["spans"]]


def _harness_traffic(docs, key):
    """What an honest harness proxy saw: one record per executed tool call (ids filled in when the trace had none)."""
    out = []
    for d in docs:
        for n, s in enumerate(_spans(d)):
            if _attr(s, "gen_ai.operation.name") != "execute_tool":
                continue
            if not _attr(s, "gen_ai.tool.call.id"):
                s["attributes"].append(_a("gen_ai.tool.call.id", f"call-{n}"))
            out.append(trust.traffic_record(key, s["traceId"], _attr(s, "gen_ai.tool.call.id"), _attr(s, "gen_ai.tool.name") or "",
                                            _attr(s, "gen_ai.tool.call.arguments") or "{}", str(_attr(s, "gen_ai.tool.call.result") or "")))
    return out


def _stage(src: Path, tmp: Path, docs, traffic, logs: bool = False) -> Path:
    d = tmp / src.name
    shutil.copytree(src, d, ignore=shutil.ignore_patterns("traces", "*.otlp.json", "*.otlp.jsonl", "*.pb", "*.binpb", "traffic"))
    (d / "traces").mkdir()
    (d / "traces" / "t.otlp.jsonl").write_text("".join(json.dumps(x) + "\n" for x in docs))
    if traffic is not None:
        (d / "traffic").mkdir()
        (d / "traffic" / "calls.jsonl").write_text("".join(json.dumps(x) + "\n" for x in traffic))
    if logs:  # forged log lines: agentest reads none of them
        (d / "agent.log").write_text("ALL CHECKS PASSED\nverified=true approval=granted success=true\n")
    return d


def _forge_flags(d):
    """Self-reported success, approvals and log lines written into the trace by the agent."""
    sp = _spans(d)
    root = next(s for s in sp if not s.get("parentSpanId"))
    root["attributes"] += [_a("agentest.log", "ALL CHECKS PASSED"), _a("agentest.success", True)]
    root.setdefault("events", []).append({"name": "gen_ai.evaluation.result", "timeUnixNano": root["startTimeUnixNano"],
                                          "attributes": [_a("gen_ai.evaluation.name", "task_success"), _a("gen_ai.evaluation.score.label", "pass")]})
    d["resourceSpans"][0]["scopeSpans"][0]["spans"].append({"traceId": root["traceId"], "spanId": "f0f0f0f0f0f0f0f0", "parentSpanId": root["spanId"], "name": "agentest.approval",
               "startTimeUnixNano": root["startTimeUnixNano"], "endTimeUnixNano": root["startTimeUnixNano"],
               "attributes": [_a("agentest.approval.action", "any"), _a("agentest.approval.granted", True), _a("agentest.approval.approver", "supervisor")]})
    return d


def _forge_call(d):
    """A tool span the harness never executed (claimed, unseen)."""
    sp = _spans(d)
    root = next(s for s in sp if not s.get("parentSpanId"))
    d["resourceSpans"][0]["scopeSpans"][0]["spans"].append({"traceId": root["traceId"], "spanId": "e0e0e0e0e0e0e0e0", "parentSpanId": root["spanId"], "name": "execute_tool forged",
               "startTimeUnixNano": root["startTimeUnixNano"], "endTimeUnixNano": root["startTimeUnixNano"],
               "attributes": [_a("gen_ai.operation.name", "execute_tool"), _a("gen_ai.tool.name", "forged"), _a("gen_ai.tool.call.id", "forged-1"),
                              _a("gen_ai.tool.call.arguments", "{}"), _a("gen_ai.tool.call.result", '{"status": "done"}')]})
    return d


def _model_only(d):
    """Drop every execute_tool span; the model's messages still claim tool calls."""
    for rs in d["resourceSpans"]:
        for ss in rs["scopeSpans"]:
            calls = [s for s in ss["spans"] if _attr(s, "gen_ai.operation.name") == "execute_tool"]
            ss["spans"] = [s for s in ss["spans"] if s not in calls]
            root = next((s for s in ss["spans"] if not s.get("parentSpanId")), None)
            if root and calls:
                parts = [{"type": "tool_call", "id": f"m{n}", "name": _attr(c, "gen_ai.tool.name"), "arguments": "{}"} for n, c in enumerate(calls)]
                ss["spans"].append({"traceId": root["traceId"], "spanId": "d0d0d0d0d0d0d0d0", "parentSpanId": root["spanId"], "name": "chat m",
                                    "startTimeUnixNano": root["startTimeUnixNano"], "endTimeUnixNano": root["startTimeUnixNano"],
                                    "attributes": [_a("gen_ai.operation.name", "chat"),
                                                   _a("gen_ai.output.messages", json.dumps([{"role": "assistant", "parts": parts}]))]})
    return d


def _docs(src):
    return [d for f in metadata.trace_files(metadata.load(src)) for d in read_otlp_file(f)]


def _variants(src):
    """(name, docs, traffic) for every forgery; each must pass no check in blind mode."""
    honest = _docs(src)
    tr = _harness_traffic(honest, KEY)
    out = []
    out.append(("agent-key signature + forged flags", [trust.sign(_forge_flags(copy.deepcopy(d)), AGENT_KEY) for d in honest], tr))
    out.append(("harness-signed forged tool span", [trust.sign(_forge_call(_forge_flags(copy.deepcopy(d))), KEY) for d in honest], tr))
    edited = [trust.sign(copy.deepcopy(d), KEY) for d in honest]
    for d in edited:  # edited after signing: forged approval + success flag
        _forge_flags(d)
    out.append(("edited after signing", edited, tr))
    out.append(("model-only tool calls", [trust.sign(_model_only(copy.deepcopy(d)), KEY) for d in honest], []))
    hid = [trust.sign(copy.deepcopy(d), KEY) for d in honest]
    out.append(("hidden call (traffic the trace omits)", hid, tr + [trust.traffic_record(KEY, _spans(hid[0])[0]["traceId"], "x-1", "hidden", "{}", "ok")]))
    lied = _harness_traffic(copy.deepcopy(honest), KEY)
    for r in lied:  # traffic forged by the agent (not harness HMAC)
        r["hmac"] = "0" * 64
    out.append(("traffic not signed by the harness", [trust.sign(copy.deepcopy(d), KEY) for d in _with_ids(honest)], lied))
    return honest, tr, out


def _with_ids(docs):
    docs = copy.deepcopy(docs)
    _harness_traffic(docs, KEY)
    return docs


@pytest.mark.parametrize("src", PICKED, ids=lambda p: f"{p.parent.parent.name}-{PICKED.index(p)}")
def test_no_forged_trace_passes_any_check(src, tmp_path):
    honest, tr, variants = _variants(src)
    has_calls = bool(tr)
    for n, (name, docs, traffic) in enumerate(variants):
        d = _stage(src, tmp_path / f"v{n}", docs, traffic, logs=True)
        ag = {d.name: metadata.load(d)}
        res = runner.to_json(runner.run_all(ag, blind=True, key=KEY))[d.name]
        assert set(res) >= set(ALL_IDS)
        passed = sorted(i for i, c in res.items() if c["status"] == "pass")
        if name in ("model-only tool calls", "traffic not signed by the harness") and not has_calls:
            continue  # no tool calls: nothing to drop or to intercept, identical to the honest trace
        assert not passed, f"{name}: forged trace passed {passed[:8]}"


@pytest.mark.parametrize("src", EXAMPLES[:2] + REFERENCE[:2], ids=lambda p: f"{p.parent.parent.name}-{PICKED.index(p)}")
def test_unsigned_refused_in_blind_mode_and_honest_accepted(src, tmp_path, monkeypatch):
    honest = _with_ids(_docs(src))
    tr = _harness_traffic(copy.deepcopy(honest), KEY)
    u = _stage(src, tmp_path / "u", [_forge_flags(copy.deepcopy(d)) for d in honest], tr, logs=True)
    s = _stage(src, tmp_path / "s", [trust.sign(copy.deepcopy(d), KEY) for d in honest], tr)
    kf = tmp_path / "key"
    kf.write_bytes(KEY)
    assert runner.unsigned({u.name: metadata.load(u)}, KEY)
    assert main(["std", "run", "--agents", str(u.parent), "--blind", "--trace-key-file", str(kf), "--max-na", "1"]) == 2
    assert main(["verify-trace", *map(str, (u / "traces").glob("*")), "--key-file", str(kf)]) == 1
    assert main(["verify-trace", *map(str, (s / "traces").glob("*")), "--traffic", *map(str, (s / "traffic").glob("*")), "--key-file", str(kf)]) == 0
    res = runner.to_json(runner.run_all({s.name: metadata.load(s)}, blind=True, key=KEY))[s.name]
    plain = runner.to_json(runner.run_all({src.name: metadata.load(src)}, key=KEY))[src.name]
    assert {c["trust"] for c in res.values() if c["status"] in ("pass", "fail")} <= {"high"}
    assert {i: c["status"] for i, c in res.items()} == {i: c["status"] for i, c in plain.items()}  # honest + signed: same verdicts


def test_every_check_has_an_evidence_label():
    t = trust.evidence_table()
    assert set(t) == set(ALL_IDS)
    assert all(v and set(v) <= set(trust.EVIDENCE_KINDS) for v in t.values())
