"""`scripts/eval_verdicts.py` / `make eval`: public example agents only, per-check summary, before/after diff."""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "eval_verdicts.py"
spec = importlib.util.spec_from_file_location("eval_verdicts", SCRIPT)
ev = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ev)


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(SCRIPT), *args], cwd=ROOT, text=True, capture_output=True, timeout=300)


def test_eval_matches_the_verdict_snapshot_and_prints_one_row_per_check():
    snap = ev.compute(ROOT)
    want = json.loads((ROOT / "fixtures" / "standards" / "v3-verdicts.json").read_text())
    assert snap["strict"] == want["strict"] and snap["examples"] == want["examples"]
    text = ev.summary(snap, ("examples",))
    assert "T2-001" in text and "X-020" in text and "pass" in text and "n/a" in text


def test_eval_reads_only_public_example_agents():
    roots = [d for _, d in ev._public_roots(ROOT)]
    assert roots and all(ev._inside(ROOT, d) for d in roots)
    src = SCRIPT.read_text(encoding="utf-8")
    for needle in ("/workspace", "/home/", "heldout", "held-out", "batch4", "HF_TOKEN", "environ[\"HF"):
        assert needle not in src, needle


def test_agents_outside_the_repo_are_refused(tmp_path):
    with pytest.raises(SystemExit) as e:
        ev.compute(ROOT, ["T2-001"], [tmp_path])
    assert "outside the repository root" in str(e.value)
    p = _run("--agents", str(tmp_path), "--quiet")
    assert p.returncode != 0 and "outside the repository root" in p.stderr


def test_root_without_agents_is_refused(tmp_path):
    with pytest.raises(SystemExit):
        ev.compute(tmp_path)


def test_diff_lists_changed_added_and_removed():
    base = {"ids": ["A-1", "A-2"], "strict": {"a": "P-", "gone": "PP"}, "examples": {"a": "P-", "gone": "PP"}}
    head = {"ids": ["A-1", "A-2"], "strict": {"a": "FP", "new": "PP"}, "examples": {"a": "P-", "new": "PP"}}
    d = ev.diff(base, head)
    assert d["changed"] == [
        {"mode": "strict", "agent": "a", "check": "A-1", "before": "pass", "after": "fail"},
        {"mode": "strict", "agent": "a", "check": "A-2", "before": "n/a", "after": "pass"},
    ]
    assert d["agents_added"] == ["new"] and d["agents_removed"] == ["gone"]
    text = ev.render_diff(d, "main")
    assert "A-1" in text and "pass -> fail" in text
    assert "No verdict differs" in ev.render_diff(ev.diff(base, base), "main")


def test_cli_json_and_base_diff_on_this_checkout():
    p = _run("--ids", "T2-001", "--quiet", "--json", "-")
    assert p.returncode == 0, p.stderr
    data = json.loads(p.stdout)
    assert data["ids"] == ["T2-001"] and set(data["strict"]) >= {"a01"}
    q = _run("--ids", "T2-001", "--base", "HEAD", "--mode", "strict")
    assert q.returncode == 0, q.stderr
    assert "T2-001" in q.stdout and "No verdict differs from HEAD" in q.stdout


def test_unknown_base_ref_falls_back_to_the_summary():
    p = _run("--ids", "T2-001", "--base", "no-such-ref-xyz", "--mode", "strict")
    assert p.returncode == 0 and "not found" in p.stdout


def test_makefile_and_docs_exist():
    mk = (ROOT / "Makefile").read_text()
    assert "eval:" in mk and "eval_verdicts.py" in mk
    doc = (ROOT / "docs" / "contributing" / "EVAL.md").read_text()
    assert "make eval" in doc and "python scripts/eval_verdicts.py" in doc
