"""Learning-path pages stay true: the from-scratch check prints what the page shows, flashcards cover all 110 rows."""
import csv
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_my_first_check_matches_page():
    p = subprocess.run([sys.executable, "examples/build_your_own/my_first_check.py",
                        "examples/first_trace/trace.otlp.json", "examples/first_trace/tools.json"],
                       cwd=ROOT, capture_output=True, text=True, timeout=60)
    assert p.returncode == 1
    assert p.stdout.strip() in (ROOT / "docs/BUILD-YOUR-OWN-AGENT-TEST.md").read_text(encoding="utf-8")


def test_flashcards_cover_catalogue(tmp_path):
    out = tmp_path / "cards.csv"
    subprocess.run([sys.executable, "scripts/checklist_flashcards.py", "--out", str(out)], cwd=ROOT, check=True)
    rows = list(csv.reader(out.open(encoding="utf-8")))
    assert len(rows) == 110 and all(len(r) == 3 for r in rows)
    out0 = tmp_path / "p0.csv"
    subprocess.run([sys.executable, "scripts/checklist_flashcards.py", "--priority", "P0", "--out", str(out0)],
                   cwd=ROOT, check=True)
    assert len(list(csv.reader(out0.open(encoding="utf-8")))) == 47


def test_pages_link_existing_check_pages():
    for page in ("BUILD-YOUR-OWN-AGENT-TEST.md", "LEARNING-ROADMAP.md"):
        text = (ROOT / "docs" / page).read_text(encoding="utf-8")
        for target in re.findall(r"\]\(([^)#]+\.md)", text):
            if target.startswith("http"):
                continue
            assert (ROOT / "docs" / target).resolve().exists(), (page, target)
