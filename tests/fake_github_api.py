"""A tiny stand-in for the GitHub issue-comments REST API, for testing the action's PR comment without any network.

Used in-process by tests/test_action_pr_comment.py and as a script by the `action-self-test` CI job:

    python tests/fake_github_api.py --port 8099 --log /tmp/gh-api.jsonl [--read-only] [--token test-token]

It keeps comments in memory, checks the bearer token, answers 403 to writes with --read-only (what a read-only token gets)
and appends one JSON line per request to the log.
"""
from __future__ import annotations

import argparse
import json
import re
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

LIST = re.compile(r"^/repos/([^/]+/[^/]+)/issues/(\d+)/comments$")
ONE = re.compile(r"^/repos/([^/]+/[^/]+)/issues/comments/(\d+)$")


class FakeGitHub(ThreadingHTTPServer):
    def __init__(self, port: int = 0, token: str = "test-token", read_only: bool = False, log: str | None = None):
        super().__init__(("127.0.0.1", port), _Handler)
        self.token, self.read_only, self.log_path = token, read_only, log
        self.comments: dict[tuple[str, int], list[dict]] = {}
        self.requests: list[dict] = []
        self.next_id = 100
        self.thread: threading.Thread | None = None

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.server_address[1]}"

    def start(self) -> FakeGitHub:
        self.thread = threading.Thread(target=self.serve_forever, daemon=True)
        self.thread.start()
        return self

    def stop(self) -> None:
        self.shutdown()
        self.server_close()

    def seed(self, repo: str, number: int, body: str, user_type: str = "User", login: str = "someone") -> dict:
        c = {"id": self.next_id, "body": body, "user": {"type": user_type, "login": login}, "html_url": f"https://example.invalid/{repo}/pull/{number}#issuecomment-{self.next_id}"}
        self.next_id += 1
        self.comments.setdefault((repo, number), []).append(c)
        return c


class _Handler(BaseHTTPRequestHandler):
    server: FakeGitHub

    def log_message(self, *args):  # quiet
        pass

    def _send(self, code: int, payload) -> None:
        raw = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def _handle(self, method: str) -> None:
        srv = self.server
        url = urlparse(self.path)
        length = int(self.headers.get("Content-Length") or 0)
        body = json.loads(self.rfile.read(length) or b"null") if length else None
        entry = {"method": method, "path": url.path, "auth_ok": self.headers.get("Authorization") == f"Bearer {srv.token}"}
        srv.requests.append(entry)
        if srv.log_path:
            with open(srv.log_path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(entry) + "\n")
        if not entry["auth_ok"]:
            return self._send(401, {"message": "Bad credentials"})
        if method != "GET" and srv.read_only:
            return self._send(403, {"message": "Resource not accessible by integration"})
        m = LIST.match(url.path)
        if m:
            key = (m.group(1), int(m.group(2)))
            if method == "GET":
                q = parse_qs(url.query)
                per, page = int(q.get("per_page", ["30"])[0]), int(q.get("page", ["1"])[0])
                return self._send(200, srv.comments.get(key, [])[(page - 1) * per: page * per])
            if method == "POST":
                c = srv.seed(key[0], key[1], body["body"], "Bot", "github-actions[bot]")
                return self._send(201, c)
        m = ONE.match(url.path)
        if m and method == "PATCH":
            for lst in srv.comments.values():
                for c in lst:
                    if c["id"] == int(m.group(2)):
                        if c["user"]["type"] != "Bot":
                            return self._send(403, {"message": "Resource not accessible by integration"})
                        c["body"] = body["body"]
                        return self._send(200, c)
        return self._send(404, {"message": "Not Found"})

    def do_GET(self):
        self._handle("GET")

    def do_POST(self):
        self._handle("POST")

    def do_PATCH(self):
        self._handle("PATCH")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8099)
    ap.add_argument("--log", default=None)
    ap.add_argument("--token", default="test-token")
    ap.add_argument("--read-only", action="store_true")
    a = ap.parse_args()
    srv = FakeGitHub(a.port, a.token, a.read_only, a.log)
    print("ready", srv.url, flush=True)
    srv.serve_forever()


if __name__ == "__main__":
    main()
