"""No-lock-in gates (docs/NO-LOCK-IN.md): no vendor SDKs, open output formats that validate against their schemas,
the plugin/override path, traces-only onboarding, catalogue export and agents that need no agentest import."""

from __future__ import annotations

import ast
import json
import sys
import tomllib
from pathlib import Path
from xml.etree import ElementTree as ET

import jsonschema
import pytest

from agentest.standards import ext, metadata, reports, rules, runner
from agentest.standards.catalog import ALL_IDS

ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = ROOT / "src" / "agentest" / "standards" / "schemas"
DEMO = ROOT / "examples" / "agnostic_demo" / "agents"


def _imports(f: Path) -> set[str]:
    out = set()
    for n in ast.walk(ast.parse(f.read_text())):
        if isinstance(n, ast.Import):
            out |= {a.name.split(".")[0] for a in n.names}
        elif isinstance(n, ast.ImportFrom) and n.level == 0 and n.module:
            out.add(n.module.split(".")[0])
    return out


def test_runtime_imports_are_stdlib_pyyaml_or_agentest_only():
    allowed = set(sys.stdlib_module_names) | {"yaml", "agentest"}
    bad = {str(f.relative_to(ROOT)): sorted(_imports(f) - allowed) for f in (ROOT / "src" / "agentest").rglob("*.py") if _imports(f) - allowed}
    assert not bad, bad  # e.g. openai, anthropic, langchain, crewai, opentelemetry-sdk, boto3, requests: none


def test_dependencies_minimal_unpinned_permissive():
    p = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]
    assert p["dependencies"] == ["pyyaml>=6"]
    assert p["license"] == "Apache-2.0"
    assert not any("==" in d for d in p["dependencies"] + sum(p.get("optional-dependencies", {}).values(), []))


def test_demo_agents_and_emitters_need_no_agentest_import():
    # reference agents are not vendored since v3.1 (they ship as standard files only); the bundled demo agent and
    # trace emitter must not depend on agentest either
    files = [ROOT / "examples" / "agnostic_demo" / "refill_agent.py", ROOT / "examples" / "otel_plain" / "emit_trace.py"]
    assert files and not [str(f) for f in files if "agentest" in _imports(f)]


@pytest.fixture(scope="module")
def res():
    return runner.to_json(runner.run_all(metadata.load_all(DEMO)))


def test_versioned_json_validates(res):
    jsonschema.Draft202012Validator(json.loads((SCHEMAS / "verdicts.schema.json").read_text())).validate(reports.to_versioned_json(res, "examples"))


def test_sarif_validates_against_oasis_schema(res):
    doc = reports.to_sarif(res)
    jsonschema.Draft7Validator(json.loads((ROOT / "tests" / "schemas" / "sarif-2.1.0.json").read_text())).validate(doc)
    assert doc["runs"][0]["results"], "the buggy demo agent must produce SARIF results"


def test_junit_structure(res):
    x = ET.fromstring(reports.to_junit(res).split("?>", 1)[1])
    assert x.tag == "testsuites" and len(x) == len(res)
    for s in x:
        cases = s.findall("testcase")
        assert int(s.get("tests")) == len(cases) == len(ALL_IDS)
        assert int(s.get("failures")) == len([c for c in cases if c.find("failure") is not None])
        assert int(s.get("skipped")) == len([c for c in cases if c.find("skipped") is not None])


def test_markdown_and_html(res):
    assert "| ID | status | detail |" in reports.to_markdown(res)
    h = reports.to_html(res)
    assert h.startswith("<!doctype html>") and "refill_bot" in h


def test_catalogue_exports_csv_and_json():
    rows = reports.catalog_rows()
    assert [r["id"] for r in rows] == list(ALL_IDS)
    assert sum(r["licence"] == "CC BY 4.0" for r in rows) == 110
    assert reports.catalog_csv().splitlines()[0].startswith("id,class_id,title")


def test_governance_extension_schema_validates_every_published_card():
    v = jsonschema.Draft202012Validator(json.loads((SCHEMAS / "governance-extension.schema.json").read_text()))
    cards = list((ROOT / "agents").glob("*/agent-card.json")) + list((ROOT / "examples").glob("*/agents/*/agent-card.json"))
    errs = [(str(f), e.message) for f in cards for x in json.loads(f.read_text()).get("capabilities", {}).get("extensions", [])
            if x.get("uri") == "urn:agentest:a2a-ext:governance:v1" for e in v.iter_errors(x.get("params", {}))]
    assert not errs, errs[:5]


def test_extension_is_optional_absent_means_na():
    a = metadata.load_all(DEMO)["refill_bot_buggy"]
    with_ext = rules.evaluate(a, runner.runs(a))
    a.gov = {}
    a.card = {k: v for k, v in a.card.items() if k != "capabilities"}
    without = rules.evaluate(a, runner.runs(a))
    flipped = [i for i in ALL_IDS if with_ext[i].status == "fail" and without[i].status == "fail"]
    assert all(without[i].status in ("pass", "fail", "n/a") for i in ALL_IDS)
    for i in ("T2-004", "T2-001"):  # governance-only checks go to n/a, not to a guessed verdict
        assert without[i].status == "n/a", (i, without[i])
    assert flipped  # MCP/OTel-only rules still catch defects without the extension


def test_local_rules_dir_config_disable_and_thresholds(tmp_path):
    (tmp_path / "rules").mkdir()
    (tmp_path / "rules" / "mine.py").write_text(
        "from agentest.standards.rules import rule, ok\n"
        "@rule('U-001', what='at most one tool call per run (user rule)')\n"
        "def _u(c, tid):\n    return ok(all(len(r.tools) <= 1 for r in c.runs), 'counted tool calls')\n")
    (tmp_path / "cfg.yaml").write_text("disable: [T1-001]\nthresholds: {steps: 1, tool_calls: 1}\nrules_dir: rules\n")
    try:
        ext.configure(ext.read_config(tmp_path / "cfg.yaml"), tmp_path)
        a = metadata.load_all(DEMO)["refill_bot"]
        out = rules.evaluate(a, runner.runs(a))
        assert out["U-001"].status == "fail"
        assert out["T1-001"].status == "n/a" and out["T1-001"].detail == "disabled by config"
        assert rules.BUDGET["steps"] == 1 and out["T5-006"].status == "fail", out["T5-006"]  # budget overridden to 1
    finally:
        ext.reset()
        rules.RULES.pop("U-001", None)
    assert rules.BUDGET["steps"] == 12


def test_entry_point_plugin(tmp_path, monkeypatch):
    pkg = tmp_path / "myrules_pkg.py"
    pkg.write_text("from agentest.standards.rules import rule, ok\n@rule('U-EP1', what='entry-point rule')\ndef _r(c, tid):\n    return ok(True, 'loaded via entry point')\n")
    dist = tmp_path / "myrules_pkg-1.0.dist-info"
    dist.mkdir()
    (dist / "METADATA").write_text("Metadata-Version: 2.1\nName: myrules-pkg\nVersion: 1.0\n")
    (dist / "entry_points.txt").write_text("[agentest.rules]\nmine = myrules_pkg\n")
    monkeypatch.syspath_prepend(str(tmp_path))
    try:
        assert "myrules_pkg" in ext.load_plugins()
        a = metadata.load_all(DEMO)["refill_bot"]
        assert rules.evaluate(a, runner.runs(a))["U-EP1"].status == "pass"
    finally:
        rules.RULES.pop("U-EP1", None)


def test_cli_otlp_file_from_any_collector(tmp_path, capsys):
    from agentest.cli import main
    from tests.test_agent_independence import _trace

    f = tmp_path / "collector-export.json"
    f.write_text(json.dumps(_trace([("lookup", {"id": "1"})] * 6, traces=3)))
    out = tmp_path / "r.sarif"
    assert main(["std", "run", "--otlp", str(f), "--format", "sarif", "--out", str(out)]) == 0
    assert "otlp_agent" in capsys.readouterr().out
    jsonschema.Draft7Validator(json.loads((ROOT / "tests" / "schemas" / "sarif-2.1.0.json").read_text())).validate(json.loads(out.read_text()))
