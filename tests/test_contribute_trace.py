"""First-test pattern: one existing check, two synthetic traces, pass and fail.

The traces use record id R-1 and subject id S-1. They are not customer data.
See CONTRIBUTING.md, "Bring an agent trace, contribute a test".

The CLI block in walkthrough 1 is the tester journey: failing trace, evidence, fixed trace, rerun.
"""

import json
import subprocess
import sys
from pathlib import Path

from agentest.standards import metadata, runner

ROOT = Path(__file__).resolve().parents[1]
FIX = ROOT / "tests" / "fixtures" / "contribute"
WALK = ROOT / "docs" / "walkthroughs" / "01-verify-before-acting.md"
FAIL_DETAIL = "case-1#0:lookup_record before ['verify_identity']"
PASS_DETAIL = "prerequisites respected in 1 run(s)"
NA_DETAIL = "no standard signal: agent publishes no prerequisites"


def test_synthetic_prerequisite_order_has_a_pass_and_a_fail():
    res = runner.to_json(runner.run_all(metadata.load_all(FIX)))
    assert res["order_ok"]["T2-001"]["status"] == "pass"
    assert "prerequisites respected" in res["order_ok"]["T2-001"]["detail"]
    assert res["order_bad"]["T2-001"]["status"] == "fail"
    assert "lookup_record before" in res["order_bad"]["T2-001"]["detail"]


def test_synthetic_side_effect_cap_has_a_pass_and_a_fail():
    res = runner.to_json(runner.run_all(metadata.load_all(FIX), ids=["T2-003"]))
    assert res["side_effect_once"]["T2-003"]["status"] == "pass"
    assert res["side_effect_twice"]["T2-003"]["status"] == "fail"
    assert "submit_reimbursement" in res["side_effect_twice"]["T2-003"]["detail"]
def test_synthetic_exfil_url_has_a_pass_and_a_fail():
    res = runner.to_json(runner.run_all(metadata.load_all(FIX), ids=["T4-002"]))
    assert res["exfil_ignored"]["T4-002"]["status"] == "pass"
    assert res["exfil_fetched"]["T4-002"]["status"] == "fail"
    assert "exfil.invalid" in res["exfil_fetched"]["T4-002"]["detail"]
def test_synthetic_numeric_slot_has_a_pass_and_a_fail():
    res = runner.to_json(runner.run_all(metadata.load_all(FIX), ids=["T6-002"]))
    assert res["amount_holds"]["T6-002"]["status"] == "pass"
    assert res["amount_drifts"]["T6-002"]["status"] == "fail"
    assert "400" in res["amount_drifts"]["T6-002"]["detail"]
def test_synthetic_turn1_constraint_has_a_pass_and_a_fail():
    res = runner.to_json(runner.run_all(metadata.load_all(FIX), ids=["T6-001"]))
    assert res["constraint_holds"]["T6-001"]["status"] == "pass"
    assert res["constraint_drift"]["T6-001"]["status"] == "fail"
    assert "bob" in res["constraint_drift"]["T6-001"]["detail"]


def test_synthetic_entity_id_binding_has_a_pass_and_a_fail():
    loaded = metadata.load_all(FIX)
    res = runner.to_json(runner.run_all(loaded, ids=["T6-003"]))
    assert res["id_stable"]["T6-003"]["status"] == "pass"
    assert res["id_switches"]["T6-003"]["status"] == "fail"
    assert "TK-77" in res["id_switches"]["T6-003"]["detail"]

    # Verify genuinely multi-turn structure
    for key in ("id_stable", "id_switches"):
        runs = runner.runs(loaded[key])
        assert len(runs) == 1
        r = runs[0]
        assert len(r.turn_starts) >= 1
        assert [r.turn_of(t.t) for t in r.tools] == [0, 1]


def test_synthetic_injection_untrusted_content_has_a_pass_and_a_fail():
    loaded = metadata.load_all(FIX)
    res = runner.to_json(runner.run_all(loaded, ids=["T4-001"]))
    assert res["inject_ignored"]["T4-001"]["status"] == "pass"
    assert "no canary" in res["inject_ignored"]["T4-001"]["detail"]
    assert res["inject_obeyed"]["T4-001"]["status"] == "fail"
    assert "PWNED-001" in res["inject_obeyed"]["T4-001"]["detail"]


def test_fixture_traces_stay_synthetic():
    blob = "\n".join(p.read_text(encoding="utf-8") for p in FIX.rglob("*") if p.is_file())
    low = blob.lower()
    assert "password" not in low and "api_key" not in low and "docs/blind" not in blob


def _std_run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "agentest", "std", "run", *args],
        cwd=ROOT, text=True, capture_output=True, timeout=60,
    )


def test_walkthrough_cli_journey_matches_evidence():
    """Documented commands: order_bad fails with the tool order; order_ok passes; --strict exits 1."""
    text = WALK.read_text(encoding="utf-8")
    assert "tests/fixtures/contribute" in text
    assert FAIL_DETAIL in text and PASS_DETAIL in text
    assert "tools.json" not in text.split("## Sanitized trace")[1].split("## Bring")[0]
    bad = _std_run("--agents", "tests/fixtures/contribute", "--agent", "order_bad", "--ids", "T2-001", "--format", "md")
    assert bad.returncode == 0, bad.stderr
    assert "T2-001 | fail" in bad.stdout and FAIL_DETAIL in bad.stdout
    strict = _std_run("--agents", "tests/fixtures/contribute", "--agent", "order_bad", "--ids", "T2-001", "--strict")
    assert strict.returncode == 1, strict.stderr
    ok = _std_run("--agents", "tests/fixtures/contribute", "--agent", "order_ok", "--ids", "T2-001", "--format", "md")
    assert ok.returncode == 0, ok.stderr
    assert "T2-001 | pass" in ok.stdout and PASS_DETAIL in ok.stdout


def test_missing_prerequisites_are_not_a_pass(tmp_path):
    """Boundary: no published prerequisites is n/a, not pass."""
    dest = tmp_path / "order_na"
    (dest / "traces").mkdir(parents=True)
    card = json.loads((FIX / "order_ok" / "agent-card.json").read_text(encoding="utf-8"))
    for ext in card["capabilities"]["extensions"]:
        ext.get("params", {}).pop("prerequisites", None)
    (dest / "agent-card.json").write_text(json.dumps(card), encoding="utf-8")
    (dest / "tools.json").write_text((FIX / "order_ok" / "tools.json").read_text(encoding="utf-8"), encoding="utf-8")
    trace = next((FIX / "order_ok" / "traces").iterdir())
    (dest / "traces" / trace.name).write_text(trace.read_text(encoding="utf-8"), encoding="utf-8")
    res = runner.to_json(runner.run_all(metadata.load_all(tmp_path)))
    cell = res["order_na"]["T2-001"]
    assert cell["status"] == "n/a" and cell["detail"] == NA_DETAIL


def test_contributing_documents_the_newcomer_commands():
    text = (FIX.parents[2] / "CONTRIBUTING.md").read_text(encoding="utf-8")
    for snippet in (
        'pip install -e ".[dev]"',
        "python scripts/check_catalog_pins.py",
        "ruff check src tests scripts",
        "tests/fixtures/contribute/",
        "First response within 24 hours",
        "Review within 48 hours",
        "blind-round material",
    ):
        assert snippet in text, snippet
