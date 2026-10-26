"""Build the 130-ID x agents matrix (15 sample agents + the vendored reference agents)."""

from __future__ import annotations

import json
from pathlib import Path

from agentest.model.expr import R
from agentest.real.ids import ALL_IDS, X_IDS, what

SYM = {"pass": "P", "fail": "F", "n/a": "-", "not-run": "?"}


def build(episodes_dir: Path | None = None, include_samples: bool = True, include_reference: bool = True) -> dict[str, dict[str, R]]:
    """Evaluate every profiled agent with the model-driven engine and return ``{agent: {id: R}}``.

    Sample agents (``adapter: sample``) come first, then reference agents in profile order.
    ``episodes_dir`` overrides where reference episodes are read from.
    """
    from agentest.model.adapters import adapt
    from agentest.model.generic import evaluate
    from agentest.model.profile import load_all
    from agentest.model.runner import native_episodes

    profs = load_all()
    from agentest.cases.registry import SAMPLE_AGENTS

    rank = {a: n for n, a in enumerate(SAMPLE_AGENTS)}
    order = sorted((a for a, p in profs.items() if p.adapter == "sample"), key=lambda a: rank.get(a, len(rank))) if include_samples else []
    order += [a for a, p in profs.items() if p.adapter != "sample"] if include_reference else []
    return {a: evaluate(profs[a], [adapt(r, profs[a]) for r in native_episodes(profs[a], episodes_dir)]) for a in order}


def to_json(m: dict[str, dict[str, R]]) -> dict:
    """Matrix as plain JSON (status + detail per cell)."""
    return {a: {i: {"status": r.status, "detail": r.detail} for i, r in row.items()} for a, row in m.items()}


def to_markdown(m: dict[str, dict[str, R]]) -> str:
    """Matrix, failures and per-ID descriptions as Markdown."""
    agents = list(m)
    lines = ["| ID | " + " | ".join(agents) + " |", "|---|" + "---|" * len(agents)]
    for i in ALL_IDS:
        lines.append(f"| {i} | " + " | ".join(SYM[m[a][i].status] for a in agents) + " |")
    tot = {a: {s: sum(1 for r in m[a].values() if r.status == s) for s in SYM} for a in agents}
    lines.append("| **pass/fail/n-a** | " + " | ".join(f"{t['pass']}/{t['fail']}/{t['n/a']}" for t in tot.values()) + " |")
    fails = [f"- **{a} {i}**: {m[a][i].detail}" for a in agents for i in ALL_IDS if m[a][i].status == "fail"]
    legend = "P = pass, F = fail, - = n/a (agent has no surface for the ID), ? = not run"
    ids = "\n".join(f"- **{i}**: {what(i)}" for i in ALL_IDS)
    head = (f"# Real-test results matrix ({len(ALL_IDS)} IDs x {len(agents)} agents)\n\n"
            f"Real checks: {len(ALL_IDS)} of {len(ALL_IDS)} ({len(ALL_IDS) - len(X_IDS)} catalogue IDs + {len(X_IDS)} repo extensions X-001..X-020). Placeholders: 0.")
    return "\n".join([head, "", legend, "", *lines, "", "## Failures", "", *fails, "", "## What each ID checks (reference agents)", "", ids, ""])


def main_report(episodes_dir: Path, md: Path | None, js: Path | None, samples: bool, reference: bool) -> dict:
    """Build the matrix and write the Markdown / JSON reports."""
    m = build(episodes_dir, samples, reference)
    if md:
        md.write_text(to_markdown(m))
    if js:
        js.write_text(json.dumps(to_json(m), indent=1))
    return m
