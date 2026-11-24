#!/usr/bin/env python3
"""Turn the Agentic AI Test Checklist 110 into a test plan for your agent, then fill it with agentest verdicts.

Course / cohort exercise. Offline by default: it reads the checklist rows bundled in this repo
(catalog/checklist-110.jsonl, the same rows as the published dataset). With --hub it loads the published
Hugging Face dataset instead, at one pinned revision, through the `datasets` cache (fetched once, reused
after). Standard library only unless --hub is used.

    python examples/course/test_plan.py --stage tool --priority P0 --out plan.csv
    python examples/course/test_plan.py --ids T1-018,T2-001,T4-003,T7-014 --out plan.csv \\
        --verdicts-from refill_bot_buggy
    python examples/course/test_plan.py --hub --priority P0 --out plan.csv     # needs: pip install datasets
"""
import argparse
import csv
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
BUNDLED = ROOT / "catalog" / "checklist-110.jsonl"
DATASET = "srinivaspadmanabhuni/agentic-ai-test-checklist-110"
REVISION = "04c1ec17265da1a2a484f3daa361e725af167363"  # same pin as agentest --hub-catalogue (catalogue v1.3.1 rows)
COLUMNS = ["id", "title", "priority", "severity", "agent_stage", "acceptance_criteria", "pass_signal",
           "fail_signal", "fixture_needed", "owner", "manual_review_done", "agentest_verdict", "agentest_detail"]


def load_rows(hub=False):
    if not hub:
        return [json.loads(line) for line in BUNDLED.read_text(encoding="utf-8").splitlines() if line.strip()]
    from datasets import load_dataset  # optional; cached by the datasets library after the first fetch
    return list(load_dataset(DATASET, "all", split="train", revision=REVISION))


def select(rows, ids=None, priority=None, stage=None, class_id=None):
    out = []
    for r in rows:
        if ids and r["id"] not in ids:
            continue
        if priority and r.get("priority") != priority:
            continue
        if stage and stage not in str(r.get("agent_stage", "")):
            continue
        if class_id and r.get("class_id") != class_id:
            continue
        out.append(r)
    return out


def verdicts(agent, ids):
    """Run agentest on a bundled example agent and return {id: (status, detail)}."""
    cmd = [sys.executable, "-m", "agentest", "std", "run", "--agents", "examples/agnostic_demo/agents",
           "--agent", agent, "--ids", ",".join(ids), "--format", "json"]
    p = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=300)
    data = json.loads(p.stdout)
    return {row["id"]: (row.get("status", ""), row.get("detail", "")) for row in data.get("results", [])}


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--hub", action="store_true", help="load the published dataset at the pinned revision (needs datasets)")
    ap.add_argument("--ids", help="comma-separated test IDs")
    ap.add_argument("--priority", choices=["P0", "P1", "P2"])
    ap.add_argument("--stage", help="substring of agent_stage, e.g. tool, memory, output")
    ap.add_argument("--class-id", help="T1 .. T7")
    ap.add_argument("--verdicts-from", metavar="AGENT", help="fill verdicts from a bundled example agent, e.g. refill_bot_buggy")
    ap.add_argument("--out", required=True)
    ns = ap.parse_args()
    rows = select(load_rows(ns.hub), set(ns.ids.split(",")) if ns.ids else None, ns.priority, ns.stage, ns.class_id)
    found = verdicts(ns.verdicts_from, [r["id"] for r in rows]) if ns.verdicts_from and rows else {}
    with open(ns.out, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS)
        w.writeheader()
        for r in rows:
            st, detail = found.get(r["id"], ("", ""))
            w.writerow({**{k: r.get(k, "") for k in COLUMNS[:9]}, "owner": "", "manual_review_done": "",
                        "agentest_verdict": st, "agentest_detail": detail})
    print(f"wrote {len(rows)} test(s) to {ns.out}")


if __name__ == "__main__":
    main()
