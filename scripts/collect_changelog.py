#!/usr/bin/env python3
"""Prepend changelog.d fragments under ## Unreleased in CHANGELOG.md.

Used at release time (see RELEASING.md). Does not delete fragment files unless
--delete is passed. Usage: python scripts/collect_changelog.py [--dry-run] [--delete]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHANGELOG = ROOT / "CHANGELOG.md"
FRAGMENTS = ROOT / "changelog.d"
SKIP = {"README.md"}


def fragment_paths() -> list[Path]:
    return sorted(
        p for p in FRAGMENTS.glob("*.md") if p.name not in SKIP and p.is_file()
    )


def load_bullets(paths: list[Path]) -> list[str]:
    bullets: list[str] = []
    for path in paths:
        text = path.read_text(encoding="utf-8").strip()
        if not text:
            raise SystemExit(f"{path}: fragment is empty")
        for raw in text.splitlines():
            line = raw.rstrip()
            if not line:
                continue
            if not line.startswith("- "):
                raise SystemExit(f"{path}: each non-empty line must start with '- '")
            bullets.append(line)
    return bullets


def insert(changelog: str, bullets: list[str]) -> str:
    needle = "## Unreleased\n"
    if needle not in changelog:
        raise SystemExit("CHANGELOG.md has no ## Unreleased heading")
    block = "".join(f"{b}\n" for b in bullets)
    if not block:
        return changelog
    parts = changelog.split(needle, 1)
    rest = parts[1].lstrip("\n")
    # Keep any intro note (text before the first existing bullet or next heading)
    return parts[0] + needle + "\n" + block + rest


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true", help="Print the bullets and do not write CHANGELOG.md")
    ap.add_argument("--delete", action="store_true", help="Delete fragment files after writing CHANGELOG.md")
    args = ap.parse_args()
    paths = fragment_paths()
    bullets = load_bullets(paths)
    if args.dry_run:
        if not bullets:
            print("no changelog.d fragments")
            return 0
        print("\n".join(bullets))
        return 0
    if not bullets:
        print("no changelog.d fragments to collect", file=sys.stderr)
        return 0
    CHANGELOG.write_text(insert(CHANGELOG.read_text(encoding="utf-8"), bullets), encoding="utf-8")
    print(f"prepended {len(bullets)} bullet(s) from {len(paths)} file(s)")
    if args.delete:
        for path in paths:
            path.unlink()
            print(f"deleted {path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
