"""One-off migration: v2 YAML profiles -> standard agent metadata (agents/<id>/).

Only the declarative, agent-describing parts of a v2 profile are carried over:
tools -> MCP tool descriptors with annotations; approvals, data classes, limits,
tenancy, prerequisites -> the governance AgentCard extension; probe roles ->
inputs.json families; observations -> adapter.json (log-to-span mapping only).
v2 ``expect`` / ``applies`` / ``defs`` / ``metamorphic_key`` (per-agent test logic)
are deliberately DROPPED.

Usage (needs a v2.0.0 checkout, which still has profiles/ and agentest.model.runner):
    git worktree add /tmp/v2 v2.0.0 && PYTHONPATH=/tmp/v2/src python scripts/v3_convert.py --profiles /tmp/v2/profiles --out agents
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
from pathlib import Path

from agentest.model.runner import native_episodes, traces

from agentest.model.profile import load_all
from agentest.standards import GOV_EXT

OPEN_WORLD = re.compile(r"send|email|mail|post|publish|pay|web|search|http|fetch|slack|notify|sms|tweet|upload|webhook", re.I)
JSON_T = {str: "string", int: "integer", float: "number", bool: "boolean", list: "array", dict: "object"}


def _schema(samples: list[dict]) -> dict:
    props: dict[str, dict] = {}
    for a in samples:
        for k, v in a.items():
            t = JSON_T.get(type(v), "string")
            props.setdefault(k, {"type": t})
    return {"type": "object", "properties": props}


def convert(p, out: Path) -> None:
    d = out / p.agent
    d.mkdir(parents=True, exist_ok=True)
    try:
        eps = traces(p)
    except Exception:  # pragma: no cover - recording failure is reported by the runner
        eps = []
    args: dict[str, list[dict]] = {}
    actors: dict[str, set] = {}
    for e in eps:
        for c in e.tool_calls:
            args.setdefault(c.name, []).append(c.arguments if isinstance(c.arguments, dict) else {})
        for k, v in ((e.final_state.get("extra") or {}).get("agents") or {}).items() if isinstance(e.final_state.get("extra"), dict) else []:
            if isinstance(v, list):
                actors.setdefault(k, set()).update(v)
    tools = []
    for name, side in sorted(p.tools.items()):
        ro = side == "read"
        tools.append({"name": name, "description": f"{name} ({'read-only' if ro else 'state-changing'})",
                      "inputSchema": _schema(args.get(name, [])),
                      "annotations": {"title": name.replace("_", " "), "readOnlyHint": ro, "destructiveHint": not ro,
                                      "idempotentHint": ro, "openWorldHint": bool(OPEN_WORLD.search(name))}})
    gov = {
        "approval": {"required": sorted(p.approval_required), "hostGated": bool(p.observations.get("executed"))},
        "dataClassification": {"restricted": sorted(p.sensitive)},
        "recipients": {"allow": list(p.allowed_recipients)},
        "limits": dict(p.limits),
        "tenancy": ({"sessionTenant": p.tenant.get("session"), "argument": p.tenant.get("key", "tenant_id")} if p.tenant.get("session") else {}),
        "prerequisites": {k: list(v) for k, v in p.depends_on.items()},
        "disclosureTools": list(p.disclosure_tools), "exportTools": list(p.export_tools),
        "roles": {"orchestrators": list(p.orchestrators), "actors": {k: sorted(v) for k, v in sorted(actors.items())}},
        "capabilities": {k: bool(v) for k, v in p.capabilities.items()},
        "languages": list(p.languages),
        "slo": {"successRate": float(p.tsr_threshold)},
        "postconditions": {"default": list(p.success), "byInput": dict(p.success_by_probe)},
    }
    gov = {k: v for k, v in gov.items() if v not in ({}, [], None)}
    canon = [x for x in p.probes.get("canonical", []) if x != "*"]
    examples = []
    for e in eps:
        if e.probe in canon and e.input and e.input not in examples:
            examples.append(e.input)
    card = {
        "protocolVersion": "0.3.0", "name": p.agent, "description": re.sub(r"\s*\b(T[1-7]|X)-\d{3}\b", "", (p.notes or f"{p.framework} reference agent {p.agent}")).strip()[:300],
        "url": f"https://agents.example.invalid/{p.agent}/a2a", "preferredTransport": "JSONRPC", "version": "1.0.0",
        "capabilities": {"streaming": False, "pushNotifications": False,
                         "extensions": [{"uri": GOV_EXT, "description": "agentest governance facts (non-standard; docs/standards/EXTENSION.md)",
                                         "required": False, "params": gov}]},
        "defaultInputModes": ["text/plain"], "defaultOutputModes": ["text/plain", "application/json"],
        "skills": [{"id": f"{p.agent}-main", "name": f"{p.agent} main task", "description": f"Primary task of {p.agent} ({p.framework}).",
                    "tags": [t for t in [p.framework, *p.languages] if t], "examples": examples[:3], "inputModes": ["text/plain"]}],
    }
    inputs: dict[str, dict] = {}
    for role, names in p.probes.items():
        if role == "metamorphic":
            continue
        fam = {"approval_scope": "approval_scope", "pii_masking": "pii", "pii_disclosure": "pii_disclosure",
               "tenant_export": "tenant_export", "prereq": "prereq"}.get(role, role)
        for n in names:
            if n != "*":
                inputs.setdefault(n, {"families": []})["families"].append(fam)
    rel = [{"relation": "declared", "members": list(pair), "kind": "same"} for pair in p.probes.get("metamorphic", [])]
    obs = dict(p.observations)
    if p.adapter == "events" and any("check_passed" in (e.final_state.get("extra") or {}) for e in eps):
        obs["evaluation"] = ["extra.check_passed"]
    adapter = {"dialect": p.adapter, "framework": p.framework, "observations": obs, "episodes": p.episodes}
    if p.adapter == "events":
        card["defaultOutputModes"] = ["application/json"]
    if p.adapter.startswith("file:"):
        src = Path(p.source).parent / p.adapter[5:]
        shutil.copy(src, d / src.name)
        adapter["dialect"] = f"file:{src.name}"
    if p.episodes:
        base = Path(p.source).parent
        files = sorted(base.glob(p.episodes))
        for f in files:
            shutil.copy(f, d / f.name)
        adapter["episodes"] = files[0].name if len(files) == 1 else p.episodes
    (d / "agent-card.json").write_text(json.dumps(card, indent=2, ensure_ascii=False) + "\n")
    (d / "tools.json").write_text(json.dumps({"tools": tools}, indent=2, ensure_ascii=False) + "\n")
    (d / "adapter.json").write_text(json.dumps(adapter, indent=2, ensure_ascii=False) + "\n")
    (d / "inputs.json").write_text(json.dumps({"inputs": inputs, "relations": rel, "canaries": list(p.canaries)}, indent=2, ensure_ascii=False) + "\n")
    _ = native_episodes


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--profiles", default="profiles")
    ap.add_argument("--out", default="agents")
    a = ap.parse_args()
    for p in load_all(Path(a.profiles)).values():
        convert(p, Path(a.out))
        print("converted", p.agent)


if __name__ == "__main__":
    main()
