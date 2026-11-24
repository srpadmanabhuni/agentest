"""Compare two saved ``agentest std run --json`` verdict files.

The files are the plain mapping ``{agent: {id: {"status", "detail"}}}`` written by
``--json``, or the versioned report from ``--format json`` (its ``results`` array).
Each top-level agent is one task set. A cell moves at most once: the transition is
``before -> after``. A check that becomes ``fail`` is newly failing; a check that
becomes ``pass`` is newly passing. Statuses that are unchanged are omitted.
"""
# Ref: internal design (src/agentest/standards/cli.py ``std diff``).

from __future__ import annotations

import json
from pathlib import Path

STATUSES = ("pass", "fail", "n/a", "not-run", "missing")


class VerdictFileError(ValueError):
    """A path is missing, not JSON, or not a verdict file this command can read."""


def load_verdicts(path: str | Path) -> dict[str, dict[str, str]]:
    """``{task: {check id: status}}`` from a saved verdict file.

    ``task`` is the agent id in the file (one agent, or one entry of a task set).
    """
    p = Path(path)
    if not p.is_file():
        raise VerdictFileError(f"{p} is not a file")
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise VerdictFileError(f"{p} is not valid JSON ({e.msg}, line {e.lineno})") from None
    if isinstance(data, dict) and isinstance(data.get("results"), list):
        return _from_results(p, data["results"])
    if isinstance(data, dict) and data and all(isinstance(v, dict) for v in data.values()):
        # A versioned document without results, or a plain --json map. Ignore the schema keys.
        body = {k: v for k, v in data.items() if k not in {"schema", "$schema", "tool", "mode", "trials"}}
        if body and all(_is_cell_map(v) for v in body.values()):
            return {task: {i: _status(p, task, i, cell) for i, cell in row.items()} for task, row in body.items()}
    raise VerdictFileError(
        f"{p} is not a verdict file from `agentest std run --json` "
        "(expected {agent: {id: {status, detail}}} or a versioned report with results)"
    )


def _is_cell_map(row: dict) -> bool:
    return all(isinstance(cell, dict) and "status" in cell for cell in row.values())


def _status(path: Path, task: str, check: str, cell: dict) -> str:
    status = cell.get("status")
    if status not in STATUSES:
        raise VerdictFileError(f"{path}: {task} {check} has status {status!r}; expected pass, fail, n/a or not-run")
    return str(status)


def _from_results(path: Path, results: list) -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {}
    for n, row in enumerate(results):
        if not isinstance(row, dict) or "agent" not in row or "id" not in row:
            raise VerdictFileError(f"{path}: results[{n}] needs agent, id and status")
        out.setdefault(str(row["agent"]), {})[str(row["id"])] = _status(path, str(row["agent"]), str(row["id"]), row)
    return out


def diff_verdicts(old: dict[str, dict[str, str]], new: dict[str, dict[str, str]]) -> dict:
    """Every status change, grouped by task then check id.

    ``newly_failing`` is every change whose new status is ``fail``.
    ``newly_passing`` is every change whose new status is ``pass``.
    ``transitions`` is every change, including those two.
    """
    transitions = []
    tasks = sorted(set(old) | set(new))
    for task in tasks:
        ids = sorted(set(old.get(task, {})) | set(new.get(task, {})))
        for check in ids:
            before = old.get(task, {}).get(check, "missing")
            after = new.get(task, {}).get(check, "missing")
            if before != after:
                transitions.append({"task": task, "id": check, "before": before, "after": after})
    newly_failing = [c for c in transitions if c["after"] == "fail"]
    newly_passing = [c for c in transitions if c["after"] == "pass"]
    return {"newly_failing": newly_failing, "newly_passing": newly_passing, "transitions": transitions}


def render_diff(report: dict) -> str:
    """Text report: summary counts, then one block per task and one line per check."""
    lines = [
        f"newly failing: {len(report['newly_failing'])}",
        f"newly passing: {len(report['newly_passing'])}",
        "",
    ]
    by_task: dict[str, list[dict]] = {}
    for change in report["transitions"]:
        by_task.setdefault(change["task"], []).append(change)
    if not by_task:
        lines.append("no verdict transition")
        return "\n".join(lines)
    blocks = []
    for task, changes in by_task.items():
        rows = [task]
        rows += [f"  {c['id']}  {c['before']} -> {c['after']}" for c in changes]
        blocks.append("\n".join(rows))
    lines.append("\n\n".join(blocks))
    return "\n".join(lines)
