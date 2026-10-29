"""One check count everywhere: catalogue + extension IDs == @rule registry == generated docs (no dead aliases)."""

import json
import re
from pathlib import Path

from agentest.standards import rules
from agentest.standards.catalog import ALL_IDS, CATALOGUE_IDS, X_WHAT

ROOT = Path(__file__).resolve().parents[1]


def test_registry_equals_catalogue():
    assert len(CATALOGUE_IDS) == 110
    assert len(ALL_IDS) == len(set(ALL_IDS)) == len(CATALOGUE_IDS) + len(X_WHAT)
    assert set(rules.RULES) == set(ALL_IDS), sorted(set(rules.RULES) ^ set(ALL_IDS))


def test_docs_state_the_registry_count():
    n = len(ALL_IDS)
    assert f"({n} checks)" in (ROOT / "docs/tests/README.md").read_text().splitlines()[0]
    assert f"(all {n} IDs)" in (ROOT / "docs/testers/PER-TEST-GUIDE.md").read_text().splitlines()[0]
    assert re.match(rf"Rules: {n} IDs;", (ROOT / "docs/standards/AGENT-INDEPENDENCE-AUDIT.md").read_text())
    assert len([ln for ln in (ROOT / "catalog/checklist-110.jsonl").read_text().splitlines() if ln.strip() and json.loads(ln)]) == 110
