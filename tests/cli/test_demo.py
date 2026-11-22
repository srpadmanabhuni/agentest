"""agentest demo: one-command summary of a bundled sample, offline."""

from __future__ import annotations

import re
from pathlib import Path

from agentest.cli import build_parser, format_demo_report, main

ROOT = Path(__file__).resolve().parents[2]
README = (ROOT / "README.md").read_text(encoding="utf-8")


def _try_it() -> str:
    assert "## Try it in 10 seconds" in README, "README lost its Try it in 10 seconds section"
    return README.split("## Try it in 10 seconds", 1)[1].split("\n## ", 1)[0]


def test_demo_is_a_subcommand():
    parser = build_parser()
    cmds = next(a for a in parser._actions if a.__class__.__name__ == "_SubParsersAction").choices
    assert "demo" in cmds


def test_demo_help_is_offline_and_count_free():
    parser = build_parser()
    help_text = parser.format_help()
    assert "agentest demo" in help_text
    assert "pip install agentest-ai" in help_text
    # no test-count breakdown in the new quickstart help
    assert "110 + 20" not in help_text
    assert "130 default" not in help_text


def test_demo_prints_counts_and_findings(capsys, monkeypatch):
    monkeypatch.delenv("FORCE_COLOR", raising=False)
    monkeypatch.delenv("CLICOLOR_FORCE", raising=False)
    monkeypatch.setenv("NO_COLOR", "1")
    assert main(["demo", "--no-color"]) == 0
    out = capsys.readouterr().out
    assert "bundled sample overreach" in out
    assert re.search(r"\d+ passed", out)
    assert re.search(r"\d+ failed", out)
    assert re.search(r"\d+ n/a", out)
    assert "FAIL  T5-007" in out
    assert "write calls without confirm=True" in out
    assert "FAIL  T3-007" in out
    assert "\033[" not in out
    # a few findings, not the full table
    assert out.count("FAIL") <= 5
    assert "| T5-007 |" not in out


def test_demo_html_report(tmp_path, capsys, monkeypatch):
    monkeypatch.setenv("NO_COLOR", "1")
    dest = tmp_path / "report.html"
    assert main(["demo", "--no-color", "--html", str(dest)]) == 0
    out = capsys.readouterr().out
    assert f"wrote HTML report to {dest}" in out
    html = dest.read_text(encoding="utf-8")
    assert "T5-007" in html
    assert "failed" in html
    assert "overreach" in html
    assert "class='fail'" in html or 'class="fail"' in html or "class='fail'" in html


def test_demo_unknown_agent(capsys):
    assert main(["demo", "--agent", "no-such-agent", "--no-color"]) == 2
    err = capsys.readouterr().err
    assert "unknown agent" in err
    assert "overreach" in err


def test_demo_respects_force_color(monkeypatch):
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.setenv("FORCE_COLOR", "1")
    from agentest.cli import _color_enabled

    assert _color_enabled(False) is True
    assert _color_enabled(True) is False


def test_format_demo_report_includes_next_steps():
    res = {
        "overreach": {
            "T5-007": {"status": "fail", "detail": "write calls without confirm=True: 1"},
            "T1-001": {"status": "pass", "detail": "ok"},
            "T1-002": {"status": "n/a", "detail": "no signal"},
        }
    }
    text = format_demo_report(res, version="0.0.0", agent="overreach", color=False)
    assert "1 passed" in text and "1 failed" in text and "1 n/a" in text
    assert "FAIL  T5-007" in text
    assert "agentest demo --html report.html" in text
    assert "agentest std run --otlp" in text
    assert "\033[" not in text


def test_readme_try_it_block_matches_demo(capsys, monkeypatch):
    section = _try_it()
    assert "```bash\npip install agentest-ai\n```" in section
    assert "```bash\nagentest demo\nagentest demo --agent a28\nagentest demo --html report.html\n```" in section
    # The fenced real-output block is the no-color demo, minus a trailing prompt.
    blocks = re.findall(r"```text\n(.*?)```", section, re.S)
    assert blocks, "README Try it section has no text output fence"
    expected = blocks[0]
    monkeypatch.setenv("NO_COLOR", "1")
    assert main(["demo", "--no-color"]) == 0
    actual = capsys.readouterr().out
    assert actual == expected, "README output snippet is not the real agentest demo --no-color output"


def test_readme_try_it_has_no_forbidden_wording():
    section = _try_it().lower()
    assert "synthetic" not in section
    assert "fork" not in section
    assert "110 + 20" not in section
    assert "130 default" not in section
    assert "30 new tests" not in section
    assert "5 opt-in" not in section
