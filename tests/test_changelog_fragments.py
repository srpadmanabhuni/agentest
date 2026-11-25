"""changelog.d fragments stay collectable, and CHANGELOG.md keeps its Unreleased note."""
from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHANGELOG = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
spec = importlib.util.spec_from_file_location("collect_changelog", ROOT / "scripts" / "collect_changelog.py")
collect = importlib.util.module_from_spec(spec)
spec.loader.exec_module(collect)


def test_unreleased_note_points_at_changelog_d():
    unreleased = CHANGELOG.split("## Unreleased", 1)[1].split("## [", 1)[0]
    assert "changelog.d/" in unreleased
    assert "## [3.6.1]" in CHANGELOG
    assert "## [3.6.0]" in CHANGELOG


def test_fragments_are_bullets_and_collectable():
    paths = collect.fragment_paths()
    bullets = collect.load_bullets(paths)
    forbidden = ("synthetic", "fork")
    joined = "\n".join(bullets).lower()
    assert not any(word in joined for word in forbidden)
    updated = collect.insert(CHANGELOG, bullets)
    assert all(b in updated.split("## [", 1)[0] for b in bullets)
