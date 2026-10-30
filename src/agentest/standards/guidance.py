"""Actionable report guidance (presentation only: never changes a status or a detail).

* ``fail``: the rule that was broken (its ``what`` text), where it happened (trace / span ids located from the
  input id and tool name the detail names), and a suggested fix (the catalogue acceptance criterion, else the rule).
* ``n/a``: which evidence or field is missing and how to supply it, from the n/a detail matched against
  :data:`FAMILIES`, falling back to the per-check table ``guidance.json`` (``scripts/gen_guidance.py``).

Nothing here names an agent, a tool or a framework.
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

# (pattern over the n/a detail, missing evidence / field, how to supply it). First match wins; order matters.
FAMILIES: list[tuple[str, str, str]] = [
    (r"harness-set reason|tool calls to score", "agentest.tool.reason (model-written, per call)",
     "record the model's own rationale for each tool call (the text it wrote next to the call) as agentest.tool.reason "
     "or a 'reason' argument; one fixed harness string does not count"),
    (r"relation members|counterfactual group|language relation", "agentest.input.relations (root span)",
     "run the related inputs (paraphrase / counterfactual / language variants) and declare them in the import map "
     "labels.relations, or set agentest.input.relations on each root span"),
    (r"\binput\b|inputs\b", "agentest.input.families (root span) for a test input of this kind",
     "add a test input of the kind named in the detail (e.g. injection, empty, read-only, repeated, PII, social) and "
     "label it with agentest.input.families (import map labels.inputs)"),
    (r"AgentCard|publishes no|declares no|declared|declares a|tool declares|no tools declared|actor roles published|"
     r"TTL published|recipient allowlist", "AgentCard / tools.json metadata",
     "publish the named field: AgentCard skills, capabilities and the agentest governance extension, or MCP tool "
     "annotations in tools.json (readOnlyHint, destructiveHint, idempotentHint, inputSchema enums); see templates/"),
    (r"no tool calls|arguments recorded|string tool arguments", "execute_tool spans with gen_ai.tool.call.arguments",
     "emit one execute_tool span per call with gen_ai.tool.name, gen_ai.tool.call.arguments and gen_ai.tool.call.result"),
    (r"approval|denied|decision", "agentest.approval spans",
     "record each human or policy decision as an agentest.approval span (granted, approver, policy_version, reason)"),
    (r"hand-?off|nested agent", "invoke_agent child spans with gen_ai.agent.name",
     "emit an invoke_agent span per sub-agent (gen_ai.agent.name) under the caller's span"),
    (r"gen_ai\.usage|tokens", "gen_ai.usage.input_tokens / output_tokens on chat spans",
     "emit a chat span per model call with gen_ai.usage.input_tokens and gen_ai.usage.output_tokens"),
    (r"duration|chat/agent spans", "span start / end times and chat spans",
     "emit chat and invoke_agent spans with real start and end timestamps"),
    (r"multi-turn|conversation", "gen_ai.conversation.id across traces",
     "record each turn as its own trace and share one gen_ai.conversation.id across the turns"),
    (r"failed|failure|timeout", "error.type on the failing tool span",
     "set error.type (and span status ERROR) on tool spans that fail; include a run where a step fails"),
    (r"repl(y|ies)|answers", "gen_ai.output.messages on the root span",
     "record the agent's final reply as gen_ai.output.messages"),
    (r"system instructions", "gen_ai.system_instructions",
     "record the system instructions on the chat span (gen_ai.system_instructions)"),
]
APPLICABILITY = ("a run where this situation occurs",
                 "the traces carry the needed fields, but no recorded run exercises this situation; add a test input "
                 "that does (see the check's doc in docs/tests/<ID>.md)")


@lru_cache(maxsize=1)
def table() -> dict:
    return json.loads((Path(__file__).parent / "guidance.json").read_text())["checks"]


def missing(detail: str) -> tuple[str, str] | None:
    d = detail.split("no standard signal:", 1)[-1]
    for pat, field, how in FAMILIES:
        if re.search(pat, d, re.I):
            return field, how
    return None


_LOC = re.compile(r"([A-Za-z0-9_.\-]+)(?:#(\d+))?:([A-Za-z0-9_.\-]+)")


def locate(detail: str, runs: list | None) -> list[dict]:
    """Trace / span ids for the (input id[#rep]:tool) references in a fail detail; [] when it names none."""
    out: list[dict] = []
    for inp, rep, tool in _LOC.findall(detail or ""):
        for r in runs or []:
            if r.input_id != inp or (rep and str(r.rep) != rep):
                continue
            for s in r.spans:
                if s.get("tool") == tool or s.get("name") == tool:
                    loc = {"input": inp, "rep": r.rep, "tool": tool, "span_id": s.get("id", "")}
                    if loc not in out:
                        out.append(loc)
                    break
        if len(out) >= 5:
            break
    if not out:  # the detail names an input but no tool span: point at that run's root span
        for inp in dict.fromkeys(re.findall(r"([A-Za-z0-9_.\-]+)(?:#\d+)?:", detail or "")):
            for r in runs or []:
                if r.input_id == inp:
                    rid = next((s.get("id", "") for s in r.spans if not s.get("parent")), "")
                    out.append({"input": inp, "rep": r.rep, "tool": "(run)", "span_id": rid})
                    break
            if len(out) >= 5:
                break
    return out


def guide(tid: str, cell: dict, runs: list | None = None) -> dict | None:
    t = table().get(tid, {})
    if cell.get("status") == "fail":
        where = locate(cell.get("detail", ""), runs)
        return {"rule": t.get("rule", ""), "where": where or "agent-level finding (no single span)", "fix": t.get("fix", "")}
    if cell.get("status") == "n/a":
        m = missing(cell.get("detail", ""))
        if m is None and t.get("needs"):
            m = (t["needs"][0]["field"], t["needs"][0]["how"])
        field, how = m or APPLICABILITY
        return {"missing": field, "how": how}
    return None


def annotate(res: dict, runs: dict | None = None) -> dict:
    """A copy of ``res`` with a ``guide`` entry on fail and n/a cells. Status and detail are untouched."""
    out = {}
    for a, row in res.items():
        out[a] = {}
        for i, c in row.items():
            g = guide(i, c, (runs or {}).get(a))
            out[a][i] = {**c, "guide": g} if g else dict(c)
    return out


def text(g: dict) -> str:
    if "missing" in g:
        return f"missing: {g['missing']}. How: {g['how']}"
    w = g["where"]
    where = w if isinstance(w, str) else "; ".join(f"{x['input']}#{x['rep']}:{x['tool']} span {x['span_id']}" for x in w)
    return f"where: {where}. Rule: {g['rule']} Fix: {g['fix']}"
