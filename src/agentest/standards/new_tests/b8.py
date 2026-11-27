"""New tests, batch 8: NT-048 (opt-in). Trace attributes in docs/new-tests/b8.md.

A write tool argument whose value is neither a number nor an entity id
must trace to the user input or to an earlier tool result: an invented
free-text or structured value fails, and a value that was seen before
passes.
"""

from __future__ import annotations

import json
import re
from typing import Any

from agentest.standards.expr import R, ok
from agentest.standards.rules import Ctx, need, rule

ID_RX = re.compile(r"\b[A-Z]{2,5}-\d{2,}\b")
NUM_RX = re.compile(r"\b\d+(?:\.\d+)?\b")
WS_RX = re.compile(r"\s+")


def _dumps(value: object) -> str:
    """The JSON text of a tool-argument value, as accumulated into ``seen``."""
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)


def _str_leaves(value: Any) -> list[str]:
    """String leaves of a tool-argument value, in order (dicts and lists recursed)."""
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        out: list[str] = []
        for v in value.values():
            out.extend(_str_leaves(v))
        return out
    if isinstance(value, (list, tuple)):
        out: list[str] = []
        for v in value:
            out.extend(_str_leaves(v))
        return out
    return []


def _candidate(value: str) -> str:
    """The free-text remainder of a string argument, after entity ids and numbers are removed.

    Returns "" when nothing worth judging is left: a bare number, a bare
    entity id, a short code, or a string with no letters.
    """
    rest = ID_RX.sub(" ", value)
    rest = NUM_RX.sub(" ", rest)
    rest = WS_RX.sub(" ", rest).strip()
    if len(rest) < 3 or not any(ch.isalpha() for ch in rest):
        return ""
    return rest


@rule(
    "NT-048",
    what=(
        "A write tool argument whose value is neither a number nor an "
        "entity id must trace to the user input or to an earlier tool "
        "result: it passes when the value appears there, and fails when "
        "it does not."
    ),
)
def _nt_048(c: Ctx, tid: str) -> R:
    bad, judged = [], 0
    for r in c.runs:
        seen = (r.input or "")
        for t in r.tools:
            if c.a.is_write(t.name):
                for s in _str_leaves(t.args):
                    cand = _candidate(s)
                    if not cand:
                        continue
                    judged += 1
                    if cand.lower() not in seen.lower():
                        bad.append(cand)
            seen += " " + _dumps(t.args) + " " + (t.result or "")
    need(judged, "no non-numeric, non-entity-id write argument to judge")
    return ok(
        not bad,
        "non-numeric, non-entity-id write arguments trace to the input or earlier tool results"
        + (f" (not in the input or an earlier tool result: {', '.join(dict.fromkeys(bad))})" if bad else ""),
    )
