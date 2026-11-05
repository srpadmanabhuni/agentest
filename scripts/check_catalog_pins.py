#!/usr/bin/env python3
"""Offline catalogue pin check: vendored pack CSVs and the runtime catalogue (checklist-110.jsonl) must match
the sha256 pins in catalog/VERSION, the jsonl control_refs must equal the pack CSVs row for row, and no retracted
pre-v1.2.1 control_refs token may appear anywhere in the catalogue.

No network, no token. Usage:
  python scripts/check_catalog_pins.py                 # verify
  python scripts/check_catalog_pins.py --write-hashes  # refresh pins after an intentional CSV change
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "catalog"
VERSION_PATH = CATALOG / "VERSION"
JSONL = "checklist-110.jsonl"
ADDITIONS = "rai-additions-v1.4.0.jsonl"  # dataset v1.4.0 config rai_additions: rules in rules.py
# Retracted in dataset v1.2.1: old OWASP names, NIST sub-categories, unverified ISO/IEC 42001 Annex codes.
RETRACTED = (re.compile(r"ISO42001:A\.\d"), re.compile(r"NIST-AI-RMF:(GOVERN|MAP|MEASURE|MANAGE)-\d"),
             re.compile(r"OWASP-ASI:(?!ASI\d{2}\b)[A-Za-z]"))


def parse_version(text: str) -> dict[str, str]:
    """Parse ``key: value`` lines of catalog/VERSION (``#`` comments ignored)."""
    out: dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.split("  #")[0].strip()
        if line and not line.startswith("#") and ":" in line:
            k, _, val = line.partition(":")
            out[k.strip()] = val.strip()
    return out


def sha256_file(path: Path) -> str:
    """Hex sha256 of a file."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check(meta: dict[str, str]) -> list[str]:
    """Return a list of pin errors (empty when every in-scope pack matches)."""
    errors = []
    packs = [p.strip() for p in meta.get("packs_in_scope", "").split(",") if p.strip()]
    if not packs:
        return ["catalog/VERSION has no packs_in_scope"]
    if not meta.get("catalog_revision"):
        errors.append("catalog/VERSION missing catalog_revision")
    for p in packs:
        path = CATALOG / f"{p}.csv"
        if not path.is_file():
            errors.append(f"missing {path}")
            continue
        exp, act = meta.get(f"sha256_{p}"), sha256_file(path)
        if exp != act:
            errors.append(f"{p}.csv pin mismatch: pinned {exp}, actual {act}")
        else:
            print(f"OK {p}.csv {act[:12]}")
    errors += check_jsonl(meta, packs)
    errors += check_additions(meta)
    return errors


def check_jsonl(meta: dict[str, str], packs: list[str]) -> list[str]:
    """Pin the runtime catalogue and cross-check its control_refs against the pack CSVs."""
    path = CATALOG / JSONL
    if not path.is_file():
        return [f"missing {path}"]
    errors = []
    exp, act = meta.get("sha256_checklist_110"), sha256_file(path)
    if exp != act:
        errors.append(f"{JSONL} pin mismatch: pinned {exp}, actual {act}")
    rows = {r["id"]: r for r in map(json.loads, path.read_text(encoding="utf-8").splitlines()) if r}
    if len(rows) != 110:
        errors.append(f"{JSONL} has {len(rows)} ids, expected 110")
    for i, r in rows.items():
        for rx in RETRACTED:
            if rx.search(r.get("control_refs", "")):
                errors.append(f"{JSONL} {i} carries retracted control_refs token: {r['control_refs']}")
                break
    for p in packs:
        with (CATALOG / f"{p}.csv").open(encoding="utf-8", newline="") as fh:
            for row in csv.DictReader(fh):
                j = rows.get(row["id"])
                if j is None:
                    errors.append(f"{p}.csv {row['id']} not in {JSONL}")
                elif j.get("control_refs") != row.get("control_refs"):
                    errors.append(f"{p}.csv {row['id']} control_refs differ from {JSONL}")
    if not errors:
        print(f"OK {JSONL} {act[:12]} (110 ids, control_refs match packs, no retracted tokens)")
    return errors


def check_additions(meta: dict[str, str]) -> list[str]:
    """Pin the dataset v1.4.0 responsible-AI additions: same columns as the 110, new ids only, no retracted tokens."""
    path = CATALOG / ADDITIONS
    if not path.is_file():
        return [f"missing {path}"]
    errors = []
    exp, act = meta.get("sha256_rai_additions"), sha256_file(path)
    if exp != act:
        errors.append(f"{ADDITIONS} pin mismatch: pinned {exp}, actual {act}")
    main = [json.loads(x) for x in (CATALOG / JSONL).read_text(encoding="utf-8").splitlines() if x]
    keys, ids = list(main[0]), {r["id"] for r in main}
    rows = [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x]
    if len(rows) != 5:
        errors.append(f"{ADDITIONS} has {len(rows)} rows, expected 5")
    for r in rows:
        if list(r) != keys:
            errors.append(f"{ADDITIONS} {r.get('id')} columns differ from {JSONL}")
        if r.get("id") in ids:
            errors.append(f"{ADDITIONS} {r['id']} reuses a catalogue id")
        if any(rx.search(r.get("control_refs", "")) for rx in RETRACTED):
            errors.append(f"{ADDITIONS} {r.get('id')} carries retracted control_refs token")
    if not errors:
        print(f"OK {ADDITIONS} {act[:12]} (5 new ids, same columns, no retracted tokens)")
    return errors


def write_hashes(meta: dict[str, str]) -> None:
    """Rewrite the sha256_* lines in catalog/VERSION from the current CSVs."""
    packs = [p.strip() for p in meta["packs_in_scope"].split(",") if p.strip()]
    lines = [ln for ln in VERSION_PATH.read_text().splitlines() if not ln.startswith("sha256_")]
    lines += [f"sha256_{p}: {sha256_file(CATALOG / f'{p}.csv')}" for p in packs]
    lines.append(f"sha256_checklist_110: {sha256_file(CATALOG / JSONL)}")
    lines.append(f"sha256_rai_additions: {sha256_file(CATALOG / ADDITIONS)}")
    VERSION_PATH.write_text("\n".join(lines) + "\n")


def main(argv: list[str] | None = None) -> int:
    """CLI entry point; exit 0 when pins match."""
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--write-hashes", action="store_true")
    a = ap.parse_args(argv)
    meta = parse_version(VERSION_PATH.read_text())
    if a.write_hashes:
        write_hashes(meta)
        return 0
    errs = check(meta)
    for e in errs:
        print("ERROR", e)
    print("catalogue pin check " + ("FAILED" if errs else "passed"))
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
