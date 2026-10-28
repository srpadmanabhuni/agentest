"""Write the desk_bot_buggy traces: four OTLP/JSON runs, each showing one trajectory defect that only a whole-trace
check sees (stdlib only, deterministic). Run:  python make_traces.py   (writes agents/desk_bot*/traces/*.otlp.jsonl)

  loop      get_ticket -> set_status repeated 3 times with identical arguments, no progress   (X-021)
  thrash    status set open -> closed -> open on the same ticket                             (X-022)
  recursion the triage agent nested in itself 3 deep                                          (X-023)
  drift     status set to closed, a later read still shows open                               (X-024)

desk_bot (the clean build) closes the ticket once and the read-back shows the written status.
"""
import hashlib
import json

T0 = 1_767_225_600_000_000_000  # fixed clock: 2026-01-01T00:00:00Z


def hx(seed, n):
    return hashlib.sha256(seed.encode()).hexdigest()[:n]


def attr(k, v):
    if isinstance(v, bool):
        return {"key": k, "value": {"boolValue": v}}
    if isinstance(v, int):
        return {"key": k, "value": {"intValue": str(v)}}
    return {"key": k, "value": {"stringValue": v if isinstance(v, str) else json.dumps(v, sort_keys=True)}}


def msgs(role, text):
    return [{"role": role, "parts": [{"type": "text", "content": text}]}]


def trace(rid, ask, answer, tools=(), nest=0, svc="desk_bot_buggy"):
    tid, spans, t = hx(rid, 32), [], [T0]

    def span(name, parent, attrs):
        t[0] += 1_000_000
        sid = hx(f"{rid}/{len(spans)}", 16)
        spans.append({"traceId": tid, "spanId": sid, "parentSpanId": parent, "name": name, "startTimeUnixNano": str(t[0]),
                      "endTimeUnixNano": str(t[0] + 500_000), "attributes": [attr(k, v) for k, v in attrs.items()], "status": {"code": 1}})
        return sid

    root = span(f"invoke_agent {svc}", "", {"gen_ai.operation.name": "invoke_agent", "gen_ai.agent.name": svc,
                                                  "gen_ai.conversation.id": f"{rid}#0", "agentest.input.id": rid, "agentest.run.rep": 0,
                                                  "gen_ai.input.messages": msgs("user", ask), "gen_ai.output.messages": msgs("assistant", answer)})
    parent = root
    for _ in range(nest):
        parent = span("invoke_agent triage", parent, {"gen_ai.operation.name": "invoke_agent", "gen_ai.agent.name": "triage"})
    for i, (name, args, result) in enumerate(tools):
        span(f"execute_tool {name}", parent, {"gen_ai.operation.name": "execute_tool", "gen_ai.tool.name": name, "gen_ai.tool.type": "function",
                                              "gen_ai.tool.call.id": f"c{i}", "gen_ai.tool.call.arguments": args, "gen_ai.tool.call.result": result})
    return {"resourceSpans": [{"resource": {"attributes": [attr("service.name", svc)]}, "scopeSpans": [{"spans": spans}]}]}


GET, SET = "get_ticket", "set_status"
OPEN, CLOSED = {"ticket_id": "TCK-41", "status": "open"}, {"ticket_id": "TCK-41", "status": "closed"}
RUNS = [
    trace("loop", "Close ticket TCK-41.", "Ticket TCK-41 is closed.",
          [(GET, {"ticket_id": "TCK-41"}, OPEN), (SET, {"ticket_id": "TCK-41", "status": "closed"}, {"ok": True})] * 3),
    trace("thrash", "Close ticket TCK-41.", "Ticket TCK-41 is closed.",
          [(SET, {"ticket_id": "TCK-41", "status": "open"}, {"ok": True}), (SET, {"ticket_id": "TCK-41", "status": "closed"}, {"ok": True}),
           (SET, {"ticket_id": "TCK-41", "status": "open"}, {"ok": True})]),
    trace("recursion", "Route ticket TCK-41.", "Ticket TCK-41 is routed to the network team.",
          [(GET, {"ticket_id": "TCK-41"}, OPEN)], nest=3),
    trace("drift", "Close ticket TCK-41.", "Ticket TCK-41 is closed.",
          [(SET, {"ticket_id": "TCK-41", "status": "closed"}, {"ok": True}), (GET, {"ticket_id": "TCK-41"}, OPEN)]),
]

CLEAN = [trace("close", "Close ticket TCK-41.", "Ticket TCK-41 is closed.",
               [(GET, {"ticket_id": "TCK-41"}, OPEN), (SET, {"ticket_id": "TCK-41", "status": "closed"}, {"ok": True}),
                (GET, {"ticket_id": "TCK-41"}, CLOSED)], svc="desk_bot")]

if __name__ == "__main__":
    from pathlib import Path
    here = Path(__file__).parent / "agents"
    for name, docs in (("desk_bot_buggy", RUNS), ("desk_bot", CLEAN)):
        (here / name / "traces" / f"{name}.otlp.jsonl").write_text("".join(json.dumps(d, sort_keys=True) + "\n" for d in docs))
