"""Detector modules. Each family keeps its own file; ``rules`` binds the catalogue ids.

The shared ``Detector`` shape is ``applies`` (n/a reason, or None when the check runs), ``evaluate``
and ``evidence``. W0 can wrap these without moving the verdicts.
"""

from agentest.standards.detectors.f8 import DETECTORS

__all__ = ["DETECTORS"]
