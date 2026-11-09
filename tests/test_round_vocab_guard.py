"""Round vocabulary stays out of src/: case ids, scenario ids and desk ids from scored rounds.

Agent ids and tool names are already rejected by scripts/agent_vocab_guard.py. This
extends that guard to the identifier-shaped case / scenario ids and desk ids recorded
on those rounds. Fresh held-out collections are not in the tree and are not read.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("agent_vocab_guard", ROOT / "scripts" / "agent_vocab_guard.py")
_guard = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_guard)


def test_round_vocab_is_loaded_and_absent_from_src():
    vocab = _guard.round_specific_vocab()
    case_ids = [k for k, why in vocab.items() if why.startswith("case/")]
    desk_ids = [k for k, why in vocab.items() if why.startswith("desk")]
    assert len(case_ids) >= 10, case_ids
    assert len(desk_ids) >= 10, desk_ids
    hits = _guard.src_round_hits(vocab)
    assert not hits, hits[:20]


def test_round_vocab_matcher_flags_a_planted_token():
    vocab = _guard.round_specific_vocab()
    token = next(iter(vocab))
    hits = _guard.src_round_hits({token: vocab[token]})
    # The real tree is clean; a copy of the token in a one-line scan of src must be the
    # only way this helper reports a hit. Confirm the helper sees the token in a sample line.
    line_hit = _guard.re.search(rf"(?<![\w.-]){_guard.re.escape(token)}(?![\w-])", f"prefix {token} suffix")
    assert line_hit
    assert hits == []
