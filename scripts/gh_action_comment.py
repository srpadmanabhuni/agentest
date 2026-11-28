#!/usr/bin/env python3
"""Optional PR comment (or job summary) for the agentest GitHub Action: the failed check IDs and the one-line evidence.

Local only: it reads the verdicts JSON that `scripts/gh_action_run.sh` saved, renders Markdown, and, when asked, calls
the GitHub REST API of the repository the workflow runs in. No other service is contacted. Standard library only.

Modes (AGENTEST_PR_COMMENT): `true` posts or updates ONE comment per pull request and key; `summary` only writes the
job summary. Anything that stops a comment (a read-only token, no pull request, an API error) degrades to the job
summary and never fails the job. The token is read from AGENTEST_GITHUB_TOKEN, only sent to the API host and never printed.
The evidence text comes from recorded traces, so it is treated as untrusted: one line, no control characters, shown
inside inline code, length-limited.
"""
from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

MAX_ROWS = 25
MAX_EVIDENCE = 160
MAX_TITLE = 90
MAX_BODY = 60000  # the API limit is 65536 characters
KEY = re.compile(r"[A-Za-z0-9_.-]{1,40}")
ID = re.compile(r"[A-Za-z0-9._-]{1,24}")
CONTROL = re.compile(r"[\x00-\x1f\x7f\u2028\u2029]+")


def marker(key: str) -> str:
    return f"<!-- agentest-action:{key} -->"


def inline(text: object, limit: int) -> str:
    """One line of untrusted text as inline code: no control characters, no backticks, pipes escaped, length-limited."""
    s = CONTROL.sub(" ", str(text)).strip()
    s = re.sub(r"\s{2,}", " ", s).replace("`", "'").replace("|", "\\|")
    if len(s) > limit:
        s = s[: limit - 1].rstrip() + "\u2026"
    return f"`{s}`" if s else "`(no detail)`"


def load(path: Path) -> dict | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) and isinstance(data.get("results"), list) else None


def titles() -> dict[str, str]:
    try:
        from agentest.standards.catalog import catalogue

        return {k: str(v.get("title") or "") for k, v in catalogue().items()}
    except Exception:  # the comment still works without the catalogue titles
        return {}


def summarise(data: dict) -> tuple[dict, list[dict]]:
    totals = {"pass": 0, "fail": 0, "n/a": 0}
    fails = []
    for r in data["results"]:
        if not isinstance(r, dict):
            continue
        st = r.get("status")
        if st in totals:
            totals[st] += 1
        if st == "fail":
            fails.append(r)
    return totals, fails


def render(data: dict, command: str, key: str) -> str:
    totals, fails = summarise(data)
    names = titles()
    out = [marker(key)]
    if fails:
        word = "check" if len(fails) == 1 else "checks"
        out.append(f"### agentest: {len(fails)} failed {word} in the recorded run")
    else:
        out.append("### agentest: no failed checks in the recorded run")
    out += ["", f"agentest (165 tests, offline, no model calls) judged the recorded traces: {totals['pass']} pass, {totals['fail']} fail, {totals['n/a']} n/a. `n/a` means the trace carries no evidence for that check; it is never counted as a pass.", ""]
    if fails:
        out += ["| Check | Agent | Evidence |", "|---|---|---|"]
        for r in sorted(fails, key=lambda r: (str(r.get("agent")), str(r.get("id"))))[:MAX_ROWS]:
            cid = str(r.get("id", ""))
            cid = cid if ID.fullmatch(cid) else "?"
            title = names.get(cid, "")
            what = f" {inline(title, MAX_TITLE)[1:-1]}" if title else ""
            out.append(f"| **`{cid}`**{what} | {inline(r.get('agent', ''), 60)} | {inline(r.get('detail', ''), MAX_EVIDENCE)} |")
        if len(fails) > MAX_ROWS:
            out += ["", f"...and {len(fails) - MAX_ROWS} more failed checks. The full report is in the workflow run."]
        out += ["", "A fail is evidence on this recorded run, not a claim about how often an agent fails.", ""]
    if command:
        out += ["Reproduce locally:", "", "```shell", "pip install agentest-ai", command.strip(), "```", ""]
    out.append("<sub>AiEnsured agentest. Updated in place on each run; there is one comment per key.</sub>")
    body = "\n".join(out) + "\n"
    return body if len(body) <= MAX_BODY else body[: MAX_BODY - 40].rsplit("\n", 1)[0] + "\n\n(truncated)\n"


class ApiError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(f"HTTP {status}: {message}")
        self.status = status


def api(method: str, url: str, token: str, payload: dict | None = None):
    req = urllib.request.Request(
        url,
        data=None if payload is None else json.dumps(payload).encode(),
        method=method,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "agentest-action",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:  # noqa: S310 - the API host the workflow already trusts
            return json.loads(resp.read().decode() or "null")
    except urllib.error.HTTPError as e:
        try:
            msg = str(json.loads(e.read().decode()).get("message", ""))[:200]
        except Exception:
            msg = e.reason if isinstance(e.reason, str) else ""
        raise ApiError(e.code, msg) from None
    except (urllib.error.URLError, OSError, ValueError) as e:
        raise ApiError(0, type(e).__name__) from None


def find_existing(base: str, repo: str, number: int, token: str, mark: str):
    for page in range(1, 11):
        url = f"{base}/repos/{repo}/issues/{number}/comments?per_page=100&page={page}"
        batch = api("GET", url, token)
        if not isinstance(batch, list):
            return None
        hits = [c for c in batch if isinstance(c, dict) and str(c.get("body", "")).startswith(mark)]
        hits.sort(key=lambda c: (c.get("user") or {}).get("type") != "Bot")
        if hits:
            return hits[0]
        if len(batch) < 100:
            return None
    return None


def pr_context(event_path: str, number_input: str) -> tuple[int | None, bool]:
    """The pull request number and whether the head lives in another repository (so the token is read-only)."""
    number, other_repo = None, False
    try:
        event = json.loads(Path(event_path).read_text(encoding="utf-8")) if event_path else {}
    except (OSError, ValueError):
        event = {}
    pr = event.get("pull_request") if isinstance(event, dict) else None
    if isinstance(pr, dict):
        number = pr.get("number")
        head = ((pr.get("head") or {}).get("repo") or {}).get("full_name")
        base = ((pr.get("base") or {}).get("repo") or {}).get("full_name")
        other_repo = head != base
    if number_input.strip():
        try:
            number = int(number_input)
        except ValueError:
            number = None
    return (number if isinstance(number, int) and number > 0 else None), other_repo


def notice(level: str, text: str) -> None:
    print(f"::{level}::agentest action: {text}")


def write_summary(text: str) -> None:
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if path:
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(text + ("" if text.endswith("\n") else "\n") + "\n")


def write_outputs(status: str, url: str = "") -> None:
    path = os.environ.get("GITHUB_OUTPUT")
    print(f"agentest action: PR comment status: {status}" + (f" ({url})" if url else ""))
    if path:
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(f"status={status}\nurl={url}\n")


def main() -> int:
    env = os.environ.get
    mode = env("AGENTEST_PR_COMMENT", "false")
    if mode not in ("true", "summary"):
        write_outputs("off")
        return 0
    key = env("AGENTEST_COMMENT_KEY", "") or "agentest"
    if not KEY.fullmatch(key):
        notice("warning", "comment-key must be 1 to 40 letters, digits, '.', '_' or '-'; using the job summary instead")
        key, mode = "agentest", "summary"
    workdir = Path(env("AGENTEST_COMMENT_DIR", ""))
    data = load(workdir / "verdicts.json") if env("AGENTEST_COMMENT_DIR") else None
    if data is None:
        notice("warning", "no verdicts to show; no comment or summary written")
        write_outputs("none")
        return 0
    cmd_file = workdir / "command.txt"
    command = cmd_file.read_text(encoding="utf-8") if cmd_file.exists() else ""
    body = render(data, command, key)
    _, fails = summarise(data)

    def degrade(status: str, why: str) -> int:
        notice("notice", why + "; the result is in the job summary instead")
        write_summary(body.replace(marker(key) + "\n", "", 1))
        write_outputs(status)
        return 0

    if mode == "summary":
        write_summary(body.replace(marker(key) + "\n", "", 1))
        write_outputs("summary")
        return 0

    token = env("AGENTEST_GITHUB_TOKEN", "")
    repo = env("GITHUB_REPOSITORY", "")
    base = (env("AGENTEST_GITHUB_API_URL") or env("GITHUB_API_URL") or "https://api.github.com").rstrip("/")
    number, other_repo = pr_context(env("GITHUB_EVENT_PATH", ""), env("AGENTEST_PR_NUMBER", ""))
    if number is None:
        return degrade("no-pr", "this run is not for a pull request")
    if other_repo:
        return degrade("read-only", "this pull request comes from another repository, so the workflow token cannot write comments")
    if not token or not re.fullmatch(r"[\w.\-]+/[\w.\-]+", repo):
        return degrade("no-token", "no GitHub token or repository was available")
    if urllib.parse.urlparse(base).scheme not in ("http", "https"):
        return degrade("error", "the GitHub API URL is not http(s)")
    try:
        existing = find_existing(base, repo, number, token, marker(key))
        if existing is None and not fails:
            write_outputs("none")
            print("agentest action: no failed checks and no earlier comment; nothing to post")
            return 0
        if existing is not None:
            if existing.get("body") == body:
                write_outputs("unchanged", str(existing.get("html_url", "")))
                return 0
            res = api("PATCH", f"{base}/repos/{repo}/issues/comments/{existing['id']}", token, {"body": body})
            status = "updated"
        else:
            res = api("POST", f"{base}/repos/{repo}/issues/{number}/comments", token, {"body": body})
            status = "created"
    except ApiError as e:
        hint = " Grant the job `pull-requests: write`." if e.status in (401, 403) else ""
        return degrade("error", f"could not post the comment ({e}).{hint}")
    url = str((res or {}).get("html_url", "")) if isinstance(res, dict) else ""
    write_summary(f"agentest: {status} the pull request comment" + (f": {url}" if url else "."))
    write_outputs(status, url)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # never fail the job because of the comment
        notice("warning", f"PR comment step stopped ({type(exc).__name__}); see the job summary and the report")
        sys.exit(0)
