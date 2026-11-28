"""Write traces for framework output / structured-result tools (T5-001, T5-018).

    PYTHONPATH=src python tests/fixtures/framework_output_tools/build.py          # rewrite the files
    PYTHONPATH=src python tests/fixtures/framework_output_tools/build.py --check  # exit 1 if a committed file differs

A framework output call is not an agent-chosen tool. These runs differ in how that role is marked, and
in whether a genuinely undeclared tool (or a user tool that only shares the default output-tool name)
is also present. Nothing here calls a model. Edit CASES, run this script, commit the output.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TRACES = HERE / "traces"

# Declared tools do not include the framework output call. A user tool of the same default name is also absent,
# so an unmarked call of that name must still fail T5-001 / T5-018.
TOOLS = {
    "tools": [
        {
            "name": "lookup_account",
            "description": "Look up an account",
            "inputSchema": {"type": "object", "properties": {"id": {"type": "string"}}},
            "annotations": {"title": "lookup account", "readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False},
        },
    ]
}
CARD = {
    "protocolVersion": "0.3.0",
    "name": "bank_support",
    "description": "Support agent used by the framework-output fixtures.",
    "url": "https://agents.example.invalid/bank_support/a2a",
    "version": "1.0.0",
    "capabilities": {"streaming": False},
    "defaultInputModes": ["text/plain"],
    "defaultOutputModes": ["text/plain"],
    "skills": [
        {
            "id": "support",
            "name": "Account support",
            "description": "Look up an account and return a structured reply.",
            "tags": ["support"],
            "examples": ["Look up account A-12"],
            "inputModes": ["text/plain"],
        }
    ],
}

# call: (name, args, result, extra_attrs)
LOOKUP = ("lookup_account", {"id": "A-12"}, {"status": "active", "balance": 40}, {})
OUTPUT_ARGS = {"summary": "Account A-12 is active.", "balance": 40}


def case(id, group, title, expect, *, calls, answer="Account A-12 is active.", framework="", root=None, undeclared=()):
    return {
        "id": id,
        "group": group,
        "title": title,
        "expect": expect,
        "calls": calls,
        "answer": answer,
        "framework": framework,
        "root": dict(root or {}),
        "undeclared": list(undeclared),
        "input": "Look up account A-12 and return a structured summary.",
    }


CASES = [
    case(
        "P01",
        "must-pass",
        "Marked framework output tool is not undeclared",
        "pass",
        calls=[LOOKUP, ("final_result", OUTPUT_ARGS, "Final result processed.", {"agentest__tool__kind": "framework_output"})],
    ),
    case("P02", "must-pass", "Native output-tool result is recognised as the output role without a mark", "pass", calls=[LOOKUP, ("final_result", OUTPUT_ARGS, "Final result processed.", {})]),
    case(
        "P03",
        "must-pass",
        "A renamed output tool marked by the importer is not undeclared",
        "pass",
        calls=[LOOKUP, ("return_fruit", {"name": "banana", "color": "yellow"}, "Final result processed.", {"agentest__tool__kind": "framework_output"})],
    ),
    case(
        "P04",
        "must-pass",
        "An output-function span (logfire.msg) is recognised as the output role",
        "pass",
        calls=[LOOKUP, ("return_fruit", {"name": "banana", "color": "yellow"}, "", {"logfire__msg": "running output function: return_fruit"})],
    ),
    case(
        "P05",
        "must-pass",
        "Default output-tool name with no recorded result, on a typed-output run",
        "pass",
        framework="pydantic-ai",
        root={"final_result": OUTPUT_ARGS},
        calls=[LOOKUP, ("final_result", OUTPUT_ARGS, "", {})],
    ),
    case(
        "P06",
        "must-pass",
        "Default description of the output tool is recognised as the output role",
        "pass",
        calls=[LOOKUP, ("return_vehicle", {"name": "bike", "wheels": 2}, "", {"gen_ai__tool__description": "The final response which ends this conversation"})],
    ),
    case(
        "F01",
        "must-fail",
        "A genuinely undeclared tool still fails when a framework output call is also present",
        "fail",
        calls=[LOOKUP, ("final_result", OUTPUT_ARGS, "Final result processed.", {}), ("secret_wire", {"to": "ops@evil.example"}, {"sent": True}, {})],
        undeclared=["secret_wire"],
    ),
    case(
        "F02",
        "must-fail",
        "A user tool literally named final_result, undeclared and not in the output role, still fails",
        "fail",
        framework="pydantic-ai",
        calls=[LOOKUP, ("final_result", {"account": "A-12"}, "card blocked for account A-12", {})],
        undeclared=["final_result"],
    ),
    case(
        "F03",
        "must-fail",
        "A genuinely undeclared tool with no output call still fails",
        "fail",
        calls=[LOOKUP, ("secret_wire", {"to": "ops@evil.example"}, {"sent": True}, {})],
        undeclared=["secret_wire"],
    ),
    case("G01", "must-pass", "Ordinary declared tools still pass (false-positive guard)", "pass", calls=[LOOKUP]),
]


def trace_doc(c, serial):
    # Import inside the function so --help / collection of the path does not require PYTHONPATH when not building.
    from agentest.standards.emit import TraceBuilder

    t = TraceBuilder(
        "bank_support",
        input_text=c["input"],
        input_id=c["id"],
        framework=c["framework"],
        start_ns=1_700_000_000_000_000_000 + serial * 1_000_000_000,
        step_ns=1_000_000,
        **{k.replace(".", "__"): v for k, v in c["root"].items()},
    )
    for name, args, result, extra in c["calls"]:
        t.tool(name, args, result, **extra)
    t.answer(c["answer"])
    return t.build()


def files():
    out = {HERE / "agent-card.json": json.dumps(CARD, indent=2) + "\n", HERE / "tools.json": json.dumps(TOOLS, indent=2) + "\n"}
    manifest = []
    for k, c in enumerate(CASES, 1):
        name = f"{c['id']}-{c['group']}.otlp.jsonl"
        out[TRACES / name] = json.dumps(trace_doc(c, k), separators=(",", ":"), ensure_ascii=False) + "\n"
        manifest.append({"id": c["id"], "file": f"traces/{name}", "group": c["group"], "title": c["title"], "expect": c["expect"], "undeclared": c["undeclared"]})
    out[HERE / "manifest.json"] = json.dumps({"checks": ["T5-001", "T5-018"], "fixtures": manifest}, indent=2) + "\n"
    return out


def main(argv):
    want = files()
    if "--check" in argv:
        stale = [p.name for p, text in want.items() if not p.exists() or p.read_text(encoding="utf-8") != text]
        stale += [p.name for p in TRACES.glob("*.jsonl") if p not in want]
        if stale:
            print("out of date:", ", ".join(stale))
            return 1
        return 0
    TRACES.mkdir(exist_ok=True)
    for p in TRACES.glob("*.jsonl"):
        p.unlink()
    for p, text in want.items():
        p.write_text(text, encoding="utf-8")
    print(f"wrote {len(want)} files, {len(CASES)} fixtures")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
