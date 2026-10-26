"""Adapter for RefillAgent's ad-hoc text log (the only code needed to onboard a new framework).

Contract: ``to_trace(raw, ep)`` fills ``ep.messages``, ``ep.tool_calls`` and ``ep.handoffs`` from
``raw["trace"]``. It never decides what is a write, what needs approval or what success means:
the YAML profile does.
"""

import json

from agentest.model.trace import Message, ToolCall


def to_trace(raw: dict, ep) -> None:
    for line in raw.get("trace") or []:
        kind, _, rest = line.partition(" ")
        if kind == "CALL":
            name, _, args = rest.partition(" ")
            ep.tool_calls.append(ToolCall(name=name, arguments=json.loads(args or "{}")))
        elif kind == "RESULT":
            name, status, res = rest.split(" ", 2)
            call = next(c for c in reversed(ep.tool_calls) if c.name == name)
            call.result, call.error = json.loads(res), status != "ok"
        elif kind == "SAY":
            ep.messages.append(Message("assistant", rest))
