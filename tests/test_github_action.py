"""The composite GitHub Action (action.yml) and the pre-commit hooks (.pre-commit-hooks.yaml) are well formed and work.

The action's run logic lives in scripts/gh_action_run.sh, so these tests run it directly with the same AGENTEST_*
environment the action sets. The CI job `action-self-test` also runs the action itself with `uses: ./`.
"""
import os
import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
DEMO = "examples/agnostic_demo/agents"
SCRIPT = ROOT / "scripts" / "gh_action_run.sh"
needs_bash = pytest.mark.skipif(not shutil.which("bash"), reason="needs bash")


def _action():
    return yaml.safe_load((ROOT / "action.yml").read_text())


def _hooks():
    return yaml.safe_load((ROOT / ".pre-commit-hooks.yaml").read_text())


def _env(**inputs):
    env = {k: v for k, v in os.environ.items() if not k.startswith(("AGENTEST_", "GITHUB_"))}
    env["PATH"] = str(Path(sys.executable).parent) + os.pathsep + env.get("PATH", "")
    env.update({f"AGENTEST_{k.upper()}": v for k, v in inputs.items()})
    return env


def _run(tmp_path, **inputs):
    inputs.setdefault("report", str(tmp_path / "report.md"))
    env = _env(**inputs)
    env["GITHUB_OUTPUT"] = str(tmp_path / "out.txt")
    env["GITHUB_STEP_SUMMARY"] = str(tmp_path / "summary.md")
    p = subprocess.run(["bash", str(SCRIPT)], cwd=ROOT, env=env, capture_output=True, text=True, timeout=600)
    out = tmp_path / "out.txt"
    outputs = dict(line.split("=", 1) for line in out.read_text().splitlines()) if out.exists() else {}
    return p, outputs


def test_action_is_composite_and_offline():
    a = _action()
    assert a["runs"]["using"] == "composite"
    assert a["name"] and a["description"] and a["branding"]
    for step in a["runs"]["steps"]:
        run = step.get("run", "")
        # Inputs reach shell code only through env, never interpolated into the script (no injection).
        assert "inputs." not in run, step["name"]
        assert "secrets." not in yaml.safe_dump(step)
        if "uses" in step:
            assert re.fullmatch(r"actions/setup-python@v\d+", step["uses"]), step["uses"]


def test_action_env_matches_inputs_and_script():
    a = _action()
    inputs = set(a["inputs"])
    run_step = next(s for s in a["runs"]["steps"] if s.get("id") == "run")
    env = run_step["env"]
    for key, value in env.items():
        name = re.fullmatch(r"\$\{\{ inputs\.([a-z-]+) \}\}", value).group(1)
        assert name in inputs, name
        assert key == "AGENTEST_" + name.upper().replace("-", "_"), key
        assert key in SCRIPT.read_text(), key
    # the comment inputs belong to the optional "Post or update the PR comment" step (tests/test_action_pr_comment.py)
    assert inputs - {"python-version", "install", "github-token", "comment-key", "pr-number", "github-api-url"} == {
        re.fullmatch(r"\$\{\{ inputs\.([a-z-]+) \}\}", v).group(1) for v in env.values()}
    for name in ("exit-code", "passed", "failed", "not-applicable", "report"):
        assert f"steps.run.outputs.{name}" in a["outputs"][name]["value"]
        assert f"{name}=" in SCRIPT.read_text()


def test_action_installs_from_its_own_ref_by_default():
    install = next(s for s in _action()["runs"]["steps"] if s["name"] == "Install agentest")
    assert install["env"]["AGENTEST_ACTION_PATH"] == "${{ github.action_path }}"
    assert '"$AGENTEST_ACTION_PATH"' in install["run"]
    assert os.access(SCRIPT, os.X_OK)


@needs_bash
def test_action_otlp_pass(tmp_path):
    p, out = _run(tmp_path, otlp=f"{DEMO}/refill_bot/traces/*.otlp.jsonl",
                  card=f"{DEMO}/refill_bot/agent-card.json", tools=f"{DEMO}/refill_bot/tools.json")
    assert p.returncode == 0, p.stdout + p.stderr
    assert out["exit-code"] == "0" and out["failed"] == "0" and int(out["passed"]) > 0
    summary = (tmp_path / "summary.md").read_text()
    assert "AiEnsured agentest" in summary and "0 fail" in summary
    assert (tmp_path / "report.md").exists()


@needs_bash
def test_action_agent_folder_fail_is_caught(tmp_path):
    p, out = _run(tmp_path, agents=DEMO, agent="refill_bot_buggy", format="junit",
                  report=str(tmp_path / "r.xml"))
    assert p.returncode == 1, p.stdout + p.stderr
    assert out["exit-code"] == "1" and int(out["failed"]) > 0
    assert (tmp_path / "r.xml").read_text().lstrip().startswith("<")


@needs_bash
def test_action_report_only_mode(tmp_path):
    p, out = _run(tmp_path, agents=DEMO, agent="refill_bot_buggy", **{"fail_on_fail": "false"})
    assert p.returncode == 0, p.stdout + p.stderr
    assert int(out["failed"]) > 0


@needs_bash
@pytest.mark.parametrize("otlp", ["no/such/*.otlp.jsonl", "missing.otlp.json", "x;$(touch pwned)"])
def test_action_rejects_missing_files_without_evaluating_input(tmp_path, otlp):
    p, _ = _run(tmp_path, otlp=otlp)
    assert p.returncode == 2 and "no OTLP trace file matches" in p.stdout
    assert not (ROOT / "pwned").exists()


@needs_bash
def test_action_rejects_unknown_format(tmp_path):
    p, _ = _run(tmp_path, format="pdf")
    assert p.returncode == 2


def test_pre_commit_hooks_manifest():
    hooks = {h["id"]: h for h in _hooks()}
    assert set(hooks) == {"agentest-otlp", "agentest-agents", "agentest-validate"}
    for h in hooks.values():
        assert h["language"] == "python" and h["entry"].startswith("agentest std ")
        assert {"name", "files", "pass_filenames"} <= set(h)
    assert hooks["agentest-otlp"]["pass_filenames"] is True and hooks["agentest-otlp"]["args"][-1] == "--otlp"
    otlp_files = re.compile(hooks["agentest-otlp"]["files"])
    agent_files = re.compile(hooks["agentest-agents"]["files"])
    for path in (f"{DEMO}/refill_bot/traces/refill_bot.otlp.jsonl", "t.otlp.json", "t.otlp.pb"):
        assert otlp_files.search(path) and agent_files.search(path), path
    assert agent_files.search(f"{DEMO}/refill_bot/agent-card.json")
    assert not otlp_files.search("README.md") and not agent_files.search("README.md")


def _hook_cmd(hook_id, *extra):
    h = {h["id"]: h for h in _hooks()}[hook_id]
    return shlex.split(h["entry"]) + list(h.get("args", [])) + list(extra)


@pytest.mark.parametrize("agent, code", [("refill_bot", 0), ("refill_bot_buggy", 1)])
def test_pre_commit_otlp_hook_command(agent, code):
    # pre-commit runs: entry + args + staged file names.
    cmd = _hook_cmd("agentest-otlp", f"{DEMO}/{agent}/traces/{agent}.otlp.jsonl")
    cmd[cmd.index("--otlp"):cmd.index("--otlp")] = ["--card", f"{DEMO}/{agent}/agent-card.json",
                                                    "--tools", f"{DEMO}/{agent}/tools.json"]
    p = subprocess.run(cmd, cwd=ROOT, env=_env(), capture_output=True, text=True, timeout=600)
    assert p.returncode == code, p.stdout + p.stderr


def test_pre_commit_agent_folder_hooks_use_cwd_agents(tmp_path):
    shutil.copytree(ROOT / DEMO / "refill_bot", tmp_path / "agents" / "refill_bot")
    for hook_id in ("agentest-validate", "agentest-agents"):
        p = subprocess.run(_hook_cmd(hook_id), cwd=tmp_path, env=_env(), capture_output=True, text=True, timeout=600)
        assert p.returncode == 0, (hook_id, p.stdout + p.stderr)
    assert "over 1 agents" in p.stdout
