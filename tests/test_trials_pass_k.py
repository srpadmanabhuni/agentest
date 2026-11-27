"""Regression test for examples/trials_pass_k/: 3 tasks x 3 trials and pass@1 / pass@3 / pass^3 output."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import jsonschema

from agentest.cli import main as agentest_main
from agentest.standards import metadata

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples" / "trials_pass_k"
SCHEMA = json.loads((ROOT / "src" / "agentest" / "standards" / "schemas" / "verdicts.schema.json").read_text(encoding="utf-8"))
GOV_SCHEMA = json.loads(
    (ROOT / "src" / "agentest" / "standards" / "schemas" / "governance-extension.schema.json").read_text(encoding="utf-8")
)

EXPECTED_TABLE = "\n".join([
    "task           passes    pass@1    pass@3    pass^3",
    "-------------  ------  --------  --------  --------",
    "task_reliable     3/3    1.0000    1.0000    1.0000",
    "task_flaky        2/3    0.6667    1.0000    0.0000",
    "task_failing      0/3    0.0000    0.0000    0.0000",
])


def _load_pass_k():
    spec = importlib.util.spec_from_file_location("trials_pass_k", EXAMPLE / "pass_k.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_example_metadata_is_valid():
    agents = metadata.load_all(EXAMPLE)
    assert list(agents) == ["trial_bot"]
    assert metadata.validate(agents["trial_bot"]) == []
    gov_validator = jsonschema.Draft202012Validator(GOV_SCHEMA)
    for ext in agents["trial_bot"].card.get("capabilities", {}).get("extensions", []):
        if ext.get("uri") == "urn:agentest:a2a-ext:governance:v1":
            assert list(gov_validator.iter_errors(ext.get("params", {}))) == []


def test_pass_k_from_std_run_json_matches_pinned_numbers(tmp_path):
    report = tmp_path / "verdicts.json"
    assert agentest_main(["std", "run", "--agents", str(EXAMPLE), "--format", "json", "--out", str(report)]) == 0

    doc = json.loads(report.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator(SCHEMA).validate(doc)
    assert [(row["task"], row["passes"], row["k"]) for row in doc["trials"]] == [
        ("task_reliable", 3, 3),
        ("task_flaky", 2, 3),
        ("task_failing", 0, 3),
    ]

    # Computing pass@k and pass^k stays strictly outside the scorer.
    pass_k = _load_pass_k()
    rows = pass_k.summarize_trials(pass_k.load_trials(report))
    assert [(r["task"], round(r["pass@1"], 4), round(r["pass@k"], 4), round(r["pass^k"], 4)) for r in rows] == [
        ("task_reliable", 1.0, 1.0, 1.0),
        ("task_flaky", 0.6667, 1.0, 0.0),
        ("task_failing", 0.0, 0.0, 0.0),
    ]

    proc = subprocess.run(
        [sys.executable, str(EXAMPLE / "pass_k.py"), str(report)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() == EXPECTED_TABLE

    piped = subprocess.run(
        [sys.executable, str(EXAMPLE / "pass_k.py"), "-"],
        input=report.read_text(encoding="utf-8"),
        capture_output=True,
        text=True,
        check=False,
    )
    assert piped.returncode == 0, piped.stderr
    assert piped.stdout.strip() == EXPECTED_TABLE


def test_pass_k_rejects_json_without_trials(tmp_path):
    bad = tmp_path / "plain.json"
    bad.write_text('{"trial_bot": {"T1-001": {"status": "pass", "detail": "ok"}}}', encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, str(EXAMPLE / "pass_k.py"), str(bad)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 2
    assert "trials" in proc.stderr
