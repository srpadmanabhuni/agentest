#!/usr/bin/env python3
"""Version-stamp drift check (offline). RELEASE is the single source of truth.

Checks: pyproject version; every ``agentest...@vX.Y.Z`` install pin in README.md and docs/ (docs/history excluded);
the standards package docstring; catalog/VERSION catalog_revision; the README coverage table has a row for the
current release whose numbers equal docs/COVERAGE.md. With ``--card PATH`` it also checks a local copy of the
Hugging Face dataset card (version line, badge, install pin, concept DOI, versionless exports filename).

  python scripts/check_versions.py                  # verify (CI)
  python scripts/check_versions.py --bump           # rewrite stamps from RELEASE (README table rows are not invented)
  python scripts/check_versions.py --card README.md --bump   # also bump an HF card copy
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PIN = re.compile(r"(agentest(?:\.git)?@)v(\d+\.\d+\.\d+)")


def release() -> dict[str, str]:
    """Parse RELEASE (``key: value``; ``#`` comments ignored)."""
    out = {}
    for raw in (ROOT / "RELEASE").read_text().splitlines():
        line = raw.split("#")[0].strip()
        if ":" in line:
            k, _, v = line.partition(":")
            out[k.strip()] = v.strip()
    return out


def doc_files() -> list[Path]:
    """README plus docs/*.md, excluding frozen history."""
    return [ROOT / "README.md"] + [p for p in sorted((ROOT / "docs").rglob("*.md")) if "history" not in p.parts]


def coverage_buckets() -> dict[str, list[str]]:
    """Bucket rows of docs/COVERAGE.md keyed by mode."""
    out = {}
    for line in (ROOT / "docs" / "COVERAGE.md").read_text().splitlines():
        m = re.fullmatch(r"\| (strict|examples) \| ([\d |]+)\|", line.strip())
        if m:
            out[m.group(1)] = [c.strip() for c in m.group(2).split("|") if c.strip()]
    return out


def check_repo(rel: dict[str, str], bump: bool) -> list[str]:
    """Return drift errors for the repo (rewriting first when ``bump``)."""
    errs, ver = [], rel["agentest"]
    py = ROOT / "pyproject.toml"
    t = py.read_text()
    if bump:
        t = re.sub(r'(?m)^version = "[^"]+"', f'version = "{ver}"', t, count=1)
        py.write_text(t)
    if f'version = "{ver}"' not in t:
        errs.append(f"pyproject.toml version != {ver}")
    for p in doc_files():
        t = p.read_text(encoding="utf-8")
        if bump:
            t2 = PIN.sub(lambda m: f"{m.group(1)}v{ver}", t)
            if t2 != t:
                p.write_text(t2, encoding="utf-8")
                t = t2
        for m in PIN.finditer(t):
            if m.group(2) != ver:
                errs.append(f"{p.relative_to(ROOT)} install pin @v{m.group(2)} != v{ver}")
    pkg = ROOT / "src" / "agentest" / "__init__.py"
    t = pkg.read_text()
    if bump:
        t = re.sub(r'__version__ = "[^"]+"', f'__version__ = "{ver}"', t, count=1)
        pkg.write_text(t)
    if f'__version__ = "{ver}"' not in t:
        errs.append(f"src/agentest/__init__.py __version__ != {ver}")
    init = ROOT / "src" / "agentest" / "standards" / "__init__.py"
    t = init.read_text()
    if bump:
        t = re.sub(r"agent-agnostic checks \(v[\d.]+\)", f"agent-agnostic checks (v{ver})", t, count=1)
        init.write_text(t)
    if f"agent-agnostic checks (v{ver})" not in t:
        errs.append(f"src/agentest/standards/__init__.py docstring != v{ver}")
    cat = ROOT / "catalog" / "VERSION"
    t = cat.read_text()
    if bump:
        t = re.sub(r"(?m)^catalog_revision: .*$", f"catalog_revision: {rel['dataset']}", t)
        cat.write_text(t)
    if f"catalog_revision: {rel['dataset']}\n" not in t:
        errs.append(f"catalog/VERSION catalog_revision != {rel['dataset']}")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    doi = rel["zenodo_concept_doi"]
    for name, text in (("README.md", readme), ("CITATION.cff", (ROOT / "CITATION.cff").read_text(encoding="utf-8"))):
        if doi not in text:
            errs.append(f"{name} does not cite the all-versions concept DOI {doi}")
    for mode, cells in coverage_buckets().items():
        row = re.search(rf"(?m)^\| v{re.escape(ver)} \([^)]*\) \| {mode} \| (.*)\|$", readme)
        if not row:
            errs.append(f"README coverage table has no v{ver} {mode} row")
        elif [c.strip() for c in row.group(1).split("|")] != cells:
            errs.append(f"README coverage v{ver} {mode} row != docs/COVERAGE.md {cells}")
    return errs


def check_card(path: Path, rel: dict[str, str], bump: bool) -> list[str]:
    """Return drift errors for a local copy of the HF dataset card."""
    ver, ds, doi = rel["agentest"], rel["dataset"], rel["zenodo_concept_doi"]
    t = path.read_text(encoding="utf-8")
    if bump:
        t = PIN.sub(lambda m: f"{m.group(1)}v{ver}", t)
        t = re.sub(r"Checklist v\d+\.\d+\.\d+ \([\d-]+\)", lambda m: re.sub(r"v[\d.]+", ds, m.group(0)), t)
        t = re.sub(r"badge/GitHub-agentest%20v[\d.]+", f"badge/GitHub-agentest%20v{ver}", t)
        t = re.sub(r"\[!\[GitHub: agentest[^\]]*\]", f"[![GitHub: agentest v{ver}]", t)
        t = re.sub(r"\*\*\[agentest\]\(([^)]+)\)\*\* \(v[\d.]+,", rf"**[agentest](\1)** (v{ver},", t)
        path.write_text(t, encoding="utf-8")
    errs = [f"card pin @v{m.group(2)} != v{ver}" for m in PIN.finditer(t) if m.group(2) != ver]
    if not re.search(rf"Checklist {re.escape(ds)} \(", t):
        errs.append(f"card version line is not Checklist {ds}")
    if f"agentest%20v{ver}" not in t or f"GitHub: agentest v{ver}]" not in t:
        errs.append(f"card badge != agentest v{ver}")
    if re.search(r"\*\*\[agentest\]\([^)]+\)\*\* \(v(?!" + re.escape(ver) + r",)", t):
        errs.append(f"card body agentest version != v{ver}")
    if not re.search(rf"\(all versions\)[^\n]*{re.escape(doi)}", t):
        errs.append(f"card does not cite the Zenodo concept DOI {doi} labelled (all versions)")
    if re.search(r"(?i)zenodo[^\n]*\bv1\.\d", t.split("## Citation")[0].split("**Version:**")[-1].split("\n\n")[0]):
        errs.append("card Zenodo line carries a version number")
    if re.search(r"exports/agentic-ai-test-checklist-110-v[\d.]+\.xlsx", t):
        errs.append("card links a versioned exports workbook filename")
    return errs


def main(argv: list[str] | None = None) -> int:
    """CLI entry point; exit 0 when every stamp matches RELEASE."""
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--bump", action="store_true", help="rewrite stamps from RELEASE, then verify")
    ap.add_argument("--card", type=Path, help="local copy of the HF dataset card README.md")
    a = ap.parse_args(argv)
    rel = release()
    errs = check_repo(rel, a.bump)
    if a.card:
        errs += check_card(a.card, rel, a.bump)
    for e in errs:
        print("ERROR", e)
    print(f"version check (agentest v{rel['agentest']}, dataset {rel['dataset']}) " + ("FAILED" if errs else "passed"))
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
