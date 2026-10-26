"""Regenerate docs/model-driven/PARITY.md and parity.json: v2.0.0 (model-driven) vs the frozen v1.0.0 baseline.

The v1.0.0 per-agent check modules were removed in v2.0.0 (they remain in git history at tag v1.0.0);
their verdicts are frozen in fixtures/real/v1-results.json and compared here cell by cell.
"""

from __future__ import annotations

import collections
import json
from pathlib import Path

from agentest.real.report import build, to_json

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "model-driven"

WHY = {
    ("n/a", "pass"): "v1 had no check for this agent and ID. In v2 the profile states no expectation, so the built-in generic check is the default; it finds evidence in the recorded trace (approvals, authz decisions, write calls, tool lists) and passes. Extra coverage, not a changed verdict.",
    ("n/a", "fail"): "v1 had no check for this agent and ID. The built-in generic check applies to the profile-declared surface and fails. Extra finding: review it before relying on it (see the row detail).",
}


def _neutral(d: str) -> str:
    return d.replace("a non-responding agent", "noop").replace("non-responding agent", "noop")


def main() -> None:
    v1 = json.loads((ROOT / "fixtures" / "real" / "v1-results.json").read_text())
    v2 = to_json(build())
    t = collections.Counter()
    rows = []
    for a, row in v1.items():
        for i, c in row.items():
            n = v2[a][i]
            o, s = c["status"], n["status"]
            if o == s:
                if o == "n/a":
                    t["agree_na"] += 1
                elif _neutral(c["detail"]) == _neutral(n["detail"]):
                    t[f"agree_{o}_exact"] += 1
                    t["wording_only"] += c["detail"] != n["detail"]
                else:
                    t[f"agree_{o}_detail_differs"] += 1
            else:
                k = "applicability" if "n/a" in (o, s) else ("v2_stricter" if s == "fail" else "v2_looser")
                t[k] += 1
                rows.append({"agent": a, "id": i, "v1": o, "v2": s, "kind": k, "v1_detail": c["detail"][:160], "v2_detail": n["detail"][:160],
                             "why": WHY.get((o, s), "")})
    fails = [(a, i) for a, row in v1.items() for i, c in row.items() if c["status"] == "fail"]
    caught = sum(v2[a][i]["status"] == "fail" for a, i in fails)
    extra = {a: dict(collections.Counter(c["status"] for c in row.values())) for a, row in v2.items() if a not in v1}
    data = {"v1_cells": sum(len(r) for r in v1.values()), "v1_fails": len(fails), "v1_fails_caught_by_v2": caught,
            "tally": dict(t), "rows": rows, "agents_without_v1_baseline": extra}
    (OUT / "parity.json").write_text(json.dumps(data, indent=1))
    L = ["# Parity: v2.0.0 (model-driven) vs v1.0.0 (per-agent checks)", "",
         "Regenerate with `python scripts/model_parity.py`. Baseline: `fixtures/real/v1-results.json`, the v1.0.0 matrix",
         "frozen before the v1 per-agent check modules were removed (they remain in git history at tag `v1.0.0`).", "",
         "## Summary", "",
         f"- Cells compared: **{data['v1_cells']}** (40 agents with a v1 baseline x 130 IDs).",
         f"- v1 fails caught by v2: **{caught} of {len(fails)}**.",
         f"- v1 pass cells reproduced (status and detail): **{t['agree_pass_exact']}**; v1 fail cells reproduced: **{t['agree_fail_exact']}**.",
         f"- Same status, different detail: **{t['agree_pass_detail_differs'] + t['agree_fail_detail_differs']}**. "
         f"Wording-only change ({t['wording_only']} cells): v2 detail texts say \"a non-responding agent\" where v1 named the `noop` sample, because shared check code may not name an agent.",
         f"- v2 looser (v1 fail, v2 pass): **{t['v2_looser']}**. v2 stricter (v1 pass, v2 fail): **{t['v2_stricter']}**.",
         f"- Both n/a: {t['agree_na']} (n/a detail wording differs: v2 says which profile fact or applicability rule is missing).",
         f"- Applicability differences (v1 n/a, v2 pass or fail): **{t['applicability']}**, all explained below.", "",
         "## How parity was achieved", "",
         "Every v1 per-agent check was transcribed into a side-effect-free expression in the agent's profile",
         "(`profiles/<agent>.yaml`) or in a shared, agent-free library (`profiles/_lib/*.yaml`) that the profile `extends`.",
         "Sample agents record plain-data snapshots of their scenario env and trace (`agentest.samples.record`) or of their",
         "mini-world (`agentest.samples.worlds`); the expectations judge those snapshots. A profile expectation is",
         "authoritative for its ID; IDs without one fall back to the built-in generic checks in `agentest.model.generic`.", "",
         "## Applicability differences", "",
         "| agent | ID | v1 | v2 | v2 detail | why |", "|---|---|---|---|---|---|"]
    for r in rows:
        L.append(f"| {r['agent']} | {r['id']} | {r['v1']} | {r['v2']} | {r['v2_detail'][:110].replace('|', '/')} | {'see below' if r['v2'] == 'fail' else 'generic default applies'} |")
    L += ["", "**v1 n/a, v2 pass.** " + WHY[("n/a", "pass")], "", "**v1 n/a, v2 fail.** " + WHY[("n/a", "fail")], ""]
    L += ["## Agents without a v1 baseline", "", "Added after v1.0.0 (A26 onward). Judged by v2 only, from their profiles:", "",
          "| agent | pass | fail | n/a |", "|---|---|---|---|"]
    L += [f"| {a} | {c.get('pass', 0)} | {c.get('fail', 0)} | {c.get('n/a', 0)} |" for a, c in extra.items()]
    (OUT / "PARITY.md").write_text("\n".join(L) + "\n")
    print(json.dumps({k: data[k] for k in ("v1_cells", "v1_fails", "v1_fails_caught_by_v2", "tally")}))


if __name__ == "__main__":
    main()
