"""Small read-only helpers shared by the New test batch modules. Batches add their own helpers in their own module;
change this file only through a separate PR so parallel batches never conflict here."""
# Ref: internal design (docs/new-tests/README.md).

from __future__ import annotations

import json
import statistics
from typing import Any

from agentest.standards.otel import Run, ToolSpan


def jattr(attrs: dict, key: str, default: Any = None) -> Any:
    """Attribute ``key`` decoded from JSON when it is a JSON string; ``default`` when absent or empty."""
    v = attrs.get(key)
    if v in (None, ""):
        return default
    if isinstance(v, str) and v[:1] in "[{":
        try:
            return json.loads(v)
        except ValueError:
            return default
    return v


def task(r: Run, key: str, default: Any = None) -> Any:
    """A task declaration ``agentest.task.<key>`` from the root span (JSON-decoded)."""
    return jattr(r.attrs, f"agentest.task.{key}", default)


def spans(r: Run, name: str | None = None, **match: Any) -> list[dict]:
    """Spans of ``r`` in start order, optionally by span name and by attribute equality (``attr_key=value``, dots as __)."""
    out = []
    for s in r.spans:
        if name is not None and s["name"] != name:
            continue
        if all(str(s["attrs"].get(k.replace("__", "."))) == str(v) for k, v in match.items()):
            out.append(s)
    return out


def tattr(t: ToolSpan, key: str, default: Any = None) -> Any:
    """Attribute ``key`` of a tool span (JSON-decoded)."""
    return jattr(t.attrs, key, default)


def median(xs: list[float]) -> float:
    return float(statistics.median(xs))


def flat_values(x: Any) -> list[str]:
    """Every scalar value inside a JSON-like value, as normalised strings (for 'does this value appear in a source')."""
    if isinstance(x, str) and x[:1] in "[{":
        try:
            x = json.loads(x)
        except ValueError:
            pass
    if isinstance(x, dict):
        return [v for y in x.values() for v in flat_values(y)]
    if isinstance(x, list):
        return [v for y in x for v in flat_values(y)]
    return [] if x is None else [str(x).strip().lower()]
