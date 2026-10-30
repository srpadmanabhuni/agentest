"""Actionable-report guidance, starter templates and the field linter: presentation only, verdicts unchanged."""

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / "examples/agnostic_demo/agents"
ENV = {**os.environ, "PYTHONPATH": str(ROOT / "src"), "AGENTEST_JUDGE_URL": "off"}


def _cli(*a):
    return subprocess.run([sys.executable, "-m", "agentest.cli", "std", *a], capture_output=True, text=True, env=ENV, cwd=ROOT)


def _run(tmp, name, *extra):
    out = tmp / name
    p = _cli("run", "--agents", str(DEMO), "--max-na", "1", "--json", str(out), "--judge", "off", *extra)
    assert p.returncode in (0, 1), p.stderr
    return out.read_bytes()


def test_verdicts_byte_identical_with_and_without_explain(tmp_path):
    plain = _run(tmp_path, "plain.json")
    shown = json.loads(_run(tmp_path, "explain.json", "--explain"))
    assert any("guide" in c for row in shown.values() for c in row.values())
    stripped = {a: {i: {k: v for k, v in c.items() if k != "guide"} for i, c in row.items()} for a, row in shown.items()}
    assert json.loads(plain) == stripped


def test_every_fail_and_na_gets_guidance(tmp_path):
    from agentest.standards import guidance, rules

    assert set(rules.RULES) <= set(guidance.table())
    shown = json.loads(_run(tmp_path, "e.json", "--explain"))
    for row in shown.values():
        for tid, c in row.items():
            if c["status"] == "fail":
                assert {"rule", "where", "fix"} <= set(c["guide"]), tid
                assert c["guide"]["where"], tid
            elif c["status"] == "n/a":
                assert c["guide"]["missing"] and c["guide"]["how"], tid


def test_guidance_table_is_current():
    p = subprocess.run([sys.executable, "scripts/gen_guidance.py", "--check"], capture_output=True, text=True, env=ENV, cwd=ROOT)
    assert p.returncode == 0, p.stdout + p.stderr


def test_template_agent_has_no_fail_and_metadata_cuts_na():
    sys.path.insert(0, str(ROOT / "scripts"))
    import template_uplift

    rows, _cols = template_uplift.measure()
    for name, bare, _t, _c, both, full in rows:
        assert both < bare, name
        assert both >= full - 1e-9, name
    p = _cli("run", "--agents", str(ROOT / "templates"), "--max-na", "1", "--strict", "--judge", "off")
    assert p.returncode == 0, p.stdout


def test_lint_lists_missing_fields_and_unlocked_checks(tmp_path):
    ag = next(d for d in sorted(DEMO.iterdir()) if (d / "traces").is_dir())  # first demo agent, whatever it is called
    traces = sorted(str(p) for p in (ag / "traces").iterdir())
    p = _cli("lint", *traces, "--json", str(tmp_path / "l.json"))
    assert p.returncode == 0, p.stderr
    rep = json.loads((tmp_path / "l.json").read_text())
    assert rep["n/a"] == sum(len(f["unlocks"]) for f in rep["missing"])
    fields = {f["field"] for f in rep["missing"]}
    assert "AgentCard / tools.json metadata" in fields
    assert any(s["signal"] == "approvals" for s in rep["absent_signals"])
    with_meta = _cli("lint", *traces, "--card", str(ag / "agent-card.json"), "--tools", str(ag / "tools.json"),
                     "--json", str(tmp_path / "m.json"))
    assert with_meta.returncode == 0
    assert json.loads((tmp_path / "m.json").read_text())["n/a"] < rep["n/a"]
    assert _cli("lint").returncode == 2
