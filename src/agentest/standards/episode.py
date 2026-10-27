"""In-memory form of one agent run, used only while importing native logs into OTLP (see :mod:`importers`)
and by the test-owned scenario oracles. Rules never read it: they read :class:`agentest.standards.otel.Run`,
built from OTLP spans."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Message:
    role: str  # user | assistant | tool | system
    content: str
    actor: str = ""


@dataclass
class ToolCall:
    name: str
    arguments: dict[str, Any] = field(default_factory=dict)
    result: Any = None
    side_effect: str = "unknown"  # read | write | unknown (from MCP readOnlyHint)
    actor: str = ""
    call_id: str = ""
    error: bool = False


@dataclass
class StateChange:
    kind: str  # executed | pending | unapproved (executed before any human step) | diff (store key changed)
    effect: str
    data: Any = None


@dataclass
class Approval:
    action: str
    granted: bool
    approver: str = ""
    target: str = ""
    policy_version: str = ""
    reason: str = ""


@dataclass
class Handoff:
    source: str
    target: str


@dataclass
class Episode:
    agent: str
    probe: str
    rep: int = 0
    input: str = ""
    messages: list[Message] = field(default_factory=list)
    tool_calls: list[ToolCall] = field(default_factory=list)
    state_changes: list[StateChange] = field(default_factory=list)
    approvals: list[Approval] = field(default_factory=list)
    handoffs: list[Handoff] = field(default_factory=list)
    final_answer: str = ""
    final_state: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    framework: str = ""
    events: list[Any] = field(default_factory=list)
    duration_s: float | None = None
    conversation: str = ""  # native session / thread id, if the log has one

    # -- helpers for user mapping functions (``--dialect file:my_mapping.py``), so they need no agentest import
    def add_tool(self, name: str, arguments: dict | None = None, result: Any = None, error: bool = False, actor: str = "", call_id: str = "") -> ToolCall:
        c = ToolCall(name=name, arguments=dict(arguments or {}), result=result, actor=actor, call_id=call_id, error=error)
        self.tool_calls.append(c)
        return c

    def say(self, text: str, actor: str = "") -> None:
        self.messages.append(Message("assistant", text, actor))

    def handoff(self, source: str, target: str) -> None:
        self.handoffs.append(Handoff(source, target))

    def approval(self, action: str, granted: bool, approver: str = "", target: str = "", policy_version: str = "", reason: str = "") -> None:
        self.approvals.append(Approval(action, granted, approver, target, policy_version, reason))
