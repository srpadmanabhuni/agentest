"""CLI: agentest run | samples | matrix."""

from __future__ import annotations

import argparse
import json
import sys

from agentest.cases.registry import ALL_AGENTS
from agentest.runner import SUITE_IDS, all_passed, matrix_ok, run_ids, run_matrix
from agentest.types import Outcome


def main(argv: list[str] | None = None) -> int:
    """Command-line entry point; returns the process exit code."""
    parser = argparse.ArgumentParser(prog="agentest", description="Agentic AI checklist runner")
    sub = parser.add_subparsers(dest="cmd")

    run = sub.add_parser("run", help="Run checklist IDs")
    run.add_argument("--suite", default="functional", choices=sorted(SUITE_IDS))
    run.add_argument(
        "--ids",
        default=None,
        help="Comma-separated catalogue IDs (default: all IDs in --suite)",
    )
    run.add_argument(
        "--agent",
        default="golden",
        choices=list(ALL_AGENTS),
        help=(
            "Agent under test: golden|broken|noop|eager|scripted|policy|reflective|"
            "supervisor|handoff|planner|critic|federation|"
            "leaky|hallucinator|biased|overreach|flaky_plan"
        ),
    )
    run.add_argument("--json", action="store_true", help="Emit machine-readable results")

    samples = sub.add_parser(
        "samples",
        help="List teaching sample agents (complexity 1–15; 11–15 expected-fail)",
    )
    samples.add_argument("--json", action="store_true", help="Emit JSON")
    samples.add_argument(
        "--failing",
        action="store_true",
        help="List only expected-fail scenarios (cx 11–15: leaky…flaky_plan)",
    )

    matrix = sub.add_parser(
        "matrix",
        help=(
            "Run all suites × sample agents (and golden). "
            "Exit 0 if scripted…federation/(golden) all-pass; "
            "noop/eager and expected-fail scenarios (leaky…flaky_plan) may fail."
        ),
    )
    matrix.add_argument(
        "--no-golden",
        action="store_true",
        help="Omit the golden oracle agent from the matrix",
    )
    matrix.add_argument("--json", action="store_true", help="Emit JSON summary")

    real = sub.add_parser(
        "real",
        help="Real checks for the 41 catalogue IDs: sample agents + recorded reference-agent episodes (offline replay)",
    )
    real.add_argument("--agents", choices=["samples", "reference", "all"], default="all")
    real.add_argument("--episodes", default=None, help="Directory of recorded *.jsonl episodes (default: bundled fixtures/real/episodes)")
    real.add_argument("--md", default=None, help="Write the markdown matrix to this path")
    real.add_argument("--json", default=None, help="Write the JSON matrix to this path")
    real.add_argument("--ids", default=None, help="Comma-separated IDs: print only these cells (agent, status, detail)")

    lst = sub.add_parser("list", help="List catalogue tests, optionally filtered by class (T1..T7), severity or eval group")
    lst.add_argument("--class", dest="class_id", default=None, help="Class ID, e.g. T3")
    lst.add_argument(
        "--severity",
        default=None,
        help="Comma-separated severities, e.g. critical,high (default: all)",
    )
    lst.add_argument(
        "--group",
        default=None,
        help="Comma-separated eval groups, e.g. security,privacy (default: all)",
    )
    lst.add_argument("--json", action="store_true", help="Emit JSON")

    chk = sub.add_parser("check", help="Check YOUR agent: trace-level checks over a JSONL file of recorded episodes")
    chk.add_argument("episodes", help="Path to episodes .jsonl (format: docs/BYO-AGENT.md)")
    chk.add_argument("--md", default=None, help="Write a Markdown report here")
    chk.add_argument("--html", default=None, help="Write a self-contained HTML report here")
    chk.add_argument("--json", action="store_true", help="Print JSON instead of a table")
    chk.add_argument("--strict", action="store_true", help="Exit 1 if any check fails")

    sub.add_parser("version", help="Print the agentest version")

    args = parser.parse_args(argv)

    if args.cmd == "check":
        return _cmd_check(args)
    if args.cmd == "version":
        from agentest import __version__

        print(__version__)
        return 0

    if args.cmd == "list":
        return _cmd_list(args)

    if args.cmd == "real":
        return _cmd_real(args)

    if args.cmd == "samples":
        return _cmd_samples(args)
    if args.cmd == "matrix":
        return _cmd_matrix(args)
    if args.cmd != "run":
        parser.print_help()
        return 2

    ids: list[str] | None = None
    if args.ids is not None:
        ids = [part.strip() for part in args.ids.split(",") if part.strip()]
        if not ids:
            print("error: --ids must list at least one checklist ID", file=sys.stderr)
            return 2

    try:
        results = run_ids(ids, suite=args.suite, agent=args.agent)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.json:
        payload = [
            {
                "id": r.checklist_id,
                "outcome": r.outcome.value,
                "reason": r.reason,
                "details": r.details,
            }
            for r in results
        ]
        print(json.dumps(payload, indent=2))
    else:
        for r in results:
            mark = {
                Outcome.PASS: "PASS",
                Outcome.FAIL: "FAIL",
                Outcome.UNVERIFIED: "UNVERIFIED",
            }[r.outcome]
            print(f"{r.checklist_id}\t{mark}\tagent={args.agent}\t{r.reason}")

    return 0 if all_passed(results) else 1


def _cmd_check(args: argparse.Namespace) -> int:
    """Run the trace checks on a user's episodes file."""
    from pathlib import Path

    from agentest import byo

    p = Path(args.episodes)
    if not p.is_file():
        print(f"error: no such file: {p}", file=sys.stderr)
        return 2
    try:
        res = byo.run(byo.load(p))
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if args.md:
        Path(args.md).write_text(byo.to_md(p.stem, res), encoding="utf-8")
    if args.html:
        Path(args.html).write_text(byo.to_html(p.stem, res), encoding="utf-8")
    if args.json:
        print(json.dumps({i: {"status": r.status, "detail": r.detail} for i, r in res.items()}, indent=2))
    else:
        for i, r in res.items():
            print(f"{i}\t{r.status.upper()}\t{r.detail}")
    fails = sum(r.status in ("fail", "error") for r in res.values())
    return 1 if (args.strict and fails) else 0


def _cmd_samples(args: argparse.Namespace) -> int:
    from agentest.samples import MATRIX_EXPECTED_FAIL, MATRIX_MUST_PASS, list_samples

    infos = list_samples(failing_only=args.failing)
    if args.json:
        print(
            json.dumps(
                [
                    {
                        "name": i.name,
                        "title": i.title,
                        "complexity": i.complexity,
                        "description": i.description,
                        "expected_fail": i.name in MATRIX_EXPECTED_FAIL,
                        "must_pass": i.name in MATRIX_MUST_PASS,
                    }
                    for i in infos
                ],
                indent=2,
            )
        )
    else:
        print(f"{'name':<14} {'cx':>2}  title")
        print("-" * 64)
        for i in infos:
            print(f"{i.name:<14} {i.complexity:>2}  {i.title}")
            print(f"{'':14}     {i.description}")
            print()
        if not args.failing:
            print(
                "Tip: `agentest samples --failing` lists cx 11–15 expected-fail scenarios only."
            )
    return 0


def _cmd_matrix(args: argparse.Namespace) -> int:
    summary = run_matrix(include_golden=not args.no_golden)
    if args.json:
        print(json.dumps(summary, indent=2))
    else:
        print(f"{'agent':<14} {'pass':>5} {'fail':>5} {'unv':>5} {'total':>5}")
        print("-" * 42)
        for agent, row in summary.items():
            print(
                f"{agent:<14} {row['pass']:>5} {row['fail']:>5} "
                f"{row['unverified']:>5} {row['total']:>5}"
            )
        print()
        print(
            "Note: noop/eager and expected-fail scenarios (leaky…flaky_plan) are "
            "meant to fail some IDs. Exit status reflects scripted…federation/"
            "(golden) all-pass only (MATRIX_MUST_PASS)."
        )
    return 0 if matrix_ok(summary) else 1




def _cmd_real(args: argparse.Namespace) -> int:
    """Exit 0 when the real matrix was built; agent failures are findings, not errors.

    Exit 1 only if a reference agent has no recorded episodes (``not-run``).
    """
    from pathlib import Path

    from agentest.paths import episodes_dir
    from agentest.real.report import main_report, to_markdown

    m = main_report(
        Path(args.episodes) if args.episodes else episodes_dir(),
        Path(args.md) if args.md else None,
        Path(args.json) if args.json else None,
        args.agents in ("samples", "all"),
        args.agents in ("reference", "all"),
    )
    if args.ids:
        want = [x.strip() for x in args.ids.split(",") if x.strip()]
        bad = [x for x in want if not any(x in row for row in m.values())]
        if bad:
            print(f"unknown IDs: {bad}")
            return 2
        for i in want:
            for a, row in m.items():
                print(f"{i}\t{a}\t{row[i].status}\t{row[i].detail}")
    elif not args.md:
        print(to_markdown(m))
    not_run = [a for a, row in m.items() if any(r.status == "not-run" for r in row.values())]
    if not_run:
        print(f"not run (no episodes): {not_run}")
        return 1
    return 0


def _parse_multi(value: str | None) -> list[str]:
    """Split a comma-separated CLI value into normalised, non-empty tokens."""
    if not value:
        return []
    return [part.strip().lower() for part in value.split(",") if part.strip()]


def _cmd_list(args: argparse.Namespace) -> int:
    """Print catalogue rows (ID, class, title), optionally filtered."""
    from agentest.real.ids import catalogue

    rows = list(catalogue().values())
    if args.class_id:
        cid = args.class_id.upper()
        rows = [r for r in rows if r.get("class_id") == cid]
        if not rows:
            print(f"No tests for class {cid}; valid classes are T1..T7", file=sys.stderr)
            return 2

    severities = _parse_multi(getattr(args, "severity", None))
    if severities:
        known = sorted({r.get("severity") for r in catalogue().values() if r.get("severity")})
        unknown = [s for s in severities if s not in known]
        if unknown:
            print(
                f"No tests for severity {','.join(unknown)}; "
                f"valid severities are {','.join(known)}",
                file=sys.stderr,
            )
            return 2
        rows = [r for r in rows if (r.get("severity") or "").lower() in severities]

    groups = _parse_multi(getattr(args, "group", None))
    if groups:
        known = sorted({r.get("eval_group") for r in catalogue().values() if r.get("eval_group")})
        unknown = [g for g in groups if g not in known]
        if unknown:
            print(
                f"No tests for group {','.join(unknown)}; "
                f"valid groups are {','.join(known)}",
                file=sys.stderr,
            )
            return 2
        rows = [r for r in rows if (r.get("eval_group") or "").lower() in groups]

    if args.json:
        print(
            json.dumps(
                [
                    {
                        **{k: r.get(k) for k in ("id", "class_id", "title", "severity")},
                        "eval_group": r.get("eval_group"),
                    }
                    for r in rows
                ],
                indent=2,
            )
        )
    else:
        for r in rows:
            print(f"{r['id']}  [{r['class_id']}] {r['title']}")
        print(f"{len(rows)} test(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

