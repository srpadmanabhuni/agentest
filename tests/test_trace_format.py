"""Trace format (docs/TRACE-FORMAT.md): the bundled example traces match the schema, the schema lists every trace
attribute the main check code reads, and the page lists every attribute in the schema."""

import json
import re
import subprocess
import sys
from pathlib import Path

import jsonschema
import pytest

from agentest.standards.episode import Episode, StateChange
from agentest.standards.otel import to_otlp

ROOT = Path(__file__).resolve().parents[1]
STD = ROOT / "src" / "agentest" / "standards"
SCHEMA = json.loads((STD / "schemas" / "trace-format.schema.json").read_text(encoding="utf-8"))
REG = SCHEMA["x-agentest-attributes"]
DOC = (ROOT / "docs" / "TRACE-FORMAT.md").read_text(encoding="utf-8")
EXAMPLES = ["examples/first_trace/trace.otlp.json", "examples/start_here/claims-success.otlp.json",
            "examples/agnostic_demo/agents/*/traces/*.otlp.jsonl", "examples/langgraph_import/agents/*/traces/*.otlp.jsonl"]
# written by the importers for reports, read by no check (listed on the page under "Written but not read by checks")
WRITTEN_ONLY = {"gen_ai.agent.id", "gen_ai.tool.type", "gen_ai.framework", "gen_ai.evaluation.name", "gen_ai.evaluation.explanation",
                "gen_ai.evaluation.result", "agentest.source.seq", "agentest.derived", "agentest.input.family", "agentest.input.relation",
                "agentest.approval", "agentest.state_change", "agentest.rules", "agentest.mode", "agentest.version"}
NAME_RX = re.compile(r"\"((?:gen_ai|agentest)\.[A-Za-z0-9_.]+)\"")
VALIDATOR = jsonschema.Draft202012Validator(SCHEMA)


def _docs(path: Path) -> list[dict]:
    text = path.read_text(encoding="utf-8")
    return [json.loads(x) for x in text.splitlines() if x.strip()] if path.suffix == ".jsonl" else [json.loads(text)]


def _example_files() -> list[Path]:
    out = [p for g in EXAMPLES for p in sorted(ROOT.glob(g))]
    assert len(out) >= 5, out
    return out


def test_schema_is_valid_draft_2020_12():
    jsonschema.Draft202012Validator.check_schema(SCHEMA)


@pytest.mark.parametrize("path", _example_files(), ids=lambda p: str(p.relative_to(ROOT)))
def test_bundled_example_traces_match_schema(path):
    for doc in _docs(path):
        errs = sorted(VALIDATOR.iter_errors(doc), key=lambda e: list(e.path))
        assert not errs, f"{path}: {errs[0].message} at {list(errs[0].path)}"


def test_plain_otel_example_matches_schema():
    out = subprocess.run([sys.executable, str(ROOT / "examples" / "otel_plain" / "emit_trace.py")], capture_output=True, text=True, check=True)
    VALIDATOR.validate(json.loads(out.stdout))


def test_exported_records_match_schema():
    ep = Episode(agent="a", probe="p1", input="refund ORD-1", final_answer="done", final_state={"ids": {"ORD-1"}})
    ep.add_tool("request_refund", {"order_id": "ORD-1"}, {"status": "ok"})
    ep.approval("request_refund", True, approver="ops", target="ORD-1", policy_version="v1")
    ep.state_changes.append(StateChange("executed", "refund", {"order_id": "ORD-1"}))
    VALIDATOR.validate(to_otlp(ep, "svc"))


def _span(name: str, attrs: dict) -> dict:
    return {"resourceSpans": [{"scopeSpans": [{"spans": [{"traceId": "t", "spanId": "s", "name": name, "startTimeUnixNano": "1",
                                                          "endTimeUnixNano": "2", "attributes": [{"key": k, "value": v} for k, v in attrs.items()]}]}]}]}


def test_schema_rejects_an_incomplete_record_and_a_wrong_type():
    assert not VALIDATOR.is_valid(_span("agentest.approval", {"agentest.approval.action": {"stringValue": "x"}}))
    assert not VALIDATOR.is_valid(_span("agentest.approval", {"agentest.approval.action": {"stringValue": "x"},
                                                              "agentest.approval.granted": {"stringValue": "false"}}))
    assert VALIDATOR.is_valid(_span("agentest.approval", {"agentest.approval.action": {"stringValue": "x"},
                                                          "agentest.approval.granted": {"boolValue": False}}))
    assert not VALIDATOR.is_valid(_span("x", {"agentest.run.rep": {"stringValue": "one"}}))


def test_schema_lists_every_name_the_main_check_code_reads():
    seen = set()
    for f in ("rules.py", "inputs.py", "otel.py", "importers.py"):
        seen |= set(NAME_RX.findall((STD / f).read_text(encoding="utf-8")))
    known = set(REG) | {a for v in REG.values() for a in v.get("aliases", [])} | WRITTEN_ONLY
    missing = sorted(n for n in seen if n not in known and not n.endswith(".") and not n.startswith("agentest.standards"))
    assert not missing, f"add to docs/TRACE-FORMAT.md and the schema: {missing}"


def test_page_lists_every_schema_attribute_and_counts_match():
    missing = [n for n in REG if f"`{n}`" not in DOC]
    assert not missing, missing
    total = re.search(r"\| \*\*all\*\* \| (\d+) \| (\d+) \| (\d+) \|", DOC)
    assert total and int(total.group(3)) == len(REG)


def test_registry_entries_are_well_formed_and_agent_agnostic():
    id_rx = re.compile(r"\b(T[1-7]|X|NT)-\d{3}\b")
    for name, e in REG.items():
        assert e["provider"] in ("auto-captured", "team-declared", "agent-output"), name
        assert e["requirement"] == "optional" or e["requirement"].startswith("required"), name
        assert not id_rx.search(json.dumps(e)), name  # check IDs live on the page, not in the schema
    assert sum(1 for e in REG.values() if e["requirement"] == "required") == 1
