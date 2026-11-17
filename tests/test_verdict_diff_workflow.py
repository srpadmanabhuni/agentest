"""The verdict-diff pull-request comment is safe for pull requests from first-time contributors.

verdict-diff.yml runs on ``pull_request`` with a read-only token and no secrets and only uploads a JSON artifact.
verdict-diff-comment.yml runs on ``workflow_run`` with a write token, never checks out pull-request code, and renders
only validated artifact fields. The comment script is exercised here with a mocked GitHub client (needs node).
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
WF = ROOT / ".github" / "workflows"


def _load(name: str) -> dict:
    return yaml.safe_load((WF / name).read_text(encoding="utf-8"))


def _on(doc: dict) -> dict:
    return doc.get("on") or doc.get(True)  # PyYAML reads the key `on` as True


def test_diff_workflow_is_read_only_and_runs_on_pull_request():
    doc = _load("verdict-diff.yml")
    assert set(_on(doc)) == {"pull_request"}
    assert doc["permissions"] == {"contents": "read"}
    text = (WF / "verdict-diff.yml").read_text(encoding="utf-8")
    assert "pull_request_target" not in text and "secrets." not in text
    steps = doc["jobs"]["diff"]["steps"]
    assert all(s.get("with", {}).get("persist-credentials") is False for s in steps if str(s.get("uses", "")).startswith("actions/checkout"))
    for s in steps:  # no pull-request text is interpolated into a shell command
        assert "github.event.pull_request.title" not in s.get("run", "") and "head_ref" not in s.get("run", "")
        assert "${{" not in s.get("run", ""), s


def test_comment_workflow_never_checks_out_code_and_scopes_its_token():
    doc = _load("verdict-diff-comment.yml")
    assert _on(doc)["workflow_run"]["workflows"] == ["verdict-diff"]
    assert doc["permissions"] == {"actions": "read", "contents": "read", "pull-requests": "write"}
    text = (WF / "verdict-diff-comment.yml").read_text(encoding="utf-8")
    assert "actions/checkout" not in text and "pull_request_target" not in text
    job = doc["jobs"]["comment"]
    assert "workflow_run.conclusion == 'success'" in job["if"]
    for s in job["steps"]:
        assert "run" not in s, "the comment job runs no shell: the artifact is untrusted data"


def test_no_workflow_uses_pull_request_target():
    for p in WF.glob("*.yml"):
        assert "pull_request_target" not in p.read_text(encoding="utf-8"), p.name


HARNESS = r"""
const fs = require('fs');
const [,, scriptFile, artifactDir, scenarioFile] = process.argv;
const scenario = JSON.parse(fs.readFileSync(scenarioFile, 'utf8'));
process.chdir(artifactDir);
const calls = { create: [], update: [], failed: [], info: [] };
const github = {
  paginate: async (fn, args) => (fn === 'listComments' ? scenario.comments : scenario.assoc),
  rest: {
    repos: { listPullRequestsAssociatedWithCommit: 'assoc' },
    issues: {
      listComments: 'listComments',
      createComment: async (a) => calls.create.push(a),
      updateComment: async (a) => calls.update.push(a),
    },
  },
};
const context = { repo: { owner: 'o', repo: 'r' }, payload: { workflow_run: scenario.run } };
const core = { setFailed: (m) => calls.failed.push(m), info: (m) => calls.info.push(m) };
const src = fs.readFileSync(scriptFile, 'utf8');
const AsyncFunction = Object.getPrototypeOf(async function () {}).constructor;
new AsyncFunction('github', 'context', 'core', 'require', src)(github, context, core, require).then(() => {
  console.log(JSON.stringify(calls));
});
"""


def _script() -> str:
    doc = _load("verdict-diff-comment.yml")
    return next(s["with"]["script"] for s in doc["jobs"]["comment"]["steps"] if "github-script" in str(s.get("uses", "")))


def _run_script(tmp_path: Path, diff, *, comments=(), assoc=(), prs=None, raw: str | None = None) -> dict:
    art = tmp_path / "w" / "artifact"
    art.mkdir(parents=True)
    (art / "diff.json").write_text(raw if raw is not None else json.dumps(diff), encoding="utf-8")
    sc = {"comments": list(comments), "assoc": list(assoc),
          "run": {"head_sha": "abcdef1234567", "repository": {"id": 7}, "pull_requests": prs if prs is not None else [{"number": 42, "base": {"repo": {"id": 7}}}]}}
    (tmp_path / "sc.json").write_text(json.dumps(sc), encoding="utf-8")
    (tmp_path / "script.js").write_text(_script(), encoding="utf-8")
    (tmp_path / "h.js").write_text(HARNESS, encoding="utf-8")
    p = subprocess.run(["node", str(tmp_path / "h.js"), str(tmp_path / "script.js"), str(tmp_path / "w"), str(tmp_path / "sc.json")],
                       capture_output=True, text=True, timeout=60)
    assert p.returncode == 0, p.stderr
    return json.loads(p.stdout.strip().splitlines()[-1])


needs_node = pytest.mark.skipif(not shutil.which("node"), reason="needs node")
ROW = {"mode": "strict", "agent": "a01", "check": "T5-006", "before": "pass", "after": "fail"}
MARK = "<!-- agentest-verdict-diff -->"


@needs_node
def test_changed_verdicts_are_posted_once(tmp_path):
    out = _run_script(tmp_path, {"changed": [ROW], "agents_added": ["new_agent"], "agents_removed": []})
    assert out["failed"] == [] and len(out["create"]) == 1 and out["update"] == []
    body = out["create"][0]["body"]
    assert body.startswith(MARK) and "`T5-006`" in body and "pass | fail" in body and "`new_agent`" in body
    assert out["create"][0]["issue_number"] == 42
    low = body.lower()
    assert "precision" not in low and "recall" not in low


@needs_node
def test_existing_bot_comment_is_updated_not_duplicated(tmp_path):
    bot = {"id": 9, "user": {"login": "github-actions[bot]"}, "body": MARK + "\nold"}
    out = _run_script(tmp_path, {"changed": [ROW], "agents_added": [], "agents_removed": []}, comments=[bot])
    assert out["create"] == [] and len(out["update"]) == 1 and out["update"][0]["comment_id"] == 9


@needs_node
def test_a_comment_by_someone_else_with_the_marker_is_ignored(tmp_path):
    spoof = {"id": 5, "user": {"login": "someone"}, "body": MARK + "\nspoof"}
    out = _run_script(tmp_path, {"changed": [ROW], "agents_added": [], "agents_removed": []}, comments=[spoof])
    assert len(out["create"]) == 1 and out["update"] == []


@needs_node
def test_no_change_and_no_earlier_comment_posts_nothing(tmp_path):
    out = _run_script(tmp_path, {"changed": [], "agents_added": [], "agents_removed": []})
    assert out["create"] == [] and out["update"] == [] and out["failed"] == []


@needs_node
def test_no_change_updates_an_earlier_comment(tmp_path):
    bot = {"id": 9, "user": {"login": "github-actions[bot]"}, "body": MARK + "\nold"}
    out = _run_script(tmp_path, {"changed": [], "agents_added": [], "agents_removed": []}, comments=[bot])
    assert len(out["update"]) == 1 and "No verdict differs" in out["update"][0]["body"]


@needs_node
@pytest.mark.parametrize("bad", [
    {"changed": [{**ROW, "agent": "x`\n<script>alert(1)</script>"}], "agents_added": [], "agents_removed": []},
    {"changed": [{**ROW, "check": "T5-006; rm -rf"}], "agents_added": [], "agents_removed": []},
    {"changed": [{**ROW, "after": "<b>fail</b>"}], "agents_added": [], "agents_removed": []},
    {"changed": [{**ROW, "mode": 7}], "agents_added": [], "agents_removed": []},
    {"changed": "nope", "agents_added": [], "agents_removed": []},
    {"agents_added": []},
])
def test_untrusted_artifact_is_rejected_and_nothing_is_posted(tmp_path, bad):
    out = _run_script(tmp_path, bad)
    assert out["failed"] and out["create"] == [] and out["update"] == []


@needs_node
def test_not_json_and_oversized_artifacts_are_rejected(tmp_path):
    assert _run_script(tmp_path, None, raw="not json")["failed"]
    big = json.dumps({"changed": [], "agents_added": ["a" * 10] * 30000, "agents_removed": []})
    out = _run_script(tmp_path / "big", None, raw=big) if (tmp_path / "big").mkdir() is None else None
    assert out["failed"] and out["create"] == []


@needs_node
def test_a_pull_request_number_in_the_artifact_is_never_used(tmp_path):
    data = {"changed": [ROW], "agents_added": [], "agents_removed": [], "pull_request": 1, "number": 1, "issue_number": 1}
    out = _run_script(tmp_path, data)
    assert out["create"][0]["issue_number"] == 42


@needs_node
def test_pull_request_is_found_through_the_api_when_the_run_lists_none(tmp_path):
    assoc = [{"number": 77, "state": "open", "base": {"repo": {"full_name": "o/r"}}, "head": {"sha": "abcdef1234567"}},
             {"number": 78, "state": "open", "base": {"repo": {"full_name": "o/other"}}, "head": {"sha": "abcdef1234567"}}]
    out = _run_script(tmp_path, {"changed": [ROW], "agents_added": [], "agents_removed": []}, assoc=assoc, prs=[])
    assert out["create"][0]["issue_number"] == 77


@needs_node
def test_long_diffs_are_truncated(tmp_path):
    rows = [{**ROW, "check": f"T1-{i:03d}"} for i in range(150)]
    out = _run_script(tmp_path, {"changed": rows, "agents_added": [], "agents_removed": []})
    body = out["create"][0]["body"]
    assert "and 50 more" in body and body.count("| strict |") == 100
