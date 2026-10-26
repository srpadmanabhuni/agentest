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

from agentest.model.trace import Episode
from agentest.standards import VERSION

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
                                                    "agentest.approval.policy_version": a.policy_version})})
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
                                                "agentest.approval.policy_version": a.policy_version})})
    events = [e for e in events if "_approvals_done" not in e]
    for ev in evaluations or []:  # OTel GenAI event gen_ai.evaluation.result
        events.append({"timeUnixNano": str(tick()), "name": "gen_ai.evaluation.result", "attributes": _attrs(ev)})
    end = tick()
    dur = int((ep.duration_s or 0) * 1e9)
    root = {"traceId": tid, "spanId": root_id, "parentSpanId": "", "name": f"invoke_agent {service}", "kind": INTERNAL,
            "startTimeUnixNano": str(start), "endTimeUnixNano": str(max(end, start + dur)),
            "attributes": _attrs({"gen_ai.operation.name": "invoke_agent", "gen_ai.agent.name": service, "gen_ai.agent.id": service,
                                  "gen_ai.conversation.id": f"{ep.probe}#{ep.rep}", "gen_ai.input.messages": _msgs("user", ep.input or ""),
                                  "gen_ai.output.messages": _msgs("assistant", ep.final_answer or ""),
                                  "agentest.input.id": ep.probe, "agentest.run.rep": int(ep.rep),
                                  "agentest.duration_s": float(ep.duration_s) if ep.duration_s is not None else None,
                                  "agentest.final_state": ep.final_state or {}, "error.type": "agent_error" if ep.error else None,
                                  "agentest.error.message": ep.error, **(extra or {})}),
            "events": events}
    if ep.error:
        root["status"] = {"code": STATUS_ERROR, "message": str(ep.error)[:200]}
    return {"resourceSpans": [{"resource": {"attributes": _attrs({"service.name": service, "gen_ai.framework": ep.framework})},
                               "scopeSpans": [{"scope": {"name": "agentest.standards.adapters", "version": VERSION},
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

    def executed(self) -> list[dict]:
        return [e for e in self.effects if e["kind"] in ("executed", "unapproved")]

    def granted(self) -> list[dict]:
        return [a for a in self.approvals if a.get("granted")]


def _text_of(msgs: str) -> str:
    try:
        return " ".join(p.get("content", "") for m in json.loads(msgs) for p in m.get("parts", []))
    except (ValueError, TypeError, AttributeError):
        return msgs or ""


def split_traces(doc: dict) -> list[dict]:
    """Split an OTLP/JSON export (any collector, many traces per file) into one document per traceId."""
    by: dict[str, list] = {}
    for rs in doc.get("resourceSpans", []):
        for ss in rs.get("scopeSpans", []):
            for sp in ss.get("spans", []):
                by.setdefault(sp.get("traceId", ""), []).append((rs.get("resource", {}), ss.get("scope", {}), sp))
    return [{"resourceSpans": [{"resource": v[0][0], "scopeSpans": [{"scope": v[0][1], "spans": [x[2] for x in v]}]}]} for v in by.values()]


def read_otlp_file(path) -> list[dict]:
    """OTLP/JSON from a file: one export document (.json) or one document per line (.jsonl)."""
    from pathlib import Path

    text = Path(path).read_text()
    raw = [json.loads(ln) for ln in text.splitlines() if ln.strip()] if str(path).endswith(".jsonl") else [json.loads(text)]
    return [t for d in raw for t in split_traces(d)]


def from_otlp(doc: dict) -> Run:
    spans = [s for rs in doc["resourceSpans"] for ss in rs["scopeSpans"] for s in ss["spans"]]
    get = lambda s: {a["key"]: _unv(a["value"]) for a in s.get("attributes", [])}  # noqa: E731
    ids = {s.get("spanId") for s in spans}
    root = next((s for s in spans if not s.get("parentSpanId")), None) or next((s for s in spans if s.get("parentSpanId") not in ids), spans[0])
    ra = get(root)
    fs = ra.get("agentest.final_state") or "{}"
    run = Run(input_id=ra.get("agentest.input.id") or ra.get("gen_ai.conversation.id") or root.get("traceId", ""), rep=int(ra.get("agentest.run.rep", 0)),
              input=_text_of(ra.get("gen_ai.input.messages", "")), answer=_text_of(ra.get("gen_ai.output.messages", "")),
              final_state=json.loads(fs, object_hook=_untyped) if isinstance(fs, str) else fs, error=ra.get("agentest.error.message") or "",
              duration_s=ra.get("agentest.duration_s") if "agentest.input.id" in ra
              else (int(root["endTimeUnixNano"]) - int(root["startTimeUnixNano"])) / 1e9, attrs=ra)  # foreign trace: root span duration
    for s in spans:
        a = get(s)
        t0, t1 = int(s["startTimeUnixNano"]), int(s["endTimeUnixNano"])
        run.times.append((t0, t1))
        run.span_blobs += [str(v) for k, v in a.items() if k not in ("gen_ai.input.messages",)]
        op = a.get("gen_ai.operation.name")
        if op == "execute_tool":
            try:
                args = json.loads(a.get("gen_ai.tool.call.arguments") or "{}")
            except ValueError:
                args = {"_raw": a.get("gen_ai.tool.call.arguments")}
            run.tools.append(ToolSpan(a.get("gen_ai.tool.name", ""), args if isinstance(args, dict) else {"_": args},
                                      str(a.get("gen_ai.tool.call.result") or ""), "error.type" in a, a.get("gen_ai.agent.name", ""), t0,
                                      a.get("gen_ai.tool.call.id", ""), a))
        elif op == "invoke_agent" and a.get("agentest.handoff.source"):
            run.handoffs.append((a["agentest.handoff.source"], a.get("gen_ai.agent.name", ""), t0))
        elif op == "chat":
            run.chats.append(_text_of(a.get("gen_ai.output.messages", "")))
        elif s["name"] == "agentest.approval":
            run.approvals.append({"action": a.get("agentest.approval.action", ""), "granted": bool(a.get("agentest.approval.granted")),
                                  "approver": a.get("agentest.approval.approver", ""), "target": a.get("agentest.approval.target", ""),
                                  "policy_version": a.get("agentest.approval.policy_version", ""), "t": t0})
    for ev in root.get("events", []):
        a = {x["key"]: _unv(x["value"]) for x in ev.get("attributes", [])}
        if ev["name"] == "gen_ai.evaluation.result":
            run.evaluations.append(a)
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
