"""``python scripts/eval_verdicts.py`` (or ``make eval``): run every check on the PUBLIC example agents and show what changed.

It reads only the example agents that ship in this repository (``agents/`` and ``examples/*/agents/``) and prints a
per-check verdict summary (pass / fail / n/a counts over those agents). With ``--base REF`` it also runs the checks of
git ref ``REF`` on that ref's own example agents and prints every verdict that differs, so a pull request can show a
before and after on public data. It computes no scores and reads no data outside the checkout: ``--root`` must be a
directory that holds the repo's public ``agents/`` folder, and ``--agents`` paths must stay inside the root.

    python scripts/eval_verdicts.py                      # summary for this checkout
    python scripts/eval_verdicts.py --base main          # summary plus verdicts that differ from main
    python scripts/eval_verdicts.py --ids T2-001 X-002   # only some checks
    python scripts/eval_verdicts.py --json out.json      # machine-readable verdicts (same shape as the verdict snapshot)

Deterministic and offline: it calls the same runner as ``agentest std run``.
"""
# Ref: internal design (docs/contributing/EVAL.md); no external source.
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

CODE = {"pass": "P", "fail": "F", "n/a": "-"}
WORD = {"P": "pass", "F": "fail", "-": "n/a"}
MODES = ("strict", "examples")
ROOT = Path(__file__).resolve().parents[1]


def _public_roots(root: Path) -> list[tuple[str, Path]]:
    """The only places agents are read from: ``<root>/agents`` and ``<root>/examples/*/agents``."""
    out = [("", root / "agents")]
    out += [(d.parent.name + "/", d) for d in sorted((root / "examples").glob("*/agents"))]
    return [(p, d) for p, d in out if d.is_dir()]


def _inside(root: Path, p: Path) -> bool:
    try:
        p.resolve().relative_to(root.resolve())
    except ValueError:
        return False
    return True


def compute(root: Path, ids: list[str] | None = None, extra: list[Path] | None = None) -> dict:
    """Verdicts of every check on every public example agent under ``root``, in both modes."""
    from agentest.standards import metadata, runner
    from agentest.standards.catalog import ALL_IDS

    root = Path(root)
    if not (root / "agents").is_dir():
        raise SystemExit(f"{root} has no agents/ folder: pass --root with a checkout of the repository")
    agents: dict = {}
    for prefix, d in _public_roots(root):
        agents.update({prefix + k: a for k, a in metadata.load_all(d).items()})
    for d in extra or []:
        if not _inside(root, d):
            raise SystemExit(f"--agents {d} is outside the repository root; only in-repo example agents are read")
        agents.update({d.name + "/" + k: a for k, a in metadata.load_all(d).items()})
    want = [i for i in ALL_IDS if not ids or i in ids]
    snap: dict = {"ids": want, "legend": "one character per ID in 'ids' order: P pass, F fail, - n/a"}
    for mode in MODES:
        res = runner.run_all(agents, mode=mode)
        snap[mode] = {k: "".join(CODE[res[k][i].status] for i in want) for k in sorted(res)}
    return snap


def base_snapshot(ref: str, root: Path, ids: list[str] | None = None) -> dict | None:
    """Verdicts of git ``ref`` on its own example agents (its code, its agents), or None when the ref does not exist."""
    root = Path(root)
    if subprocess.run(["git", "-C", str(root), "rev-parse", "--verify", "-q", ref + "^{commit}"], capture_output=True).returncode:
        return None
    with tempfile.TemporaryDirectory() as tmp:
        arch = subprocess.run(["git", "-C", str(root), "archive", ref], capture_output=True, check=True).stdout
        subprocess.run(["tar", "-x", "-C", tmp], input=arch, check=True)
        env = {k: v for k, v in os.environ.items() if k not in ("AGENTEST_ROOT", "PYTHONPATH")}
        env.update(PYTHONPATH=str(Path(tmp) / "src"), PYTHONSAFEPATH="1")
        cmd = [sys.executable, str(Path(__file__).resolve()), "--root", tmp, "--json", "-", "--quiet"]
        if ids:
            cmd += ["--ids", *ids]
        out = subprocess.run(cmd, capture_output=True, text=True, env=env)
        if out.returncode:
            raise SystemExit(f"could not run the checks of {ref}: {out.stderr.strip()[-300:]}")
        return json.loads(out.stdout)


def summary(snap: dict, modes: tuple[str, ...] = MODES) -> str:
    lines = []
    for mode in modes:
        rows = snap[mode]
        lines.append(f"mode: {mode}   example agents: {len(rows)}")
        lines.append(f"{'check':<8} {'pass':>5} {'fail':>5} {'n/a':>5}")
        for n, cid in enumerate(snap["ids"]):
            col = [r[n] for r in rows.values()]
            lines.append(f"{cid:<8} {col.count('P'):>5} {col.count('F'):>5} {col.count('-'):>5}")
        lines.append("")
    return "\n".join(lines)


def diff(base: dict, head: dict) -> dict:
    """Changed verdicts between two snapshots, over the agents and checks both have."""
    changed, added, removed = [], [], []
    ids = [i for i in head["ids"] if i in base["ids"]]
    for mode in MODES:
        b, h = base.get(mode, {}), head.get(mode, {})
        if mode == "strict":
            added = sorted(set(h) - set(b))
            removed = sorted(set(b) - set(h))
        for agent in sorted(set(b) & set(h)):
            for cid in ids:
                was, now = b[agent][base["ids"].index(cid)], h[agent][head["ids"].index(cid)]
                if was != now:
                    changed.append({"mode": mode, "agent": agent, "check": cid, "before": WORD[was], "after": WORD[now]})
    return {"changed": changed, "agents_added": added, "agents_removed": removed}


def render_diff(d: dict, ref: str) -> str:
    if not (d["changed"] or d["agents_added"] or d["agents_removed"]):
        return f"No verdict differs from {ref} on the public example agents."
    lines = [f"Verdicts that differ from {ref} on the public example agents: {len(d['changed'])}"]
    lines += [f"  {c['mode']:<8} {c['agent']:<28} {c['check']:<8} {c['before']} -> {c['after']}" for c in d["changed"]]
    if d["agents_added"]:
        lines.append("example agents added: " + ", ".join(d["agents_added"]))
    if d["agents_removed"]:
        lines.append("example agents removed: " + ", ".join(d["agents_removed"]))
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python scripts/eval_verdicts.py", description=__doc__.split("\n\n")[0])
    ap.add_argument("--root", type=Path, help="repository checkout (default: this checkout)")
    ap.add_argument("--base", metavar="REF", help="git ref to compare with, for example main or origin/main")
    ap.add_argument("--ids", nargs="*", help="only these check IDs")
    ap.add_argument("--mode", choices=MODES, help="show one mode only (default: both)")
    ap.add_argument("--agents", type=Path, action="append", help="extra agents folder INSIDE the repository")
    ap.add_argument("--json", metavar="FILE", help="write verdicts as JSON ('-' for stdout)")
    ap.add_argument("--diff-json", metavar="FILE", help="write the diff against --base as JSON")
    ap.add_argument("--quiet", action="store_true", help="no text summary")
    a = ap.parse_args(argv)
    root = a.root or ROOT
    head = compute(root, a.ids, a.agents)
    if a.json:
        text = json.dumps(head, indent=1) + "\n"
        sys.stdout.write(text) if a.json == "-" else Path(a.json).write_text(text, encoding="utf-8")
    if not a.quiet:
        print(summary(head, (a.mode,) if a.mode else MODES))
    if a.base:
        base = base_snapshot(a.base, root, a.ids)
        if base is None:
            print(f"(git ref {a.base!r} not found: showing the summary only)")
        else:
            d = diff(base, head)
            if a.diff_json:
                Path(a.diff_json).write_text(json.dumps(d, indent=1) + "\n", encoding="utf-8")
            if not a.quiet:
                print(render_diff(d, a.base))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
