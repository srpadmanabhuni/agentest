"""Standards map: every catalogue ID mapped; only verified vocabulary IDs used."""

from pathlib import Path

import yaml

from agentest.standards.catalog import ALL_IDS

M = yaml.safe_load((Path(__file__).resolve().parents[1] / "src/agentest/standards/standards_map.yaml").read_text())


def test_every_id_mapped_to_at_least_two_frameworks():
    assert set(M["map"]) == set(ALL_IDS)
    for i, refs in M["map"].items():
        assert len(refs) >= 2, i


def test_only_vocabulary_ids():
    for i, refs in M["map"].items():
        for fam, ids in refs.items():
            assert fam in M["vocabulary"], (i, fam)
            assert set(ids) <= set(M["vocabulary"][fam]), (i, fam, ids)
