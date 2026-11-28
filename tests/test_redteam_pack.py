"""Red-team trace pack: 20 trace files (prompt injection, data exfiltration, over-refusal) with the verdicts the existing checks give.

Fixtures, tests and docs only: no check is changed. The expected verdicts in ``tests/fixtures/redteam_pack/manifest.json`` are
what the checks return today. The over-refusal fixtures are pending: no check in the catalogue judges over-refusal yet, so no
verdict is asserted for them, and a guard fails when such a check appears so the manifest gets updated.
"""
from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path

import pytest
import yaml

import agentest
from agentest.standards import catalog

ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "tests" / "fixtures" / "redteam_pack"
CARD, TOOLS = PACK / "agent-card.json", PACK / "tools.json"
MANIFEST = json.loads((PACK / "manifest.json").read_text(encoding="utf-8"))
FIXTURES = MANIFEST["fixtures"]
ASI = yaml.safe_load((ROOT / "taxonomy" / "asi-mapping.yaml").read_text(encoding="utf-8"))["checks"]
GUIDE = ROOT / "docs" / "guides" / "RED-TEAM-YOUR-AGENT-TRACES-IN-CI.md"
WORKFLOW = ROOT / "examples" / "integrations" / "github-actions-redteam-cron.yml"
ACTIVE = [f for f in FIXTURES if not f["pending"]]
PENDING = [f for f in FIXTURES if f["pending"]]


def _judge(fixture, ids=None):
    return agentest.run(PACK / fixture["file"], card=CARD, tools=TOOLS, ids=ids or list(fixture["expect"]))


def test_pack_size_and_categories():
    assert 15 <= len(FIXTURES) <= 20
    assert {f["category"] for f in FIXTURES} == {"prompt-injection", "data-exfiltration", "over-refusal"}
    assert len({f["id"] for f in FIXTURES}) == len(FIXTURES)
    for category in ("prompt-injection", "data-exfiltration"):
        assert sum(f["category"] == category for f in ACTIVE) >= 5
        verdicts = {v for f in ACTIVE if f["category"] == category for v in f["expect"].values()}
        assert {"pass", "fail"} <= verdicts, f"{category} needs both a failing and a passing run"


def test_builder_output_matches_committed_files():
    spec = importlib.util.spec_from_file_location("redteam_build", PACK / "build.py")
    build = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(build)
    assert build.main(["--check"]) == 0, "run: python tests/fixtures/redteam_pack/build.py"


@pytest.mark.parametrize("fixture", FIXTURES, ids=[f["id"] for f in FIXTURES])
def test_each_trace_file_holds_a_canonical_run_and_one_adversarial_run(fixture):
    docs = [json.loads(line) for line in (PACK / fixture["file"]).read_text(encoding="utf-8").splitlines() if line.strip()]
    roots = [sp for d in docs for rs in d["resourceSpans"] for ss in rs["scopeSpans"] for sp in ss["spans"] if not sp["parentSpanId"]]
    ids = [next(a["value"]["stringValue"] for a in sp["attributes"] if a["key"] == "agentest.input.id") for sp in roots]
    assert len(ids) == 2 and ids[0] == "canon"


@pytest.mark.parametrize("fixture", ACTIVE, ids=[f["id"] for f in ACTIVE])
def test_expected_verdicts_from_existing_checks(fixture):
    got = {c.id: c.status for c in _judge(fixture)}
    assert got == fixture["expect"]


@pytest.mark.parametrize("fixture", [f for f in ACTIVE if "fail" in f["expect"].values()], ids=lambda f: f["id"])
def test_failing_fixture_names_what_went_wrong(fixture):
    """A fail comes with a detail line (what the report shows), not a bare status."""
    for c in _judge(fixture):
        if c.status == "fail":
            assert c.detail.strip()


def test_pack_covers_the_checks_it_claims_to_exercise():
    """Every check id the pack asserts has a failing fixture (except T4-014), and the main injection and exfiltration checks also have a passing one."""
    seen: dict[str, set[str]] = {}
    for f in ACTIVE:
        for cid, v in f["expect"].items():
            seen.setdefault(cid, set()).add(v)
    assert {c for c, v in seen.items() if "fail" not in v} <= {"T4-014"}  # the encoded-payload check is shown on its passing side only
    both = {c for c, v in seen.items() if v == {"pass", "fail"}}
    assert {"T4-001", "T4-003", "T4-004", "T4-002", "T4-012", "T4-018", "T5-004", "T5-005", "T5-017", "T6-011", "X-019", "X-020"} <= both


@pytest.mark.parametrize("fixture", ACTIVE, ids=[f["id"] for f in ACTIVE])
def test_manifest_owasp_mapping_matches_the_existing_table(fixture):
    for cid, listed in fixture["asi"].items():
        rows = (ASI.get(cid) or {}).get("asi") or []
        assert listed == [a["id"] for a in rows], cid
    # every fixture maps to at least one entry of the existing OWASP table
    assert any(fixture["asi"].values())


def test_generated_pack_page_lists_every_fixture_and_asi_entry():
    page = (ROOT / "docs" / "guides" / "RED-TEAM-TRACE-PACK.md").read_text(encoding="utf-8")
    for f in FIXTURES:
        assert f"`{f['id']}`" in page
    for asi in {a for f in ACTIVE for ids in f["asi"].values() for a in ids}:
        assert asi in page
    assert "no ASI mapping" in page  # checks without an ASI row are shown as such, never forced into an entry


@pytest.mark.parametrize("fixture", PENDING, ids=[f["id"] for f in PENDING])
def test_over_refusal_fixtures_are_pending_and_make_no_claim(fixture):
    assert fixture["expect"] == {} and fixture["asi"] == {}
    # the trace still loads and runs through the existing checks without error
    assert _judge(fixture, ids="T4,T5,X-019").exit_code in (0, 1)


def test_pending_guard_no_over_refusal_check_in_the_catalogue_yet():
    """When a check for over-refusal is added, fail here so the four pending fixtures get its id and a verdict."""
    titles = [row.get("title", "") for row in ASI.values()] + [r.get("title", "") for r in catalog.catalogue().values()]
    assert len(titles) > 200, "catalogue not readable"
    hits = [t for t in titles if re.search(r"over[- ]?refus|refus\w* (?:a |the )?(?:benign|valid|legitimate)", t, re.I)]
    assert not hits, f"an over-refusal check now exists ({hits}); add it to the manifest for the pending fixtures and drop the pending flag"


def test_guide_and_workflow_example():
    text = GUIDE.read_text(encoding="utf-8")
    assert "pip install agentest-ai" in text
    wf = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    on = wf.get("on", wf.get(True))
    assert "schedule" in on and "workflow_dispatch" in on
    steps = next(iter(wf["jobs"].values()))["steps"]
    runs = "\n".join(s.get("run", "") for s in steps)
    assert "agentest std run" in runs and "--strict" in runs
    for line in runs.splitlines():
        if "--ids" in line:
            ids = re.search(r"--ids (\S+)", line).group(1).split(",")
            known = {c.id for c in agentest.run(PACK / ACTIVE[0]["file"], card=CARD, tools=TOOLS)}
            assert all(i in known or re.fullmatch(r"[TX]\d?", i) or i == "X" for i in ids), ids


def test_public_wording_rules():
    """No banned words in the pack's public text, and the only test count stated is 165."""
    texts = [GUIDE.read_text(encoding="utf-8"), (ROOT / "docs" / "guides" / "RED-TEAM-TRACE-PACK.md").read_text(encoding="utf-8"),
             (PACK / "build.py").read_text(encoding="utf-8"), WORKFLOW.read_text(encoding="utf-8"), (PACK / "README.md").read_text(encoding="utf-8")]
    for t in texts:
        low = t.lower()
        assert "synthetic" not in low and "fork" not in low
        for m in re.finditer(r"\b(\d{2,3}) tests\b", t):
            assert m.group(1) == "165"
