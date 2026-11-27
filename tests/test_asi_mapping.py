"""Every registered check is mapped to the OWASP Top 10 for Agentic Applications (or says why not), and the docs match.

The mapping lives in taxonomy/asi-mapping.yaml; docs/taxonomy/*.md are generated from it. If this test names a missing ID,
run ``python scripts/gen_taxonomy_docs.py --missing`` for a YAML stub, fill it in, then ``python scripts/gen_taxonomy_docs.py``.
"""

from __future__ import annotations

import importlib.util
import re
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("gen_taxonomy_docs", ROOT / "scripts" / "gen_taxonomy_docs.py")
gen = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gen)

M = yaml.safe_load((ROOT / "taxonomy" / "asi-mapping.yaml").read_text(encoding="utf-8"))
REGISTERED = gen.registered_checks()
ASI_IDS = {f"ASI{n:02d}" for n in range(1, 11)}
NIST_FUNCTIONS = {"GOVERN", "MAP", "MEASURE", "MANAGE"}


def test_every_registered_check_is_in_the_mapping_and_nothing_else():
    missing = sorted(set(REGISTERED) - set(M["checks"]))
    extra = sorted(set(M["checks"]) - set(REGISTERED))
    assert not missing, f"checks with no row in taxonomy/asi-mapping.yaml: {missing}. Run: python scripts/gen_taxonomy_docs.py --missing"
    assert not extra, f"mapping rows for checks that are not registered: {extra}"


def test_sets_are_labelled_as_the_published_counts_say():
    tiers = {i: t for i, (t, _, _) in REGISTERED.items()}
    assert sum(1 for t in tiers.values() if t == "core") == 165
    assert {i for i, t in tiers.items() if t == "opt-in"} <= {i for i in REGISTERED if i.startswith("NT-")}
    for i, e in M["checks"].items():
        tier, pack, _ = REGISTERED[i]
        assert e["tier"] == tier, (i, e["tier"], tier)
        assert e.get("pack") == pack, (i, e.get("pack"), pack)


def test_the_ten_asi_entries_are_the_ones_in_the_cited_document():
    assert set(M["asi"]) == ASI_IDS
    assert M["asi"]["ASI01"] == "Agent Goal Hijack"
    assert M["asi"]["ASI04"] == "Agentic Supply Chain Vulnerabilities"
    assert M["asi"]["ASI10"] == "Rogue Agents"
    src = M["source"]
    assert src["url"].startswith("https://genai.owasp.org/") and re.fullmatch(r"\d{4}-\d{2}-\d{2}", src["fetched"])
    assert "OWASP has not reviewed or endorsed it" in src["notice"]


@pytest.mark.parametrize("check_id", sorted(M["checks"], key=gen.check_key))
def test_each_row_is_well_formed(check_id):
    e = M["checks"][check_id]
    assert e["title"].strip()
    assert e["category"] in M["categories"]
    ids = [a["id"] for a in e["asi"]]
    assert len(ids) == len(set(ids)) and set(ids) <= ASI_IDS
    assert all(a["fit"] in M["fit_values"] for a in e["asi"])
    if e["status"] == "mapped":
        assert e["asi"] and "reason" not in e
    else:
        assert e["status"] == "no ASI mapping" and not e["asi"], "an unmapped check must say 'no ASI mapping' and list no ASI ID"
        assert len(e.get("reason", "")) > 30, "say why no ASI entry fits"
    assert set(e.get("nist_ai_rmf_functions", [])) <= NIST_FUNCTIONS


def test_every_category_is_used_and_has_a_definition():
    used = {e["category"] for e in M["checks"].values()}
    assert used == set(M["categories"])
    for k, c in M["categories"].items():
        assert re.fullmatch(r"AFC-\d{2}", k) and c["slug"] and c["title"] and len(c["definition"]) > 30


def test_coverage_counts_add_up():
    t = gen.totals(M)
    assert t["all"] == len(REGISTERED) == t["tiers"]["core"] + t["tiers"]["opt-in"] + t["tiers"]["pack"]
    cov = gen.coverage(M)
    for a in ASI_IDS:
        assert sum(1 for e in M["checks"].values() if any(x["id"] == a for x in e["asi"])) == cov[a]["direct"] + cov[a]["partial"]


def test_wording_rules_hold_in_the_data_and_generated_pages():
    for path in (ROOT / "taxonomy" / "asi-mapping.yaml", gen.OUT_MAP, gen.OUT_TAX):
        text = path.read_text(encoding="utf-8").lower()
        assert "synthetic" not in text, path
        assert not re.search(r"\bfork", text), path
        assert not re.search(r"precision|recall|p/r|world's first|best-in-class", text), path


def test_generated_pages_are_up_to_date():
    stale = [p.relative_to(ROOT).as_posix() for p, text in gen.render().items() if not p.is_file() or p.read_text(encoding="utf-8") != text]
    assert not stale, f"{stale} is stale; run python scripts/gen_taxonomy_docs.py"


def test_a_check_missing_from_the_mapping_is_reported_with_a_stub(monkeypatch, capsys):
    trimmed = {**M, "checks": {k: v for k, v in M["checks"].items() if k != "T4-003"}}
    monkeypatch.setattr(gen, "load", lambda: trimmed)
    assert gen.print_missing() == 1
    out = capsys.readouterr().out
    assert "T4-003:" in out and "category: AFC-??" in out
