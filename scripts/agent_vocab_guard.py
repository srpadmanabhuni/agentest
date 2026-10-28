"""CI guard: agentest code and test logic must not depend on any specific agent.

Fails when src/agentest/**/*.py|yaml|json or tests/**/*.py (test logic) contain an agent ID token (A\\d+ / a\\d+), an agent
folder name, an agent's card name, or a tool name declared by a bundled/example/blind agent. Data fixtures and
snapshots are excluded (tests/fixtures/, tests/schemas/, *snapshot*, fixtures/), as is this script.
Usage: python scripts/agent_vocab_guard.py [--list]   (exit 1 on any hit)
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AGENT_DIRS = [p for g in ("agents/*", "examples/*/agents/*", "examples/*", "docs/blind/*/agents/*") for p in ROOT.glob(g)
              if (p / "agent-card.json").is_file()]
GENERIC = {"search", "lookup", "run", "get", "read", "write", "query", "send", "fetch", "handoff", "tool", "echo", "calc",
           "calculator", "add", "delete", "update", "list", "status", "approve", "reject", "transfer", "refund", "book"}


IDENT = re.compile(r"[a-z0-9]+(?:[_.][a-z0-9]+)+|[a-z]+[A-Z]\w*")  # identifier-shaped: snake_case, dotted, camelCase


def world_tools() -> set[str]:
    """Tools of agentest's own scenario worlds (standards/scenarios.yaml): agentest defines them and feeds them to every
    agent under test, so they belong to the test harness, not to any agent."""
    import yaml
    doc = yaml.safe_load((ROOT / "src/agentest/standards/scenarios.yaml").read_text())
    out: set[str] = set()
    def walk(x):
        if isinstance(x, dict):
            for k, v in x.items():
                walk(v)
                if isinstance(k, str):
                    out.add(k)
        elif isinstance(x, list):
            for v in x:
                walk(v)
        elif isinstance(x, str):
            out.update(re.findall(r"[A-Za-z_][\w.]*", x))
    walk(doc)
    return out


def vocab() -> dict[str, str]:
    v: dict[str, str] = {}
    W = world_tools()
    for d in AGENT_DIRS:
        card = json.loads((d / "agent-card.json").read_text())
        if IDENT.fullmatch(d.name) or re.search(r"\d", d.name):
            v.setdefault(d.name, f"agent folder {d.relative_to(ROOT)}")
        nm = card.get("name", "")
        if len(nm) > 3 and (" " in nm or IDENT.fullmatch(nm)):
            v.setdefault(nm, f"agent name ({d.name})")
        tj = d / "tools.json"
        if tj.is_file():
            data = json.loads(tj.read_text())
            for t in data.get("tools", data) if isinstance(data, dict) else data:
                n = t.get("name") if isinstance(t, dict) else None
                if n and n not in W and IDENT.fullmatch(n):
                    v.setdefault(n, f"tool of {d.name}")
    return v


def files():
    out = [p for p in (ROOT / "src" / "agentest").rglob("*") if p.suffix in (".py", ".yaml", ".yml", ".json")]
    out += list((ROOT / "tests").rglob("*.py"))
    skip = ("/fixtures/", "/schemas/", "snapshot", "__pycache__", ".egg-info")
    return [p for p in out if not any(s in str(p) for s in skip)]


def main() -> int:
    V = vocab()
    hits = []
    id_re = re.compile(r"(?<![\w.-])[Aa]\d{2,3}(?![\w-])")
    word_res = {w: re.compile(rf"(?<![\w.-]){re.escape(w)}(?![\w-])") for w in V}
    for f in files():
        for i, line in enumerate(f.read_text(errors="ignore").splitlines(), 1):
            m = id_re.search(line)
            if m:
                hits.append(f"{f.relative_to(ROOT)}:{i}: agent id {m.group(0)!r}")
            for w, r in word_res.items():
                if r.search(line):
                    hits.append(f"{f.relative_to(ROOT)}:{i}: {w!r} ({V[w]})")
    print(f"agent-vocab guard: {len(V)} agent identifiers from {len(AGENT_DIRS)} agents; {len(files())} files scanned; {len(hits)} hits")
    for h in hits[:600]:
        print("  " + h)
    return 1 if hits else 0


if __name__ == "__main__":
    sys.exit(main())
