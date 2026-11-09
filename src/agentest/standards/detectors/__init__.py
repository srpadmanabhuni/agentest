"""Detector registry. Extra findings attach to catalogue IDs that already exist.

The catalogue size, the aggregation, the thresholds and the n/a = miss rule stay as they are.
A detector returns no verdict of its own: ``apply`` may only turn a non-fail into a fail.
"""

from __future__ import annotations

from agentest.standards.detectors.hallucinated_action import HonestyDetector
from agentest.standards.expr import R

_DETECTORS = (HonestyDetector(),)


def apply(ctx, tid: str, verdict: R) -> R:
    """Run every detector registered for ``tid`` and keep a fail from either source."""
    if verdict.status == "fail":
        return verdict
    for det in _DETECTORS:
        if not det.applies(tid):
            continue
        extra = det.evaluate(ctx, tid)
        if extra is not None and extra.status == "fail":
            return extra
    return verdict
