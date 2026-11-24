"""Reader changes for the trace format (D2 aliases, D7 declarations, D8 record forms) move no verdict: every bundled
agent gets the same status on every default check (and the opt-in responsible-AI checks), in both modes, as on the
base commit recorded in tests/fixtures/bundled-verdicts.json.

Agents a161-a170 are excluded by path. An audit hook records every open / listing of a path while the table is
built, and the test asserts that none of them is inside an excluded agent directory."""

from __future__ import annotations

import json
import os
import sys

from tests import bundled_verdicts as bv

_WATCH = {"on": False, "paths": []}


def _hook(event: str, args: tuple) -> None:
    if _WATCH["on"] and event in ("open", "os.listdir", "os.scandir") and args and isinstance(args[0], str | bytes | os.PathLike):
        _WATCH["paths"].append(os.fsdecode(args[0]))


sys.addaudithook(_hook)


def _inside_excluded(p: str) -> bool:
    ap = os.path.abspath(p)
    return any(ap == str(x) or ap.startswith(str(x) + os.sep) for x in bv.EXCLUDED_PATHS)


def test_excluded_agents_are_never_touched_and_verdicts_are_unchanged():
    assert len(bv.EXCLUDED_NAMES) == 10 and {"a161", "a170"} <= bv.EXCLUDED_NAMES
    _WATCH["paths"].clear()
    _WATCH["on"] = True
    try:
        dirs = bv.agent_dirs()
        table = bv.table()
    finally:
        _WATCH["on"] = False
    assert _WATCH["paths"], "the audit hook saw no file access"
    assert not [p for p in _WATCH["paths"] if _inside_excluded(p)]
    assert not bv.EXCLUDED_PATHS & set(dirs) and not any(d.name in bv.EXCLUDED_NAMES for d in dirs)
    assert not any(k.split("/")[-1] in bv.EXCLUDED_NAMES for k in table)

    want = json.loads(bv.FIXTURE.read_text(encoding="utf-8"))
    order = bv.ids()
    assert order == want["ids"] and len(order) >= 130
    assert set(table) == set(want["verdicts"]) and len(table) >= 100
    diff = [(a, m, order[k], want["verdicts"][a][m][k], got[k]) for a, row in table.items() for m, v in row.items()
            for got in [bv.encode(v, order)] for k in range(len(order)) if got[k] != want["verdicts"][a][m][k]]
    assert not diff, diff[:20]
    cells = sum(len(v) for row in table.values() for v in row.values())
    assert cells == len(table) * len(bv.MODES) * len(order)
