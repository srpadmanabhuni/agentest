"""How far the starter templates cut the n/a share on the demo agents (no verdict logic; measurement only).

For each demo agent: 'bare' = its traces with a name-only AgentCard and name-only tools.json; then the fields of
templates/my_agent/tools.json, of templates/my_agent/agent-card.json, and both, filled with the agent's own values;
'full' = the agent's complete published metadata. Run: python scripts/template_uplift.py [--md OUT]"""

import copy
import json
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from agentest.standards import metadata, runner  # noqa: E402

DEMOS = [ROOT / "examples/agnostic_demo/agents", ROOT / "examples/langgraph_import/agents"]
TPL = ROOT / "templates/my_agent"


def _keys(t):
    card = json.loads((t / "agent-card.json").read_text())
    gov = next(e["params"] for e in card["capabilities"]["extensions"] if "governance" in e["uri"])
    tool = json.loads((t / "tools.json").read_text())["tools"][0]
    return set(card), set(gov), set(tool)


def _card(c: dict, top: set, gov: set | None) -> dict:
    out = {k: v for k, v in c.items() if k in top} if top else {k: c[k] for k in ("protocolVersion", "name", "version") if k in c}
    out.setdefault("skills", [])
    if gov is not None and "capabilities" in c:
        caps = copy.deepcopy(c["capabilities"])
        for e in caps.get("extensions", []):
            if "governance" in e.get("uri", ""):
                e["params"] = {k: v for k, v in e.get("params", {}).items() if k in gov}
        out["capabilities"] = caps
    elif "capabilities" in out:
        out.pop("capabilities")
    return out


def _tools(t: dict, keys: set | None) -> dict:
    return {"tools": [{k: v for k, v in x.items() if k in keys} if keys else {"name": x["name"]} for x in t.get("tools", [])]}


def share(row: dict) -> float:
    return sum(c["status"] == "n/a" for c in row.values()) / max(len(row), 1)


def measure() -> list[tuple]:
    top, gov, tk = _keys(TPL)
    variants = {"bare": (False, False), "+tools template": (True, False), "+card template": (False, True), "+both templates": (True, True)}
    rows = []
    for base in DEMOS + [TPL.parent]:
        for d in sorted(p for p in base.iterdir() if (p / "agent-card.json").exists()):
            card = json.loads((d / "agent-card.json").read_text())
            tools = json.loads((d / "tools.json").read_text()) if (d / "tools.json").exists() else {"tools": []}
            out = []
            for _name, (ut, uc) in variants.items():
                with tempfile.TemporaryDirectory() as tmp:
                    a = Path(tmp) / d.name
                    shutil.copytree(d, a)
                    (a / "agent-card.json").write_text(json.dumps(_card(card, top if uc else set(), gov if uc else None)))
                    (a / "tools.json").write_text(json.dumps(_tools(tools, tk if ut else None)))
                    res = runner.to_json(runner.run_all({d.name: metadata.load(a)}))
                    out.append(share(res[d.name]))
            full = share(runner.to_json(runner.run_all({d.name: metadata.load(d)}))[d.name])
            rows.append((d.name, *out, full))
    return rows, list(variants) + ["full metadata"]


if __name__ == "__main__":
    rows, cols = measure()
    lines = ["| agent | " + " | ".join(cols) + " |", "|---" * (len(cols) + 1) + "|"]
    lines += [f"| {r[0]} | " + " | ".join(f"{100 * v:.0f}%" for v in r[1:]) + " |" for r in rows]
    text = "n/a share (n/a cells / all cells) per variant, judge off\n\n" + "\n".join(lines) + "\n"
    if "--md" in sys.argv:
        Path(sys.argv[sys.argv.index("--md") + 1]).write_text(text)
    print(text)
