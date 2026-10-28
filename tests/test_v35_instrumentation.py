"""v3.5 instrumentation-coverage gate: share of n/a verdicts per agent against a configurable threshold, reported in
JSON, JUnit and SARIF and turned into a non-zero exit code. Generic inputs only (no agent ids)."""
from __future__ import annotations

import json
import json as _json
import pathlib as _pl
from pathlib import Path
from xml.etree import ElementTree as ET

import jsonschema
import pytest

from agentest.cli import main
from agentest.standards import ext, instrumentation, reports

INPUTS = _json.loads((_pl.Path(__file__).parent / "fixtures" / "agent_inputs.json").read_text())  # agent inputs are data

ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = ROOT / "src" / "agentest" / "standards" / "schemas"
SARIF = json.loads((ROOT / "tests" / "schemas" / "sarif-2.1.0.json").read_text())


def _row(n_pass: int, n_na: int, n_disabled: int = 0, n_not_run: int = 0, n_not_assessed: int = 0) -> dict:
    row, k = {}, 0
    for st, n, d in (("pass", n_pass, "ok"), ("n/a", n_na, "no standard signal: x"), ("n/a", n_disabled, "disabled by config"),
                     ("not-run", n_not_run, "no traces"), ("not-assessed", n_not_assessed, "needs a judge")):
        for _ in range(n):
            row[f"U-{k:03d}"] = {"status": st, "detail": d}
            k += 1
    return row


def _root_only_trace(tmp_path: Path) -> Path:
    """A trace with nothing but a root span: no tool, model or state instrumentation."""
    span = {"traceId": "a" * 32, "spanId": "b" * 16, "name": "invoke_agent bare", "kind": 1, "startTimeUnixNano": "1", "endTimeUnixNano": "2",
            "attributes": [{"key": "gen_ai.operation.name", "value": {"stringValue": "invoke_agent"}},
                           {"key": "gen_ai.input.messages", "value": {"stringValue": json.dumps([{"role": "user", "parts": [{"type": "text", "content": "hi"}]}])}}]}
    f = tmp_path / "bare.otlp.json"
    f.write_text(json.dumps({"resourceSpans": [{"resource": {"attributes": []}, "scopeSpans": [{"scope": {"name": "t"}, "spans": [span]}]}]}))
    return f


def test_share_counts_na_and_not_run_but_not_disabled_or_not_assessed():
    c = instrumentation.agent_coverage(_row(2, 5, n_disabled=10, n_not_run=1, n_not_assessed=2), 0.9)
    assert c["considered"] == 10 and c["n/a"] == 5 and c["not-run"] == 1 and c["not-assessed"] == 2
    assert c["na_share"] == 0.6 and c["ok"]


def test_threshold_boundary_is_inclusive():
    assert instrumentation.agent_coverage(_row(1, 9), 0.9)["ok"]          # exactly 90% passes
    assert not instrumentation.agent_coverage(_row(1, 9), 0.89)["ok"]
    assert not instrumentation.agent_coverage(_row(0, 0, n_disabled=3), 0.9)["ok"]  # nothing considered = no coverage


def test_threshold_sources_and_validation():
    try:
        assert instrumentation.threshold() == instrumentation.DEFAULT_MAX_NA == 0.90
        ext.CONFIG["thresholds"] = {"max_na_share": 0.5}
        assert instrumentation.threshold() == 0.5
        assert instrumentation.threshold(0.7) == 0.7  # CLI wins over config
        with pytest.raises(ValueError):
            instrumentation.threshold(1.5)
    finally:
        ext.reset()


def test_gate_lists_failing_agents_and_missing_signals():
    res = {"good": _row(8, 2), "thin": _row(1, 19)}
    g = instrumentation.gate(res, 0.9)
    assert not g["ok"] and g["failing"] == ["thin"]
    assert g["agents"]["good"]["ok"] and not g["agents"]["thin"]["ok"]
    assert "signals_missing" not in g["agents"]["good"]  # no runs given -> no signal inventory


def test_json_report_carries_coverage_and_validates():
    res = {"good": _row(8, 2), "thin": _row(1, 19)}
    doc = reports.to_versioned_json(res, "examples", instrumentation.gate(res, 0.9))
    jsonschema.Draft202012Validator(json.loads((SCHEMAS / "verdicts.schema.json").read_text())).validate(doc)
    assert doc["coverage"]["failing"] == ["thin"] and doc["coverage"]["rule"] == instrumentation.RULE_ID


def test_junit_adds_a_failure_only_for_agents_over_the_threshold():
    res = {"good": _row(8, 2), "thin": _row(1, 19)}
    x = ET.fromstring(reports.to_junit(res, "examples", instrumentation.gate(res, 0.9)).split("?>", 1)[1])
    suites = {s.get("name"): s for s in x}
    good, thin = suites["good"], suites["thin"]
    assert int(good.get("tests")) == 10 and int(good.get("failures")) == 0
    assert int(thin.get("tests")) == 21 and int(thin.get("failures")) == 1
    gate_case = [c for c in thin.findall("testcase") if c.get("name") == instrumentation.RULE_ID]
    assert len(gate_case) == 1 and gate_case[0].find("failure") is not None
    assert not [c for c in good.findall("testcase") if c.get("name") == instrumentation.RULE_ID]
    props = {p.get("name"): p.get("value") for p in thin.find("properties")}
    assert props["agentest.coverage.na_share"] == "0.95" and props["agentest.coverage.ok"] == "false"


def test_sarif_reports_gate_rule_and_results():
    res = {"good": _row(8, 2), "thin": _row(1, 19)}
    doc = reports.to_sarif(res, "examples", instrumentation.gate(res, 0.9))
    jsonschema.Draft7Validator(SARIF).validate(doc)
    run = doc["runs"][0]
    assert instrumentation.RULE_ID in [r["id"] for r in run["tool"]["driver"]["rules"]]
    hits = [r for r in run["results"] if r["ruleId"] == instrumentation.RULE_ID]
    assert len(hits) == 1 and "thin" in hits[0]["message"]["text"] and hits[0]["level"] == "error"
    assert run["properties"]["instrumentationCoverage"]["failing"] == ["thin"]


def test_sarif_has_no_gate_result_when_all_agents_are_covered():
    res = {"good": _row(8, 2)}
    doc = reports.to_sarif(res, "examples", instrumentation.gate(res, 0.9))
    assert not [r for r in doc["runs"][0]["results"] if r["ruleId"] == instrumentation.RULE_ID]


def test_cli_fails_an_uninstrumented_trace_and_threshold_overrides(tmp_path, capsys):
    f = _root_only_trace(tmp_path)
    assert main(["std", "run", "--otlp", str(f)]) == 1
    out = capsys.readouterr().out
    assert "instrumentation coverage FAIL" in out and "tool_spans" in out
    assert main(["std", "run", "--otlp", str(f), "--max-na", "1"]) == 0
    assert main(["std", "run", "--otlp", str(f), "--max-na", "2"]) == 2  # out of range
    cfg = tmp_path / "c.yaml"
    cfg.write_text("thresholds:\n  max_na_share: 1.0\n")
    try:
        assert main(["std", "run", "--otlp", str(f), "--config", str(cfg)]) == 0
    finally:
        ext.reset()


def test_cli_reports_gate_in_written_json_junit_and_sarif(tmp_path):
    f = _root_only_trace(tmp_path)
    for fmt in ("json", "junit", "sarif"):
        out = tmp_path / f"r.{fmt}"
        assert main(["std", "run", "--otlp", str(f), "--format", fmt, "--out", str(out)]) == 1
        text = out.read_text()
        assert instrumentation.RULE_ID in text, fmt


def test_cli_passes_an_instrumented_trace(tmp_path):
    import subprocess
    import sys

    t = subprocess.run([sys.executable, str(ROOT / INPUTS["otel_script"])], capture_output=True, text=True, check=True)
    f = tmp_path / "plain.otlp.json"
    f.write_text(t.stdout)
    assert main(["std", "run", "--otlp", str(f)]) == 0
