"""`std run --format coverage-json`: mapped tests and pass/fail/n-a counts per check class and per standards control."""
from __future__ import annotations

import json
import subprocess
import sys

from agentest.standards import reports

RES = {"ag": {"T1-001": {"status": "pass", "detail": ""}, "T1-002": {"status": "fail", "detail": "x"},
              "T4-012": {"status": "n/a", "detail": "no evidence"}, "X-001": {"status": "pass", "detail": ""}}}


def test_counts_by_class_and_control_add_up() -> None:
    cov = reports.to_coverage(RES, "strict")
    assert cov["schema"] == "agentest.coverage/1" and cov["mode"] == "strict"
    assert cov["disclaimer"] == "test coverage, not a compliance determination"
    ag = cov["agents"]["ag"]
    o = ag["overall"]
    assert (o["mapped_tests"], o["assessed"], o["pass"], o["fail"], o["n/a"]) == (4, 3, 2, 1, 1)
    assert o["fail_ids"] == ["T1-002"] and o["not_assessed"] == ["T4-012"]
    assert set(ag["by_class"]) == {"T1", "T4", "X"} and ag["by_class"]["T1"]["fail"] == 1
    sm = reports.standards_map()
    for fw, ctrls in ag["by_control"].items():
        for ctrl, t in ctrls.items():
            ids = sorted(i for i in RES["ag"] if ctrl in [str(c) for c in (sm.get(i, {}).get(fw) or [])])
            assert t["mapped_tests"] == len(ids) == t["pass"] + t["fail"] + t["n/a"], (fw, ctrl)
    # T1-001 and T1-002 both map to OWASP LLM06 in the shipped map
    assert ag["by_control"]["owasp_llm_2025"]["LLM06"]["mapped_tests"] >= 2


def test_no_compliance_or_score_wording() -> None:
    text = json.dumps(reports.to_coverage(RES)).lower()
    assert "compliance determination" in text
    for bad in ("compliant", "compliance %", "score\"", "pass_rate", "percent"):
        assert bad not in text, bad


def test_cli_writes_coverage_json(tmp_path) -> None:
    out = tmp_path / "cov.json"
    subprocess.run([sys.executable, "-m", "agentest", "std", "run", "--agent", "a01", "--format", "coverage-json", "--out", str(out)],
                   check=True, capture_output=True)
    cov = json.loads(out.read_text(encoding="utf-8"))
    ag = next(iter(cov["agents"].values()))
    assert ag["overall"]["mapped_tests"] == ag["overall"]["assessed"] + ag["overall"]["n/a"]
    assert {"owasp_llm_2025", "nist_ai_rmf", "iso_42001_annex_a"} <= set(ag["by_control"])
