"""Bibliography integrity: every test ID has references, every key resolves, Zenodo only for the author's own work."""

from agentest.refs import BIB, CLASS_REFS, ID_REFS, refs_for
from agentest.standards.catalog import ALL_IDS


def test_every_id_has_specific_or_class_references():
    for i in ALL_IDS:
        assert len([k for k in refs_for(i) if k not in ("taxonomy", "catalogue")]) >= 1, i


def test_all_keys_resolve():
    for v in list(ID_REFS.values()) + list(CLASS_REFS.values()):
        assert all(k in BIB for k in v)


def test_zenodo_only_for_own_taxonomy():
    assert {k for k, v in BIB.items() if "zenodo" in v.lower()} == {"taxonomy", "catalogue"}


def test_no_hugging_face_links():
    assert not any("huggingface.co" in v or "hf.co/" in v for v in BIB.values())
