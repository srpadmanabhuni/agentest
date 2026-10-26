"""Plain-data snapshots of the sample harness (env + trace) for model-driven checks.

Agent-side recording only: turns the scenario ``Env`` and the agent's ``Trace`` into
plain dicts/lists/sets (dataclass fields plus read-only properties) so that profile
expectations can judge them without importing any harness or agent code.
"""

from __future__ import annotations

import dataclasses
import enum
import inspect
from typing import Any


def snap(obj: Any, _seen: frozenset[int] = frozenset()) -> Any:
    """Recursively convert ``obj`` to plain data (dict/list/tuple/set/scalars)."""
    if obj is None or isinstance(obj, (bool, int, float, str, bytes)):
        return obj
    if isinstance(obj, enum.Enum):
        return obj.value
    if id(obj) in _seen:
        return None
    seen = _seen | {id(obj)}
    if isinstance(obj, dict):
        return {k: snap(v, seen) for k, v in obj.items()}
    if isinstance(obj, list):
        return [snap(v, seen) for v in obj]
    if isinstance(obj, tuple):
        return tuple(snap(v, seen) for v in obj)
    if isinstance(obj, (set, frozenset)):
        return {snap(v, seen) for v in obj}
    if callable(obj) and not dataclasses.is_dataclass(obj):
        return None
    if hasattr(obj, "__dict__") or dataclasses.is_dataclass(obj):
        out = {k: snap(v, seen) for k, v in vars(obj).items() if not k.startswith("__") and not callable(v)}
        for name, attr in inspect.getmembers(type(obj)):
            if isinstance(attr, property) and not name.startswith("_"):
                try:
                    out[name] = snap(getattr(obj, name), seen)
                except Exception:  # noqa: BLE001 - a failing property is simply absent
                    pass
        return out
    return repr(obj)
