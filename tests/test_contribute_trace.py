"""First-test pattern: one existing check, two synthetic traces, pass and fail.

The traces use record id R-1 and subject id S-1. They are not customer data.
See CONTRIBUTING.md, "Bring an agent trace, contribute a test".
"""

from pathlib import Path

from agentest.standards import metadata, runner

FIX = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "contribute"


def test_synthetic_prerequisite_order_has_a_pass_and_a_fail():
    res = runner.to_json(runner.run_all(metadata.load_all(FIX)))
    assert res["order_ok"]["T2-001"]["status"] == "pass"
    assert "prerequisites respected" in res["order_ok"]["T2-001"]["detail"]
    assert res["order_bad"]["T2-001"]["status"] == "fail"
    assert "lookup_record before" in res["order_bad"]["T2-001"]["detail"]


def test_fixture_traces_stay_synthetic():
    blob = "\n".join(p.read_text(encoding="utf-8") for p in FIX.rglob("*") if p.is_file())
    low = blob.lower()
    assert "password" not in low and "api_key" not in low and "docs/blind" not in blob


def test_contributing_documents_the_newcomer_commands():
    text = (FIX.parents[2] / "CONTRIBUTING.md").read_text(encoding="utf-8")
    for snippet in (
        'pip install -e ".[dev]"',
        "python scripts/check_catalog_pins.py",
        "ruff check src tests scripts",
        "tests/fixtures/contribute/",
        "no promised response time",
        "blind-round material",
    ):
        assert snippet in text, snippet
