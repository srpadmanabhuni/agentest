"""``agentest std serve``: a minimal OTLP/HTTP trace receiver (standard library only).

Point any OpenTelemetry SDK or Collector at it (``OTEL_EXPORTER_OTLP_TRACES_ENDPOINT=http://127.0.0.1:4318/v1/traces``).
It accepts ``POST /v1/traces`` with ``application/json`` (OTLP/JSON) or ``application/x-protobuf`` (OTLP/protobuf,
decoded by :mod:`agentest.standards.otlp_proto`), optionally gzip-compressed, as the OTLP/HTTP specification
(https://opentelemetry.io/docs/specs/otlp/#otlphttp) requires, and appends every trace to
``<out>/<service.name>/traces/<service.name>.otlp.jsonl``: one agent folder per service, ready for
``agentest std run --agents <out>`` (add the agent's ``agent-card.json`` and ``tools.json`` next to ``traces/``) or ``--otlp``.
It is a test-time sink, not a production collector: no auth, no TLS, binds to localhost by default.
"""

from __future__ import annotations

import gzip
import json
import re
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from agentest.standards.otel import split_traces
from agentest.standards.otlp_proto import DecodeError, decode_traces

MAX_BODY = 64 * 1024 * 1024
_SAFE = re.compile(r"[^A-Za-z0-9_.-]+")


def _service(doc: dict) -> str:
    for rs in doc.get("resourceSpans", []):
        for a in rs.get("resource", {}).get("attributes", []):
            if a.get("key") == "service.name":
                return _SAFE.sub("_", str(a.get("value", {}).get("stringValue", "")))[:80] or "unknown_service"
    return "unknown_service"


def make_server(out: Path, host: str = "127.0.0.1", port: int = 4318, max_requests: int = 0) -> ThreadingHTTPServer:
    out.mkdir(parents=True, exist_ok=True)
    lock = threading.Lock()
    state = {"n": 0}

    class Handler(BaseHTTPRequestHandler):
        server_version = "agentest-otlp/1"

        def log_message(self, *a) -> None:  # quiet
            return

        def _reply(self, code: int, body: bytes, ctype: str) -> None:
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self) -> None:  # noqa: N802 - http.server API
            if self.path.split("?")[0] != "/v1/traces":
                self._reply(404, b"", "text/plain")
                return
            n = int(self.headers.get("Content-Length") or 0)
            if n > MAX_BODY:
                self._reply(413, b"", "text/plain")
                return
            body = self.rfile.read(n)
            if (self.headers.get("Content-Encoding") or "").lower() == "gzip":
                body = gzip.decompress(body)
            ctype = (self.headers.get("Content-Type") or "").split(";")[0].strip().lower()
            try:
                doc = decode_traces(body) if ctype == "application/x-protobuf" else json.loads(body or b"{}")
            except (DecodeError, ValueError) as ex:
                self._reply(400, json.dumps({"message": str(ex)[:200]}).encode(), "application/json")
                return
            with lock:
                for t in split_traces(doc):
                    svc = _service(t)
                    (out / svc / "traces").mkdir(parents=True, exist_ok=True)
                    with (out / svc / "traces" / f"{svc}.otlp.jsonl").open("a") as f:
                        f.write(json.dumps(t, separators=(",", ":")) + "\n")
                state["n"] += 1
                done = max_requests and state["n"] >= max_requests
            # ExportTraceServiceResponse with no partial_success: an empty message
            if ctype == "application/x-protobuf":
                self._reply(200, b"", "application/x-protobuf")
            else:
                self._reply(200, b"{}", "application/json")
            if done:
                threading.Thread(target=self.server.shutdown, daemon=True).start()

    return ThreadingHTTPServer((host, port), Handler)


def serve(out: Path, host: str = "127.0.0.1", port: int = 4318, max_requests: int = 0) -> int:
    srv = make_server(out, host, port, max_requests)
    print(f"agentest OTLP/HTTP receiver on http://{host}:{srv.server_address[1]}/v1/traces -> {out}/", flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        srv.server_close()
    return 0
