"""Detector registry.

Each family lives in its own module and registers a refiner. ``rules.evaluate`` calls
:func:`refine` once per check. A refiner may promote a pass, n/a or not-assessed verdict
to fail; it must leave an existing fail untouched so parallel detectors do not fight
over detail text. Add a family by registering it from ``detectors/__init__.py``.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

Refiner = Callable[[str, Any, Any], Any]

_REFINERS: list[Refiner] = []


def register(fn: Refiner) -> Refiner:
    _REFINERS.append(fn)
    return fn


def refine(test_id: str, ctx: Any, verdict: Any) -> Any:
    for fn in _REFINERS:
        verdict = fn(test_id, ctx, verdict)
    return verdict
