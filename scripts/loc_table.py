"""Count agent-specific vs generic lines of code (non-blank, non-comment) for docs/model-driven (v2.0.0-dev)."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def loc(paths) -> int:
    n = 0
    for p in paths:
        for ln in p.read_text().splitlines():
            s = ln.strip()
            if s and not s.startswith("#"):
                n += 1
    return n


def rows() -> list[tuple[str, str, int, int]]:
    m = ROOT / "src" / "agentest" / "model"
    ad = (m / "adapters.py").read_text().splitlines()
    dialect = 0
    cur = None
    for ln in ad:
        d = re.match(r"def (_\w+)\(", ln)
        if d:
            cur = d.group(1)
        elif re.match(r"\S", ln):
            cur = None
        if cur and cur not in ("_args", "_text", "_effects", "_plugin") and ln.strip() and not ln.strip().startswith("#"):
            dialect += 1
    v1 = sorted((ROOT / "src" / "agentest" / "real").glob("checks*.py"))
    return [
        ("v2 generic: checks", "src/agentest/model/generic.py", 0, loc([m / "generic.py"])),
        ("v2 generic: trace, profile, runner, generator, cli", "src/agentest/model/{trace,profile,runner,generator,cli}.py", 0,
         loc([m / f for f in ("trace.py", "profile.py", "runner.py", "generator.py", "cli.py")])),
        ("v2 generic: adapter core (adapt, plugin loader, effects)", "src/agentest/model/adapters.py", 0, loc([m / "adapters.py"]) - dialect),
        ("v2 framework-specific: 7 built-in dialect parsers", "src/agentest/model/adapters.py", dialect, 0),
        ("v2 agent-specific: 40 YAML profiles", "profiles/*.yaml", loc(sorted((ROOT / "profiles").glob("*.yaml"))), 0),
        ("v2 new agent (agnostic demo): profile + adapter", "examples/agnostic_demo/{refill_bot.yaml,adapter.py}", loc([ROOT / "examples/agnostic_demo/refill_bot.yaml", ROOT / "examples/agnostic_demo/adapter.py"]), 0),
        ("v1 reference: per-agent real checks", "src/agentest/real/checks*.py", loc(v1), 0),
    ]


def md() -> str:
    out = ["| Component | Files | Agent/framework-specific LOC | Generic LOC |", "|---|---|---:|---:|"]
    out += [f"| {a} | `{b}` | {c or '-'} | {d or '-'} |" for a, b, c, d in rows()]
    return "\n".join(out)


if __name__ == "__main__":
    print(md())
