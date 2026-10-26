"""Count agent-specific vs generic lines of code (non-blank, non-comment) for the v3.0.0 standards-based engine."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _lines(text: str) -> int:
    return sum(1 for ln in text.splitlines() if ln.strip() and not ln.strip().startswith("#"))


def loc_v1(paths: list[str]) -> int:
    """LOC of files as they were at the v1.0.0 tag (removed in v2)."""
    n = 0
    for f in paths:
        try:
            n += _lines(subprocess.run(["git", "show", f"v1.0.0:{f}"], cwd=ROOT, capture_output=True, text=True, check=True).stdout)
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass
    return n


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
    st = ROOT / "src" / "agentest" / "standards"
    meta = sorted(p for p in (ROOT / "agents").rglob("*") if p.suffix in (".json", ".py"))
    demo = sorted((ROOT / "examples/agnostic_demo/agents/refill_bot").glob("*.json")) + [ROOT / "examples/agnostic_demo/agents/refill_bot/adapter.py"]
    return [
        ("v3 universal rules (130 IDs)", "src/agentest/standards/rules.py", 0, loc([st / "rules.py"])),
        ("v3 OTel GenAI export/import, metadata, inputs, runner, cli", "src/agentest/standards/{otel,metadata,inputs,runner,cli}.py", 0,
         loc([st / f for f in ("otel.py", "metadata.py", "inputs.py", "runner.py", "cli.py")])),
        ("v3 test-owned scenario oracles (keyed by catalogue ID, not agent)", "src/agentest/standards/scenarios.yaml", 0, loc([st / "scenarios.yaml"])),
        ("adapter core (adapt, plugin loader, effects)", "src/agentest/model/adapters.py", 0, loc([m / "adapters.py"]) - dialect),
        ("framework-specific: 7 built-in log dialect parsers", "src/agentest/model/adapters.py", dialect, 0),
        ("agent-published metadata (AgentCard, MCP tools, adapter map, inputs) - no rules", "agents/*/*", loc(meta), 0),
        ("new agent (agnostic demo): metadata + adapter, 0 test changes", "examples/agnostic_demo/agents/refill_bot/*", loc(demo), 0),
        ("per-agent rule / expectation files", "-", 0, 0),
    ]


def md() -> str:
    out = ["| Component | Files | Agent/framework-specific LOC | Generic LOC |", "|---|---|---:|---:|"]
    out += [f"| {a} | `{b}` | {c or '-'} | {d or '-'} |" for a, b, c, d in rows()]
    return "\n".join(out)


if __name__ == "__main__":
    print(md())
