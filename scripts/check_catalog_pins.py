#!/usr/bin/env python3
"""Offline catalogue pin check: vendored pack CSVs must match the sha256 pins in catalog/VERSION.

No network, no token. Usage:
  python scripts/check_catalog_pins.py                 # verify
  python scripts/check_catalog_pins.py --write-hashes  # refresh pins after an intentional CSV change
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "catalog"
VERSION_PATH = CATALOG / "VERSION"


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
    return errors


def write_hashes(meta: dict[str, str]) -> None:
    """Rewrite the sha256_* lines in catalog/VERSION from the current CSVs."""
    packs = [p.strip() for p in meta["packs_in_scope"].split(",") if p.strip()]
    lines = [ln for ln in VERSION_PATH.read_text(encoding="utf-8").splitlines() if not ln.startswith("sha256_")]
    lines += [f"sha256_{p}: {sha256_file(CATALOG / f'{p}.csv')}" for p in packs]
    VERSION_PATH.write_text("\n".join(lines) + "\n")


def main(argv: list[str] | None = None) -> int:
    """CLI entry point; exit 0 when pins match."""
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--write-hashes", action="store_true")
    a = ap.parse_args(argv)
    meta = parse_version(VERSION_PATH.read_text(encoding="utf-8"))
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
