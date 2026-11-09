"""Per-family detectors.

Each family lives in its own module. ``REGISTRY`` maps a catalogue id to the detector
class. A rule in ``rules`` keeps a one-line hook so this layout can land beside the
modular registry refactor without editing the shared rule body.
"""

from __future__ import annotations

from agentest.standards.detectors.state_outcome import StateOutcome

REGISTRY: dict[str, type] = {"T1-001": StateOutcome}
