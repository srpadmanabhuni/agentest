"""The action's optional PR comment: off by default, one comment per key updated in place, and a job summary whenever a
comment cannot be written. Runs the real scripts against a local stand-in for the GitHub API (tests/fake_github_api.py)."""
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).parent))
from fake_github_api import FakeGitHub  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DEMO = "examples/agnostic_demo/agents"
RUN = ROOT / "scripts" / "gh_action_run.sh"
COMMENT = ROOT / "scripts" / "gh_action_comment.py"
REPO = "octo/repo"
needs_bash = pytest.mark.skipif(not shutil.which("bash"), reason="needs bash")

spec = importlib.util.spec_from_file_location("gh_action_comment", COMMENT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


@pytest.fixture()
def api():
    srv = FakeGitHub().start()
    yield srv
    srv.stop()


def _event(tmp_path, number=7, head=REPO, base=REPO):
    p = tmp_path / "event.json"
    p.write_text(json.dumps({"pull_request": {"number": number, "head": {"repo": {"full_name": head}}, "base": {"repo": {"full_name": base}}}}))
    return str(p)


def _base_env(tmp_path, **inputs):
    env = {k: v for k, v in os.environ.items() if not k.startswith(("AGENTEST_", "GITHUB_", "RUNNER_"))}
    env["PATH"] = str(Path(sys.executable).parent) + os.pathsep + env.get("PATH", "")
    env["RUNNER_TEMP"] = str(tmp_path)
    env.update({f"AGENTEST_{k.upper()}": v for k, v in inputs.items()})
    return env


def _flow(tmp_path, srv=None, event=None, token="test-token", **inputs):
    """Run the action's two scripts the way action.yml chains them. Returns (run result, comment result, outputs, summary)."""
    inputs.setdefault("agents", DEMO)
    inputs.setdefault("agent", "refill_bot_buggy")
    inputs.setdefault("fail_on_fail", "false")
    inputs.setdefault("pr_comment", "true")
    inputs.setdefault("report", str(tmp_path / "report.md"))
    env = _base_env(tmp_path, **inputs)
    env["GITHUB_OUTPUT"] = str(tmp_path / "run-out.txt")
    env["GITHUB_STEP_SUMMARY"] = str(tmp_path / "run-summary.md")
    run = subprocess.run(["bash", str(RUN)], cwd=ROOT, env=env, capture_output=True, text=True, timeout=600)
    outs = dict(line.split("=", 1) for line in (tmp_path / "run-out.txt").read_text().splitlines())
    cenv = _base_env(tmp_path)
    cenv.update({
        "AGENTEST_PR_COMMENT": inputs["pr_comment"], "AGENTEST_COMMENT_DIR": outs.get("comment-dir", ""),
        "AGENTEST_COMMENT_KEY": inputs.get("comment_key", "agentest"), "AGENTEST_PR_NUMBER": inputs.get("pr_number", ""),
        "AGENTEST_GITHUB_TOKEN": token if inputs["pr_comment"] == "true" else "",
        "GITHUB_REPOSITORY": REPO, "GITHUB_OUTPUT": str(tmp_path / "c-out.txt"), "GITHUB_STEP_SUMMARY": str(tmp_path / "c-summary.md"),
    })
    if srv:
        cenv["AGENTEST_GITHUB_API_URL"] = srv.url
    if event:
        cenv["GITHUB_EVENT_PATH"] = event
    c = subprocess.run([sys.executable, str(COMMENT)], cwd=tmp_path, env=cenv, capture_output=True, text=True, timeout=120)
    out = tmp_path / "c-out.txt"
    couts = dict(line.split("=", 1) for line in out.read_text().splitlines()) if out.exists() else {}
    summ = tmp_path / "c-summary.md"
    couts["_summary"] = summ.read_text() if summ.exists() else ""
    for f in ("c-out.txt", "c-summary.md", "run-out.txt", "run-summary.md"):
        (tmp_path / f).unlink(missing_ok=True)
    return run, c, couts


def _bodies(srv):
    return [c["body"] for lst in srv.comments.values() for c in lst]


# --- action.yml: off by default, least privilege ---------------------------------------------------------------------

def _action():
    return yaml.safe_load((ROOT / "action.yml").read_text())


def test_comment_is_off_by_default_and_token_is_scoped_to_its_own_step():
    a = _action()
    assert a["inputs"]["pr-comment"]["default"] == "false"
    steps = {s.get("id"): s for s in a["runs"]["steps"] if s.get("id")}
    comment = steps["comment"]
    assert "inputs.pr-comment != 'false'" in comment["if"] and "always()" in comment["if"]
    token_env = comment["env"]["AGENTEST_GITHUB_TOKEN"]
    assert "inputs.pr-comment == 'true'" in token_env and "inputs.github-token" in token_env
    assert "token" not in yaml.safe_dump(steps["run"]).lower().replace("github.action_path", "")
    assert "github.token" in a["inputs"]["github-token"]["default"]  # the workflow's own token, nothing extra
    assert "inputs." not in comment["run"]
    assert "permissions" not in a["runs"]["steps"][0]  # a composite action cannot raise the job's permissions
    for name in ("comment-status", "comment-url"):
        assert "steps.comment.outputs." in a["outputs"][name]["value"]


def test_comment_step_env_matches_inputs():
    a = _action()
    comment = next(s for s in a["runs"]["steps"] if s.get("id") == "comment")
    names = {"AGENTEST_PR_COMMENT": "pr-comment", "AGENTEST_COMMENT_KEY": "comment-key", "AGENTEST_PR_NUMBER": "pr-number", "AGENTEST_GITHUB_API_URL": "github-api-url"}
    for key, name in names.items():
        assert comment["env"][key] == "${{ inputs." + name + " }}"
        assert name in a["inputs"]


@needs_bash
def test_default_run_writes_no_comment_files_and_makes_no_request(tmp_path):
    env = _base_env(tmp_path, agents=DEMO, agent="refill_bot_buggy", fail_on_fail="false", report=str(tmp_path / "r.md"))
    env["GITHUB_OUTPUT"] = str(tmp_path / "out.txt")
    p = subprocess.run(["bash", str(RUN)], cwd=ROOT, env=env, capture_output=True, text=True, timeout=600)
    assert p.returncode == 0
    out = dict(line.split("=", 1) for line in (tmp_path / "out.txt").read_text().splitlines())
    assert out["comment-dir"] == ""
    assert not list(tmp_path.glob("agentest-comment.*"))
    r = subprocess.run([sys.executable, str(COMMENT)], cwd=tmp_path, env=_base_env(tmp_path), capture_output=True, text=True)
    assert r.returncode == 0 and "status: off" in r.stdout


@needs_bash
def test_unknown_pr_comment_value_is_rejected(tmp_path):
    env = _base_env(tmp_path, agents=DEMO, pr_comment="always")
    p = subprocess.run(["bash", str(RUN)], cwd=ROOT, env=env, capture_output=True, text=True)
    assert p.returncode == 2 and "pr-comment must be one of" in p.stdout


# --- posting, updating in place --------------------------------------------------------------------------------------

@needs_bash
def test_one_comment_per_pull_request_updated_in_place(tmp_path, api):
    ev = _event(tmp_path)
    run, c, o = _flow(tmp_path, api, ev)
    assert run.returncode == 0 and c.returncode == 0, c.stdout + c.stderr
    assert o["status"] == "created" and o["url"]
    assert [r["method"] for r in api.requests] == ["GET", "POST"]
    first = _bodies(api)[0]
    assert first.startswith("<!-- agentest-action:agentest -->")
    # same result again: found, identical, no edit
    _, _, o = _flow(tmp_path, api, ev)
    assert o["status"] == "unchanged" and len(_bodies(api)) == 1
    assert [r["method"] for r in api.requests[2:]] == ["GET"]
    # a different result: the same comment is edited, not a second one
    api.comments[(REPO, 7)][0]["body"] = first.replace("agentest: ", "agentest (old): ")
    _, _, o = _flow(tmp_path, api, ev)
    assert o["status"] == "updated" and len(_bodies(api)) == 1 and _bodies(api)[0] == first


@needs_bash
def test_comment_lists_failed_ids_with_evidence(tmp_path, api):
    _, _, o = _flow(tmp_path, api, _event(tmp_path))
    body = _bodies(api)[0]
    assert "16 failed checks" in body
    assert re.search(r"\| \*\*`T1-018`\*\* .+ \| `refill_bot_buggy` \| `social#0: claims success` \|", body)
    assert "`T1-004`" in body and "recipients outside fence" in body
    assert "pip install agentest-ai\nagentest std run --agents examples/agnostic_demo/agents --agent refill_bot_buggy --format md" in body
    assert "165 tests" in body
    low = body.lower()
    for word in ("fork", "synthetic", "star ", "best", "fastest"):
        assert word not in low, word
    assert "test-token" not in body


@needs_bash
def test_passing_run_posts_nothing_new_but_updates_an_earlier_comment(tmp_path, api):
    ev = _event(tmp_path)
    _, _, o = _flow(tmp_path, api, ev, agent="refill_bot")
    assert o["status"] == "none" and not api.comments
    api.seed(REPO, 7, "<!-- agentest-action:agentest -->\nold", "Bot", "github-actions[bot]")
    _, _, o = _flow(tmp_path, api, ev, agent="refill_bot")
    assert o["status"] == "updated" and "no failed checks" in _bodies(api)[0]
    assert len(_bodies(api)) == 1


@needs_bash
def test_comment_key_gives_separate_comments(tmp_path, api):
    ev = _event(tmp_path)
    _flow(tmp_path, api, ev, comment_key="a")
    _flow(tmp_path, api, ev, comment_key="b")
    _flow(tmp_path, api, ev, comment_key="a", agent="refill_bot")
    assert len(_bodies(api)) == 2
    assert {b.split("\n", 1)[0] for b in _bodies(api)} == {"<!-- agentest-action:a -->", "<!-- agentest-action:b -->"}


@needs_bash
def test_explicit_pr_number_and_a_person_who_pastes_the_marker(tmp_path, api):
    api.seed(REPO, 9, "<!-- agentest-action:agentest -->\nnot ours", "User", "someone")
    _, c, o = _flow(tmp_path, api, None, pr_number="9")
    # the person's comment cannot be edited with this token: degrade to the summary, add nothing
    assert o["status"] == "error" and len(_bodies(api)) == 1 and _bodies(api)[0].endswith("not ours")
    assert "T1-018" in o["_summary"]
    api.seed(REPO, 9, "<!-- agentest-action:agentest -->\nours", "Bot", "github-actions[bot]")
    _, _, o = _flow(tmp_path, api, None, pr_number="9")
    assert o["status"] == "updated"  # the bot's own comment is preferred


# --- degrade to the job summary --------------------------------------------------------------------------------------

@needs_bash
def test_pull_request_from_another_repository_uses_the_summary_only(tmp_path, api):
    run, c, o = _flow(tmp_path, api, _event(tmp_path, head="someone/repo"))
    assert c.returncode == 0 and o["status"] == "read-only"
    assert api.requests == []
    assert "T1-018" in o["_summary"] and "social#0: claims success" in o["_summary"]
    assert "<!--" not in o["_summary"]
    assert "cannot write comments" in c.stdout and "fork" not in (c.stdout + o["_summary"]).lower()


@needs_bash
def test_read_only_token_degrades_to_the_summary_and_does_not_fail(tmp_path):
    srv = FakeGitHub(read_only=True).start()
    try:
        _, c, o = _flow(tmp_path, srv, _event(tmp_path))
    finally:
        srv.stop()
    assert c.returncode == 0 and o["status"] == "error"
    assert "pull-requests: write" in c.stdout and "403" in c.stdout
    assert "T1-018" in o["_summary"]
    assert "test-token" not in c.stdout + c.stderr + o["_summary"]


@needs_bash
def test_bad_token_and_missing_token_and_no_pull_request(tmp_path, api):
    _, c, o = _flow(tmp_path, api, _event(tmp_path), token="wrong")
    assert c.returncode == 0 and o["status"] == "error" and "401" in c.stdout and not api.comments
    _, c, o = _flow(tmp_path, api, _event(tmp_path), token="")
    assert o["status"] == "no-token"
    _, c, o = _flow(tmp_path, api, None)
    assert o["status"] == "no-pr" and "T1-018" in o["_summary"]


@needs_bash
def test_summary_mode_needs_no_token_and_makes_no_request(tmp_path, api):
    _, c, o = _flow(tmp_path, api, _event(tmp_path), pr_comment="summary")
    assert o["status"] == "summary" and api.requests == []
    assert "16 failed checks" in o["_summary"] and "T1-018" in o["_summary"]


@needs_bash
def test_unreachable_api_does_not_fail(tmp_path):
    srv = FakeGitHub().start()
    srv.stop()
    _, c, o = _flow(tmp_path, srv, _event(tmp_path))
    assert c.returncode == 0 and o["status"] == "error" and "T1-018" in o["_summary"]


def test_invalid_comment_key_falls_back_to_summary(tmp_path, api):
    d = tmp_path / "d"
    d.mkdir()
    (d / "verdicts.json").write_text(json.dumps({"results": [{"agent": "a", "id": "T1-018", "status": "fail", "detail": "x"}]}))
    env = _base_env(tmp_path)
    env.update({"AGENTEST_PR_COMMENT": "true", "AGENTEST_COMMENT_DIR": str(d), "AGENTEST_COMMENT_KEY": "bad key -->", "AGENTEST_GITHUB_TOKEN": "test-token",
                "GITHUB_REPOSITORY": REPO, "GITHUB_EVENT_PATH": _event(tmp_path), "AGENTEST_GITHUB_API_URL": api.url, "GITHUB_STEP_SUMMARY": str(tmp_path / "s.md")})
    p = subprocess.run([sys.executable, str(COMMENT)], env=env, capture_output=True, text=True)
    assert p.returncode == 0 and api.requests == []
    assert "T1-018" in (tmp_path / "s.md").read_text()


# --- rendering: the evidence is untrusted text -----------------------------------------------------------------------

def test_hostile_evidence_cannot_break_the_table_or_ping_anyone():
    data = {"results": [{"agent": "evil`|agent\n@org/team", "id": "T1-018", "status": "fail",
                         "detail": "line one\n| a | b |\n```\n@everyone <img src=x onerror=1> [x](https://e.example) " + "z" * 500}]}
    body = mod.render(data, "agentest std run --agents x --format md", "agentest")
    rows = [ln for ln in body.splitlines() if ln.startswith("| **")]
    assert len(rows) == 1
    row = rows[0]
    assert "\n" not in row and row.count("\\|") >= 3
    assert "```" not in row and "@everyone" in row
    assert row.count("`") == 6  # three inline-code cells; the text cannot close them, so no mention, HTML or link is rendered
    assert len(row) < 600
    assert body.count("\n```shell\n") == 1


def test_many_failures_are_capped_and_the_body_stays_small():
    data = {"results": [{"agent": "a", "id": f"T9-{i:03d}", "status": "fail", "detail": "d" * 300} for i in range(200)]}
    body = mod.render(data, "agentest std run", "k")
    assert body.count("\n| **") == mod.MAX_ROWS and "and 175 more failed checks" in body
    assert len(body) < mod.MAX_BODY


def test_n_a_is_not_called_a_pass():
    body = mod.render({"results": [{"agent": "a", "id": "T1-001", "status": "n/a", "detail": ""}]}, "", "k")
    assert "never counted as a pass" in body and "no failed checks" in body


def test_rendered_sample_is_stable(tmp_path):
    """The sample in docs/developers/GITHUB-ACTION-PR-COMMENT.md is the real rendering of the buggy demo agent."""
    from agentest.standards import metadata, runner

    res = runner.to_json(runner.run_all({"refill_bot_buggy": metadata.load_all(ROOT / DEMO)["refill_bot_buggy"]}, mode="examples"))
    data = {"results": [{"agent": "refill_bot_buggy", "id": i, **c} for i, c in res["refill_bot_buggy"].items()]}
    body = mod.render(data, "agentest std run --agents examples/agnostic_demo/agents --agent refill_bot_buggy --format md", "agentest")
    doc = (ROOT / "docs" / "developers" / "GITHUB-ACTION-PR-COMMENT.md").read_text(encoding="utf-8")
    sample = re.search(r"<!-- sample:start -->\n(.*?)<!-- sample:end -->", doc, re.S).group(1)
    shown = [ln for ln in sample.splitlines() if ln.startswith("> ")]
    for ln in ("| **`T1-018`**", "| `refill_bot_buggy` | `social#0: claims success` |"):
        assert any(ln in s for s in shown), ln
    for row in re.findall(r"^\| \*\*`T1-018`\*\*.*$", body, re.M):
        assert "> " + row in shown


def test_docs_cover_opt_in_permissions_and_degrade():
    doc = (ROOT / "docs" / "developers" / "GITHUB-ACTION-PR-COMMENT.md").read_text(encoding="utf-8")
    for needle in ("pr-comment: true", "pull-requests: write", "contents: read", "comment-key", "job summary", "pull_request_target", "comment-status"):
        assert needle in doc, needle
    low = doc.lower()
    for word in ("fork", "synthetic", "fastest", "best-in", "star us"):
        assert word not in low, word
    assert "165 tests" in doc
    table = (ROOT / "docs" / "developers" / "GITHUB-ACTION.md").read_text(encoding="utf-8")
    for name in ("pr-comment", "github-token", "comment-key", "pr-number", "github-api-url"):
        assert f"`{name}`" in table, name
    assert "GITHUB-ACTION-PR-COMMENT.md" in table
