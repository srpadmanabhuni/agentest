"""The agent-vocabulary guard also rejects round desk, scenario and case ids inside src/."""
from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("agent_vocab_guard", ROOT / "scripts" / "agent_vocab_guard.py")
G = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(G)


def test_rounds_a127_to_a170_contribute_desk_scenario_and_case_ids():
    tokens = G.round_tokens()
    kinds = {v.split()[0] for v in tokens.values()}
    assert {"desk", "scenario", "case"} <= kinds
    assert any(k.startswith("a1") for k in (v.split("(")[-1].rstrip(")") for v in tokens.values()))


def test_a_round_token_in_src_is_a_hit(tmp_path):
    tokens = G.round_tokens()
    sample = next(iter(tokens))
    planted = tmp_path / "planted.py"
    planted.write_text(f"obj = {sample!r}\n")
    hits = G.round_hits([planted], tokens)
    assert hits and sample in hits[0]


def test_src_names_no_round_desk_scenario_or_case():
    assert G.round_hits() == []
