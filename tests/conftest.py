"""Judge mode for the test session: AGENTEST_TEST_JUDGE=replay (default; answers replayed from the bundled judge cache,
no model needed) or off (no judge: semantic checks must report 'not-assessed', never fall back to regex)."""
from __future__ import annotations

import os

import pytest

from agentest.standards import judge

MODE = os.environ.get("AGENTEST_TEST_JUDGE", "replay")


def pytest_configure(config):
    config.addinivalue_line("markers", "judge_replay: needs the judge (bundled replay cache); skipped when judge is off")
    if MODE == "off":
        judge.configure("off", offline=False)
    else:
        judge.configure("off", offline=True)


def pytest_collection_modifyitems(config, items):
    if MODE == "off":
        skip = pytest.mark.skip(reason="AGENTEST_TEST_JUDGE=off")
        for it in items:
            if "judge_replay" in it.keywords:
                it.add_marker(skip)
