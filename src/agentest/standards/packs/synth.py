"""Build small synthetic OTLP/JSON traces (OTel GenAI conventions) for tests, examples and bug reports.

Nothing here is read by a check. It writes the same attribute names an instrumented agent would emit, so a
trace built here goes through exactly the same path as a recorded one (``from_otlp(json.loads(json.dumps(doc)))``).
Timestamps are logical (one step = 1 ms from a fixed epoch), so the output is byte-for-byte reproducible.

>>> t = Synth("case-1", user="Refund order ORD-1001")
>>> worker = t.agent("billing", handoff_from="supervisor", input="Refund order ORD-1001")
>>> _ = t.tool("issue_refund", {"order_id": "ORD-1001"}, "ok", parent=worker)
>>> doc = t.answer("Refund issued for ORD-1001.").build()
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from agentest.standards.otel import BASE, INTERNAL, STATUS_ERROR, STEP, _attrs

__all__ = ["Synth"]


def _hex(seed: str, n: int) -> str:
    return hashlib.sha256(seed.encode()).hexdigest()[:n]


def _msg(role: str, text: str) -> str:
    return json.dumps([{"role": role, "parts": [{"type": "text", "content": text}]}], ensure_ascii=False)


class Synth:
    """One trace = one recorded input. ``root_agent=None`` makes the root an ``invoke_workflow`` span (no agent name)."""

    def __init__(self, input_id: str, user: str = "", *, root_agent: str | None = "supervisor", conversation: str = "", rep: int = 0,
                 root_attrs: dict[str, Any] | None = None, t0: int = 0, system: str = "") -> None:
        self.input_id, self.rep, self.user, self.root_agent = input_id, rep, user, root_agent
        self.tid = _hex(f"synth/{input_id}/{conversation}/{rep}", 32)
        self.clock = BASE + t0 * 1000 * STEP
        self.spans: list[dict] = []
        self.events: list[dict] = []
        self.root_attrs: dict[str, Any] = dict(root_attrs or {})
        self.conversation, self._answer, self._system = conversation, "", system
        self.root_id = self._sid("root")
        self._start = self._tick()
        self._agents: dict[str, str] = {}
        if root_agent:
            self._agents[root_agent] = self.root_id

    # ---- internals
    def _tick(self) -> int:
        self.clock += STEP
        return self.clock

    def _sid(self, label: str) -> str:
        return _hex(f"{self.tid}/{label}/{len(self.spans)}", 16)

    def _span(self, name: str, parent: str, attrs: dict, error: bool = False, events: list | None = None) -> dict:
        t = self._tick()
        sp = {"traceId": self.tid, "spanId": self._sid(name), "parentSpanId": parent, "name": name, "kind": INTERNAL,
              "startTimeUnixNano": str(t), "endTimeUnixNano": str(t + 1), "attributes": _attrs(attrs)}
        if events:
            sp["events"] = events
        if error:
            sp["status"] = {"code": STATUS_ERROR, "message": "error"}
        self.spans.append(sp)
        return sp

    def _parent(self, parent: str | None) -> str:
        return parent or self.root_id

    # ---- agents and tools
    def agent(self, name: str, *, parent: str | None = None, handoff_from: str | None = None, input: str | None = None, output: str | None = None,
              error: bool = False, role: str | None = None, decision: str | None = None, agent_id: str | None = None, attrs: dict | None = None) -> str:
        """An ``invoke_agent`` span. ``input`` is what the agent was handed, ``output`` what it returned."""
        a = {"gen_ai.operation.name": "invoke_agent", "gen_ai.agent.name": name, "gen_ai.agent.id": agent_id,
             "agentest.handoff.source": handoff_from, "agentest.agent.role": role, "agentest.agent.decision": decision,
             "gen_ai.input.messages": _msg("user", input) if input is not None else None,
             "gen_ai.output.messages": _msg("assistant", output) if output is not None else None,
             "error.type": "agent_error" if error else None, **(attrs or {})}
        sp = self._span(f"invoke_agent {name}", self._parent(parent), a, error)
        return sp["spanId"]

    def tool(self, name: str, args: dict | None = None, result: Any = "", *, parent: str | None = None, agent: str | None = None, error: bool = False,
             call_id: str | None = None, reason: str | None = None, attrs: dict | None = None) -> str:
        """An ``execute_tool`` span. ``agent`` sets ``gen_ai.agent.name`` on the tool span itself (optional in the conventions)."""
        n = sum(1 for s in self.spans if s["name"].startswith("execute_tool"))
        res = result if isinstance(result, str) else json.dumps(result, ensure_ascii=False)
        a = {"gen_ai.operation.name": "execute_tool", "gen_ai.tool.name": name, "gen_ai.tool.type": "function",
             "gen_ai.tool.call.id": call_id if call_id is not None else f"call_{n}", "gen_ai.agent.name": agent,
             "gen_ai.tool.call.arguments": json.dumps(args or {}, ensure_ascii=False, sort_keys=True), "gen_ai.tool.call.result": res or None,
             "error.type": "tool_error" if error else None, "agentest.tool.reason": reason, **(attrs or {})}
        return self._span(f"execute_tool {name}", self._parent(parent), a, error)["spanId"]

    def chat(self, text: str = "", *, parent: str | None = None, calls: list[tuple[str, str, dict]] | None = None, input: str | None = None) -> str:
        """A model call; ``calls`` = [(call_id, tool_name, arguments)] are recorded as ``tool_call`` parts of the output."""
        parts: list[dict] = [{"type": "text", "content": text}] if text else []
        parts += [{"type": "tool_call", "id": i, "name": n, "arguments": a} for i, n, a in calls or []]
        out = json.dumps([{"role": "assistant", "parts": parts}], ensure_ascii=False)
        a = {"gen_ai.operation.name": "chat", "gen_ai.output.messages": out, "gen_ai.input.messages": _msg("user", input) if input is not None else None}
        return self._span("chat", self._parent(parent), a)["spanId"]

    def approval(self, action: str, granted: bool = True, *, approver: str = "human", kind: str = "", data_class: str = "", purpose: str = "", reason: str = "") -> str:
        a = {"agentest.approval.action": action, "agentest.approval.granted": granted, "agentest.approval.approver": approver,
             "agentest.approval.kind": kind or None, "agentest.approval.dataClass": data_class or None, "agentest.approval.purpose": purpose or None,
             "agentest.approval.reason": reason or None}
        return self._span("agentest.approval", self.root_id, a)["spanId"]

    def answer(self, text: str) -> Synth:
        self._answer = text
        return self

    def build(self) -> dict:
        end = self._tick()
        ra = {"gen_ai.operation.name": "invoke_agent" if self.root_agent else "invoke_workflow", "gen_ai.agent.name": self.root_agent,
              "gen_ai.conversation.id": self.conversation or None, "gen_ai.input.messages": _msg("user", self.user),
              "gen_ai.output.messages": _msg("assistant", self._answer), "gen_ai.system_instructions": self._system or None,
              "agentest.input.id": self.input_id, "agentest.run.rep": self.rep, **self.root_attrs}
        root = {"traceId": self.tid, "spanId": self.root_id, "parentSpanId": "",
                "name": f"invoke_agent {self.root_agent}" if self.root_agent else "invoke_workflow demo", "kind": INTERNAL,
                "startTimeUnixNano": str(self._start), "endTimeUnixNano": str(end), "attributes": _attrs(ra), "events": self.events}
        return {"resourceSpans": [{"resource": {"attributes": _attrs({"service.name": self.root_agent or "workflow"})},
                                   "scopeSpans": [{"scope": {"name": "agentest.synth"}, "spans": [root, *self.spans]}]}]}
