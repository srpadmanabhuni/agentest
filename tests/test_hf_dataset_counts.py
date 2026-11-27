"""Offline unit tests for scripts/check_hf_dataset_counts.py."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "scripts" / "hf_dataset_counts.json"

spec = importlib.util.spec_from_file_location("check_hf_dataset_counts", ROOT / "scripts" / "check_hf_dataset_counts.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def _sample_tables(manifest: dict) -> dict[str, str]:
    all_lines = ["id,class_id"]
    for cls, count in manifest["all"]["classes"].items():
        for idx in range(1, count + 1):
            all_lines.append(f"{cls}-{idx:03d},{cls}")

    enr_lines = ["id,starter_set"]
    for idx in range(manifest["enriched"]["starter_set"]["yes"]):
        enr_lines.append(f"Y-{idx},yes")
    for idx in range(manifest["enriched"]["starter_set"]["no"]):
        enr_lines.append(f"N-{idx},no")

    traces_lines = ["trace_id"] + [f"TR-{i}" for i in range(manifest["traces"]["rows"])]
    p0_lines = ["id"] + [f"P0-{i}" for i in range(manifest["p0_smoke"]["rows"])]

    return {
        manifest["all"]["file"]: "\n".join(all_lines) + "\n",
        manifest["enriched"]["file"]: "\n".join(enr_lines) + "\n",
        manifest["traces"]["file"]: "\n".join(traces_lines) + "\n",
        manifest["p0_smoke"]["file"]: "\n".join(p0_lines) + "\n",
    }


def _fetcher(tables: dict[str, str]):
    def fetch(url: str) -> str:
        for rel, body in tables.items():
            if url.endswith("/" + rel):
                return body
        raise AssertionError(f"unexpected URL: {url}")

    return fetch


def test_pinned_manifest_passes_when_counts_match():
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    tables = _sample_tables(manifest)
    assert mod.check_counts(manifest, _fetcher(tables)) == []


def test_check_fails_on_added_removed_or_duplicate_rows():
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))

    # Duplicate ID in `all`
    dup_tables = _sample_tables(manifest)
    lines = dup_tables[manifest["all"]["file"]].splitlines()
    lines[2] = lines[1]  # duplicate T1-001
    dup_tables[manifest["all"]["file"]] = "\n".join(lines) + "\n"
    errs = mod.check_counts(manifest, _fetcher(dup_tables))
    assert any("duplicate IDs" in e for e in errs)

    # Extra row in `traces`
    extra_trace = _sample_tables(manifest)
    extra_trace[manifest["traces"]["file"]] += "TR-extra\n"
    errs = mod.check_counts(manifest, _fetcher(extra_trace))
    assert any("traces rows" in e for e in errs)

    # Missing row in `p0_smoke`
    short_p0 = _sample_tables(manifest)
    short_p0[manifest["p0_smoke"]["file"]] = "\n".join(short_p0[manifest["p0_smoke"]["file"]].splitlines()[:-1]) + "\n"
    errs = mod.check_counts(manifest, _fetcher(short_p0))
    assert any("p0_smoke rows" in e for e in errs)

    # Shifted `starter_set` split in `enriched`
    shifted_enr = _sample_tables(manifest)
    shifted_enr[manifest["enriched"]["file"]] = shifted_enr[manifest["enriched"]["file"]].replace("Y-0,yes", "Y-0,no", 1)
    errs = mod.check_counts(manifest, _fetcher(shifted_enr))
    assert any("enriched starter_set" in e for e in errs)
