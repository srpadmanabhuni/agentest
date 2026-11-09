"""Per-family detectors. Each module owns one family and is hooked from the rule registry.

The registry maps a catalogue id to a detector. A detector answers ``applies`` (why it does not apply, or
None), ``evaluate`` (the verdict) and ``evidence`` (the findings of the last evaluation).
"""
from __future__ import annotations

from agentest.standards.detectors.constraint_memory import DETECTOR as CONSTRAINT_MEMORY

REGISTRY = {tid: CONSTRAINT_MEMORY for tid in CONSTRAINT_MEMORY.ids}
