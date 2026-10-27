"""Per-rule standard-fields table (agent-independence audit item 4).

Parses src/agentest/standards/rules.py, follows each @rule function through the module helpers and Ctx methods it
calls, and lists the standard fields it reads. Fields marked EXT come from the optional agentest governance extension
or agentest.* span attributes (no standard equivalent). Usage: python scripts/rule_fields.py [--md OUT] [--json OUT]
"""

from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src" / "agentest" / "standards" / "rules.py"

RUN = {  # Run / ToolSpan attribute -> standard source (see standards/otel.py from_otlp)
    "input": "OTel gen_ai.input.messages (root)", "answer": "OTel gen_ai.output.messages (root)",
    "tools": "OTel execute_tool spans (gen_ai.tool.name)", "args": "OTel gen_ai.tool.call.arguments",
    "result": "OTel gen_ai.tool.call.result", "error": "OTel span status / error.type",
    "actor": "OTel gen_ai.agent.name (ancestor invoke_agent)", "chats": "OTel chat spans gen_ai.output.messages",
    "handoffs": "OTel invoke_agent span tree (+EXT agentest.handoff.source)", "duration_s": "OTel span start/end time",
    "times": "OTel span start/end time", "span_blobs": "OTel all span attributes", "evaluations": "OTel gen_ai.evaluation.result events",
    "approvals": "EXT agentest.approval.* span events", "effects": "EXT agentest.state_change span events",
    "final_state": "EXT agentest.final_state (root)", "call_id": "OTel gen_ai.tool.call.id",
    "batches": "OTel chat span gen_ai.output.messages (tool_call parts per response)", "t1": "OTel span start/end time",
    "t0": "OTel span start/end time", "conversation": "OTel gen_ai.conversation.id",
    "attachments": "OTel gen_ai.input.messages (uri / blob / file parts)",
}
META = {
    "is_write": "MCP annotations.readOnlyHint", "is_destructive": "MCP annotations.destructiveHint",
    "ann": "MCP tool annotations", "card": "A2A AgentCard", "tools": "MCP tools/list",
}
CTX = {"gated": "EXT governance.approval.required", "host_gated": "EXT governance.approval.hostGated",
       "restricted": "EXT governance.dataClassification.restricted (default card/PAN)",
       "canaries": "A2A skills.examples + MCP inputSchema (generated canaries)",
       "fam": "A2A skills / MCP inputSchema (generated input families)", "writes": "MCP annotations.readOnlyHint",
       "ok_writes": "MCP annotations.readOnlyHint"}


def analyse() -> list[dict]:
    tree = ast.parse(SRC.read_text())
    funcs = {n.name: n for n in tree.body if isinstance(n, ast.FunctionDef)}
    for n in tree.body:
        if isinstance(n, ast.ClassDef) and n.name == "Ctx":
            funcs.update({f"Ctx.{m.name}": m for m in n.body if isinstance(m, ast.FunctionDef)})

    def direct(fn) -> tuple[set, set]:
        fields, calls = set(), set()
        for x in ast.walk(fn):
            if isinstance(x, ast.Attribute):
                if x.attr in CTX and isinstance(x.value, ast.Name) and x.value.id in ("c", "self"):
                    fields.add(CTX[x.attr])
                    calls.add(f"Ctx.{x.attr}")
                elif x.attr in RUN and not (isinstance(x.value, ast.Name) and x.value.id == "c"):
                    fields.add(RUN[x.attr])
                elif x.attr in META and isinstance(x.value, ast.Attribute) and x.value.attr == "a":
                    fields.add(META[x.attr])
                elif x.attr == "g" and isinstance(x.value, ast.Attribute) and x.value.attr == "a":
                    pass
                elif isinstance(x.value, ast.Name) and x.value.id == "I":
                    fields.add("A2A skills.examples/tags + MCP inputSchema (generated inputs)")
            if isinstance(x, ast.Call):
                f = x.func
                if isinstance(f, ast.Attribute) and f.attr == "g" and x.args and isinstance(x.args[0], ast.Constant):
                    fields.add("EXT governance." + ".".join(str(a.value) for a in x.args if isinstance(a, ast.Constant)))
                if isinstance(f, ast.Name) and f.id in funcs:
                    calls.add(f.id)
            if isinstance(x, ast.Constant) and x.value in ("user.roles", "enduser.roles"):
                fields.add("OTel user.roles / enduser.roles (root)")
            if isinstance(x, ast.Constant) and isinstance(x.value, str) and x.value.startswith(("gen_ai.", "agentest.")) and " " not in x.value:
                fields.add(("OTel " if x.value.startswith("gen_ai.") else "EXT ") + x.value)
        return fields, calls

    memo: dict[str, set] = {}

    def closure(name: str, seen=()) -> set:
        if name in memo:
            return memo[name]
        if name in seen or name not in funcs:
            return set()
        f, calls = direct(funcs[name])
        for c in calls:
            f |= closure(c, seen + (name,))
        memo[name] = f
        return f

    out = []
    for name, fn in funcs.items():
        for d in fn.decorator_list:
            if isinstance(d, ast.Call) and getattr(d.func, "id", "") == "rule":
                ids = [a.value for a in d.args if isinstance(a, ast.Constant)]
                what = next((k.value.value for k in d.keywords if k.arg == "what"), "")
                fields = sorted(closure(name))
                for i in ids:
                    out.append({"id": i, "function": name, "what": what, "fields": fields,
                                "standard": [f for f in fields if not f.startswith("EXT")],
                                "extension": [f for f in fields if f.startswith("EXT")]})
    from agentest.standards.rules import RULES

    have = {r["id"] for r in out}
    so = ["EXT agentest.final_state (root)", "OTel gen_ai.input.messages (root)"]
    for i, (what, _) in RULES.items():
        if i not in have:
            out.append({"id": i, "function": "_scenario_only", "what": what, "fields": so, "standard": so[1:], "extension": so[:1]})
    from agentest.standards.catalog import ALL_IDS

    return sorted((r for r in out if r["id"] in ALL_IDS), key=lambda r: r["id"])


def to_md(rows: list[dict]) -> str:
    ext = sum(1 for r in rows if r["extension"])
    std_only = sum(1 for r in rows if not r["extension"])
    lines = [f"Rules: {len(rows)} IDs; {std_only} read only standard fields; {ext} also read the extension (flagged EXT).", "",
             "| ID | standard fields read | extension fields (EXT) |", "|---|---|---|"]
    for r in rows:
        lines.append(f"| {r['id']} | {'<br>'.join(r['standard']) or '-'} | {'<br>'.join(x[4:] for x in r['extension']) or '-'} |")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--md")
    ap.add_argument("--json")
    a = ap.parse_args()
    rows = analyse()
    if a.json:
        Path(a.json).write_text(json.dumps(rows, indent=1))
    md = to_md(rows)
    if a.md:
        Path(a.md).write_text(md)
    else:
        print(md)
