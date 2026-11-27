"""The welcome comment on a first-time contributor's pull request works without a write token on the PR event.

first-interaction.yml runs on ``pull_request`` with a read-only token and only uploads a tiny artifact.
welcome-comment.yml runs on ``workflow_run`` with a write token, never checks out pull-request code, validates the
artifact and posts one comment, only for a first-time contributor. The script is exercised with a mocked GitHub client
(needs node), the same way as the verdict-diff comment.
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
MARK = "<!-- agentest-welcome -->"


def _load(name: str) -> dict:
    return yaml.safe_load((WF / name).read_text(encoding="utf-8"))


def _on(doc: dict) -> dict:
    return doc.get("on") or doc.get(True)  # PyYAML reads the key `on` as True


def test_recording_workflow_is_unprivileged_and_runs_no_pull_request_code():
    doc = _load("first-interaction.yml")
    assert set(_on(doc)) == {"issues", "pull_request"}
    assert doc["permissions"] == {}
    job = doc["jobs"]["record-pull-request"]
    assert job["permissions"] == {"contents": "read"}
    text = (WF / "first-interaction.yml").read_text(encoding="utf-8")
    assert "actions/checkout" not in text and "pull_request_target" not in text and "secrets." not in text.split("welcome-issue:")[1].split("record-pull-request:")[1]
    for s in job["steps"]:
        assert "${{" not in s.get("run", ""), "no pull-request text is interpolated into a shell command"
    assert doc["jobs"]["welcome-issue"]["permissions"] == {"issues": "write"}
    assert str(doc["jobs"]["welcome-issue"]["steps"][0]["uses"]).startswith("actions/first-interaction@")
    assert len(doc["jobs"]["welcome-issue"]["steps"][0]["uses"].split("@")[1]) == 40, "the action stays pinned to a commit"


def test_comment_workflow_never_checks_out_code_and_scopes_its_token():
    doc = _load("welcome-comment.yml")
    assert _on(doc)["workflow_run"]["workflows"] == ["Welcome first-time contributors"]
    assert doc["permissions"] == {"actions": "read", "contents": "read", "pull-requests": "write"}
    text = (WF / "welcome-comment.yml").read_text(encoding="utf-8")
    assert "actions/checkout" not in text and "pull_request_target" not in text
    job = doc["jobs"]["comment"]
    assert "workflow_run.conclusion == 'success'" in job["if"] and "workflow_run.event == 'pull_request'" in job["if"]
    for s in job["steps"]:
        assert "run" not in s, "the comment job runs no shell: the artifact is untrusted data"


HARNESS = r"""
const fs = require('fs');
const [,, scriptFile, artifactDir, scenarioFile] = process.argv;
const scenario = JSON.parse(fs.readFileSync(scenarioFile, 'utf8'));
process.chdir(artifactDir);
const calls = { create: [], failed: [], info: [] };
const github = {
  paginate: async (fn) => (fn === 'listComments' ? scenario.comments : scenario.assoc),
  rest: {
    repos: { listPullRequestsAssociatedWithCommit: 'assoc' },
    pulls: { get: async () => ({ data: { author_association: scenario.live } }) },
    issues: { listComments: 'listComments', createComment: async (a) => calls.create.push(a) },
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
    doc = _load("welcome-comment.yml")
    return next(s["with"]["script"] for s in doc["jobs"]["comment"]["steps"] if "github-script" in str(s.get("uses", "")))


def _run_script(tmp_path: Path, art, *, live="FIRST_TIME_CONTRIBUTOR", comments=(), assoc=None, prs=(), raw: str | None = None) -> dict:
    d = tmp_path / "w" / "artifact"
    d.mkdir(parents=True)
    (d / "pr.json").write_text(raw if raw is not None else json.dumps(art), encoding="utf-8")
    head = "abcdef1234567"
    if assoc is None:  # a pull request from outside the repository: the run lists none, the API finds it
        assoc = [{"number": 42, "state": "open", "head": {"sha": head}, "base": {"repo": {"full_name": "o/r"}}}]
    sc = {"comments": list(comments), "assoc": assoc, "live": live,
          "run": {"head_sha": head, "repository": {"id": 7}, "pull_requests": list(prs)}}
    (tmp_path / "sc.json").write_text(json.dumps(sc), encoding="utf-8")
    (tmp_path / "script.js").write_text(_script(), encoding="utf-8")
    (tmp_path / "h.js").write_text(HARNESS, encoding="utf-8")
    p = subprocess.run(["node", str(tmp_path / "h.js"), str(tmp_path / "script.js"), str(tmp_path / "w"), str(tmp_path / "sc.json")],
                       capture_output=True, text=True, timeout=60)
    assert p.returncode == 0, p.stderr
    return json.loads(p.stdout.strip().splitlines()[-1])


needs_node = pytest.mark.skipif(not shutil.which("node"), reason="needs node")
GOOD = {"number": "42", "author_association": "FIRST_TIME_CONTRIBUTOR"}


@needs_node
def test_first_time_contributor_gets_one_welcome(tmp_path):
    out = _run_script(tmp_path, GOOD)
    assert out["failed"] == [] and len(out["create"]) == 1
    body = out["create"][0]["body"]
    assert out["create"][0]["issue_number"] == 42 and body.startswith(MARK)
    assert "welcome to agentest" in body and "git commit -s" in body
    low = body.lower()
    assert "precision" not in low and "recall" not in low


@needs_node
def test_pull_request_listed_on_the_run_is_used(tmp_path):
    out = _run_script(tmp_path, GOOD, assoc=[], prs=[{"number": 42, "base": {"repo": {"id": 7}}}])
    assert out["failed"] == [] and len(out["create"]) == 1


@needs_node
@pytest.mark.parametrize("live", ["CONTRIBUTOR", "MEMBER", "OWNER", "NONE"])
def test_nobody_else_is_welcomed(tmp_path, live):
    out = _run_script(tmp_path, {"number": "42", "author_association": live}, live=live)
    assert out["create"] == [] and out["failed"] == []


@needs_node
def test_a_forged_association_in_the_artifact_is_not_enough(tmp_path):
    out = _run_script(tmp_path, GOOD, live="CONTRIBUTOR")
    assert out["create"] == []


@needs_node
def test_artifact_number_must_match_the_tested_commit(tmp_path):
    out = _run_script(tmp_path, {"number": "7", "author_association": "FIRST_TIME_CONTRIBUTOR"})
    assert out["create"] == [] and out["failed"] == ["artifact pull request number does not match the tested commit"]


@needs_node
@pytest.mark.parametrize("number", ["abc", "4.2", "0", "-1", "42; rm -rf /", "", "1234567890123", 42])
def test_artifact_number_must_be_an_integer(tmp_path, number):
    out = _run_script(tmp_path, {"number": number, "author_association": "FIRST_TIME_CONTRIBUTOR"})
    assert out["create"] == [] and out["failed"] == ["unexpected artifact shape"]


@needs_node
def test_bad_artifacts_are_refused(tmp_path):
    assert _run_script(tmp_path, None, raw="not json")["failed"] == ["artifact is not JSON"]
    assert _run_script(tmp_path / "big", None, raw=json.dumps({"number": "42", "author_association": "x" * 2000}))["failed"] == ["missing or oversized artifact"]


@needs_node
def test_welcome_is_not_posted_twice(tmp_path):
    bot = {"id": 9, "user": {"login": "github-actions[bot]"}, "body": MARK + "\nold"}
    out = _run_script(tmp_path, GOOD, comments=[bot])
    assert out["create"] == []


@needs_node
def test_a_marker_comment_by_someone_else_does_not_block_the_welcome(tmp_path):
    spoof = {"id": 5, "user": {"login": "someone"}, "body": MARK + "\nspoof"}
    out = _run_script(tmp_path, GOOD, comments=[spoof])
    assert len(out["create"]) == 1


@needs_node
def test_no_open_pull_request_for_the_commit_posts_nothing(tmp_path):
    out = _run_script(tmp_path, GOOD, assoc=[])
    assert out["create"] == [] and out["failed"] == []
