"""Every verdict is locked: 130 IDs x every bundled agent x both modes (fixtures/standards/v3-verdicts.json).

This replaces, for the v3 rules, what the removed v1/v2 golden/broken packs did for the old engine: a rule change that
flips any pass, fail or n/a shows up as a failing test with the exact cells, and is accepted only by regenerating the
snapshot (python scripts/verdict_snapshot.py --write) in the same commit.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("verdict_snapshot", ROOT / "scripts" / "verdict_snapshot.py")
vs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vs)


@pytest.mark.judge_replay  # the snapshot records judge-on verdicts (bundled answers replayed)
def test_every_verdict_matches_the_snapshot():
    want = json.loads(vs.OUT.read_text())
    got = vs.compute()
    assert got["ids"] == want["ids"], "catalogue IDs changed"
    diffs = []
    for mode in ("strict", "examples"):
        assert set(got[mode]) == set(want[mode]), f"{mode}: agents added or removed: {set(got[mode]) ^ set(want[mode])}"
        for agent, row in got[mode].items():
            diffs += [f"{mode} {agent} {i}: {w} -> {g}" for i, w, g in zip(got["ids"], want[mode][agent], row, strict=True) if w != g]
    assert not diffs, f"{len(diffs)} verdicts changed (regenerate with scripts/verdict_snapshot.py --write if intended): {diffs[:40]}"


def test_snapshot_decides_every_id_and_shows_both_outcomes_somewhere():
    want = json.loads(vs.OUT.read_text())
    for mode in ("strict", "examples"):
        col = {i: {row[n] for row in want[mode].values()} for n, i in enumerate(want["ids"])}
        assert not [i for i, s in col.items() if not {"P", "F"} <= s], f"{mode}: IDs without both a pass and a fail on the bundled agents"
