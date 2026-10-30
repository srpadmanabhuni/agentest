"""r12-prep Fix 8: clean-control gate. Runs EVERY check over a cached pool of audited-clean control traces and fails if
any check fires (a fail on a clean control is a false alarm by definition).

The pool is data (fixtures/controls/pool.json), not code: this script names no agent. Each control is copied to a temp
folder and scored offline against its own round's frozen judge cache(s), so the gate needs no live judge and never
writes into the repo. A judge question missing from the cache comes back not-assessed (reported, not a failure).

Usage: python scripts/control_gate.py [--pool fixtures/controls/pool.json] [--mode examples] [--json OUT] [--integrity]
Exit: 0 = no check fires on any control; 1 = at least one fires; 2 = pool/setup error.
"""
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
FORBIDDEN_PARTS = ("trail", "whowhen", "who_when", "sealed")


def _check_entry(e: dict) -> str | None:
    p = str(e.get("agents_dir", "")).lower()
    if any(x in p for x in FORBIDDEN_PARTS):
        return f"forbidden source for a control: {e.get('agents_dir')}"
    rnd = e.get("round")
    if rnd and not list((ROOT / "docs/blind").glob(f"{rnd}-*results*.json")) and not (ROOT / "docs/blind" / rnd / "SCORE.md").exists():
        return f"round {rnd} has no scored results: its agents are still blind and may not be used as controls"
    return None


def run_control(e: dict, mode: str, tmp: Path, integrity: bool) -> dict:
    src = ROOT / e["agents_dir"] / e["agent"]
    work = tmp / e["round"] / "agents"
    work.mkdir(parents=True, exist_ok=True)
    shutil.copytree(src, work / e["agent"])
    out = {"round": e["round"], "agent": e["agent"]}
    if integrity:
        from agentest.standards import integrity as I
        r = I.check_agent(work / e["agent"], None, allow_unsigned=True, allow_no_traffic=True)
        out["integrity"] = {"status": r["status"], "errors": r["errors"][:5]}
    cmd = [sys.executable, "-m", "agentest.cli", "std", "run", "--agents", str(work), "--mode", mode, "--run-env", "cpu",
           "--max-na", "1", "--json", str(tmp / f"{e['round']}.json")]
    for n in ("", "2"):
        c = e.get(f"judge{n}_cache")
        if c:
            cp = tmp / f"{e['round']}-j{n or 1}.jsonl"
            shutil.copy(ROOT / c, cp)
            cmd += [f"--judge{n}", "http://127.0.0.1:9/v1", f"--judge{n}-model", e.get(f"judge{n}_model", "default"), f"--judge{n}-cache", str(cp)]
    env = {**os.environ, "AGENTEST_JUDGE_OFFLINE": "1", "PYTHONPATH": str(ROOT / "src") + os.pathsep + os.environ.get("PYTHONPATH", "")}
    p = subprocess.run(cmd, env=env, capture_output=True, text=True, cwd=str(ROOT))
    res_path = tmp / f"{e['round']}.json"
    if not res_path.exists():
        out["error"] = (p.stderr or p.stdout)[-800:]
        return out
    row = json.loads(res_path.read_text()).get(e["agent"], {})
    out["fires"] = {i: r.get("detail", "")[:200] for i, r in sorted(row.items()) if r.get("status") == "fail"}
    out["not_assessed"] = sorted(i for i, r in row.items() if r.get("status") == "not-assessed")
    out["pass"] = sum(1 for r in row.values() if r.get("status") == "pass")
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--pool", type=Path, default=ROOT / "fixtures/controls/pool.json")
    ap.add_argument("--mode", default="examples", choices=["examples", "strict"])
    ap.add_argument("--json", type=Path)
    ap.add_argument("--integrity", action="store_true", help="also run the pre-scoring integrity validator on each control")
    a = ap.parse_args(argv)
    pool = json.loads(a.pool.read_text()).get("controls") or []
    if not pool:
        print("empty control pool", file=sys.stderr)
        return 2
    for e in pool:
        why = _check_entry(e)
        if why:
            print(f"pool error: {why}", file=sys.stderr)
            return 2
    with tempfile.TemporaryDirectory(prefix="agentest-control-gate-") as t:
        rep = [run_control(e, a.mode, Path(t), a.integrity) for e in pool]
    fired, by_check = 0, {}
    for r in rep:
        if "error" in r:
            print(f"{r['round']}/{r['agent']}: ERROR {r['error']}")
            fired += 1
            continue
        f = r["fires"]
        fired += len(f)
        for i in f:
            by_check.setdefault(i, []).append(f"{r['round']}/{r['agent']}")
        line = f"{r['round']}/{r['agent']}: {r['pass']} pass, {len(f)} FIRE" + (f" ({', '.join(f)})" if f else "")
        line += f", {len(r['not_assessed'])} not-assessed" if r["not_assessed"] else ""
        if "integrity" in r:
            line += f"; integrity {r['integrity']['status']}"
        print(line)
        for i, d in f.items():
            print(f"    {i}: {d}")
    print(f"control gate ({a.mode}): {len(rep)} control(s), {fired} firing cell(s)"
          + (f"; checks firing: {', '.join(f'{k} x{len(v)}' for k, v in sorted(by_check.items()))}" if by_check else "")
          + (" -> FAIL" if fired else " -> PASS"))
    if a.json:
        a.json.write_text(json.dumps({"mode": a.mode, "controls": rep, "checks_firing": by_check}, indent=1, ensure_ascii=False))
    return 1 if fired else 0


if __name__ == "__main__":
    sys.exit(main())
