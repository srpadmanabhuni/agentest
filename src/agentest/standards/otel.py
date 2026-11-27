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
# Ref: [OTel-GenAI-semconv], [OTel-GenAI-agent-spans] (span and attribute names); [OTLP-spec] (JSON encoding). `agentest.*` attributes are the in-house extension
# Ref: internal design (docs/standards/EXTENSION.md).

from __future__ import annotations

import bisect
import hashlib
import json
import re
from dataclasses import dataclass, field
from typing import Any

from agentest.standards import VERSION
from agentest.standards.episode import Episode, Message

INTERNAL = 1  # SPAN_KIND_INTERNAL
# gen_ai.operation.name values of a model call. ``realtime_inference`` is one server-side generation of a realtime session.
CHAT_OPS = ("chat", "text_completion", "generate_content", "realtime_inference")
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


def _user_turns(ep: Episode) -> list[tuple[int, list[str]]]:
    """User turns of a native log, in log order: ``(order of the turn's first user message, user texts of the turn)``.

    A user message that follows agent activity (a tool call or an assistant message) opens a new turn; user messages with
    no agent activity between them (the run input and the same request echoed as the log's first event, or a user who
    sends two messages before the agent answers) are one turn. A log with one turn returns one entry."""
    items = sorted([(m.seq, m) for m in ep.messages] + [(c.seq, c) for c in ep.tool_calls], key=lambda x: x[0])
    turns: list[tuple[int, list[str]]] = []
    active = False
    for seq, x in items:
        if isinstance(x, Message) and x.role == "user":
            if not turns or active:
                turns.append((seq, []))
                active = False
            turns[-1][1].append(x.content)
        elif turns:
            active = True
    return turns


def _turn_spans(ep: Episode, tid: str, root_id: str, service: str, start: int, tool_t: list[int]) -> list[dict]:
    """One ``invoke_agent`` span per user turn when a native log records more than one user turn, placed before the turn's
    first tool call. Its ``gen_ai.input.messages`` is the user side of the conversation so far, so the number of user
    messages grows at every turn: the same signal a model call's input history gives (see ``_turn_starts``). A log with
    one user turn gets no extra span, so its OTLP is unchanged."""
    turns = _user_turns(ep)
    if len(turns) < 2:
        return []
    seqs = [c.seq for c in ep.tool_calls]
    out, history, last = [], [], start
    for k, (seq, texts) in enumerate(turns):
        history += texts
        nxt = next((i for i, s in enumerate(seqs) if s > seq), None)
        t = (tool_t[nxt] - STEP // 2) if nxt is not None else ((tool_t[-1] if tool_t else start) + STEP // 2)
        t = max(t, last + 1)  # keep turns in order when several open before the same tool call
        last = t
        msgs = json.dumps([{"role": "user", "parts": [{"type": "text", "content": x}]} for x in history], ensure_ascii=False)
        out.append({"traceId": tid, "spanId": _hex(tid + f"turn{k}", 16), "parentSpanId": root_id, "name": f"invoke_agent {service}",
                    "kind": INTERNAL, "startTimeUnixNano": str(t), "endTimeUnixNano": str(t + 1),
                    "attributes": _attrs({"gen_ai.operation.name": "invoke_agent", "gen_ai.input.messages": msgs})})
    return out


def to_otlp(ep: Episode, service: str, extra: dict | None = None, tool_attrs: list[dict] | None = None,
            evaluations: list[dict] | None = None, steps: list[str] | None = None, resource: dict | None = None) -> dict:
    """One episode -> one OTLP/JSON ``TracesData`` document (one trace).

    ``resource`` adds run-level attributes to the resource (trace format 1.0.0: ``agentest.trace_format.version``,
    ``agentest.run.id``, ``user.id``, ``agentest.source.start_time_unix_nano``). Without it the output is unchanged."""
    tid = _hex(f"{service}/{ep.probe}/{ep.rep}", 32)
    spans: list[dict] = []
    # A source start (n8n startedAt, and the like) shifts the whole clock; with none, the fixed epoch is unchanged.
    clock = [BASE if ep.t0_ns is None else ep.t0_ns - STEP]

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
    tool_t: list[int] = []
    for i, c in enumerate(ep.tool_calls):
        if c.start_ns is None:
            t = tick()
            t1 = t + 1
        else:
            t = c.start_ns
            t1 = c.end_ns if c.end_ns is not None else t + 1
        tool_t.append(t)
        span = {"traceId": tid, "spanId": _hex(tid + f"tool{i}", 16), "parentSpanId": agent_span(c.actor) if c.actor else root_id,
                "name": f"execute_tool {c.name}", "kind": INTERNAL, "startTimeUnixNano": str(t), "endTimeUnixNano": str(t1),
                "attributes": _attrs({"gen_ai.operation.name": "execute_tool", "gen_ai.tool.name": c.name, "gen_ai.tool.type": "function",
                                      "gen_ai.tool.call.id": c.call_id or f"call_{i}", "gen_ai.agent.name": c.actor,
                                      "gen_ai.tool.call.arguments": json.dumps(c.arguments, ensure_ascii=False, sort_keys=True, default=str),
                                      "gen_ai.tool.call.result": c.result if isinstance(c.result, str) else (None if c.result is None else json.dumps(c.result, ensure_ascii=False, default=str)),
                                      "error.type": "tool_error" if c.error else None,
                                      **((tool_attrs or [])[i] if i < len(tool_attrs or []) else {})})}
        if c.error:
            span["status"] = {"code": STATUS_ERROR, "message": "tool error"}
        spans.append(span)
    spans += _turn_spans(ep, tid, root_id, service, start, tool_t)
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
                                                    "agentest.approval.reason": a.reason or None,
                                                    "agentest.approval.kind": getattr(a, "kind", None) or None,
                                                    "agentest.approval.dataClass": getattr(a, "dataClass", None) or None,
                                                    "agentest.approval.purpose": getattr(a, "purpose", None) or None})})
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
                                                "agentest.approval.reason": a.reason or None,
                                                "agentest.approval.kind": getattr(a, "kind", None) or None,
                                                "agentest.approval.dataClass": getattr(a, "dataClass", None) or None,
                                                "agentest.approval.purpose": getattr(a, "purpose", None) or None})})
    events = [e for e in events if "_approvals_done" not in e]
    for ev in evaluations or []:  # OTel GenAI event gen_ai.evaluation.result
        events.append({"timeUnixNano": str(tick()), "name": "gen_ai.evaluation.result", "attributes": _attrs(ev)})
    end = tick()
    for c in ep.tool_calls:  # source-timed tool spans may end after the importer clock
        if c.end_ns is not None:
            end = max(end, c.end_ns)
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
    return {"resourceSpans": [{"resource": {"attributes": _attrs({"service.name": service, "gen_ai.framework": ep.framework, **(resource or {})})},
                               "scopeSpans": [{"scope": {"name": "agentest.standards.importers", "version": VERSION},
                                               "schemaUrl": semconv()["pinned"]["schema_url"], "spans": [root, *spans]}]}]}


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
    turn_starts: list[int] = field(default_factory=list)  # start of each later user turn recorded inside this one trace (empty = one turn)
    batches: list[list[str]] = field(default_factory=list)  # tool calls issued together in one model response (>= 2)
    semconv: str = ""  # semantic-convention version the trace declares through an OTel schema URL ("" = none declared)
    trace_id: str = ""  # OTLP traceId of the root span (a replay names its original by this id)
    spans: list[dict] = field(default_factory=list)  # every span in start order: name, attrs, t0, t1, id, parent, error (New tests read these); op, agent, agent_id, root, events, pack_parent, pack_error (extension packs only)

    def executed(self) -> list[dict]:
        return [e for e in self.effects if e["kind"] in ("executed", "unapproved")]

    def turn_of(self, t: int) -> int:
        """Index of the user turn, inside this trace, that a call or effect at time ``t`` belongs to (0 = the first).

        A trace that records one user message is one turn, so every call is turn 0 (the unmarked fallback)."""
        return bisect.bisect_right(self.turn_starts, int(t or 0))

    def granted(self) -> list[dict]:
        return [a for a in self.approvals if a.get("granted")]


def usage_tokens(r: Run) -> float | None:
    """Sum of ``gen_ai.usage.input_tokens`` and ``gen_ai.usage.output_tokens`` on one run.

    Child spans are summed; the root's own totals are used only when no child records usage
    (the same rule as NT-002). Returns None when no span records usage.
    """
    def _num(v: Any) -> float | None:
        if isinstance(v, bool) or v in (None, ""):
            return None
        try:
            return float(v)
        except (TypeError, ValueError):
            return None

    def tot(spans: list[dict]) -> float | None:
        tok = None
        for s in spans:
            a = s["attrs"]
            for k in ("gen_ai.usage.input_tokens", "gen_ai.usage.output_tokens"):
                v = _num(a.get(k))
                if v is not None:
                    tok = (tok or 0) + v
        return tok

    if r.spans:
        root = [s for s in r.spans if not s.get("parent")][:1]
        kids = [s for s in r.spans if s not in root]
        tk = tot(kids)
        return tk if tk is not None else tot(root)
    steps = [{"attrs": t.attrs} for t in r.tools]
    return tot([{"attrs": r.attrs}] + steps)


def _text_of(msgs) -> str:
    try:
        ms = json.loads(msgs) if isinstance(msgs, str) else msgs
        return " ".join(str(p.get("content", "")) for m in ms for p in m.get("parts", []) if p.get("type", "text") == "text")
    except (ValueError, TypeError, AttributeError):
        return msgs if isinstance(msgs, str) else ""


def _user_messages(msgs) -> int:
    """User messages with text in one model call's input. Messages whose parts are only tool results do not count."""
    try:
        ms = json.loads(msgs) if isinstance(msgs, str) else msgs
        return sum(1 for m in ms or [] if isinstance(m, dict) and m.get("role") == "user"
                   and any(isinstance(p, dict) and p.get("type", "text") == "text" and str(p.get("content", "")).strip() for p in m.get("parts", [])))
    except (ValueError, TypeError, AttributeError):
        return 0


def _turn_starts(allattrs: list, root: dict | None = None) -> list[int]:
    """Turn markers inside one trace: a model call, or an agent invocation below the root span, whose input carries more
    user messages than any earlier one of the trace starts a new user turn (the conversation grows by a user message).
    Without such inputs, or with one user message throughout, the trace is one turn and the list is empty."""
    out: list[int] = []
    seen = 0
    for s, a in allattrs:
        op = a.get("gen_ai.operation.name")
        if not a.get("gen_ai.input.messages") or s is root:
            continue
        if op not in CHAT_OPS and not (op == "invoke_agent" and s.get("parentSpanId")):
            continue
        n = _user_messages(a.get("gen_ai.input.messages"))
        if seen and n > seen:
            out.append(int(s["startTimeUnixNano"]))
        seen = max(seen, n)
    return out


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

        _SEMCONV = yaml.safe_load((Path(__file__).parent / "semconv.yaml").read_text(encoding="utf-8"))
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
    for k in ("gen_ai.tool.call.arguments", "gen_ai.tool.call.result"):  # structured values (OTLP kvlist / array), not JSON text
        if isinstance(out.get(k), (dict, list)):
            out[k] = json.dumps(out[k], ensure_ascii=False)
    return out


def split_traces(doc: dict) -> list[dict]:
    """Split an OTLP/JSON export (any collector, many traces per file) into one document per traceId.
    The resource, scope and their ``schemaUrl`` (the semantic-convention version) of a trace's first span are kept."""
    by: dict[str, list] = {}
    for rs in doc.get("resourceSpans", []):
        for ss in rs.get("scopeSpans", []):
            for sp in ss.get("spans", []):
                got = by.setdefault(sp.get("traceId", ""), [])
                if sp.get("spanId") and any(x[2].get("spanId") == sp["spanId"] for x in got):
                    continue  # the same span sent again (an exporter retry): the first copy wins
                got.append((rs, ss, sp))
    logs: dict[str, list] = {}  # trace-format records sent as OTLP log records (D8), by traceId
    for rl in doc.get("resourceLogs") or []:
        for sl in rl.get("scopeLogs") or []:
            for lr in sl.get("logRecords") or []:
                if lr.get("traceId") in by:
                    logs.setdefault(lr["traceId"], []).append(lr)
    out = []
    for tid, v in by.items():
        rs, ss = v[0][0], v[0][1]
        r = {"resource": rs.get("resource", {}), "scopeSpans": [{"scope": ss.get("scope", {}), "spans": [x[2] for x in v]}]}
        if rs.get("schemaUrl"):
            r["schemaUrl"] = rs["schemaUrl"]
        if ss.get("schemaUrl"):
            r["scopeSpans"][0]["schemaUrl"] = ss["schemaUrl"]
        d = {"resourceSpans": [r]}
        if tid in logs:
            d["resourceLogs"] = [{"scopeLogs": [{"logRecords": logs[tid]}]}]
        out.append(d)
    return out


def read_otlp_file(path) -> list[dict]:
    """OTLP traces from a file: OTLP/JSON (one export per file, or one per line in .jsonl) or OTLP/protobuf (.pb / .binpb,
    an ``ExportTraceServiceRequest``; decoded with the standard library, see :mod:`agentest.standards.otlp_proto`)."""
    from pathlib import Path

    p = Path(path)
    if p.suffix in (".pb", ".binpb", ".protobuf"):
        from agentest.standards.otlp_proto import decode_traces

        return split_traces(decode_traces(p.read_bytes()))
    text = p.read_text(encoding="utf-8")
    raw = [json.loads(ln) for ln in text.splitlines() if ln.strip()] if str(path).endswith(".jsonl") else [json.loads(text)]
    # an SDK exports a trace in several requests (one per span with a simple processor, or across batches), so
    # spans of one traceId are merged across lines before the file is split into one document per trace
    return split_traces({"resourceSpans": [rs for d in raw for rs in d.get("resourceSpans", [])],
                         "resourceLogs": [rl for d in raw for rl in d.get("resourceLogs", [])]})


_SCHEMA_RX = re.compile(r"/schemas/(\d+\.\d+\.\d+)/?$")


def declared_semconv(doc: dict) -> list[str]:
    """Semantic-convention versions a trace declares: the version in each ResourceSpans / ScopeSpans ``schemaUrl``
    (https://opentelemetry.io/docs/specs/otel/schemas/), in order of appearance, without duplicates."""
    out: list[str] = []
    for rs in doc.get("resourceSpans", []):
        for u in [rs.get("schemaUrl", "")] + [ss.get("schemaUrl", "") for ss in rs.get("scopeSpans", [])]:
            m = _SCHEMA_RX.search(u or "")
            if m and m.group(1) not in out:
                out.append(m.group(1))
    return out


def semconv_status(version: str) -> str:
    """How agentest maps a declared version: ``pinned``, the name of the semconv.yaml style that lists it, ``newer``
    (newer than the pinned version: attributes added since are not mapped yet) or ``unknown`` (older than every table)."""
    sc = semconv()
    if version == sc["pinned"]["semconv"]:
        return "pinned"
    for name, st in sc["styles"].items():
        if version in st.get("versions", []):
            return name
    key = lambda v: tuple(int(x) for x in v.split("."))  # noqa: E731
    return "newer" if key(version) > key(sc["pinned"]["semconv"]) else "unknown"


# Trace format 1.0.0 read aliases (D1/D2) that semconv.yaml does not already rename: alias -> canonical name. The
# canonical name wins when both are present; between two aliases of one name the first listed wins. The alias key is
# kept, and alias copies are not added to ``span_blobs``, so size-based checks see the trace as it was written.
READ_ALIASES = {
    "agentest.approval.dataClass": "agentest.approval.data_class",
    "agentest.output": "agentest.output.structured",
    "enduser.roles": "user.roles",
    "agentest.auth.role": "user.roles",
    "agentest.undo.before": "agentest.task.initial_state",
}


def aliased(a: dict) -> dict:
    """Add the canonical name for every read alias present (D2). Existing canonical values are never replaced."""
    out = dict(a)
    for alias, canon in READ_ALIASES.items():
        if alias in a and canon not in out:
            out[canon] = a[alias]
    return out


def apply_tool_declarations(agent, runs: list) -> None:
    """Per-tool ``tools.json`` ``_meta`` declarations onto each tool span (D7). The span's own value wins."""
    cache: dict[str, dict] = {}
    for r in runs:
        for t in r.tools:
            if t.name not in cache:
                cache[t.name] = agent.declared(t.name) if hasattr(agent, "declared") else {}
            decl = cache[t.name]
            if decl and any(k not in t.attrs for k in decl):
                t.attrs = {**decl, **t.attrs}


# Trace format records (D8). A record may arrive as a dedicated span, a span event or an OTLP log record (``eventName``,
# or the ``event.name`` attribute, with the trace and span ids of where it happened). ``lift_records`` rewrites the other
# forms into the one the checks read: span records become child spans, event records become root-span events.
SPAN_RECORDS = ("agentest.approval", "agentest.human_input", "agentest.handoff", "agentest.stop", "agentest.decision", "agentest.notice",
                "agentest.access_log", "agentest.user_setting", "agentest.dsar.request", "agentest.dsar.completion", "agentest.consent.revoke",
                "agentest.snapshot", "agentest.alert")
EVENT_RECORDS = ("agentest.state_change", "gen_ai.evaluation.result")


def _root_of(spans: list[dict]) -> dict | None:
    ids = {s.get("spanId") for s in spans}
    return next((s for s in spans if not s.get("parentSpanId")), None) or next((s for s in spans if s.get("parentSpanId") not in ids),
                                                                              spans[0] if spans else None)


def _log_records(doc: dict) -> list[tuple[str, dict]]:
    """(record name, log record) for every OTLP log record that carries a trace-format record."""
    out = []
    for rl in doc.get("resourceLogs") or []:
        for sl in rl.get("scopeLogs") or []:
            for lr in sl.get("logRecords") or []:
                attrs = {a.get("key"): _unv(a.get("value", {})) for a in lr.get("attributes") or []}
                name = lr.get("eventName") or attrs.get("event.name") or ""
                if name in SPAN_RECORDS or name in EVENT_RECORDS:
                    out.append((name, lr))
    return out


def _with_details(spans: list[dict], doc: dict) -> dict[str, dict]:
    """``{spanId: copy of the span}`` for every span that an ``operation.details`` event (span event, or OTLP log record
    carrying the span id) gives content it does not carry itself. An attribute on the span is never replaced."""
    extra: dict[str, dict[str, dict]] = {}
    ids = {s.get("spanId") for s in spans}
    reads = semconv()["reads"]  # names are data (semconv.yaml): the event, and the content it may carry in place of the span
    event_name, wanted = reads["details_event"], set(reads["details_attrs"])

    def take(span_id: str, attrs: list) -> None:
        got = extra.setdefault(span_id, {})
        for a in attrs or []:
            if a.get("key") in wanted and a.get("key") not in got:
                got[a["key"]] = a

    for s in spans:
        for ev in s.get("events") or []:
            if ev.get("name") == event_name:
                take(s.get("spanId"), ev.get("attributes"))
    for rl in doc.get("resourceLogs") or []:
        for sl in rl.get("scopeLogs") or []:
            for lr in sl.get("logRecords") or []:
                attrs = list(lr.get("attributes") or [])
                if (lr.get("eventName") or next((_unv(a.get("value", {})) for a in attrs if a.get("key") == "event.name"), "")) == event_name \
                        and lr.get("spanId") in ids:
                    take(lr["spanId"], attrs + list((lr.get("body") or {}).get("kvlistValue", {}).get("values") or []))
    out: dict[str, dict] = {}
    for s in spans:
        have = {a.get("key") for a in s.get("attributes") or []}
        add = [a for k, a in extra.get(s.get("spanId"), {}).items() if k not in have]
        if add:
            out[s["spanId"]] = dict(s, attributes=list(s.get("attributes") or []) + add)
    return out


def lift_records(doc: dict) -> dict:
    """Return ``doc`` with every record in the form the reader reads (D8). A document whose records are already in that
    form (span records as spans, event records as root-span events, no log records) is returned as it is."""
    spans = [s for rs in doc.get("resourceSpans", []) for ss in rs.get("scopeSpans", []) for s in ss.get("spans", [])]
    logs = _log_records(doc)
    root = _root_of(spans)
    if root is None:
        return doc
    detailed = _with_details(spans, doc)
    if detailed:  # spans that gained content from operation.details events: read those copies from here on
        spans = [detailed.get(s.get("spanId"), s) for s in spans]
        root = detailed.get(root.get("spanId"), root)
    by_id = {s.get("spanId"): s for s in spans}
    new_spans: list[dict] = []
    root_events: list[dict] = []

    def as_span(name: str, carrier: dict, t: Any, attrs: list, key: str) -> None:
        t = str(t or carrier.get("startTimeUnixNano") or 0)
        new_spans.append({"traceId": carrier.get("traceId", ""), "spanId": _hex(f"{carrier.get('spanId')}/{key}", 16), "parentSpanId": carrier.get("spanId", ""),
                          "name": name, "kind": INTERNAL, "startTimeUnixNano": t, "endTimeUnixNano": t, "attributes": list(attrs or [])})

    for s in spans:
        for i, ev in enumerate(s.get("events") or []):
            if ev.get("name") in SPAN_RECORDS:
                as_span(ev["name"], s, ev.get("timeUnixNano"), ev.get("attributes"), f"event{i}")
            elif ev.get("name") in EVENT_RECORDS and s is not root:
                root_events.append({"name": ev["name"], "timeUnixNano": str(ev.get("timeUnixNano") or s.get("startTimeUnixNano") or 0),
                                    "attributes": list(ev.get("attributes") or [])})
        if s.get("name") in EVENT_RECORDS and s is not root:
            root_events.append({"name": s["name"], "timeUnixNano": str(s.get("startTimeUnixNano") or 0), "attributes": list(s.get("attributes") or [])})
    for j, (name, lr) in enumerate(logs):
        if lr.get("traceId") and lr["traceId"] != root.get("traceId"):
            continue
        carrier = by_id.get(lr.get("spanId")) or root
        attrs = [a for a in lr.get("attributes") or [] if a.get("key") != "event.name"]
        body = (lr.get("body") or {}).get("kvlistValue", {}).get("values") or []
        attrs += [b for b in body if b.get("key") not in {a.get("key") for a in attrs}]
        t = lr.get("timeUnixNano") or lr.get("observedTimeUnixNano")
        if name in SPAN_RECORDS:
            as_span(name, carrier, t, attrs, f"log{j}")
        else:
            root_events.append({"name": name, "timeUnixNano": str(t or carrier.get("startTimeUnixNano") or 0), "attributes": attrs})
    if not new_spans and not root_events and not detailed:
        return doc
    lifted_root = dict(root)
    if root_events:
        lifted_root["events"] = sorted([*(root.get("events") or []), *root_events], key=lambda e: int(e.get("timeUnixNano") or 0))
    out_spans = [lifted_root if s is root else s for s in spans] + new_spans
    rs0 = (doc.get("resourceSpans") or [{}])[0]
    ss0 = (rs0.get("scopeSpans") or [{}])[0]
    r = {"resource": rs0.get("resource", {}), "scopeSpans": [{"scope": ss0.get("scope", {}), "spans": out_spans}]}
    if rs0.get("schemaUrl"):
        r["schemaUrl"] = rs0["schemaUrl"]
    if ss0.get("schemaUrl"):
        r["scopeSpans"][0]["schemaUrl"] = ss0["schemaUrl"]
    return {"resourceSpans": [r]}


def from_otlp(doc: dict) -> Run:
    doc = lift_records(doc)
    spans = [s for rs in doc["resourceSpans"] for ss in rs["scopeSpans"] for s in ss["spans"]]
    # export order is not causal order (SDKs export a span when it ends, children first): read spans by start time
    spans.sort(key=lambda s: int(s.get("startTimeUnixNano") or 0))
    get = lambda s: normalize({a["key"]: _unv(a["value"]) for a in s.get("attributes", [])}, s.get("events"), s.get("name", ""))  # noqa: E731
    ids = {s.get("spanId") for s in spans}
    root = next((s for s in spans if not s.get("parentSpanId")), None) or next((s for s in spans if s.get("parentSpanId") not in ids), spans[0])
    normed = [(s, get(s)) for s in spans]
    ra = aliased(next(n for s, n in normed if s is root))
    fs = ra.get("agentest.final_state") or "{}"
    allattrs = [(s, aliased(n)) for s, n in normed]
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
    run.semconv = next(iter(declared_semconv(doc)), "")
    run.t0 = int(root.get("startTimeUnixNano") or 0)
    run.trace_id = root.get("traceId", "")
    run.attachments = [p for p in user_in if p.get("type") in ("uri", "blob", "file")]
    seen_calls: set[str] = set()
    for (s, a), (_, n) in zip(allattrs, normed, strict=True):
        t0, t1 = int(s["startTimeUnixNano"]), int(s["endTimeUnixNano"])
        run.times.append((t0, t1))
        run.span_blobs += [str(v) for k, v in n.items() if k not in ("gen_ai.input.messages",)]
        run.spans.append({"name": s.get("name", ""), "attrs": a, "t0": t0, "t1": t1, "id": s.get("spanId", ""),
                          "parent": s.get("parentSpanId", ""), "error": (s.get("status") or {}).get("code") in (2, "STATUS_CODE_ERROR"),
                          # read by the opt-in extension packs only
                          "op": a.get("gen_ai.operation.name", ""), "agent": a.get("gen_ai.agent.name", ""), "agent_id": a.get("gen_ai.agent.id", ""),
                          "root": s is root,
                          "pack_parent": s.get("parentSpanId", "") if s.get("parentSpanId", "") in ids else "",
                          "pack_error": "error.type" in a or (s.get("status") or {}).get("code") in (2, "STATUS_CODE_ERROR"),
                          "events": [{"name": e.get("name", ""), "t": int(e.get("timeUnixNano") or 0),
                                      "attrs": {x["key"]: _unv(x["value"]) for x in e.get("attributes", [])}} for e in s.get("events", [])]})
        op = a.get("gen_ai.operation.name")
        if op == "execute_tool":
            raw = a.get("gen_ai.tool.call.arguments")
            try:
                args = json.loads(raw) if isinstance(raw, (str, bytes)) and raw else ({} if raw in (None, "") else raw)  # a scalar is kept whole
            except ValueError:
                args = {"_raw": raw}
            err = "error.type" in a or (s.get("status") or {}).get("code") in (2, "STATUS_CODE_ERROR")
            run.tools.append(ToolSpan(a.get("gen_ai.tool.name", ""), args if isinstance(args, dict) else {"_": args},
                                      str(a.get("gen_ai.tool.call.result") or ""), bool(err), a.get("gen_ai.agent.name", ""), t0,
                                      a.get("gen_ai.tool.call.id", ""), a, t1))
            seen_calls.add(a.get("gen_ai.tool.call.id", "") or f"#{len(run.tools)}")
            target = a.get(semconv()["reads"]["transfer_target"])  # execute_tool.transfer refinement: the agent handed to
            if target and not a.get("agentest.handoff.source"):
                run.handoffs.append((a.get("gen_ai.agent.name") or ra.get("gen_ai.agent.name", ""), str(target), t0))
        elif op == "invoke_agent" and a.get("agentest.handoff.source"):
            run.handoffs.append((a["agentest.handoff.source"], a.get("gen_ai.agent.name", ""), t0))
        elif op in CHAT_OPS:
            run.chats.append(_text_of(a.get("gen_ai.output.messages", "")))
            batch = [p.get("name", "") for p in _parts_of(a.get("gen_ai.output.messages")) if p.get("type") == "tool_call"]
            if len(batch) > 1:
                run.batches.append(batch)
        elif s["name"] == "agentest.approval":
            run.approvals.append({"action": a.get("agentest.approval.action", ""), "granted": bool(a.get("agentest.approval.granted")),
                                  "approver": a.get("agentest.approval.approver", ""), "target": a.get("agentest.approval.target", ""),
                                  "policy_version": a.get("agentest.approval.policy_version", ""), "reason": a.get("agentest.approval.reason", ""),
                                  "kind": a.get("agentest.approval.kind", ""), "dataClass": a.get("agentest.approval.data_class", ""),
                                  "purpose": a.get("agentest.approval.purpose", ""),
                                  "t": t0})
    _calls_from_messages(run, allattrs, seen_calls)
    run.turn_starts = _turn_starts(allattrs, root)
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
    if run.turn_starts:
        _effect_turns(run)
    return run


def _effect_turns(run: Run) -> None:
    """Give an effect the user turn of the tool call it records. Logs that list effects only at the end of the run (an
    ``executed`` list in the final output) stamp them after every call, so their time says nothing about the turn. An
    effect records a call when its payload names the tool and carries the call's arguments (flat, or under ``args``);
    calls are matched in order, once each. Unmatched effects keep the turn of their own time."""
    used: set[int] = set()
    for e in run.effects:
        d = e.get("data")
        if not isinstance(d, dict):
            continue
        names = {str(v) for v in d.values() if isinstance(v, str)}
        args = d.get("args") if isinstance(d.get("args"), dict) else d
        for i, t in enumerate(run.tools):
            if i in used or t.name not in names or not t.args or any(args.get(k) != v for k, v in t.args.items()):
                continue
            used.add(i)
            e["turn"] = run.turn_of(t.t)
            break


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
