"""Write the roll-up span fixtures: one run per file, recorded as OpenTelemetry GenAI spans.

    python tests/fixtures/rollup_spans/build.py          # rewrite the files
    python tests/fixtures/rollup_spans/build.py --check  # exit 1 if a committed file differs

Some instrumentations add one more ``execute_tool`` span after parallel tool calls, an aggregate of calls that already
have spans of their own. It is not a call and must not be judged as one. These runs pair that span with declared and
undeclared real tools. ``expect`` maps a check id to the verdict it must return. Nothing here calls a model.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TRACES = HERE / "traces"

TOOLS = {"tools": [
    {"name": n, "description": d, "inputSchema": {"type": "object", "properties": {p: {"type": "string"} for p in props}},
     "annotations": {"title": n.replace("_", " "), "readOnlyHint": ro, "destructiveHint": False, "idempotentHint": ro, "openWorldHint": False}}
    for n, d, props, ro in [("get_weather", "Weather for a city", ["city"], True), ("get_time", "Local time for a city", ["city"], True),
                            ("book_slot", "Book a calendar slot", ["slot"], False)]]}
CARD = {"protocolVersion": "0.3.0", "name": "trip_agent", "description": "Trip assistant used by the roll-up span fixtures.",
        "url": "https://agents.example.invalid/trip_agent/a2a", "version": "1.0.0",
        "capabilities": {"streaming": False}, "defaultInputModes": ["text/plain"], "defaultOutputModes": ["text/plain"],
        "skills": [{"id": "trip", "name": "Trip help", "description": "Weather and time for a city.", "tags": ["travel"],
                    "examples": ["Weather and time in Paris"], "inputModes": ["text/plain"]}]}

# a merged span as an instrumentation writes it: a placeholder tool name, no arguments, the joined response as an attribute
MERGED = {"name": "(merged tools)", "span": "execute_tool (merged)", "args": "N/A"}


def case(id, group, title, calls, *, merged=None, user_input=None, empty_input=False, rollups=0, expect):
    """``rollups`` is how many of the run's spans the reader must set aside as roll-ups (the merged span, when it is one)."""
    return {"id": id, "group": group, "title": title, "calls": calls, "merged": merged, "input": user_input, "empty": empty_input,
            "rollups": rollups, "expect": expect}


PAIR = [("get_weather", {"city": "Paris"}, '{"temp_c": 14}'), ("get_time", {"city": "Paris"}, '{"time": "10:05"}')]
CASES = [
    case("R01", "rollup", "Two parallel real calls plus a merged-tools span, no user text recorded", PAIR, merged=dict(MERGED),
         rollups=1, expect={"T5-001": "pass", "T5-018": "pass", "T1-007": "pass"}),
    case("R02", "rollup", "Same run with a user message recorded: T1-007 has no empty input to judge", PAIR, merged=dict(MERGED), user_input="Weather and time in Paris",
         rollups=1, expect={"T5-001": "pass", "T5-018": "pass", "T1-007": "n/a"}),
    case("R03", "rollup", "A roll-up marked by the generic attribute, with a name no table lists", PAIR,
         merged={"name": "(turn summary)", "span": "execute_tool (turn summary)", "args": "{\"calls\": 2}", "marker": True},
         rollups=1, expect={"T5-001": "pass", "T5-018": "pass", "T1-007": "pass"}),
    case("R04", "control", "The same run without any roll-up span (the control)", PAIR,
         expect={"T5-001": "pass", "T5-018": "pass", "T1-007": "pass"}),
    case("U01", "undeclared", "A genuinely undeclared tool beside the merged-tools span still fails", PAIR + [("wipe_calendar", {"scope": "all"}, '{"ok": true}')],
         merged=dict(MERGED), rollups=1, expect={"T5-001": "fail", "T5-018": "fail", "T1-007": "fail"}),
    case("U02", "undeclared", "A real tool that happens to be named like the placeholder, with arguments, is still a call", PAIR,
         merged={"name": "(merged tools)", "span": "execute_tool (merged tools)", "args": "{\"city\": \"Paris\"}"},
         expect={"T5-001": "fail", "T5-018": "fail", "T1-007": "fail"}),
    case("U03", "undeclared", "A span that says it is not a roll-up is judged as a tool", PAIR,
         merged={"name": "(turn summary)", "span": "execute_tool (turn summary)", "args": "N/A", "marker": False},
         expect={"T5-001": "fail", "T5-018": "fail", "T1-007": "fail"}),
    case("E01", "empty-input", "A recorded empty message with a state-changing call still fails T1-007", PAIR + [("book_slot", {"slot": "10:00"}, '{"booked": true}')],
         merged=dict(MERGED), empty_input=True, rollups=1, expect={"T5-001": "pass", "T5-018": "pass", "T1-007": "fail"}),
]


def _attr(k, v):
    if isinstance(v, bool):
        return {"key": k, "value": {"boolValue": v}}
    return {"key": k, "value": {"stringValue": v if isinstance(v, str) else json.dumps(v, separators=(", ", ": "))}}


def _msg(role, text):
    return json.dumps([{"role": role, "parts": [{"type": "text", "content": text}]}])


def trace_doc(c, k):
    tid = f"{k:032x}"
    ids = iter(f"{k:04x}{i:012x}" for i in range(1, 99))
    root_id, chat_id, t = next(ids), next(ids), 1_000_000_000_000 + k * 1_000_000_000
    parts = [{"type": "tool_call", "id": f"call_{i}", "name": n, "arguments": a} for i, (n, a, _) in enumerate(c["calls"])]
    spans = [{"traceId": tid, "spanId": chat_id, "parentSpanId": root_id, "name": "chat model", "startTimeUnixNano": str(t + 1_000_000),
              "endTimeUnixNano": str(t + 2_000_000),
              "attributes": [_attr("gen_ai.operation.name", "chat"), _attr("gen_ai.output.messages", json.dumps([{"role": "assistant", "parts": parts}]))]}]
    for i, (n, a, res) in enumerate(c["calls"]):
        spans.append({"traceId": tid, "spanId": next(ids), "parentSpanId": root_id, "name": f"execute_tool {n}",
                      "startTimeUnixNano": str(t + 3_000_000 + i), "endTimeUnixNano": str(t + 4_000_000 + i),
                      "attributes": [_attr("gen_ai.operation.name", "execute_tool"), _attr("gen_ai.tool.name", n), _attr("gen_ai.tool.call.id", f"call_{i}"),
                                     _attr("gen_ai.tool.call.arguments", a), _attr("gen_ai.tool.call.result", res)]})
    m = c["merged"]
    if m:
        a = [_attr("gen_ai.operation.name", "execute_tool"), _attr("gen_ai.tool.name", m["name"]), _attr("gen_ai.tool.description", m["name"]),
             _attr("gen_ai.tool.call.id", f"event_{k}"), _attr("gen_ai.tool.call.arguments", m["args"]),
             _attr("gen_ai.tool.call.result", json.dumps({"responses": [r for _, _, r in c["calls"]]}))]
        if "marker" in m:
            a.append(_attr("agentest.span.rollup", m["marker"]))
        spans.append({"traceId": tid, "spanId": next(ids), "parentSpanId": root_id, "name": m["span"],
                      "startTimeUnixNano": str(t + 5_000_000), "endTimeUnixNano": str(t + 5_500_000), "attributes": a})
    attrs = [_attr("gen_ai.operation.name", "invoke_agent"), _attr("gen_ai.agent.name", "trip_agent"), _attr("gen_ai.conversation.id", c["id"]),
             _attr("gen_ai.output.messages", _msg("assistant", "It is 14 C and 10:05 in Paris."))]
    if c["input"] is not None or c["empty"]:
        attrs.append(_attr("gen_ai.input.messages", _msg("user", c["input"] or "")))
    root = {"traceId": tid, "spanId": root_id, "parentSpanId": "", "name": "invoke_agent trip_agent", "startTimeUnixNano": str(t),
            "endTimeUnixNano": str(t + 6_000_000), "attributes": attrs}
    return {"resourceSpans": [{"resource": {"attributes": [_attr("service.name", "trip_agent")]}, "schemaUrl": "https://opentelemetry.io/schemas/1.42.0",
                               "scopeSpans": [{"scope": {"name": "rollup-fixtures", "version": "recorded"}, "spans": [root] + spans}]}]}


def files():
    out = {HERE / "agent-card.json": json.dumps(CARD, indent=2) + "\n", HERE / "tools.json": json.dumps(TOOLS, indent=2) + "\n"}
    manifest = []
    for k, c in enumerate(CASES, 1):
        name = f"{c['id']}-{c['group']}.otlp.jsonl"
        out[TRACES / name] = json.dumps(trace_doc(c, k), separators=(",", ":"), ensure_ascii=False) + "\n"
        manifest.append({"id": c["id"], "file": f"traces/{name}", "group": c["group"], "title": c["title"], "expect": c["expect"],
                         "rollups": c["rollups"]})
    out[HERE / "manifest.json"] = json.dumps({"checks": ["T5-001", "T5-018", "T1-007"], "fixtures": manifest}, indent=2) + "\n"
    return out


def main(argv):
    want = files()
    if "--check" in argv:
        stale = [p.name for p, text in want.items() if not p.exists() or p.read_text(encoding="utf-8") != text]
        if stale:
            print("stale:", ", ".join(stale))
        return 1 if stale else 0
    TRACES.mkdir(parents=True, exist_ok=True)
    for p, text in want.items():
        p.write_text(text, encoding="utf-8")
    print(f"wrote {len(want)} files")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
