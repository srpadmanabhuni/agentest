"""Standard agent trace format (v2.0.0-dev).

Field names follow the OpenTelemetry GenAI semantic conventions where a
counterpart exists (https://opentelemetry.io/docs/specs/semconv/gen-ai/ ;
spans ``invoke_agent`` / ``execute_tool``, attributes ``gen_ai.tool.name``,
``gen_ai.tool.call.arguments``, ``gen_ai.tool.call.result``,
``gen_ai.agent.name``, ``gen_ai.operation.name``). Those conventions are still
marked *Development* upstream, so the mapping is recorded in
``OTEL_MAPPING`` rather than baked into field names. The JSON Schema is in
``trace.schema.json`` next to this file.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

SCHEMA_PATH = Path(__file__).with_name("trace.schema.json")
SIDE_EFFECTS = ("read", "write", "unknown")

OTEL_MAPPING = {
    "Episode": "span gen_ai.operation.name=invoke_agent",
    "Episode.agent": "gen_ai.agent.name",
    "Message.role": "gen_ai input/output message role",
    "ToolCall": "span gen_ai.operation.name=execute_tool",
    "ToolCall.name": "gen_ai.tool.name",
    "ToolCall.arguments": "gen_ai.tool.call.arguments",
    "ToolCall.result": "gen_ai.tool.call.result",
    "ToolCall.call_id": "gen_ai.tool.call.id",
    "ToolCall.actor": "gen_ai.agent.name (of the calling agent)",
    "ToolCall.side_effect": "no OTel attribute (agentest extension)",
    "Approval/Handoff/StateChange": "no OTel attribute (agentest extension, emitted as span events)",
}


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
    side_effect: str = "unknown"  # read | write | unknown (filled from the profile)
    actor: str = ""
    call_id: str = ""
    error: bool = False


@dataclass
class StateChange:
    kind: str  # executed | pending | unapproved (executed before any human step) | diff (store key changed)
    effect: str  # e.g. refund, send_email, payment
    data: Any = None


@dataclass
class Approval:
    action: str
    granted: bool
    approver: str = ""
    target: str = ""
    policy_version: str = ""


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

    def writes(self) -> list[ToolCall]:
        """Tool calls classified as writes."""
        return [c for c in self.tool_calls if c.side_effect == "write"]

    def executed(self) -> list[StateChange]:
        return [s for s in self.state_changes if s.kind in ("executed", "unapproved")]

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> Episode:
        d = dict(d)
        d["messages"] = [Message(**m) for m in d.get("messages", [])]
        d["tool_calls"] = [ToolCall(**c) for c in d.get("tool_calls", [])]
        d["state_changes"] = [StateChange(**s) for s in d.get("state_changes", [])]
        d["approvals"] = [Approval(**a) for a in d.get("approvals", [])]
        d["handoffs"] = [Handoff(**h) for h in d.get("handoffs", [])]
        return cls(**d)


def schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text())


def validate(d: dict, sch: dict | None = None, path: str = "$") -> list[str]:
    """Minimal JSON-Schema (draft 2020-12 subset: type/required/properties/items/enum) validator, no dependency."""
    sch = sch or schema()
    defs = schema().get("$defs", {})
    if "$ref" in sch:
        sch = defs[sch["$ref"].split("/")[-1]]
    errs: list[str] = []
    types = sch.get("type")
    tmap = {"object": dict, "array": list, "string": str, "integer": int, "boolean": bool, "null": type(None), "number": (int, float)}
    if types:
        tl = types if isinstance(types, list) else [types]
        if not any(isinstance(d, tmap[t]) for t in tl if t in tmap) and "any" not in tl:
            return [f"{path}: expected {types}"]
    if "enum" in sch and d not in sch["enum"]:
        errs.append(f"{path}: {d!r} not in {sch['enum']}")
    if isinstance(d, dict):
        for r in sch.get("required", []):
            if r not in d:
                errs.append(f"{path}: missing {r}")
        for k, s in sch.get("properties", {}).items():
            if k in d:
                errs += validate(d[k], s, f"{path}.{k}")
    if isinstance(d, list) and "items" in sch:
        for i, x in enumerate(d):
            errs += validate(x, sch["items"], f"{path}[{i}]")
    return errs
