#!/usr/bin/env python3
"""Verify published row and class counts for the pinned Hugging Face checklist dataset.

Reads the pinned revision in ``scripts/hf_dataset_counts.json`` over HTTPS using the
standard library only (no GPU, no model, no third-party dependencies). Exits 1 if any
expected row count, class count, starter_set split or ID uniqueness check fails.

Usage:
    python scripts/check_hf_dataset_counts.py
    python scripts/check_hf_dataset_counts.py --manifest scripts/hf_dataset_counts.json
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import sys
import urllib.request
from collections import Counter
from collections.abc import Callable
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "scripts" / "hf_dataset_counts.json"
DATASET_URL = "https://huggingface.co/datasets/srinivaspadmanabhuni/agentic-ai-test-checklist-110"


def _fetch_csv(url: str, timeout: float = 30.0) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "agentest-release-count-check"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 (https Hub URL)
        return resp.read().decode("utf-8")


def _parse_rows(text: str) -> list[dict[str, str]]:
    return list(csv.DictReader(io.StringIO(text)))


def check_counts(
    manifest: dict,
    fetch_text: Callable[[str], str] = _fetch_csv,
) -> list[str]:
    """Compare live Hub CSV files at ``manifest['revision']`` against pinned counts."""
    dataset = manifest["dataset"]
    base = DATASET_URL.replace("srinivaspadmanabhuni/agentic-ai-test-checklist-110", dataset)
    revision = manifest["revision"]

    def rows_for(rel_path: str) -> list[dict[str, str]]:
        return _parse_rows(fetch_text(f"{base}/resolve/{revision}/{rel_path}"))

    errors: list[str] = []

    all_spec = manifest["all"]
    all_rows = rows_for(all_spec["file"])
    if len(all_rows) != all_spec["rows"]:
        errors.append(f"all rows: expected {all_spec['rows']}, got {len(all_rows)}")
    ids = [r.get("id", "") for r in all_rows]
    if all_spec.get("unique_ids", True):
        dups = sorted(k for k, v in Counter(ids).items() if v > 1)
        if dups:
            errors.append(f"all duplicate IDs: {dups}")
    classes = dict(sorted(Counter(r.get("class_id", "") for r in all_rows).items()))
    if classes != all_spec["classes"]:
        errors.append(f"all class counts: expected {all_spec['classes']}, got {classes}")

    enr_spec = manifest["enriched"]
    enr_rows = rows_for(enr_spec["file"])
    if len(enr_rows) != enr_spec["rows"]:
        errors.append(f"enriched rows: expected {enr_spec['rows']}, got {len(enr_rows)}")
    starter = dict(sorted(Counter((r.get("starter_set") or "").strip().lower() for r in enr_rows).items()))
    if starter != enr_spec["starter_set"]:
        errors.append(f"enriched starter_set: expected {enr_spec['starter_set']}, got {starter}")

    traces_spec = manifest["traces"]
    traces_rows = rows_for(traces_spec["file"])
    if len(traces_rows) != traces_spec["rows"]:
        errors.append(f"traces rows: expected {traces_spec['rows']}, got {len(traces_rows)}")

    p0_spec = manifest["p0_smoke"]
    p0_rows = rows_for(p0_spec["file"])
    if len(p0_rows) != p0_spec["rows"]:
        errors.append(f"p0_smoke rows: expected {p0_spec['rows']}, got {len(p0_rows)}")

    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    args = parser.parse_args(argv)

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    errors = check_counts(manifest)
    if errors:
        for err in errors:
            print(f"ERROR: {err}", file=sys.stderr)
        return 1
    print(
        f"OK {manifest['dataset']}@{manifest['revision'][:12]} ({manifest['version']}): "
        f"all={manifest['all']['rows']}, enriched={manifest['enriched']['rows']}, "
        f"traces={manifest['traces']['rows']}, p0_smoke={manifest['p0_smoke']['rows']}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
