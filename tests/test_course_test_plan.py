"""The course test-plan script works offline and its verdict columns match real agentest runs."""
import csv
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "examples/course/test_plan.py"
IDS = "T1-018,T2-001,T4-003,T7-014"


def run(tmp_path, *args):
    out = tmp_path / "plan.csv"
    p = subprocess.run([sys.executable, str(SCRIPT), *args, "--out", str(out)], cwd=ROOT,
                       capture_output=True, text=True, timeout=300)
    assert p.returncode == 0, (p.stdout, p.stderr)
    return list(csv.DictReader(out.open(encoding="utf-8")))


def test_p0_plan_offline(tmp_path):
    rows = run(tmp_path, "--priority", "P0")
    assert len(rows) == 47 and all(r["priority"] == "P0" for r in rows)
    assert {"owner", "manual_review_done", "agentest_verdict"} <= set(rows[0])


def test_buggy_fails_and_fixed_passes(tmp_path):
    buggy = run(tmp_path, "--ids", IDS, "--verdicts-from", "refill_bot_buggy")
    fixed = run(tmp_path, "--ids", IDS, "--verdicts-from", "refill_bot")
    assert [r["agentest_verdict"] for r in buggy] == ["fail"] * 4
    assert [r["agentest_verdict"] for r in fixed] == ["pass"] * 4


def test_pin_matches_hub_catalogue():
    from agentest.standards import hub
    assert hub.REVISION in SCRIPT.read_text(encoding="utf-8")
