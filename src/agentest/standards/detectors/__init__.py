"""Detector registry.

W0 splits ``rules.py`` into one module per family. Until that lands, each new family
registers here and ``rules.py`` keeps a one-line hook. Detectors read declared metadata
only: MCP annotations, governance records, OTel GenAI spans, the task spec and state snapshots.
"""
from __future__ import annotations

from agentest.standards.detectors.ordering import DETECTOR as ORDERING

REGISTRY: dict = {i: ORDERING for i in ORDERING.ids}

__all__ = ["REGISTRY"]
