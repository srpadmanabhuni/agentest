"""Mapping for RefillAgent's ad-hoc text log -> OTel GenAI spans (used by ``agentest std import --dialect file:refill_log.py``).

This is the only code needed to onboard a framework that has no OpenTelemetry instrumentation. It maps fields; it never
decides what is a write, what needs approval or what success means (the MCP tool annotations and the rules do).
It needs no agentest import: ``ep`` offers ``add_tool``, ``say``, ``handoff`` and ``approval``.
"""

import json


def to_trace(raw: dict, ep) -> None:
    for line in raw.get("trace") or []:
        kind, _, rest = line.partition(" ")
        if kind == "CALL":
            name, _, args = rest.partition(" ")
            ep.add_tool(name, json.loads(args or "{}"))
        elif kind == "RESULT":
            name, status, res = rest.split(" ", 2)
            call = next(c for c in reversed(ep.tool_calls) if c.name == name)
            call.result, call.error = json.loads(res), status != "ok"
        elif kind == "SAY":
            ep.say(rest)
