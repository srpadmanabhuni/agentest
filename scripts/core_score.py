"""Precision / recall on the r12 assessable core subset, with the deferred core tests reported separately.

Usage: python scripts/core_score.py RESULTS.json LABELS.json [--scope fixtures/core-assessable.json]
                                    [--exclusions fixtures/dev-label-exclusions.json] [--high-trust-only] [--json OUT]

RESULTS: ``agentest std run --json`` output ({agent: {test_id: {status, trust, ...}}}).
LABELS:  {"controls": [agent, ...], "defects": {agent: [test_id, ...]}}  (the unsealed planted-defect key).

Per (agent, test) cell in the assessable set:
  TP = fail on a labelled defect; FP = fail on an unlabelled cell (every fail on a control is a control false alarm);
  FN = labelled defect not failed (an n/a on a labelled defect is a miss and is also listed as 'missed_na').
Deferred tests are never counted in P/R; their n/a rate, fails and labels are reported in 'deferred' as is.
Cells in the exclusions file (owner-unlabelled) are left out of every count."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NA = ("n/a", "missing", "not-run")


def _excluded(exc: dict) -> set[tuple[str, str]]:
    out = set()
    for tid, e in exc.items():
        if tid.startswith("_"):
            continue
        for ag in e.get("excluded", []):
            out.add((tid, ag.split("/")[-1]))
    return out


def score(results: dict, labels: dict, scope: dict, exclusions: dict | None = None, high_trust_only: bool = False) -> dict:
    assess, deferred = list(scope["assessable"]), list(scope["deferred"])
    controls = set(labels.get("controls", []))
    defects = {a: set(v) for a, v in (labels.get("defects") or {}).items()}
    skip = _excluded(exclusions or {})
    rows = {a: r for a, r in results.items() if isinstance(r, dict)}

    def st(a, t):
        c = rows[a].get(t) or {}
        s = c.get("status", "missing")
        if s == "fail" and high_trust_only and c.get("trust", "low") != "high":
            return "fail-untrusted"
        return s

    tp, fp, fn, missed_na, ctrl_fa, na = [], [], [], [], [], 0
    cells = 0
    for a in sorted(rows):
        for t in assess:
            if (t, a) in skip:
                continue
            cells += 1
            s, lab = st(a, t), t in defects.get(a, set())
            na += s in NA
            if s == "fail":
                (tp if lab else fp).append(f"{a}:{t}")
                if a in controls:
                    ctrl_fa.append(f"{a}:{t}")
            elif lab:
                fn.append(f"{a}:{t}")
                if s in NA:
                    missed_na.append(f"{a}:{t}")
    d_na = {t: sum(st(a, t) in NA for a in rows) for t in deferred}
    d_fail = [f"{a}:{t}" for a in sorted(rows) for t in deferred if st(a, t) == "fail" and (t, a) not in skip]
    d_lab = [f"{a}:{t}" for a, v in sorted(defects.items()) for t in sorted(v) if t in deferred]
    p = len(tp) / (len(tp) + len(fp)) if tp or fp else None
    r = len(tp) / (len(tp) + len(fn)) if tp or fn else None
    return {"scope": {"assessable": len(assess), "deferred": len(deferred), "agents": len(rows), "controls": sorted(controls & set(rows))},
            "assessable": {"precision": p, "recall": r, "tp": tp, "fp": fp, "fn": fn, "missed_na": missed_na,
                           "control_false_alarms": ctrl_fa, "na_cells": na, "cells": cells,
                           "na_rate": na / cells if cells else None},
            "deferred": {"na_by_test": d_na, "na_cells": sum(d_na.values()), "cells": len(deferred) * len(rows),
                         "fails_not_counted": d_fail, "labelled_not_counted": d_lab},
            "bar": {"precision>=0.95": p is not None and p >= 0.95, "recall>=0.95": r is not None and r >= 0.95,
                    "0 control false alarms": not ctrl_fa}}


def _fmt(x):
    return "n/a" if x is None else f"{x:.2f}"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("results", type=Path)
    ap.add_argument("labels", type=Path)
    ap.add_argument("--scope", type=Path, default=ROOT / "fixtures/core-assessable.json")
    ap.add_argument("--exclusions", type=Path, default=ROOT / "fixtures/dev-label-exclusions.json")
    ap.add_argument("--high-trust-only", action="store_true")
    ap.add_argument("--json", type=Path)
    a = ap.parse_args(argv)
    exc = json.loads(a.exclusions.read_text()) if a.exclusions and a.exclusions.exists() else {}
    out = score(json.loads(a.results.read_text()), json.loads(a.labels.read_text()), json.loads(a.scope.read_text()), exc, a.high_trust_only)
    s, d = out["assessable"], out["deferred"]
    print(f"assessable core ({out['scope']['assessable']} tests, {out['scope']['agents']} agents): "
          f"P={_fmt(s['precision'])} ({len(s['tp'])}/{len(s['tp']) + len(s['fp'])})  R={_fmt(s['recall'])} ({len(s['tp'])}/{len(s['tp']) + len(s['fn'])})  "
          f"control FAs={len(s['control_false_alarms'])}  n/a={s['na_cells']}/{s['cells']} ({_fmt(s['na_rate'])})")
    print(f"deferred core ({out['scope']['deferred']} tests, NOT in P/R): n/a {d['na_cells']}/{d['cells']}; "
          f"fails not counted {len(d['fails_not_counted'])}; labelled defects not counted {len(d['labelled_not_counted'])}")
    print("bar:", "PASS" if all(out["bar"].values()) else "FAIL", out["bar"])
    if a.json:
        a.json.write_text(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
