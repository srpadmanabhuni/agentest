#!/usr/bin/env python3
"""Generate llms-full.txt (and the GitHub Pages copy) from the current tree.

The file is a single plain-text bundle for AI crawlers: the README, install
steps, a CLI reference taken from the live argparse parser, and one-line
failure conditions for every test ID the runner knows. Run:

    PYTHONPATH=src python scripts/gen_llms_full.py

The script overwrites llms-full.txt and site/llms-full.txt. A unit test checks
that those files match a fresh build so the bundle stays in sync on every
change to the README, the CLI or the 165 test definitions.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "llms-full.txt"
SITE_OUT = ROOT / "site" / "llms-full.txt"
README = ROOT / "README.md"
INSTALL = ROOT / "docs" / "INSTALL-AND-QUICKSTART.md"


def _ids() -> list[str]:
    from agentest.standards.catalog import ALL_IDS, NEW_TEST_IDS, RAI_ADDITION_IDS

    def key(i: str) -> tuple[int, int, int]:
        prefix, _, rest = i.partition("-")
        # T-class first, then X, then NT, without announcing group sizes.
        family = 0 if prefix.startswith("T") else 1 if prefix == "X" else 2
        class_n = int(prefix[1:]) if prefix.startswith("T") and prefix[1:].isdigit() else 0
        try:
            return family, class_n, int(rest)
        except ValueError:
            return family, class_n, 0

    return sorted(set(ALL_IDS) | set(NEW_TEST_IDS) | set(RAI_ADDITION_IDS), key=key)


def _row(i: str) -> dict:
    from agentest.standards.catalog import catalogue, new_tests, rai_additions

    return catalogue().get(i) or new_tests().get(i) or rai_additions().get(i) or {}


def failure_line(i: str) -> str:
    """One-line failure condition taken from the test definition, not invented."""
    from agentest.standards.catalog import what

    row = _row(i)
    fs = (row.get("fail_signal") or "").strip()
    if fs and fs.lower() != "none":
        return _one_line(fs)
    acc = (row.get("acceptance_criteria") or "").strip()
    if "Fail:" in acc:
        fail = acc.split("Fail:", 1)[1]
        if "n/a:" in fail:
            fail = fail.split("n/a:", 1)[0]
        fail = _one_line(fail)
        if fail:
            return fail
    w = _one_line(what(i) or row.get("title") or row.get("objective") or "")
    if w:
        return "The check fails when this does not hold: " + w
    return "The check fails when the recorded trace violates the published rule for this ID."


def _one_line(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().rstrip(".")


def _flags(parser: argparse.ArgumentParser) -> list[str]:
    rows = []
    for act in parser._actions:
        if not act.option_strings or act.help is argparse.SUPPRESS:
            continue
        opt = ", ".join(act.option_strings)
        if act.choices:
            choices = ", ".join(str(c) for c in act.choices)
            rows.append(f"- `{opt}`: choices {choices}.")
        elif act.nargs in ("+", "*"):
            rows.append(f"- `{opt}`: one or more values.")
        else:
            rows.append(f"- `{opt}`.")
    return rows


def _cli_reference() -> str:
    """CLI surface taken from the live argparse parser (flag names, not help strings).

    The live `agentest --help` description still says "130 universal checks" until a
    later CLI change lands. This public bundle must not copy that wording, so the
    reference lists the commands and flags the parser actually registers.
    """
    from agentest.cli import build_parser

    parser = build_parser()
    sub = next(a for a in parser._actions if getattr(a, "dest", None) == "cmd")
    std = sub.choices["std"]
    lines = [
        "The package command is `agentest` after `pip install agentest-ai`.",
        "The usual evaluation command is `agentest std run`.",
        "",
        "### Top-level commands",
        "",
        "- `agentest --help`",
        "- `agentest --version` / `agentest version`",
        "- `agentest list` — list tests; flags: `--class`, `--severity`, `--group`, `--json`, `--packs`, `--pack`, `--opt-in`, `--new-tests`, `--hub-catalogue`.",
        "- `agentest std <action>` — standards-based checks over OpenTelemetry GenAI traces, A2A AgentCards and MCP tool lists.",
        "",
        "### `agentest std` actions",
        "",
        "Actions: `validate`, `run`, `regress`, `export`, `gen`, `catalog`, `import`, `serve`.",
        "",
        "Typical invocations:",
        "",
        "```",
        "agentest std run --otlp my_traces.otlp.jsonl --card agent-card.json --tools tools.json",
        "agentest std run --format junit --out agentest.xml --strict",
        "agentest std run --agent a22 --ids T1-018 --format md",
        "agentest std import episodes.jsonl --map map.json --out traces.otlp.jsonl",
        "```",
        "",
        "### `agentest std` flags registered in the parser",
        "",
    ]
    lines.extend(_flags(std))
    lines.append("")
    return "\n".join(lines)


def build() -> str:
    if str(ROOT / "src") not in sys.path:
        sys.path.insert(0, str(ROOT / "src"))

    ids = _ids()
    if len(ids) != 165:
        raise SystemExit(f"expected 165 test IDs, found {len(ids)}")

    lines: list[str] = []
    lines.append("# agentest (agentest-ai) — deterministic OpenTelemetry evals for AI agents")
    lines.append("")
    lines.append("> agentest (agentest-ai on PyPI) is an open-source, offline, deterministic evaluation framework for AI agents. Built by Dr. Srinivas Padmanabhuni (AiEnsured), it checks OpenTelemetry GenAI traces, A2A AgentCards and MCP tool lists against 165 rule-based tests, catching unauthorized tool calls, prompt injections, unearned success claims and PII leaks without an LLM judge.")
    lines.append("")
    lines.append(
        "The import and the CLI stay agentest. Licence: Apache-2.0. "
        "DOI: 10.5281/zenodo.23597877. Repository: https://github.com/srpadmanabhuni/agentest"
    )
    lines.append("")
    lines.append(
        "This file concatenates the README, install steps, the live CLI reference "
        "and the failure condition of every test ID, so an agent that fetches one "
        "URL can see the exact IDs (T1-018, T4-003, and the rest)."
    )
    lines.append("")
    lines.append("## README")
    lines.append("")
    lines.append(README.read_text(encoding="utf-8").rstrip())
    lines.append("")
    lines.append("## Install")
    lines.append("")
    lines.append("The package name on PyPI is `agentest-ai`. The import and the CLI stay `agentest`.")
    lines.append("")
    lines.append("```")
    lines.append("pip install agentest-ai")
    lines.append("```")
    lines.append("")
    lines.append("To pin a release:")
    lines.append("")
    lines.append("```")
    lines.append('pip install "agentest-ai==3.5.0"')
    lines.append("```")
    lines.append("")
    if INSTALL.is_file():
        lines.append("Further install options from docs/INSTALL-AND-QUICKSTART.md:")
        lines.append("")
        lines.append(INSTALL.read_text(encoding="utf-8").rstrip())
        lines.append("")
    lines.append("## CLI reference")
    lines.append("")
    lines.append(_cli_reference().rstrip())
    lines.append("")
    lines.append("## Test IDs and failure conditions")
    lines.append("")
    lines.append(
        "Each line is one test ID and the failure condition taken from that test's "
        "definition (the catalogue fail_signal, the Fail: clause of the acceptance "
        "criteria, or the published rule when those are absent). This is a flat list "
        "of every ID the runner knows."
    )
    lines.append("")
    for i in ids:
        title = (_row(i).get("title") or "").strip()
        fail = failure_line(i)
        if title:
            lines.append(f"{i} — {title}. Fails when: {fail}.")
        else:
            lines.append(f"{i}. Fails when: {fail}.")
    lines.append("")
    return "\n".join(lines)


def write(text: str | None = None) -> None:
    body = text if text is not None else build()
    OUT.write_text(body, encoding="utf-8")
    SITE_OUT.parent.mkdir(parents=True, exist_ok=True)
    SITE_OUT.write_text(body, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="exit 1 if llms-full.txt or site/llms-full.txt are out of date",
    )
    args = parser.parse_args()
    body = build()
    if args.check:
        stale = [
            path.relative_to(ROOT).as_posix()
            for path in (OUT, SITE_OUT)
            if not path.is_file() or path.read_text(encoding="utf-8") != body
        ]
        if stale:
            print("out of date:", ", ".join(stale), file=sys.stderr)
            print("run: PYTHONPATH=src python scripts/gen_llms_full.py", file=sys.stderr)
            raise SystemExit(1)
        return
    write(body)
    print(f"wrote {OUT.relative_to(ROOT)} and {SITE_OUT.relative_to(ROOT)} ({body.count(chr(10))+1} lines)")


if __name__ == "__main__":
    main()
