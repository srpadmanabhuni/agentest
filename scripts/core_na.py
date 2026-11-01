"""Core-47 n/a rate on scored dev rounds (offline judge-cache replay; never an unscored/blind round).
Usage: python scripts/core_na.py [--rounds r5,r6,r7,r8,r9,r10] [--mode examples] [--json OUT]"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORE = json.loads((ROOT / "fixtures/core47.json").read_text())["core"]
J2 = {k: tuple(v) for k, v in json.loads((ROOT / "fixtures/core47.json").read_text()).get("judge_models", {}).items()}


def run_round(rnd, mode, tmp):
    if not (ROOT / f"docs/blind/{rnd}/SCORE.md").exists() and not list((ROOT / "docs/blind").glob(f"{rnd}-*results*.json")):
        raise SystemExit(f"{rnd} not scored: refusing")
    work = tmp / rnd
    shutil.copytree(ROOT / f"docs/blind/{rnd}/agents", work)
    out = tmp / f"{rnd}.json"
    m1, m2 = J2.get(rnd, ("default", None))
    cmd = [sys.executable, "-m", "agentest.cli", "std", "run", "--agents", str(work), "--mode", mode, "--run-env", "cpu",
           "--max-na", "1", "--json", str(out)]
    c1 = ROOT / f"docs/blind/{rnd}-judge-cache.jsonl"
    if c1.exists():
        shutil.copy(c1, tmp / f"{rnd}-j1.jsonl")
        cmd += ["--judge", "http://127.0.0.1:9/v1", "--judge-model", m1, "--judge-cache", str(tmp / f"{rnd}-j1.jsonl")]
    c2 = ROOT / f"docs/blind/{rnd}-judge2-cache.jsonl"
    if m2 and c2.exists():
        shutil.copy(c2, tmp / f"{rnd}-j2.jsonl")
        cmd += ["--judge2", "http://127.0.0.1:9/v1", "--judge2-model", m2, "--judge2-cache", str(tmp / f"{rnd}-j2.jsonl")]
    env = {**os.environ, "AGENTEST_JUDGE_OFFLINE": "1", "PYTHONPATH": str(ROOT / "src")}
    p = subprocess.run(cmd, env=env, capture_output=True, text=True, cwd=str(ROOT))
    if not out.exists():
        raise SystemExit(p.stderr[-1500:])
    return json.loads(out.read_text())


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--rounds", default="r5,r6,r7,r8,r9,r10")
    ap.add_argument("--mode", default="examples")
    ap.add_argument("--json", type=Path)
    a = ap.parse_args(argv)
    rows = {}
    with tempfile.TemporaryDirectory() as t:
        for rnd in a.rounds.split(","):
            for ag, row in run_round(rnd, a.mode, Path(t)).items():
                if isinstance(row, dict):
                    rows[f"{rnd}/{ag}"] = {i: (row.get(i) or {}).get("status", "missing") for i in CORE}
    tot = sum(len(v) for v in rows.values())
    na = sum(1 for v in rows.values() for s in v.values() if s in ("n/a", "missing"))
    allna = [i for i in CORE if all(v[i] in ("n/a", "missing") for v in rows.values())]
    exc = json.loads((ROOT / "fixtures/dev-label-exclusions.json").read_text())
    unl = {(i, ag) for i, e in exc.items() if not i.startswith("_") for ag in e.get("excluded", [])}
    fails = {i: sum(v[i] == "fail" and (i, ag) not in unl for ag, v in rows.items()) for i in CORE}  # unlabelled cells not counted
    print(f"agents={len(rows)} core verdicts={tot} n/a={na} ({na/tot:.0%}); checks n/a on every agent: {len(allna)}")
    print("all-n/a:", " ".join(allna))
    if a.json:
        a.json.write_text(json.dumps({"rows": rows, "na": na, "total": tot, "all_na": allna, "fails": fails}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
