"""The wheel ships every bundled agent's standard files, and pyproject carries no stale v1/v2 entries."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from gen_data_files import table  # noqa: E402


def test_data_files_table_is_current():
    assert table() in (ROOT / "pyproject.toml").read_text(), "run: python scripts/gen_data_files.py"


def test_no_legacy_entries():
    t = (ROOT / "pyproject.toml").read_text()
    for stale in ("fixtures/real", "reference_agents", "byo_agent", "agentest.model", "agentest/real"):
        assert stale not in t, stale
