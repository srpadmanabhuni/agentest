#!/usr/bin/env python3
"""Export the 110 checklist designs as study flashcards (CSV that Anki and most flashcard apps import).

Front: test ID and title. Back: objective, pass signal and fail signal. Tags: class, priority, severity.
Reads the rows bundled in this repo (catalog/checklist-110.jsonl); standard library only, offline.

    python scripts/checklist_flashcards.py --out agentest-flashcards.csv
    python scripts/checklist_flashcards.py --priority P0 --out p0-flashcards.csv

Anki: File > Import, choose the CSV, separator Comma, field 1 = Front, field 2 = Back, field 3 = Tags.
"""
import argparse
import csv
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
CATALOG = ROOT / "catalog" / "checklist-110.jsonl"


def cards(priority=None):
    for line in CATALOG.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        if priority and r["priority"] != priority:
            continue
        front = f"{r['id']}: {r['title']}"
        back = (f"{r['objective']}<br><br><b>Pass:</b> {r['pass_signal']}<br><b>Fail:</b> {r['fail_signal']}"
                f"<br><br>{r['class_id']} {r['class_name']}")
        tags = " ".join(["agentest", r["class_id"], r["priority"], r["severity"]])
        yield front, back, tags


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--priority", choices=["P0", "P1", "P2"])
    ap.add_argument("--out", required=True)
    ns = ap.parse_args()
    rows = list(cards(ns.priority))
    with open(ns.out, "w", newline="", encoding="utf-8") as fh:
        csv.writer(fh).writerows(rows)
    print(f"wrote {len(rows)} card(s) to {ns.out}")


if __name__ == "__main__":
    main()
