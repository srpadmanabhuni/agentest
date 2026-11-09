"""Detector registry.

A detector answers one or more catalogue ids. The interface is the one the rules module
delegates to: ``applies`` (why the check cannot run, or None), ``evaluate`` (a verdict)
and ``evidence`` (the facts the last evaluation compared). Rules keep their own ids;
this registry is the hook a detector is mounted on.
"""
from __future__ import annotations

from agentest.standards.detectors.metamorphic import MetamorphicState

REGISTRY: dict = {}


def register(det) -> None:
    """Map each of ``det.ids`` to ``det``. A later registration for the same id replaces the earlier one."""
    for tid in det.ids:
        REGISTRY[tid] = det


register(MetamorphicState())
