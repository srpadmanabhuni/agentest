"""Replay the recorded reference-agent episodes offline and build the full matrix.

Agent failures are findings (reported in the matrix), not test failures. This test
asserts the replay is complete, deterministic and matches the committed results.
"""

from __future__ import annotations

import json
from pathlib import Path

from agentest.real.checks import REF_AGENTS
from agentest.real.ids import ALL_IDS
from agentest.real.report import build, to_json

ROOT = Path(__file__).resolve().parents[2]
EPS = ROOT / "fixtures" / "real" / "episodes"
EXPECTED = ROOT / "fixtures" / "real" / "results.json"


def test_all_reference_agents_recorded():
    for a in REF_AGENTS:
        assert (EPS / f"{a}.jsonl").exists(), a


def test_matrix_is_complete_for_all_130_ids():
    m = build(EPS)
    assert len(m) == 15 + len(REF_AGENTS)
    for row in m.values():
        assert list(row) == ALL_IDS
        assert all(r.status in {"pass", "fail", "n/a"} for r in row.values())


def test_replay_matches_committed_results():
    assert to_json(build(EPS)) == json.loads(EXPECTED.read_text(encoding="utf-8"))


def test_every_id_has_a_passing_and_a_failing_agent():
    m = build(EPS)
    for i in ALL_IDS:
        st = {m[a][i].status for a in m}
        assert {"pass", "fail"} <= st, (i, st)


def test_replay_is_offline_no_network_imports():
    import agentest.real.checks as c
    import agentest.real.checks2 as c2
    import agentest.real.synth as s
    for mod in (c, c2, s):
        src = Path(mod.__file__).read_text(encoding="utf-8")
        for bad in ("requests", "urllib.request", "httpx", "socket", "openai"):
            assert f"import {bad}" not in src, (mod.__name__, bad)
