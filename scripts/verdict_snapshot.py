"""Snapshot of every verdict: all 130 IDs x every bundled agent (agents/ and examples/*/agents/) x both modes.

``tests/test_verdict_snapshot.py`` compares a fresh run with ``fixtures/standards/v3-verdicts.json`` so that any change
of a pass, fail or n/a, on any ID, is a visible, reviewed diff (the v3 counterpart of the v1/v2 golden/broken packs).
Regenerate after an intended rule change:  python scripts/verdict_snapshot.py --write
The file is data keyed by agent folder and catalogue ID; no check code reads it.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from agentest.standards import metadata, runner  # noqa: E402
from agentest.standards.catalog import ALL_IDS  # noqa: E402

OUT = ROOT / "fixtures" / "standards" / "v3-verdicts.json"
CODE = {"pass": "P", "fail": "F", "n/a": "-"}


def agents() -> dict:
    out = dict(metadata.load_all(ROOT / "agents"))
    for d in sorted((ROOT / "examples").glob("*/agents")):
        out.update({f"{d.parent.name}/{k}": a for k, a in metadata.load_all(d).items()})
    return out


def compute() -> dict:
    ags = agents()
    snap = {"ids": list(ALL_IDS), "legend": "one character per ID in 'ids' order: P pass, F fail, - n/a"}
    for mode in ("strict", "examples"):
        res = runner.run_all(ags, mode=mode)
        snap[mode] = {k: "".join(CODE[res[k][i].status] for i in ALL_IDS) for k in sorted(res)}
    return snap


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args()
    snap = compute()
    if a.write:
        OUT.write_text(json.dumps(snap, indent=1) + "\n")
        print(f"wrote {OUT.relative_to(ROOT)}: {len(snap['strict'])} agents x {len(snap['ids'])} IDs x 2 modes")
        return 0
    print(json.dumps(snap, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
