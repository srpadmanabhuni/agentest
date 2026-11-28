"""New tests, batch 8: NT-048 (opt-in). Trace attributes in docs/new-tests/b8.md.

A write tool argument whose value is neither a number nor an entity id
must trace to the user input or to an earlier tool result: an invented
free-text or structured value fails, and a value that was seen before
passes.
A value the tool schema constrains with `enum`, `const` or
`default` is exempt, because the wording is the tool's, not the agent's.
A free-text field where a paraphrase is normal is still judged on its
exact wording: a paraphrase that does not appear in the input or in an
earlier tool result fails, because the check matches text, not meaning.
"""

from __future__ import annotations

import json
import re
from typing import Any

from agentest.standards.expr import R, ok
from agentest.standards.rules import Ctx, ID_RX, need, rule

NUM_RX = re.compile(r"\b\d+(?:\.\d+)?\b")
WS_RX = re.compile(r"\s+")


def _dumps(value: object) -> str:
    """The JSON text of a tool-argument value, as accumulated into ``seen``."""
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)


def _str_leaves(value: Any, k: str | None = None) -> list[tuple[str | None, str]]:
    """(Field key, string value) leaves of a tool-argument value, in order (dicts and lists recursed)."""
    if isinstance(value, str):
        return [(k, value)]
    if isinstance(value, dict):
        out: list[tuple[str | None, str]] = []
        for k, v in value.items():
            out.extend(_str_leaves(v, k))
        return out
    if isinstance(value, (list, tuple)):
        out: list[tuple[str | None, str]] = []
        for v in value:
            out.extend(_str_leaves(v, k))
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


def _constrained(c: Ctx, tool: str, key: str | None) -> bool:
    """True when the tool schema fixes this field's value with enum, const or default."""
    if key is None:
        return False
    props = c.a.schema(tool).get("properties", {})
    spec = props.get(key) if isinstance(props, dict) else None
    return isinstance(spec, dict) and any(k in spec for k in ("enum", "const", "default"))


@rule(
    "NT-048",
    what=(
        "A write tool argument whose value is neither a number nor an "
        "entity id must trace to the user input or to an earlier tool "
        "result: it passes when the value appears there, and fails when "
        "it does not; schema-constrained values are exempt."
    ),
)
def _nt_048(c: Ctx, tid: str) -> R:
    bad, judged = [], 0
    for r in c.runs:
        seen = (r.input or "")
        for t in r.tools:
            if c.a.is_write(t.name):
                for key, s in _str_leaves(t.args):
                    cand = "" if _constrained(c, t.name, key) else _candidate(s)
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
