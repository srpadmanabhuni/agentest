"""Emit traces in the agentest trace format (docs/TRACE-FORMAT.md, format 1.0.0), with the standard library only.

Two ways to use it, for any agent and any framework:

* ``attrs_*`` functions return attribute dictionaries in the approved names and encodings. Pass them to an
  OpenTelemetry SDK span (``span.set_attributes(attrs_tool(...))``); lists of scalars stay lists (OTLP string arrays)
  and objects become JSON strings (decision D4).
* :class:`TraceBuilder` writes one run as an OTLP/JSON ``TracesData`` document, for teams without an OTel SDK, or to
  turn a framework callback stream into a file ``agentest std run --otlp`` reads.

Nothing here names an agent, a framework or a check. Records (approvals, decisions, ...) can be spans or span events
(decision D8); the run's identity follows decision D9 (``agentest.run.id``, ``gen_ai.conversation.id``, ``user.id``).
"""
# Ref: [OTel-GenAI-semconv], [OTel-GenAI-agent-spans] (names); [OTLP-spec] (JSON encoding); docs/TRACE-FORMAT.md (agentest.* names).

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any

FORMAT_VERSION = "1.0.0"
SCHEMA_URL = "https://opentelemetry.io/schemas/1.42.0"
INTERNAL = 1
STATUS_OK, STATUS_ERROR = 1, 2


def _scalar_list(x: Any) -> bool:
    return isinstance(x, (list, tuple)) and all(isinstance(v, str) for v in x)


def clean(attrs: dict) -> dict:
    """Attribute values in the approved encoding: scalars as is, lists of strings as lists, everything else JSON."""
    out: dict[str, Any] = {}
    for k, v in attrs.items():
        if v is None or v == "":
            continue
        if isinstance(v, (bool, int, float, str)) or _scalar_list(v):
            out[k] = list(v) if isinstance(v, tuple) else v
        else:
            out[k] = json.dumps(v, ensure_ascii=False, sort_keys=True, default=str)
    return out


def _dotted(extra: dict) -> dict:
    """Keyword attributes: dots written as ``__`` (``agentest__tool__kind="page_snapshot"``)."""
    return {k.replace("__", "."): v for k, v in extra.items()}


def _msgs(role: str, text: str) -> str:
    return json.dumps([{"role": role, "parts": [{"type": "text", "content": text}]}], ensure_ascii=False)


# ---------------------------------------------------------------- attribute dictionaries (for an OTel SDK span)

def attrs_root(agent: str, input_text: str = "", answer: str = "", input_id: str = "", rep: int = 0, conversation: str = "",
               run_id: str = "", user_id: str = "", final_state: Any = None, error: str = "", task: dict | None = None,
               **extra: Any) -> dict:
    """Root (``invoke_agent``) span of one run. ``task`` keys become ``agentest.task.<key>`` declarations."""
    a = {"gen_ai.operation.name": "invoke_agent", "gen_ai.agent.name": agent, "gen_ai.conversation.id": conversation,
         "gen_ai.input.messages": _msgs("user", input_text) if input_text else None,
         "gen_ai.output.messages": _msgs("assistant", answer) if answer else None,
         "agentest.input.id": input_id, "agentest.run.rep": int(rep), "agentest.run.id": run_id, "user.id": user_id,
         "agentest.final_state": final_state if final_state is not None else None, "agentest.error.message": error,
         "error.type": "agent_error" if error else None}
    a.update({f"agentest.task.{k}": v for k, v in (task or {}).items()})
    a.update(_dotted(extra))
    return clean(a)


def attrs_tool(name: str, arguments: dict | None = None, result: Any = None, call_id: str = "", agent: str = "",
               error: bool = False, reason: str = "", **extra: Any) -> dict:
    """``execute_tool`` span. ``extra`` takes any further attribute, dots as ``__`` (``agentest__tool__kind=...``)."""
    return clean({"gen_ai.operation.name": "execute_tool", "gen_ai.tool.name": name, "gen_ai.tool.type": "function",
                  "gen_ai.tool.call.id": call_id, "gen_ai.agent.name": agent,
                  "gen_ai.tool.call.arguments": json.dumps(arguments or {}, ensure_ascii=False, sort_keys=True, default=str),
                  "gen_ai.tool.call.result": result if isinstance(result, str) or result is None else json.dumps(result, ensure_ascii=False, default=str),
                  "error.type": "tool_error" if error else None, "agentest.tool.reason": reason, **_dotted(extra)})


def attrs_chat(text: str = "", input_text: str = "", input_tokens: int | None = None, output_tokens: int | None = None, **extra: Any) -> dict:
    """Model call (``chat``) span."""
    return clean({"gen_ai.operation.name": "chat", "gen_ai.output.messages": _msgs("assistant", text) if text else None,
                  "gen_ai.input.messages": _msgs("user", input_text) if input_text else None,
                  "gen_ai.usage.input_tokens": input_tokens, "gen_ai.usage.output_tokens": output_tokens, **_dotted(extra)})


def attrs_agent(name: str, source: str = "") -> dict:
    """Agent invocation; ``source`` names the agent that handed off to it."""
    return clean({"gen_ai.operation.name": "invoke_agent", "gen_ai.agent.name": name, "agentest.handoff.source": source})


def attrs_approval(action: str, granted: bool, approver: str = "", target: str = "", policy_version: str = "", reason: str = "",
                   kind: str = "", data_class: str = "", purpose: str = "") -> dict:
    """An ``agentest.approval`` record. ``data_class`` is written as ``agentest.approval.dataClass``, the name the reader
    reads today (D2 canonical name ``agentest.approval.data_class``; see docs/TRACE-FORMAT.md)."""
    return clean({"agentest.approval.action": action, "agentest.approval.granted": bool(granted), "agentest.approval.approver": approver,
                  "agentest.approval.target": target, "agentest.approval.policy_version": policy_version,
                  "agentest.approval.reason": reason, "agentest.approval.kind": kind, "agentest.approval.dataClass": data_class,
                  "agentest.approval.purpose": purpose})


def attrs_state_change(kind: str, effect: str, data: Any = None) -> dict:
    """An ``agentest.state_change`` record (executed | pending | unapproved | diff)."""
    return clean({"agentest.state_change.kind": kind, "agentest.state_change.effect": effect,
                  "agentest.state_change.data": data if isinstance(data, str) or data is None else json.dumps(data, ensure_ascii=False, default=str)})


def resource_attrs(service: str, framework: str = "", **extra: Any) -> dict:
    """Resource attributes, including the trace format version (D5)."""
    return clean({"service.name": service, "gen_ai.framework": framework, "agentest.trace_format.version": FORMAT_VERSION, **_dotted(extra)})


# ---------------------------------------------------------------- OTLP/JSON writer

def _value(v: Any) -> dict:
    if isinstance(v, bool):
        return {"boolValue": v}
    if isinstance(v, int):
        return {"intValue": str(v)}
    if isinstance(v, float):
        return {"doubleValue": v}
    if isinstance(v, list):
        return {"arrayValue": {"values": [_value(x) for x in v]}}
    return {"stringValue": str(v)}


def otlp_attributes(attrs: dict) -> list[dict]:
    return [{"key": k, "value": _value(v)} for k, v in clean(attrs).items()]


class TraceBuilder:
    """One run as one OTLP/JSON document. Calls are recorded in the order they are made; each takes one clock step.

    >>> t = TraceBuilder("refund-desk", input_text="Refund ORD-7", input_id="case-1")
    >>> _ = t.tool("lookup_order", {"order_id": "ORD-7"}, {"total": 40})
    >>> t.answer("Refund requested.")
    >>> doc = t.build()
    """

    def __init__(self, service: str, input_text: str = "", input_id: str = "", rep: int = 0, conversation: str = "",
                 run_id: str = "", user_id: str = "", framework: str = "", start_ns: int | None = None, step_ns: int = 1_000_000,
                 trace_id: str = "", task: dict | None = None, **root_extra: Any) -> None:
        self.service, self.framework = service, framework
        self.trace_id = trace_id or hashlib.sha256(f"{service}/{input_id}/{rep}/{run_id}".encode()).hexdigest()[:32]
        self._t = int(start_ns if start_ns is not None else time.time_ns())
        self._t0, self._step = self._t, step_ns
        self._root = attrs_root(service, input_text, "", input_id, rep, conversation or (f"{input_id}#{rep}" if input_id else ""),
                                run_id, user_id, task=task, **root_extra)
        self._root_id = self._id("root")
        self._spans: list[dict] = []
        self._events: list[dict] = []
        self._links: list[dict] = []
        self._agents: dict[str, str] = {}
        self._status_error = ""

    # -- helpers
    def _id(self, seed: str) -> str:
        return hashlib.sha256(f"{self.trace_id}/{seed}".encode()).hexdigest()[:16]

    def _tick(self) -> int:
        self._t += self._step
        return self._t

    def _span(self, name: str, attrs: dict, parent: str = "", error: bool = False) -> str:
        t = self._tick()
        sid = self._id(f"s{len(self._spans)}")
        s = {"traceId": self.trace_id, "spanId": sid, "parentSpanId": parent or self._root_id, "name": name, "kind": INTERNAL,
             "startTimeUnixNano": str(t), "endTimeUnixNano": str(t + self._step // 2), "attributes": otlp_attributes(attrs)}
        if error:
            s["status"] = {"code": STATUS_ERROR, "message": "error"}
        self._spans.append(s)
        return sid

    # -- what happened
    def agent(self, name: str, source: str = "") -> str:
        """An agent invocation (a handoff when ``source`` is given). Returns its span id, for ``parent=``."""
        if name not in self._agents:
            parent = self._agents.get(source, "")
            self._agents[name] = self._span(f"invoke_agent {name}", attrs_agent(name, source), parent)
        return self._agents[name]

    def tool(self, name: str, arguments: dict | None = None, result: Any = None, error: bool = False, call_id: str = "",
             agent: str = "", reason: str = "", **extra: Any) -> str:
        cid = call_id or f"call_{sum(1 for s in self._spans if s['name'].startswith('execute_tool '))}"
        parent = self.agent(agent) if agent else ""
        return self._span(f"execute_tool {name}", attrs_tool(name, arguments, result, cid, agent, error, reason, **extra), parent, error)

    def chat(self, text: str = "", agent: str = "", **extra: Any) -> str:
        return self._span("chat", attrs_chat(text, **extra), self.agent(agent) if agent else "")

    def approval(self, action: str, granted: bool, form: str = "span", **kw: Any) -> None:
        self.record("agentest.approval", attrs_approval(action, granted, **kw), form)

    def state_change(self, kind: str, effect: str, data: Any = None) -> None:
        self.record("agentest.state_change", attrs_state_change(kind, effect, data), "event")

    def record(self, name: str, attrs: dict, form: str = "span") -> None:
        """A named record (D8): ``form="span"`` (a child span) or ``"event"`` (an event on the root span)."""
        if form == "event":
            self._events.append({"timeUnixNano": str(self._tick()), "name": name, "attributes": otlp_attributes(attrs)})
        elif form == "span":
            self._span(name, attrs)
        else:
            raise ValueError("form must be 'span' or 'event'")

    def evaluation(self, label: str, value: float | None = None, name: str = "", explanation: str = "") -> None:
        """A ``gen_ai.evaluation.result`` event: a harness or oracle verdict on the run."""
        self.record("gen_ai.evaluation.result", {"gen_ai.evaluation.name": name, "gen_ai.evaluation.score.label": label,
                                                 "gen_ai.evaluation.score.value": value, "gen_ai.evaluation.explanation": explanation}, "event")

    def link(self, trace_id: str, span_id: str, **attrs: Any) -> None:
        """An OTel span link from the root span to a span of another trace of the same run (D9)."""
        self._links.append({"traceId": trace_id, "spanId": span_id, **({"attributes": otlp_attributes(attrs)} if attrs else {})})

    def set(self, **attrs: Any) -> None:
        """More root-span attributes (dots written as ``__``: ``set(agentest__input__families=["injection"])``)."""
        self._root.update(clean(_dotted(attrs)))

    def answer(self, text: str) -> None:
        self._root.update(clean({"gen_ai.output.messages": _msgs("assistant", text)}))

    def final_state(self, state: Any) -> None:
        self._root.update(clean({"agentest.final_state": state}))

    def error(self, message: str) -> None:
        self._status_error = message
        self._root.update(clean({"agentest.error.message": message, "error.type": "agent_error"}))

    # -- output
    def build(self) -> dict:
        end = self._tick()
        root = {"traceId": self.trace_id, "spanId": self._root_id, "parentSpanId": "", "name": f"invoke_agent {self.service}",
                "kind": INTERNAL, "startTimeUnixNano": str(self._t0), "endTimeUnixNano": str(end),
                "attributes": otlp_attributes(self._root), "events": list(self._events)}
        if self._links:
            root["links"] = list(self._links)
        if self._status_error:
            root["status"] = {"code": STATUS_ERROR, "message": self._status_error[:200]}
        return {"resourceSpans": [{"resource": {"attributes": otlp_attributes(resource_attrs(self.service, self.framework))},
                                   "scopeSpans": [{"scope": {"name": "agentest.standards.emit", "version": FORMAT_VERSION},
                                                   "schemaUrl": SCHEMA_URL, "spans": [root, *self._spans]}]}]}

    def write(self, path: str | Path, append: bool = True) -> Path:
        """Append the run as one line of an ``.otlp.jsonl`` file (or write a ``.json`` file)."""
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(self.build(), ensure_ascii=False)
        if p.suffix == ".jsonl":
            with p.open("a" if append else "w", encoding="utf-8") as f:
                f.write(line + "\n")
        else:
            p.write_text(line + "\n", encoding="utf-8")
        return p
