"""docs/FRAMEWORK.md and docs/coverage-map.json are current, cover all 110 IDs once, and use coverage wording only."""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_framework_files_current():
    r = subprocess.run([sys.executable, "scripts/gen_framework.py", "--check"], cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr


def test_every_catalogue_id_in_exactly_one_pillar():
    d = json.loads((ROOT / "docs" / "coverage-map.json").read_text())
    ids = [t["id"] for p in d["pillars"] for t in p["tests"]]
    cat = [json.loads(x)["id"] for x in (ROOT / "catalog" / "checklist-110.jsonl").read_text().splitlines() if x.strip()]
    assert len(d["pillars"]) == 4
    assert sorted(ids) == sorted(cat) and len(ids) == len(set(ids)) == 110


def test_coverage_wording_only():
    for name in ("FRAMEWORK.md", "coverage-map.json"):
        text = (ROOT / "docs" / name).read_text().lower()
        assert "%" not in text, name
        assert "not a compliance determination" in text, name
        assert "compliant" not in text and "compliance score" not in text, name
