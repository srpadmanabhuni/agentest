"""Universal checks, one detector per test id.

The check bodies live in :mod:`agentest.standards.detectors`. This module remains
the import path for ``evaluate``, ``RULES`` and the helpers other modules already
use. Registering a detector (see :mod:`agentest.standards.detectors.registry`)
writes ``RULES``, which ``evaluate`` walks.

No agent id appears here. When a check has no standard signal the verdict is
``n/a`` with that reason.
"""
from __future__ import annotations

import sys

from agentest.standards import detectors as _detectors
from agentest.standards.detectors import _core

_ORIGIN_LINE: dict[str, int] = {}


def _publish(mod) -> None:
    """Copy a detector module's names here. The definition latest in the original source wins."""
    origin = getattr(mod, "_ORIGIN", {})
    for name, val in vars(mod).items():
        if name.startswith("__") or name == "_ORIGIN":
            continue
        line = origin.get(name, -1)
        if line < _ORIGIN_LINE.get(name, -1):
            continue
        if line < 0 and name in globals():
            continue
        globals()[name] = val
        if line >= 0:
            _ORIGIN_LINE[name] = line


_publish(_core)
_detectors.load()
for _mod_name, _mod in list(sys.modules.items()):
    if _mod_name.startswith("agentest.standards.detectors.") and _mod_name.rsplit(".", 1)[-1] != "_core":
        _publish(_mod)

# v3.5 trace checks and v4.0 packs register themselves through the same hook.
from agentest.standards import packs as _packs  # noqa: E402,F401
from agentest.standards import trace_checks as _trace_checks  # noqa: E402,F401

# X-021 and X-022 register from trace_checks, after the detector package has loaded.
from agentest.standards.detectors.loop_policy import install as _install_loop_policy  # noqa: E402

_install_loop_policy()
