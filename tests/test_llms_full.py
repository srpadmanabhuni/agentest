"""llms.txt follows the llmstxt.org layout, and llms-full.txt stays in sync."""

from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

SPEC = importlib.util.spec_from_file_location(
    "gen_llms_full", ROOT / "scripts" / "gen_llms_full.py"
)
GEN = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(GEN)


# Public wording: no check-count breakdown. A Hugging Face dataset *name* may
# contain "110"; this only flags count phrases, not that identifier in a URL.
BREAKDOWN = re.compile(
    r"\b(?:130 default|30 opt-in|110 tests in four pillars|default 110/130|"
    r"110 catalogue|20 repo extensions|30 New tests)\b",
    re.I,
)


def test_root_llms_txt_follows_llmstxt_org():
    text = (ROOT / "llms.txt").read_text(encoding="utf-8")
    lines = text.splitlines()
    assert lines[0].startswith("# ")
    # Optional blank lines, then a blockquote.
    rest = [ln for ln in lines[1:] if ln.strip()]
    assert rest and rest[0].startswith("> ")
    assert "165 tests" in rest[0] or "165 rule-based tests" in rest[0]
    assert "OpenTelemetry" in rest[0]
    assert re.search(r"^## ", text, re.M)
    assert re.search(r"^- \[[^\]]+\]\(https://raw\.githubusercontent\.com/", text, re.M)
    assert "examples/colab_quickstart.ipynb" in text
    assert "srpadmanabhuni.github.io" not in text.lower()
    assert "llms-full.txt" in text
    assert not BREAKDOWN.search(text)


def test_pages_llms_txt_follows_llmstxt_org():
    text = (ROOT / "site" / "llms.txt").read_text(encoding="utf-8")
    lines = text.splitlines()
    assert lines[0].startswith("# ")
    rest = [ln for ln in lines[1:] if ln.strip()]
    assert rest and rest[0].startswith("> ")
    assert "165" in rest[0]
    assert "llms-full.txt" in text
    assert not BREAKDOWN.search(text)


def test_llms_full_is_up_to_date():
    body = GEN.build()
    for path in (ROOT / "llms-full.txt", ROOT / "site" / "llms-full.txt"):
        assert path.is_file(), path
        assert path.read_text(encoding="utf-8") == body, (
            f"{path.relative_to(ROOT)} is stale; run "
            "PYTHONPATH=src python scripts/gen_llms_full.py"
        )


def test_llms_full_lists_every_test_id_once():
    from agentest.standards.catalog import NEW_TEST_IDS, PUBLISHED_TEST_COUNT, published_ids

    # The published list stays 165. Later or opt-in checks outside published_ids() are real and are not added to that list.
    ids = list(published_ids())
    assert len(ids) == PUBLISHED_TEST_COUNT == 165
    assert {"NT-041", "NT-042", "NT-043"} <= set(NEW_TEST_IDS)
    assert not ({"NT-041", "NT-042", "NT-043"} & set(ids))
    body = (ROOT / "llms-full.txt").read_text(encoding="utf-8")
    section = body.split("## Test IDs and failure conditions", 1)[1]
    for i in ids:
        assert re.search(rf"^{re.escape(i)}\b", section, re.M), i
    built_ids = GEN._ids()
    assert built_ids == ids
    assert len(built_ids) == PUBLISHED_TEST_COUNT


def test_llms_full_failure_lines_come_from_definitions():
    from agentest.standards.catalog import ALL_IDS

    # Spot-check well-known IDs against catalogue fail_signal / acceptance text.
    t1018 = GEN.failure_line("T1-018")
    t4003 = GEN.failure_line("T4-003")
    assert "API true while oracle false" in t1018 or "oracle" in t1018.lower()
    assert "evil" in t4003.lower() or "Attacker-controlled address" in t4003
    body = (ROOT / "llms-full.txt").read_text(encoding="utf-8")
    assert "T1-018" in body and "T4-003" in body
    # Do not copy the stale CLI "130 universal checks" string into this public file.
    assert "130 universal checks" not in body
    assert "DeepEval" not in body and "Ragas" not in body and "Phoenix" not in body
    _ = ALL_IDS  # documents the default ID set is still available to the runner


def test_landing_page_jsonld_has_source_and_matching_faq():
    import json
    from pathlib import Path as _P

    html = (_P(__file__).resolve().parents[1] / "site" / "index.html").read_text(encoding="utf-8")
    match = re.search(r'<script type="application/ld\+json">\s*(.*?)\s*</script>', html, re.S)
    assert match, "missing JSON-LD"
    data = json.loads(match.group(1))
    types = {node.get("@type") for node in data["@graph"]}
    assert "SoftwareSourceCode" in types
    assert "FAQPage" in types
    assert "Organization" in types
    source = next(n for n in data["@graph"] if n.get("@type") == "SoftwareSourceCode")
    same = set(source["sameAs"])
    assert "https://pypi.org/project/agentest-ai/" in same
    assert "https://huggingface.co/datasets/srinivaspadmanabhuni/agentic-ai-test-checklist-110" in same
    assert "https://doi.org/10.5281/zenodo.23597877" in same
    assert "https://github.com/srpadmanabhuni/agentest-starter" in same
    assert source["codeRepository"] == "https://github.com/srpadmanabhuni/agentest"
    org = next(n for n in data["@graph"] if n.get("@type") == "Organization")
    assert "Mint All About AI Tech4Good Awards 2026" in org["award"]
    faq = next(n for n in data["@graph"] if n.get("@type") == "FAQPage")
    for q in faq["mainEntity"]:
        assert q["name"] in html
    # Award is on the organisation, not claimed as an award of the package.
    source_blob = json.dumps(source)
    assert "Tech4Good" not in source_blob


CANONICAL_DEFINITION = (
    "agentest (agentest-ai on PyPI) is an open-source, offline, deterministic "
    "evaluation framework for AI agents. Built by Dr. Srinivas Padmanabhuni "
    "(AiEnsured), it checks OpenTelemetry GenAI traces, A2A AgentCards and MCP "
    "tool lists against 165 rule-based tests, catching unauthorized tool calls, "
    "prompt injections, unearned success claims and PII leaks without an LLM judge."
)


def test_canonical_definition_is_verbatim_on_primary_surfaces():
    """The same 51-word definition appears on the README, llms.txt, docs homepage and JSON-LD."""
    import json

    assert len(CANONICAL_DEFINITION.split()) == 51
    readme_first = (ROOT / "README.md").read_text(encoding="utf-8").split("\n", 2)[2].split("\n\n", 1)[0]
    assert readme_first == CANONICAL_DEFINITION
    quote = next(
        ln[2:]
        for ln in (ROOT / "llms.txt").read_text(encoding="utf-8").splitlines()
        if ln.startswith("> ")
    )
    assert quote == CANONICAL_DEFINITION
    docs_first = (ROOT / "docs/README.md").read_text(encoding="utf-8").split("\n", 2)[2].split("\n\n", 1)[0]
    assert docs_first == CANONICAL_DEFINITION
    html = (ROOT / "site/index.html").read_text(encoding="utf-8")
    assert f'<p class="lede">{CANONICAL_DEFINITION}</p>' in html
    match = re.search(r'<script type="application/ld\+json">\s*(.*?)\s*</script>', html, re.S)
    data = json.loads(match.group(1))
    for node in data["@graph"]:
        if node.get("@type") in {"WebPage", "SoftwareApplication", "SoftwareSourceCode"}:
            assert node["description"] == CANONICAL_DEFINITION, node.get("@type")
