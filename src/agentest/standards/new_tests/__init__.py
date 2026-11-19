"""New tests (NT-001..NT-030): opt-in checks over recorded traces, registered by batch modules.

Each batch owns exactly one module here (``b1.py`` .. ``b4.py``), one catalogue fragment
(``catalog/new-tests/b<N>.jsonl``), one test file (``tests/test_new_tests_b<N>.py``) and one doc fragment
(``docs/new-tests/b<N>.md``). Modules are found by name, so adding a batch edits no shared file.

Rules are the usual ``@rule("NT-0xx", what=...)`` blocks from :mod:`agentest.standards.rules`. They are opt-in:
``evaluate`` leaves them out of the default 130 and ``agentest std run --ids NT`` (or ``--ids NT-001,...``) selects them.
Missing attributes give ``n/a`` (raise ``NA`` via ``need``), never a pass.
"""
# Ref: internal design (docs/new-tests/README.md); article test mapping in catalog/new-tests/*.jsonl.

from __future__ import annotations

import importlib
import pkgutil

_LOADED: list[str] = []


def load() -> list[str]:
    """Import every batch module ``b<N>`` in this package once (sorted), so its @rule blocks register."""
    for m in sorted(x.name for x in pkgutil.iter_modules(__path__) if x.name.startswith("b") and x.name[1:].isdigit()):
        if m not in _LOADED:
            importlib.import_module(f"{__name__}.{m}")
            _LOADED.append(m)
    return list(_LOADED)
