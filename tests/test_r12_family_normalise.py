"""r12: hyphenated family names from harnesses (``multi-turn``) match the shared vocabulary (``multi_turn``)."""
from types import SimpleNamespace

from agentest.standards import inputs as I


def test_hyphenated_family_is_normalised():
    runs = [SimpleNamespace(input_id="conv-2", attrs={"agentest.input.families": ["multi-turn", "canonical"]})]
    assert {"multi_turn", "canonical"} <= I.families(runs, "conv-2")


def test_underscore_family_unchanged():
    runs = [SimpleNamespace(input_id="x", attrs={"agentest.input.families": ["policy_deny"]})]
    assert "policy_deny" in I.families(runs, "x")
