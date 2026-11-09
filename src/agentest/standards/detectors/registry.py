"""Registry hook for detector modules.

A detector implements three methods:

* ``applies(ctx) -> str | None`` — a reason the check does not apply, or None;
* ``evaluate(ctx) -> R`` — the verdict, called only when ``applies`` returns None;
* ``evidence() -> list`` — what the last ``evaluate`` recorded.

Register one with :func:`register`. A second registration for the same test id
replaces the first (``replace=True``, the default). Built-in families load
before any other module in this package, and entry-point modules
(``agentest.detectors``) load after both, so a new module can take over a
test id without editing the built-in family.

``rules.RULES`` stays the map ``evaluate`` walks. :func:`register` writes that
map, so existing plugins that use ``@rule`` and code that reads ``RULES`` see
the same detectors.
"""
from __future__ import annotations

from agentest.standards.detectors._core import (
    REGISTRY,
    Detector,
    FunctionDetector,
    get,
    register,
    rule,
)

__all__ = ["REGISTRY", "Detector", "FunctionDetector", "get", "register", "rule"]
