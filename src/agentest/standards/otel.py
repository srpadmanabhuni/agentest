"""Episode <-> OTLP/JSON spans following the OpenTelemetry GenAI semantic conventions.

Spec: https://opentelemetry.io/docs/specs/semconv/gen-ai/ (agent spans:
https://opentelemetry.io/docs/specs/semconv/gen-ai/gen-ai-agent-spans/ ; status
*Development*). OTLP/JSON encoding:
https://opentelemetry.io/docs/specs/otlp/#json-protobuf-encoding .

Standard attributes used: ``gen_ai.operation.name`` (invoke_agent | execute_tool | chat),
``gen_ai.agent.name``, ``gen_ai.agent.id``, ``gen_ai.conversation.id``, ``gen_ai.tool.name``,
``gen_ai.tool.type``, ``gen_ai.tool.call.id``, ``gen_ai.tool.call.arguments``,
``gen_ai.tool.call.result``, ``gen_ai.input.messages``, ``gen_ai.output.messages``,
``error.type``.

Non-standard attributes are prefixed ``agentest.`` (documented in docs/standards/EXTENSION.md):
``agentest.input.id``, ``agentest.run.rep``, ``agentest.final_state``, the
``agentest.approval`` span (human/policy decision; no GenAI convention exists yet)
and ``agentest.state_change`` span events (observed effects in the system of record).
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any

from agentest.standards import VERSION
from agentest.standards.episode import Episode

INTERNAL = 1  # SPAN_KIND_INTERNAL
STATUS_ERROR = 2
BASE = 1_700_000_000_000_000_000  # fixed epoch for deterministic replay timestamps
STEP = 1_000_000  # 1 ms per logical step


def _typed(o: Any) -> Any:
    """JSON default hook: keep set/frozenset/bytes recoverable (agentest.final_state is a JSON string attribute)."""
    if isinstance(o, frozenset):
        return {"$frozenset": sorted(o, key=str)}
    if isinstance(o, set):
        return {"$set": sorted(o, key=str)}
    if isinstance(o, bytes):
        return {"$bytes": o.decode("latin-1")}
    return str(o)


def _untyped(d: dict) -> Any:
    if len(d) == 1:
        k, v = next(iter(d.items()))
        if k == "$frozenset":
            return frozenset(v)
        if k == "$set":
            return set(v)
        if k == "$bytes":
            return v.encode("latin-1")
    return d


def _v(x: Any) -> dict:
    if isinstance(x, bool):
        return {"boolValue": x}
    if isinstance(x, int):
        return {"intValue": str(x)}
    if isinstance(x, float):
        return {"doubleValue": x}
    if isinstance(x, str):
        return {"stringValue": x}
    return {"stringValue": json.dumps(x, ensure_ascii=False, default=_typed, sort_keys=False)}


def _attrs(d: dict) -> list[dict]:
    return [{"key": k, "value": _v(v)} for k, v in d.items() if v is not None and v != ""]


def _unv(v: dict) -> Any:
    if "stringValue" in v:
        return v["stringValue"]
    if "intValue" in v:
        return int(v["intValue"])
    if "doubleValue" in v:
        return v["doubleValue"]
    if "boolValue" in v:
        return v["boolValue"]
    if "arrayValue" in v:
        return [_unv(x) for x in v["arrayValue"].get("values", [])]
    if "kvlistValue" in v:
        return {x["key"]: _unv(x.get("value", {})) for x in v["kvlistValue"].get("values", [])}
    if "bytesValue" in v:
        return v["bytesValue"]
    return None


def _hex(seed: str, n: int) -> str:
    return hashlib.sha256(seed.encode()).hexdigest()[:n]


def _msgs(role: str, text: str) -> str:
    return json.dumps([{"role": role, "parts": [{"type": "text", "content": text}]}], ensure_ascii=False)


def to_otlp(ep: Episode, service: str, extra: dict | None = None, tool_attrs: list[dict] | None = None,
            evaluations: list[dict] | None = None, steps: list[str] | None = None) -> dict:
    """One episode -> one OTLP/JSON ``TracesData`` document (one trace)."""
    tid = _hex(f"{service}/{ep.probe}/{ep.rep}", 32)
    spans: list[dict] = []
    clock = [BASE]

    def tick() -> int:
        clock[0] += STEP
        return clock[0]

    root_id = _hex(tid + "root", 16)
    start = tick()
    agent_spans: dict[str, str] = {}

    def agent_span(name: str, parent: str = root_id, source: str = "") -> str:
        if name in agent_spans:
            return agent_spans[name]
        sid = _hex(tid + "agent" + name, 16)
        t = tick()
        spans.append({"traceId": tid, "spanId": sid, "parentSpanId": parent, "name": f"invoke_agent {name}",
                      "kind": INTERNAL, "startTimeUnixNano": str(t), "endTimeUnixNano": str(t + STEP // 2),
                      "attributes": _attrs({"gen_ai.operation.name": "invoke_agent", "gen_ai.agent.name": name,
                                            "agentest.handoff.source": source})})
        agent_spans[name] = sid
        return sid

    for h in ep.handoffs:
        agent_span(h.source)
        agent_span(h.target, agent_spans[h.source], h.source)
    for st in steps or []:  # native LLM/agent steps without message text
        t = tick()
        spans.append({"traceId": tid, "spanId": _hex(tid + f"step{t}", 16), "parentSpanId": root_id, "name": "chat", "kind": INTERNAL,
                      "startTimeUnixNano": str(t), "endTimeUnixNano": str(t + 1),
                      "attributes": _attrs({"gen_ai.operation.name": "chat", "gen_ai.output.messages": _msgs("assistant", st)})})
    for m in ep.messages:
        if m.role == "assistant":
            t = tick()
            spans.append({"traceId": tid, "spanId": _hex(tid + f"chat{t}", 16), "parentSpanId": agent_span(m.actor) if m.actor else root_id,
                          "name": "chat", "kind": INTERNAL, "startTimeUnixNano": str(t), "endTimeUnixNano": str(t + 1),
                          "attributes": _attrs({"gen_ai.operation.name": "chat", "gen_ai.output.messages": _msgs("assistant", m.content)})})
    for i, c in enumerate(ep.tool_calls):
        t = tick()
        span = {"traceId": tid, "spanId": _hex(tid + f"tool{i}", 16), "parentSpanId": agent_span(c.actor) if c.actor else root_id,
                "name": f"execute_tool {c.name}", "kind": INTERNAL, "startTimeUnixNano": str(t), "endTimeUnixNano": str(t + 1),
                "attributes": _attrs({"gen_ai.operation.name": "execute_tool", "gen_ai.tool.name": c.name, "gen_ai.tool.type": "function",
                                      "gen_ai.tool.call.id": c.call_id or f"call_{i}", "gen_ai.agent.name": c.actor,
                                      "gen_ai.tool.call.arguments": json.dumps(c.arguments, ensure_ascii=False, sort_keys=True, default=str),
                                      "gen_ai.tool.call.result": c.result if isinstance(c.result, str) else (None if c.result is None else json.dumps(c.result, ensure_ascii=False, default=str)),
                                      "error.type": "tool_error" if c.error else None,
                                      **((tool_attrs or [])[i] if i < len(tool_attrs or []) else {})})}
        if c.error:
            span["status"] = {"code": STATUS_ERROR, "message": "tool error"}
        spans.append(span)
    events = []
    # Effects observed before any human step, then pending requests, then the human/policy decision, then executed effects.
    order = {"unapproved": 0, "pending": 1, "diff": 1, "executed": 3}
    for s in sorted(ep.state_changes, key=lambda s: order.get(s.kind, 1)):
        if s.kind == "executed" and not any(e.get("_approvals_done") for e in events):
            for j, a in enumerate(ep.approvals):
                t = tick()
                spans.append({"traceId": tid, "spanId": _hex(tid + f"appr{j}", 16), "parentSpanId": root_id, "name": "agentest.approval",
                              "kind": INTERNAL, "startTimeUnixNano": str(t), "endTimeUnixNano": str(t + 1),
                              "attributes": _attrs({"agentest.approval.action": a.action, "agentest.approval.granted": a.granted,
                                                    "agentest.approval.approver": a.approver, "agentest.approval.target": a.target,
                                                    "agentest.approval.policy_version": a.policy_version,
                                                    "agentest.approval.reason": a.reason or None})})
            events.append({"_approvals_done": True})
        events.append({"timeUnixNano": str(tick()), "name": "agentest.state_change",
                       "attributes": _attrs({"agentest.state_change.kind": s.kind, "agentest.state_change.effect": s.effect,
                                             "agentest.state_change.data": s.data})})
    if not any(e.get("_approvals_done") for e in events):
        for j, a in enumerate(ep.approvals):
            t = tick()
            spans.append({"traceId": tid, "spanId": _hex(tid + f"appr{j}", 16), "parentSpanId": root_id, "name": "agentest.approval",
                          "kind": INTERNAL, "startTimeUnixNano": str(t), "endTimeUnixNano": str(t + 1),
                          "attributes": _attrs({"agentest.approval.action": a.action, "agentest.approval.granted": a.granted,
                                                "agentest.approval.approver": a.approver, "agentest.approval.target": a.target,
                                                "agentest.approval.policy_version": a.policy_version,
                                                    "agentest.approval.reason": a.reason or None})})
    events = [e for e in events if "_approvals_done" not in e]
    for ev in evaluations or []:  # OTel GenAI event gen_ai.evaluation.result
        events.append({"timeUnixNano": str(tick()), "name": "gen_ai.evaluation.result", "attributes": _attrs(ev)})
    end = tick()
    dur = int((ep.duration_s or 0) * 1e9)
    root = {"traceId": tid, "spanId": root_id, "parentSpanId": "", "name": f"invoke_agent {service}", "kind": INTERNAL,
            "startTimeUnixNano": str(start), "endTimeUnixNano": str(max(end, start + dur)),
            "attributes": _attrs({"gen_ai.operation.name": "invoke_agent", "gen_ai.agent.name": service, "gen_ai.agent.id": service,
                                  "gen_ai.conversation.id": f"{ep.conversation}#{ep.rep}" if ep.conversation else f"{ep.probe}#{ep.rep}", "gen_ai.input.messages": _msgs("user", ep.input or ""),
                                  "gen_ai.output.messages": _msgs("assistant", ep.final_answer or ""),
                                  "agentest.input.id": ep.probe, "agentest.run.rep": int(ep.rep),
                                  "agentest.duration_s": float(ep.duration_s) if ep.duration_s is not None else None,
                                  "agentest.final_state": ep.final_state or {}, "error.type": "agent_error" if ep.error else None,
                                  "agentest.error.message": ep.error, **(extra or {})}),
            "events": events}
    if ep.error:
        root["status"] = {"code": STATUS_ERROR, "message": str(ep.error)[:200]}
    return {"resourceSpans": [{"resource": {"attributes": _attrs({"service.name": service, "gen_ai.framework": ep.framework})},
                               "scopeSpans": [{"scope": {"name": "agentest.standards.importers", "version": VERSION},
                                               "spans": [root, *spans]}]}]}


# ---------------------------------------------------------------- reading OTLP back (what the rules see)

@dataclass
class ToolSpan:
    name: str
    args: dict
    result: str
    error: bool
    actor: str
    t: int
    call_id: str = ""
    attrs: dict = field(default_factory=dict)
    t1: int = 0  # span end (0 when unknown)


@dataclass
class Run:
    """The view of one OTLP trace that universal rules read. Built only from OTel attributes."""

    input_id: str
    rep: int
    input: str
    answer: str
    tools: list[ToolSpan] = field(default_factory=list)
    approvals: list[dict] = field(default_factory=list)
    handoffs: list[tuple[str, str, int]] = field(default_factory=list)
    effects: list[dict] = field(default_factory=list)
    chats: list[str] = field(default_factory=list)
    final_state: dict = field(default_factory=dict)
    error: str = ""
    duration_s: float | None = None
    times: list[tuple[int, int]] = field(default_factory=list)
    span_blobs: list[str] = field(default_factory=list)  # every attribute value, for log/trace leak rules
    attrs: dict = field(default_factory=dict)  # root-span attributes
    evaluations: list[dict] = field(default_factory=list)  # gen_ai.evaluation.result events
    conversation: str = ""  # gen_ai.conversation.id
    attachments: list[dict] = field(default_factory=list)  # non-text parts of the user input (uri / blob / file)
    t0: int = 0  # root span start (orders the turns of a conversation)
    batches: list[list[str]] = field(default_factory=list)  # tool calls issued together in one model response (>= 2)

    def executed(self) -> list[dict]:
        return [e for e in self.effects if e["kind"] in ("executed", "unapproved")]

    def granted(self) -> list[dict]:
        return [a for a in self.approvals if a.get("granted")]


def _text_of(msgs) -> str:
    try:
        ms = json.loads(msgs) if isinstance(msgs, str) else msgs
        return " ".join(str(p.get("content", "")) for m in ms for p in m.get("parts", []) if p.get("type", "text") == "text")
    except (ValueError, TypeError, AttributeError):
        return msgs if isinstance(msgs, str) else ""


def _parts_of(msgs) -> list[dict]:
    try:
        ms = json.loads(msgs) if isinstance(msgs, str) else msgs
        return [dict(p, role=m.get("role", "")) for m in ms or [] for p in m.get("parts", []) if isinstance(p, dict)]
    except (ValueError, TypeError, AttributeError):
        return []


# ---------------------------------------------------------------- semantic-convention versions and styles (data in semconv.yaml)

_SEMCONV: dict | None = None


def semconv() -> dict:
    """The pinned GenAI semantic-convention version and the alias tables for older versions and other styles."""
    global _SEMCONV
    if _SEMCONV is None:
        from pathlib import Path

        import yaml

        _SEMCONV = yaml.safe_load((Path(__file__).parent / "semconv.yaml").read_text())
    return _SEMCONV


def _loads(v: Any) -> Any:
    if isinstance(v, str) and v[:1] in "[{":
        try:
            return json.loads(v)
        except ValueError:
            return v
    return v


def _args_of(v: Any) -> dict:
    v = _loads(v)
    if isinstance(v, dict) and set(v) <= {"args", "kwargs", "inputs"} and isinstance(v.get("kwargs", v.get("inputs")), dict):
        v = v.get("kwargs") or v.get("inputs")  # decorator-style capture {"args": [...], "kwargs": {...}}
    return v if isinstance(v, dict) else ({} if v in (None, "") else {"_": v})


def _msg(role: str, content: Any = "", tool_calls: Any = None, call_id: str = "") -> dict:
    parts: list[dict] = []
    if role == "tool":
        parts.append({"type": "tool_call_response", "id": call_id, "response": content})
    elif content not in (None, ""):
        if isinstance(content, list):  # already a list of parts
            parts += [p if isinstance(p, dict) else {"type": "text", "content": str(p)} for p in content]
        else:
            parts.append({"type": "text", "content": content if isinstance(content, str) else json.dumps(content)})
    for tc in _loads(tool_calls) or []:
        fn = tc.get("function", tc) if isinstance(tc, dict) else {}
        parts.append({"type": "tool_call", "id": tc.get("id", "") if isinstance(tc, dict) else "", "name": fn.get("name", ""),
                      "arguments": _loads(fn.get("arguments", {}))})
    return {"role": role, "parts": parts}


def _indexed(a: dict, spec: dict) -> list[dict]:
    """Flattened ``prefix.N.field`` (and ``prefix.N.tool_calls.M.field``) attributes -> structured messages."""
    pre = spec["prefix"] + "."
    rows: dict[int, dict] = {}
    for k, v in a.items():
        if not k.startswith(pre):
            continue
        head, _, rest = k[len(pre):].partition(".")
        if head.isdigit():
            rows.setdefault(int(head), {})[rest] = v
    out = []
    for i in sorted(rows):
        r = rows[i]
        tcs: dict[int, dict] = {}
        tpre = spec.get("tool_calls", "\0") + "."
        for k, v in r.items():
            if k.startswith(tpre):
                j, _, f = k[len(tpre):].partition(".")
                if j.isdigit():
                    tcs.setdefault(int(j), {})[f] = v
        calls = [{"id": t.get(spec.get("tc_id", "id"), ""), "function": {"name": t.get(spec.get("tc_name", "name"), ""),
                                                                        "arguments": t.get(spec.get("tc_args", "arguments"), "{}")}}
                 for _, t in sorted(tcs.items())]
        role = r.get(spec.get("role", "role")) or ("assistant" if spec["to"] == "output" else "user")
        out.append(_msg(role, r.get(spec.get("content", "content"), ""), calls, r.get(spec.get("tool_call_id", "tool_call_id"), "")))
    return out


def normalize(a: dict, events: list[dict] | None = None, name: str = "") -> dict:
    """Map one span's attributes (and span events) from any supported convention version or instrumentation style onto the
    current GenAI attribute names. Pure table lookup over ``semconv.yaml``; existing current-name attributes win."""
    sc = semconv()
    out = dict(a)
    msgs: dict[str, list] = {"input": [], "output": []}
    for st in sc["styles"].values():
        for old, new in (st.get("rename") or {}).items():
            if old in a and new not in out:
                out[new] = a[old]
        for rule in st.get("operation") or []:
            if "gen_ai.operation.name" not in out and str(a.get(rule["attr"], "")) in rule["map"]:
                out["gen_ai.operation.name"] = rule["map"][str(a[rule["attr"]])]
        for old, to in (st.get("json_messages") or {}).items():
            v = _loads(a.get(old))
            if isinstance(v, list):
                msgs[to] += [_msg(m.get("role", "user" if to == "input" else "assistant"), m.get("content", ""), m.get("tool_calls"),
                                  m.get("tool_call_id", "")) for m in v if isinstance(m, dict)]
            elif isinstance(v, str) and v:
                msgs[to].append(_msg("user" if to == "input" else "assistant", v))
        for spec in st.get("indexed") or []:
            msgs[spec["to"]] += _indexed(a, spec)
        ef = st.get("event_fields") or {"content": ["content", "body"], "tool_calls": ["tool_calls"], "id": ["id"]}
        for ev in events or []:
            spec = (st.get("events") or {}).get(ev.get("name", ""))
            if not spec:
                continue
            ea = {x["key"]: _unv(x.get("value", {})) for x in ev.get("attributes", [])}
            body = next((_loads(ea[k]) for k in st.get("event_body", ["body"]) if k in ea), None)
            src = dict(ea, **(body if isinstance(body, dict) else {}))
            if isinstance(src.get("message"), dict):  # gen_ai.choice body {"index", "finish_reason", "message": {...}}
                src = dict(src, **src["message"])
            def pick(k: str, src: dict = src, ef: dict = ef) -> Any:
                return next((src[f] for f in ef.get(k, []) if f in src), None)

            if spec.get("attr"):
                v = _loads(src.get(spec["attr"]))
                if isinstance(v, list):
                    msgs[spec["to"]] += [_msg(m.get("role", spec["role"]), m.get("content", "")) for m in v if isinstance(m, dict)]
                elif v:
                    msgs[spec["to"]].append(_msg(spec["role"], v))
                continue
            msgs[spec["to"]].append(_msg(src.get("role", spec["role"]), pick("content") or "", pick("tool_calls"), pick("id") or ""))
        tool = st.get("tool") or {}
        if out.get("gen_ai.operation.name") == "execute_tool":
            for key, canon in (("name", "gen_ai.tool.name"), ("args", "gen_ai.tool.call.arguments"), ("result", "gen_ai.tool.call.result")):
                v = next((a[k] for k in tool.get(key, []) if a.get(k) not in (None, "")), None)
                if v is not None and canon not in out:
                    out[canon] = json.dumps(_args_of(v)) if key == "args" else (v if isinstance(v, str) else json.dumps(v))
        if out.get("gen_ai.operation.name") == "invoke_agent" and "gen_ai.agent.name" not in out:
            v = next((a[k] for k in st.get("agent_name", []) if a.get(k)), None)
            if v:
                out["gen_ai.agent.name"] = v
    for to, canon in (("input", "gen_ai.input.messages"), ("output", "gen_ai.output.messages")):
        if msgs[to] and canon not in out:
            out[canon] = json.dumps(msgs[to], ensure_ascii=False)
    if out.get("gen_ai.operation.name") == "execute_tool" and "gen_ai.tool.name" not in out and name.startswith("execute_tool "):
        out["gen_ai.tool.name"] = name[len("execute_tool "):]
    if isinstance(out.get("gen_ai.tool.call.arguments"), dict):
        out["gen_ai.tool.call.arguments"] = json.dumps(out["gen_ai.tool.call.arguments"])
    return out


def split_traces(doc: dict) -> list[dict]:
    """Split an OTLP/JSON export (any collector, many traces per file) into one document per traceId."""
    by: dict[str, list] = {}
    for rs in doc.get("resourceSpans", []):
        for ss in rs.get("scopeSpans", []):
            for sp in ss.get("spans", []):
                by.setdefault(sp.get("traceId", ""), []).append((rs.get("resource", {}), ss.get("scope", {}), sp))
    return [{"resourceSpans": [{"resource": v[0][0], "scopeSpans": [{"scope": v[0][1], "spans": [x[2] for x in v]}]}]} for v in by.values()]


def read_otlp_file(path) -> list[dict]:
    """OTLP traces from a file: OTLP/JSON (one export per file, or one per line in .jsonl) or OTLP/protobuf (.pb / .binpb,
    an ``ExportTraceServiceRequest``; decoded with the standard library, see :mod:`agentest.standards.otlp_proto`)."""
    from pathlib import Path

    p = Path(path)
    if p.suffix in (".pb", ".binpb", ".protobuf"):
        from agentest.standards.otlp_proto import decode_traces

        return split_traces(decode_traces(p.read_bytes()))
    text = p.read_text()
    raw = [json.loads(ln) for ln in text.splitlines() if ln.strip()] if str(path).endswith(".jsonl") else [json.loads(text)]
    return [t for d in raw for t in split_traces(d)]


def from_otlp(doc: dict) -> Run:
    spans = [s for rs in doc["resourceSpans"] for ss in rs["scopeSpans"] for s in ss["spans"]]
    get = lambda s: normalize({a["key"]: _unv(a["value"]) for a in s.get("attributes", [])}, s.get("events"), s.get("name", ""))  # noqa: E731
    ids = {s.get("spanId") for s in spans}
    root = next((s for s in spans if not s.get("parentSpanId")), None) or next((s for s in spans if s.get("parentSpanId") not in ids), spans[0])
    ra = get(root)
    fs = ra.get("agentest.final_state") or "{}"
    allattrs = [(s, get(s)) for s in spans]
    first_in = next((a.get("gen_ai.input.messages") for _, a in allattrs if a.get("gen_ai.input.messages")), "")
    last_out = next((a.get("gen_ai.output.messages") for _, a in reversed(allattrs) if a.get("gen_ai.output.messages")), "")
    user_in = [p for p in _parts_of(ra.get("gen_ai.input.messages") or first_in) if p["role"] == "user"]
    conv = ra.get("gen_ai.conversation.id") or next((a["gen_ai.conversation.id"] for _, a in allattrs if a.get("gen_ai.conversation.id")), "")
    run = Run(input_id=ra.get("agentest.input.id") or conv or root.get("traceId", ""), rep=int(ra.get("agentest.run.rep", 0)),
              input=" ".join(str(p.get("content", "")) for p in user_in if p.get("type", "text") == "text") or _text_of(ra.get("gen_ai.input.messages", "")),
              answer=_text_of(ra.get("gen_ai.output.messages") or last_out),
              final_state=json.loads(fs, object_hook=_untyped) if isinstance(fs, str) else fs, error=ra.get("agentest.error.message") or "",
              duration_s=ra.get("agentest.duration_s") if "agentest.input.id" in ra
              else (int(root["endTimeUnixNano"]) - int(root["startTimeUnixNano"])) / 1e9, attrs=ra)  # foreign trace: root span duration
    run.conversation = conv
    run.t0 = int(root.get("startTimeUnixNano") or 0)
    run.attachments = [p for p in user_in if p.get("type") in ("uri", "blob", "file")]
    seen_calls: set[str] = set()
    for s, a in allattrs:
        t0, t1 = int(s["startTimeUnixNano"]), int(s["endTimeUnixNano"])
        run.times.append((t0, t1))
        run.span_blobs += [str(v) for k, v in a.items() if k not in ("gen_ai.input.messages",)]
        op = a.get("gen_ai.operation.name")
        if op == "execute_tool":
            try:
                args = json.loads(a.get("gen_ai.tool.call.arguments") or "{}")
            except ValueError:
                args = {"_raw": a.get("gen_ai.tool.call.arguments")}
            err = "error.type" in a or (s.get("status") or {}).get("code") in (2, "STATUS_CODE_ERROR")
            run.tools.append(ToolSpan(a.get("gen_ai.tool.name", ""), args if isinstance(args, dict) else {"_": args},
                                      str(a.get("gen_ai.tool.call.result") or ""), bool(err), a.get("gen_ai.agent.name", ""), t0,
                                      a.get("gen_ai.tool.call.id", ""), a, t1))
            seen_calls.add(a.get("gen_ai.tool.call.id", "") or f"#{len(run.tools)}")
        elif op == "invoke_agent" and a.get("agentest.handoff.source"):
            run.handoffs.append((a["agentest.handoff.source"], a.get("gen_ai.agent.name", ""), t0))
        elif op in ("chat", "text_completion", "generate_content"):
            run.chats.append(_text_of(a.get("gen_ai.output.messages", "")))
            batch = [p.get("name", "") for p in _parts_of(a.get("gen_ai.output.messages")) if p.get("type") == "tool_call"]
            if len(batch) > 1:
                run.batches.append(batch)
        elif s["name"] == "agentest.approval":
            run.approvals.append({"action": a.get("agentest.approval.action", ""), "granted": bool(a.get("agentest.approval.granted")),
                                  "approver": a.get("agentest.approval.approver", ""), "target": a.get("agentest.approval.target", ""),
                                  "policy_version": a.get("agentest.approval.policy_version", ""), "reason": a.get("agentest.approval.reason", ""),
                                  "t": t0})
    _calls_from_messages(run, allattrs, seen_calls)
    for ev in root.get("events", []):
        a = {x["key"]: _unv(x["value"]) for x in ev.get("attributes", [])}
        if ev["name"] == "gen_ai.evaluation.result":
            run.evaluations.append(a)
            continue
        if ev["name"] != "agentest.state_change":
            continue
        d = a.get("agentest.state_change.data")
        try:
            # only structured payloads are decoded: a bare id such as "6E-2131" must stay a string, not become 0.0
            d = json.loads(d) if isinstance(d, str) and d[:1] in '{["' else d
        except ValueError:
            pass
        run.effects.append({"kind": a.get("agentest.state_change.kind"), "effect": a.get("agentest.state_change.effect"), "data": d,
                            "t": int(ev["timeUnixNano"])})
    return run


def _calls_from_messages(run: Run, allattrs: list, seen: set[str]) -> None:
    """Instrumentations that trace only model calls record tools as ``tool_call`` parts of assistant messages and
    ``tool_call_response`` parts of the next request. Those become tool calls when no ``execute_tool`` span has the id."""
    calls: dict[str, dict] = {}
    results: dict[str, Any] = {}
    for s, a in allattrs:
        if a.get("gen_ai.operation.name") == "execute_tool":
            continue
        for key in ("gen_ai.input.messages", "gen_ai.output.messages"):
            for p in _parts_of(a.get(key)):
                if p.get("type") == "tool_call" and p.get("role") == "assistant":
                    cid = p.get("id") or f"{p.get('name')}@{len(calls)}"
                    calls.setdefault(cid, dict(p, t=int(s["startTimeUnixNano"])))
                elif p.get("type") == "tool_call_response" and p.get("id"):
                    results[p["id"]] = p.get("response")
    if run.tools:  # the trace has execute_tool spans: they are the record of what ran
        for t in run.tools:  # older conventions put arguments / results only in the messages: join them by tool-call id
            p = calls.get(t.call_id) if t.call_id else None
            if p is not None and not t.args and p.get("arguments"):
                t.args = _args_of(p.get("arguments"))
            if t.call_id in results and not t.result:
                res = results[t.call_id]
                t.result = res if isinstance(res, str) else json.dumps(res)
        return
    for cid, p in calls.items():
        if cid in seen:
            continue
        args = p.get("arguments")
        args = _args_of(args)
        res = results.get(cid)
        run.tools.append(ToolSpan(p.get("name", ""), args, res if isinstance(res, str) else ("" if res is None else json.dumps(res)),
                                  isinstance(_loads(res), dict) and bool(_loads(res).get("error")), "", p["t"], cid,
                                  {"gen_ai.tool.name": p.get("name", ""), "gen_ai.tool.call.id": cid, "agentest.derived": "message"}))
    run.tools.sort(key=lambda t: t.t)


def root_ids(doc: dict) -> list[tuple[str, str]]:
    """(traceId, spanId) of the root span(s) of one OTLP/JSON document."""
    spans = [s for rs in doc.get("resourceSpans", []) for ss in rs.get("scopeSpans", []) for s in ss.get("spans", [])]
    ids = {s.get("spanId") for s in spans}
    return [(s.get("traceId", ""), s.get("spanId", "")) for s in spans if not s.get("parentSpanId") or s.get("parentSpanId") not in ids]
