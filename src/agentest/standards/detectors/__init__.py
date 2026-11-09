"""Detector registry.

W0 will own the shared ``Detector`` interface. Until then a family adds one module and
:func:`install` rebinds the catalogue IDs it deepens. The catalogue, the 38-test scope and
the thresholds stay where they are.
"""

from __future__ import annotations


def install(rules_mod) -> None:
    """Point the loop and policy catalogue IDs at :mod:`loop_policy`. Idempotent."""
    from agentest.standards.detectors.loop_policy import HOOKS

    if getattr(rules_mod, "_loop_policy_installed", False):
        return
    for tid, hook in HOOKS.items():
        what, old = rules_mod.RULES[tid]

        def wrapped(c, _old=old, _hook=hook, _tid=tid):
            return _hook(c, _tid, _old)

        rules_mod.RULES[tid] = (what, wrapped)
    rules_mod._loop_policy_installed = True
