"""Score agents with their identity hidden (blind rounds), then map the verdicts back.

Before agentest runs, every agent folder is copied to a temporary directory under an opaque ID (``x`` + 8 hex chars,
from a random secret salt) and every identity string is renamed consistently in the AgentCard, the governance
extension, tools.json and the OTLP traces: the agent ID / folder name, the card name, ``service.name``,
``gen_ai.agent.id`` and the actor names (``gen_ai.agent.name``, ``agentest.handoff.source``). Folder order is shuffled.
Tool names, tool descriptions and message text are capabilities and evidence, not identity, and are kept, so the
judge sees exactly the payloads it would see unanonymised (its replay cache still answers). After the run, result keys
and details are mapped back to the real IDs.

Usage: python scripts/blind_anon.py --agents <dir> --json out.json [--map-out map.json] [-- extra `agentest std run` args]
"""
from __future__ import annotations

import argparse
import json
import random
import secrets
import subprocess
import sys
import tempfile
from pathlib import Path

ID_ATTRS = {"gen_ai.agent.name", "gen_ai.agent.id", "agentest.handoff.source", "service.name"}


def rename_otlp(x, m: dict[str, str], id_attrs=ID_ATTRS, rename_tool_parts: bool = False):
    """Rename identifier attributes and span names; payload text is left alone."""
    if isinstance(x, dict):
        if x.get("key") in id_attrs and isinstance(x.get("value", {}).get("stringValue"), str):
            v = x["value"]["stringValue"]
            return {"key": x["key"], "value": {"stringValue": m.get(v, v)}}
        out = {k: rename_otlp(v, m, id_attrs, rename_tool_parts) for k, v in x.items()}
        if isinstance(out.get("name"), str) and "spanId" in out:
            op, _, rest = out["name"].partition(" ")
            out["name"] = f"{op} {m.get(rest, rest)}" if rest else m.get(op, op)
        return out
    if isinstance(x, list):
        return [rename_otlp(v, m, id_attrs, rename_tool_parts) for v in x]
    return x


def rename_meta(x, m: dict[str, str], parent: str = ""):
    if isinstance(x, dict):
        return {(m.get(k, k) if parent in ("prerequisites", "compensations", "freshness", "actors", "rateLimits") else k):
                (v if k in ("postconditions", "enum", "description", "tools", "inputSchema") else rename_meta(v, m, k)) for k, v in x.items()}
    if isinstance(x, list):
        return [rename_meta(v, m, parent) for v in x]
    if isinstance(x, str):
        return m.get(x, x)
    return x


def identity_strings(a) -> set[str]:
    from agentest.standards import runner
    out = {a.id, a.card.get("name", "")}
    for d in runner.otlp_docs(a):
        def walk(x):
            if isinstance(x, dict):
                if x.get("key") in ID_ATTRS and isinstance(x.get("value", {}).get("stringValue"), str):
                    out.add(x["value"]["stringValue"])
                for v in x.values():
                    walk(v)
            elif isinstance(x, list):
                for v in x:
                    walk(v)
        walk(d)
    return {s for s in out if s and s not in a.tools}


def anonymise(src: Path, dst: Path, rng: random.Random) -> dict[str, dict]:
    """Copy every agent in src to dst under opaque IDs. Returns {opaque_id: {"id": real_id, "map": {real: opaque}}}."""
    from agentest.standards import metadata, runner
    agents = metadata.load_all(src)
    order = list(agents)
    rng.shuffle(order)
    out: dict[str, dict] = {}
    for aid in order:
        a = agents[aid]
        m = {s: "x" + "".join(rng.choice("0123456789abcdef") for _ in range(8)) for s in sorted(identity_strings(a))}
        new = m[a.id]
        d = dst / new
        (d / "traces").mkdir(parents=True)
        (d / "agent-card.json").write_text(json.dumps(rename_meta(a.card, m), ensure_ascii=False))
        (d / "tools.json").write_text(json.dumps({"tools": list(a.tools.values())}, ensure_ascii=False))
        (d / "traces" / "t.otlp.jsonl").write_text("".join(json.dumps(rename_otlp(x, m), ensure_ascii=False) + "\n" for x in runner.otlp_docs(a)))
        out[new] = {"id": a.id, "map": m}
    return out


def unmap(detail: str, m: dict[str, str]) -> str:
    for real, opaque in m.items():
        detail = detail.replace(opaque, real)
    return detail


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--agents", required=True, type=Path)
    ap.add_argument("--json", required=True, type=Path)
    ap.add_argument("--map-out", type=Path, help="write the opaque-to-real map here (keep it away from the scorer until scoring is done)")
    ap.add_argument("rest", nargs=argparse.REMAINDER)
    ns = ap.parse_args(argv)
    rng = random.Random(secrets.token_hex(16))
    with tempfile.TemporaryDirectory(prefix="agentest-blind-") as tmp:
        maps = anonymise(ns.agents, Path(tmp), rng)
        raw = Path(tmp) / "raw.json"
        extra = [x for x in ns.rest if x != "--"]
        rc = subprocess.call([sys.executable, "-m", "agentest.cli", "std", "run", "--agents", tmp, "--json", str(raw), *extra])
        if not raw.is_file():
            return rc or 1
        res = json.loads(raw.read_text())
        back = {maps[k]["id"]: json.loads(unmap(json.dumps(v, ensure_ascii=False), maps[k]["map"])) if k in maps else v for k, v in res.items()}
        ns.json.write_text(json.dumps(dict(sorted(back.items())), indent=1, ensure_ascii=False))
        if ns.map_out:
            ns.map_out.write_text(json.dumps(maps, indent=1, ensure_ascii=False))
    return rc


if __name__ == "__main__":
    sys.exit(main())
