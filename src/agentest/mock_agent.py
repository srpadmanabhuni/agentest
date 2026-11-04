"""A tiny mock agent endpoint so you can try ``agentest run`` without your own agent.

It replays the recorded OpenTelemetry GenAI traces of a bundled demo agent. Two modes:

* in-process: ``agentest run --agent mock`` (no sockets, no network);
* HTTP (stdlib only, binds 127.0.0.1): ``python -m agentest.mock_agent --port 8765`` then
  ``agentest run --agent http://127.0.0.1:8765``.

Endpoint contract (what any agent endpoint needs to expose to ``agentest run``):

* ``GET  /probes``           -> ``[{"id": "...", "input": "..."}]`` (optional; a default probe set is used otherwise)
* ``GET  /agent-card.json``  -> A2A AgentCard (optional)
* ``GET  /tools.json``       -> MCP ``tools/list`` result (optional)
* ``POST /invoke`` ``{"probe": id, "input": text}`` -> ``{"otlp": <OTLP/JSON traces document or list of them>}``
"""

from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from agentest.paths import root


def _agent_dir() -> Path:
    for d in (root() / "examples" / "agnostic_demo" / "agents" / "refill_bot", root() / "agents" / "a01"):
        if (d / "traces").is_dir():
            return d
    raise FileNotFoundError("no bundled demo agent traces found (set AGENTEST_ROOT to a git clone)")


class MockAgent:
    """In-process mock: one probe per recorded trace."""

    def __init__(self, agent_dir: Path | None = None):
        d = agent_dir or _agent_dir()
        self.name = d.name
        self.card = json.loads((d / "agent-card.json").read_text()) if (d / "agent-card.json").exists() else None
        self.tools = json.loads((d / "tools.json").read_text()) if (d / "tools.json").exists() else None
        docs = [json.loads(x) for f in sorted((d / "traces").glob("*.jsonl")) for x in f.read_text().splitlines() if x.strip()]
        self._docs = {f"p{i:02d}": doc for i, doc in enumerate(docs)}

    def probes(self) -> list[dict]:
        return [{"id": k, "input": f"recorded probe {k}"} for k in self._docs]

    def invoke(self, probe: str, text: str = "") -> dict:
        return {"otlp": self._docs[probe]} if probe in self._docs else {"otlp": [], "error": f"unknown probe {probe!r}"}


def make_handler(agent: MockAgent):
    class H(BaseHTTPRequestHandler):
        def _send(self, code: int, obj) -> None:
            body = json.dumps(obj).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):  # noqa: N802
            route = {"/probes": agent.probes(), "/agent-card.json": agent.card, "/tools.json": agent.tools}
            if self.path in route and route[self.path] is not None:
                self._send(200, route[self.path])
            else:
                self._send(404, {"error": "not found"})

        def do_POST(self):  # noqa: N802
            if self.path != "/invoke":
                return self._send(404, {"error": "not found"})
            req = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)) or b"{}")
            self._send(200, agent.invoke(req.get("probe", ""), req.get("input", "")))

        def log_message(self, *a):  # quiet
            pass

    return H


def make_server(host: str = "127.0.0.1", port: int = 8765) -> ThreadingHTTPServer:
    return ThreadingHTTPServer((host, port), make_handler(MockAgent()))


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="python -m agentest.mock_agent", description="Serve a mock agent endpoint on localhost (stdlib only).")
    p.add_argument("--host", default="127.0.0.1", help="bind address (default 127.0.0.1)")
    p.add_argument("--port", type=int, default=8765, help="port (default 8765)")
    a = p.parse_args(argv)
    srv = make_server(a.host, a.port)
    print(f"mock agent listening on http://{a.host}:{srv.server_address[1]}  (Ctrl+C to stop)", flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
