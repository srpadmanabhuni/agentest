"""The vocab guard also rejects desk, scenario and case identifiers from scored round desks inside src/."""
from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("agent_vocab_guard", ROOT / "scripts" / "agent_vocab_guard.py")
guard = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(guard)


def test_round_vocab_sees_scenario_and_case_ids():
    tokens = guard.round_tokens()
    kinds = " ".join(tokens.values())
    assert "scenario id" in kinds
    assert "case id" in kinds
    assert "desk id" in kinds


def test_src_has_no_round_desk_scenario_or_case_ids():
    assert guard.round_src_hits() == []
