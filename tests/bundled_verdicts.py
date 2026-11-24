"""Verdict table of every bundled agent, used to prove reader changes move no verdict.

Agents ``a161``-``a170`` are excluded by path: their directories are never opened, listed or read. The agent folder
is scanned by entry name only, and an excluded name is dropped before any filesystem call on it.

Regenerate the fixture only on the base commit, before a reader change:
    PYTHONPATH=src python -m tests.bundled_verdicts --write
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AGENTS = ROOT / "agents"
EXCLUDED_NAMES = frozenset(f"a{i}" for i in range(161, 171))
EXCLUDED_PATHS = frozenset(AGENTS / n for n in EXCLUDED_NAMES)
EXAMPLE_AGENTS = ("examples/agnostic_demo/agents/refill_bot", "examples/agnostic_demo/agents/refill_bot_buggy",
                  "examples/langgraph_import/agents/expense_bot", "examples/first_trace", "examples/otel_plain")
FIXTURE = ROOT / "tests" / "fixtures" / "bundled-verdicts.json"
MODES = ("examples", "strict")
CODE = {"pass": "p", "fail": "f", "n/a": "n", "not-run": "r", "error": "e"}


def encode(row: dict[str, str], order: list[str]) -> str:
    """Statuses in check-id order, one letter each (p pass, f fail, n n/a, r not-run, e error)."""
    return "".join(CODE[row[i]] for i in order)


def agent_dirs() -> list[Path]:
    """Bundled agent directories, a161-a170 excluded by name before any access."""
    out = []
    with os.scandir(AGENTS) as it:
        names = sorted(e.name for e in it if e.name not in EXCLUDED_NAMES)
    for n in names:
        p = AGENTS / n
        assert p not in EXCLUDED_PATHS and n not in EXCLUDED_NAMES
        if p.is_dir():
            out.append(p)
    out += [ROOT / x for x in EXAMPLE_AGENTS if (ROOT / x).is_dir()]
    assert not EXCLUDED_PATHS & set(out)
    assert all(not str(p.resolve()).startswith(tuple(str(x) + os.sep for x in EXCLUDED_PATHS)) for p in out)
    return out


def ids() -> list[str]:
    from agentest.standards.catalog import ALL_IDS, RAI_ADDITION_IDS

    return list(ALL_IDS) + [i for i in RAI_ADDITION_IDS if i not in ALL_IDS]


def table() -> dict:
    """{agent path: {mode: {check id: status}}} for every bundled agent with traces."""
    from agentest.standards import metadata
    from agentest.standards.rules import evaluate
    from agentest.standards.runner import runs

    out = {}
    for d in agent_dirs():
        a = metadata.load(d)
        rs = runs(a)
        if not rs:
            continue
        out[d.relative_to(ROOT).as_posix()] = {m: {k: r.status for k, r in evaluate(a, rs, ids=ids(), mode=m).items()} for m in MODES}
    return out


def main() -> int:
    t = table()
    if "--write" in sys.argv:
        sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
        FIXTURE.parent.mkdir(parents=True, exist_ok=True)
        order = ids()
        enc = {a: {m: encode(v, order) for m, v in row.items()} for a, row in t.items()}
        FIXTURE.write_text(json.dumps({"base": sha, "codes": CODE, "ids": order, "verdicts": enc}, indent=1, sort_keys=True) + "\n",
                           encoding="utf-8")
    cells = sum(len(v) for row in t.values() for v in row.values())
    print(f"{len(t)} agents, {cells} cells")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
