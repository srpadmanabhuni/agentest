"""Locate the data files (catalogue, reference-agent metadata and traces, verdict baseline).

Order: ``$AGENTEST_ROOT``; the source checkout (editable / git install);
``<sys.prefix>/share/agentest`` (wheel install, see ``[tool.setuptools.data-files]``).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


def root() -> Path:
    """Directory that contains ``catalog/``, ``agents/`` and ``fixtures/standards/``."""
    env = os.environ.get("AGENTEST_ROOT")
    if env:
        return Path(env)
    src = Path(__file__).resolve().parents[2]
    if (src / "catalog" / "checklist-110.jsonl").exists():
        return src
    for base in (Path(sys.prefix), Path(sys.base_prefix), Path.home() / ".local"):
        p = base / "share" / "agentest"
        if (p / "catalog").exists():
            return p
    return src
