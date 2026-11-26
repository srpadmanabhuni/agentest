#!/usr/bin/env python3
"""Re-run every failure registry entry and check its recorded verdicts.

    python scripts/run_registry.py                 # validate and re-run every entry in registry/entries/
    python scripts/run_registry.py --entry AFR-0002
    python scripts/run_registry.py --write-index   # rewrite docs/registry/INDEX.md
    python scripts/run_registry.py --check-index   # exit 1 if docs/registry/INDEX.md is stale

For each entry it checks: the JSON matches registry/schema/afr-entry.schema.json; the file name is the ID; the trace,
card and tools paths exist; the category and ASI IDs agree with taxonomy/asi-mapping.yaml; ``failing_checks`` is exactly
the set expected to fail on the original run; and ``agentest`` gives every expected verdict on every variant. The recorded
traces are judged, so no model, key or network is needed. An entry with status ``withdrawn`` keeps its ID and is not re-run.
"""
# Ref: failure registry schema registry/schema/afr-entry.schema.json; taxonomy docs/taxonomy/TAXONOMY.md.

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
ENTRIES = ROOT / "registry" / "entries"
SCHEMA = ROOT / "registry" / "schema" / "afr-entry.schema.json"
MAPPING = ROOT / "taxonomy" / "asi-mapping.yaml"
INDEX = ROOT / "docs" / "registry" / "INDEX.md"


def load_entries(only: str | None = None) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for p in sorted(ENTRIES.glob("AFR-*.json")):
        if only and p.stem != only:
            continue
        out[p.stem] = json.loads(p.read_text(encoding="utf-8"))
    return out


def validate(entry: dict, name: str) -> list[str]:
    """Schema and cross-file problems for one entry (empty list = fine)."""
    import jsonschema

    problems: list[str] = []
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    for err in sorted(jsonschema.Draft202012Validator(schema).iter_errors(entry), key=lambda e: list(e.path)):
        problems.append(f"schema: {'/'.join(map(str, err.path)) or '(entry)'}: {err.message}")
    if problems:
        return problems
    if entry["id"] != name:
        problems.append(f"file name {name}.json does not match id {entry['id']}")
    mapping = yaml.safe_load(MAPPING.read_text(encoding="utf-8"))
    if str(entry["taxonomy_version"]) != str(mapping["taxonomy_version"]):
        problems.append(f"taxonomy_version {entry['taxonomy_version']} is not the current {mapping['taxonomy_version']}")
    if entry["category"] not in mapping["categories"]:
        problems.append(f"unknown category {entry['category']}")
    covered: set[str] = set()
    cats: set[str] = set()
    for cid in entry["failing_checks"]:
        meta = mapping["checks"].get(cid)
        if meta is None:
            problems.append(f"failing check {cid} is not in taxonomy/asi-mapping.yaml")
            continue
        covered |= {a["id"] for a in meta["asi"]}
        cats.add(meta["category"])
    if entry["category"] not in cats:
        problems.append(f"category {entry['category']} is not the category of any failing check ({sorted(cats)})")
    extra = set(entry["asi"]) - covered
    if extra:
        problems.append(f"asi {sorted(extra)} is not in the mapping of the failing checks")
    original = entry["variants"]["original"]["expected_verdicts"]
    expected_fail = {c for c, v in original.items() if v == "fail"}
    if expected_fail != set(entry["failing_checks"]):
        problems.append(f"failing_checks {sorted(entry['failing_checks'])} must equal the checks expected to fail on the original run {sorted(expected_fail)}")
    fixed = entry["variants"].get("fixed")
    if fixed and any(v == "fail" for v in fixed["expected_verdicts"].values()):
        problems.append("the fixed variant expects a fail verdict")
    for vname, v in entry["variants"].items():
        for key in ("trace", "card", "tools"):
            if key in v and not (ROOT / v[key]).is_file():
                problems.append(f"variants.{vname}.{key}: {v[key]} does not exist")
    lab = entry["links"].get("lab")
    if lab and not (ROOT / lab).exists():
        problems.append(f"links.lab: {lab} does not exist")
    for token in re.findall(r"[\w./-]+\.py", entry["reproduce"]["command"]):
        if not (ROOT / token).is_file():
            problems.append(f"reproduce.command mentions {token}, which does not exist")
    return problems


def judge(entry: dict) -> list[str]:
    """Run agentest on each variant's recorded trace and compare every expected verdict."""
    import agentest

    problems: list[str] = []
    for vname, v in entry["variants"].items():
        kw = {}
        if "card" in v:
            kw["card"] = ROOT / v["card"]
        if "tools" in v:
            kw["tools"] = ROOT / v["tools"]
        ids = sorted(v["expected_verdicts"])
        got = {c.id: c.status for c in agentest.run(ROOT / v["trace"], ids=ids, **kw)}
        for cid in ids:
            if got.get(cid) != v["expected_verdicts"][cid]:
                problems.append(f"{vname}: {cid} expected {v['expected_verdicts'][cid]}, got {got.get(cid)}")
    return problems


def build_index(entries: dict[str, dict]) -> str:
    mapping = yaml.safe_load(MAPPING.read_text(encoding="utf-8"))
    L = ["# Failure registry index", "",
         "<!-- Generated by scripts/run_registry.py --write-index. Do not edit by hand. -->", "",
         "Reproducible agent failures, one entry per ID. How the registry works and how to add an entry: [registry/README.md](../../registry/README.md). "
         "Categories: [taxonomy](../taxonomy/TAXONOMY.md). OWASP entries are those the failing checks map to ([mapping](../taxonomy/ASI-MAPPING.md)).", "",
         "| ID | Failure | Category | ASI | Failing checks | Status | Lab | Added |", "|---|---|---|---|---|---|---|---|"]
    for name, e in entries.items():
        cat = f"{e['category']} {mapping['categories'][e['category']]['title']}"
        lab = f"[write-up](../../{e['links']['lab']})" if e["links"].get("lab") else ""
        L.append(f"| [{e['id']}](../../registry/entries/{name}.json) | {e['title']} | {cat} | {', '.join(e['asi']) or 'none'} | "
                 f"{', '.join(f'`{c}`' for c in e['failing_checks'])} | {e['status']} | {lab} | {e['added']} |")
    L.append("")
    return "\n".join(L)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--entry", help="only this entry, for example AFR-0002")
    ap.add_argument("--write-index", action="store_true")
    ap.add_argument("--check-index", action="store_true")
    a = ap.parse_args()
    entries = load_entries(a.entry)
    if a.entry and not entries:
        print(f"no entry {a.entry}", file=sys.stderr)
        return 2
    if a.write_index or a.check_index:
        text = build_index(load_entries())
        if a.write_index:
            INDEX.parent.mkdir(parents=True, exist_ok=True)
            INDEX.write_text(text, encoding="utf-8")
            print(f"wrote {INDEX.relative_to(ROOT)}")
            return 0
        if not INDEX.is_file() or INDEX.read_text(encoding="utf-8") != text:
            print("stale: docs/registry/INDEX.md; run python scripts/run_registry.py --write-index", file=sys.stderr)
            return 1
        return 0
    if not entries:
        print("registry is empty", file=sys.stderr)
        return 1
    failed = 0
    for name, entry in entries.items():
        problems = validate(entry, name)
        if not problems and entry["status"] != "withdrawn":
            problems = judge(entry)
        if problems:
            failed += 1
            print(f"FAIL {name}")
            for p in problems:
                print(f"  - {p}")
        else:
            note = " (withdrawn, not re-run)" if entry["status"] == "withdrawn" else ""
            checks = sum(len(v["expected_verdicts"]) for v in entry["variants"].values())
            print(f"ok   {name}  {entry['title']}  [{checks} verdicts]{note}")
    ids = sorted(entries)
    if not a.entry and ids != [f"AFR-{i:04d}" for i in range(1, len(ids) + 1)]:
        print("FAIL IDs must run AFR-0001, AFR-0002, ... with no gap or reuse (withdrawn entries keep their file)")
        failed += 1
    print(f"{len(entries) - failed} of {len(entries)} entries ok")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
