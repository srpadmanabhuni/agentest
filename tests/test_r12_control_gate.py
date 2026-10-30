"""r12-prep Fix 8: the clean-control gate refuses forbidden sources and unscored rounds; the pool is data only."""
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("control_gate", ROOT / "scripts/control_gate.py")
G = importlib.util.module_from_spec(spec)
spec.loader.exec_module(G)


def test_forbidden_sources():
    assert G._check_entry({"agents_dir": "data/trail/test", "round": None})
    assert G._check_entry({"agents_dir": "x/whowhen", "round": None})
    assert G._check_entry({"agents_dir": "docs/blind/r99/agents", "round": "r99"})  # never scored -> still blind


def test_pool_entries_are_valid():
    pool = json.loads((ROOT / "fixtures/controls/pool.json").read_text())["controls"]
    assert pool
    for e in pool:
        assert G._check_entry(e) is None, e
        assert (ROOT / e["agents_dir"] / e["agent"]).is_dir()
