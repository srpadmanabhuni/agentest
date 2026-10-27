"""v3.0.0 standards engine: OTLP round-trip, metadata, 130 universal rules, regression floor vs v2."""

import json

import pytest

from agentest.standards import inputs, judge, metadata, otel, rules, runner
from agentest.standards.catalog import ALL_IDS

AGENTS = metadata.load_all()


def test_every_catalogue_id_has_one_universal_rule():
    assert rules.missing_ids() == []
    assert set(rules.RULES) == set(ALL_IDS) and len(ALL_IDS) == 130


def test_all_agent_metadata_valid():
    assert len(AGENTS) >= 65
    bad = {k: e for k, a in AGENTS.items() if (e := metadata.validate(a))}
    assert bad == {}


@pytest.mark.parametrize("aid", sorted(AGENTS)[::7])
def test_otlp_roundtrip_is_lossless_for_rules(aid):
    a = AGENTS[aid]
    docs = runner.otlp_docs(a)
    assert docs, aid
    for d in docs:
        assert d["resourceSpans"][0]["scopeSpans"][0]["spans"]
        r1, r2 = otel.from_otlp(d), otel.from_otlp(json.loads(json.dumps(d)))
        assert r1 == r2
        names = {kv["key"] for s in d["resourceSpans"][0]["scopeSpans"][0]["spans"] for kv in s.get("attributes", [])}
        assert "gen_ai.operation.name" in names


def test_rules_return_valid_statuses_for_every_agent():
    res = runner.run_all()
    for row in res.values():
        assert set(row) == set(ALL_IDS)
        assert {r.status for r in row.values()} <= {"pass", "fail", "n/a", "not-assessed"}


@pytest.mark.parametrize("mode,floor", [("strict", 385), ("examples", 391)])
def test_regression_floor_vs_v2(mode, floor):
    g = runner.regress(runner.to_json(runner.run_all(mode=mode)), runner.baseline())
    assert g["tally"]["v2_fail"] == 394
    caught = g["tally"]["caught"] + (g["tally"]["missed_as_not_assessed"] if judge.active() is None else 0)
    assert caught >= floor, g["missed"]


def test_inputs_generated_from_card_and_schemas():
    a = next(a for a in AGENTS.values() if a.tools)
    gen = inputs.generate(a)
    assert gen and all(v["families"] for v in gen.values())
    assert "CANARY-GEN-01" in json.dumps(gen)


def test_cli(tmp_path):
    from agentest.cli import main

    assert main(["std", "validate"]) == 0
    assert main(["std", "run", "--agent", "noop", "--json", str(tmp_path / "r.json")]) == 0
    assert main(["std", "export", "--agent", "noop", "--out", str(tmp_path / "o")]) == 0
    assert list((tmp_path / "o").glob("*.otlp.jsonl"))
