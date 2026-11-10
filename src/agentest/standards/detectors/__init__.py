"""Detector families for the universal checks.

Importing this package does not load the families. Call :func:`load` so each
family module registers its detectors. Built-in families (``t*`` and ``x_*``)
load first. Any other module in this package loads afterwards, and a later
:func:`agentest.standards.detectors.registry.register` for the same test id
replaces the built-in detector. That is the hook parallel tasks use.
"""
from __future__ import annotations

import importlib
import pkgutil

from agentest.standards.detectors._core import REGISTRY

__all__ = ["REGISTRY", "load", "load_entry_points"]

_LOADED = False
_EP = False
_BUILTIN = ("t1", "t2", "t3", "t4", "t5", "t6", "t7", "x_")


def load() -> list[str]:
    """Import every in-package detector module once. Returns the module names in load order.

    Built-ins (``t1``…``t7``, ``x_*``) load first. Any other module in this package loads
    afterwards, so its :func:`register` calls replace a built-in for the same test id.
    Entry-point modules are not imported here; call :func:`load_entry_points`.
    """
    global _LOADED
    if _LOADED:
        return []
    names = [m.name for m in pkgutil.iter_modules(__path__) if not m.name.startswith("_") and m.name != "registry"]
    builtin = [n for n in names if n.startswith(_BUILTIN)]
    extra = [n for n in names if n not in set(builtin)]
    loaded = []
    for n in sorted(builtin) + sorted(extra):
        importlib.import_module(f"{__name__}.{n}")
        loaded.append(n)
    _LOADED = True
    _mount_replacements()
    return loaded


def _mount_replacements() -> None:
    """Register family replacements after the built-ins, even if a test imported a module first."""
    from agentest.standards.detectors import (
        constraint_memory,
        f8,
        object_ledger,
        ordering,
    )
    from agentest.standards.detectors._core import RULES

    object_ledger.install()
    constraint_memory._mount()
    ordering._mount()
    f8.bind(RULES)


def load_entry_points() -> None:
    """Import modules registered under the ``agentest.detectors`` entry-point group, once.

    Called from configuration (alongside ``agentest.rules`` plugins), not from package import,
    so importing the checks does not pull the package metadata stack.
    """
    global _EP
    if _EP:
        return
    _EP = True
    try:
        from importlib.metadata import entry_points
    except ImportError:  # pragma: no cover
        return
    try:
        found = entry_points(group="agentest.detectors")
    except TypeError:  # pragma: no cover
        return
    for ep in found:
        ep.load()
