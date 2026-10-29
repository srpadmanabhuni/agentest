"""OTLP transport: OTLP/protobuf ingest (standard-library codec, checked against fixtures written by the official
opentelemetry-proto package), the ``agentest std serve`` OTLP/HTTP receiver, verdicts emitted as OTLP/JSON, and
``agentest std import`` for native logs. No new runtime dependency: pyyaml stays the only one."""

from __future__ import annotations

import gzip
import json
import json as _json
import pathlib as _pl
import threading
import tomllib
import urllib.request
from pathlib import Path

import pytest

from agentest.cli import main
from agentest.standards import metadata, otel, otlp_proto, rules, runner

INPUTS = _json.loads((_pl.Path(__file__).parent / "fixtures" / "agent_inputs.json").read_text())  # agent inputs are data
SVC = INPUTS["import_service"]

ROOT = Path(__file__).resolve().parents[1]
FIX = ROOT / "tests" / "fixtures" / "otlp"
PAIRS = ["ticket_current", "ticket_events_1_28"]  # .pb written by opentelemetry-proto 1.45.1 / protobuf 7.36.2


def _run_view(r):
    return (r.input, r.answer, [(t.name, t.args, t.result, t.error, t.call_id) for t in r.tools], r.chats, r.duration_s)


@pytest.mark.parametrize("name", PAIRS)
def test_official_protobuf_fixture_decodes_like_its_json(name):
    pb = otel.read_otlp_file(FIX / f"{name}.pb")
    js = otel.read_otlp_file(FIX / f"{name}.otlp.json")
    assert [_run_view(otel.from_otlp(d)) for d in pb] == [_run_view(otel.from_otlp(d)) for d in js]


@pytest.mark.parametrize("name", PAIRS)
def test_protobuf_encoder_is_byte_identical_to_official(name):
    doc = json.loads((FIX / f"{name}.otlp.json").read_text())
    assert otlp_proto.encode_traces(doc) == (FIX / f"{name}.pb").read_bytes()


def test_protobuf_rejects_garbage():
    with pytest.raises(otlp_proto.DecodeError):
        otlp_proto.decode_traces(b"\x0a\xff\xff\xff\xff\xff\xff")


def test_reference_agent_traces_roundtrip_through_protobuf():
    a = metadata.load_all()[INPUTS["registry_first"]]
    for d in runner.otlp_docs(a)[:5]:
        back = otlp_proto.decode_traces(otlp_proto.encode_traces(d))
        assert _run_view(otel.from_otlp(back)) == _run_view(otel.from_otlp(d))


def test_cli_runs_protobuf_files(tmp_path, capsys):
    out = tmp_path / "v.json"
    assert main(["std", "run", "--otlp", str(FIX / "ticket_current.pb"), "--json", str(out)]) == 0
    assert json.loads(out.read_text())


def _post(url, body, ctype, gz=False):
    data = gzip.compress(body) if gz else body
    req = urllib.request.Request(url, data=data, method="POST", headers={"Content-Type": ctype, **({"Content-Encoding": "gzip"} if gz else {})})
    with urllib.request.urlopen(req, timeout=10) as r:
        return r.status


def test_serve_receives_json_protobuf_and_gzip(tmp_path):
    from agentest.standards.serve import make_server

    srv = make_server(tmp_path / "recv", "127.0.0.1", 0)
    th = threading.Thread(target=srv.serve_forever, daemon=True)
    th.start()
    try:
        url = f"http://127.0.0.1:{srv.server_address[1]}/v1/traces"
        assert _post(url, (FIX / "ticket_current.otlp.json").read_bytes(), "application/json") == 200
        assert _post(url, (FIX / "ticket_events_1_28.pb").read_bytes(), "application/x-protobuf") == 200
        assert _post(url, (FIX / "ticket_current.pb").read_bytes(), "application/x-protobuf", gz=True) == 200
        with pytest.raises(urllib.error.HTTPError) as e:
            _post(url, b"\x0a\xff\xff\xff\xff", "application/x-protobuf")
        assert e.value.code == 400
    finally:
        srv.shutdown()
        srv.server_close()
    got = tmp_path / "recv" / "ticket-desk" / "traces" / "ticket-desk.otlp.jsonl"
    assert len(got.read_text().splitlines()) == 3  # one line per request
    docs = otel.read_otlp_file(got)
    assert len(docs) == 1  # the same trace (same traceId and spanIds) sent three times is read once: retries are idempotent
    assert {r.answer for r in map(otel.from_otlp, docs)} == {"Filed the billing ticket for T-1."}
    # the receiver's output directory is a ready-made agent folder set (traces only)
    (tmp_path / "recv" / "ticket-desk" / "tools.json").write_text((FIX / "ticket_tools.json").read_text())  # MCP tools/list
    a = metadata.load_all(tmp_path / "recv")
    assert list(a) == ["ticket-desk"] and all(rules.evaluate(x, runner.runs(x))["T1-006"].status == "fail" for x in a.values())


def test_emit_otlp_verdicts(tmp_path):
    out = tmp_path / "verdicts.otlp.json"
    rc = main(["std", "run", "--agents", str(ROOT / "examples" / "agnostic_demo" / "agents"), "--emit-otlp", str(out)])
    assert rc == 0
    doc = json.loads(out.read_text())
    spans = {s["name"]: s for rs in doc["resourceSpans"] for ss in rs["scopeSpans"] for s in ss["spans"]}
    bad = spans["agentest.run " + INPUTS["demo_bad"]]
    ev = {a["key"]: list(a["value"].values())[0] for e in bad["events"] for a in e["attributes"]
          if e["name"] == "gen_ai.evaluation.result" and any(x["value"].get("stringValue") == "T2-005" for x in e["attributes"])}
    assert ev["gen_ai.evaluation.score.label"] == "fail" and ev["gen_ai.evaluation.score.value"] == 0.0
    assert len(bad["events"]) == 171 and bad["status"]["code"] == 2 and bad["links"]
    # links point at the judged traces' root spans
    judged = {x for d in otel.read_otlp_file(next((ROOT / INPUTS["demo_dir"] / "agents" / INPUTS["demo_bad"] / "traces").iterdir()))
              for x in otel.root_ids(d)}
    assert {(lk["traceId"], lk["spanId"]) for lk in bad["links"]} == judged
    # the verdict file is itself valid OTLP: it can be re-read and sent through the protobuf codec
    assert otlp_proto.decode_traces(otlp_proto.encode_traces(doc))["resourceSpans"]


def test_import_cli_with_builtin_dialect(tmp_path):
    ex = ROOT / "examples" / "langgraph_import"
    out = tmp_path / "t.otlp.jsonl"
    assert main(["std", "import", str(ex / "native" / (SVC + ".jsonl")), "--map", str(ex / "import" / "map.json"),
                 "--tools", str(ex / "agents" / SVC / "tools.json"), "--service", SVC, "--out", str(out)]) == 0
    assert out.read_text() == (ex / "agents" / SVC / "traces" / (SVC + ".otlp.jsonl")).read_text()


def test_no_new_runtime_dependency():
    deps = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["dependencies"]
    assert [d.split(">")[0].split("=")[0].strip().lower() for d in deps] == ["pyyaml"]
    for f in ("serve.py", "otel.py", "importers.py", "reports.py"):  # otlp_proto.py: see test_no_lock_in.OPTIONAL
        src = (ROOT / "src" / "agentest" / "standards" / f).read_text()
        assert "google.protobuf" not in src and "opentelemetry" not in src.replace("opentelemetry.io", "").replace(
            "open-telemetry", "").replace("OpenTelemetry", "").split('"""', 2)[-1] or f == "serve.py"


@pytest.mark.parametrize("name,want", [("..", "unknown_service"), (".", "unknown_service"), ("../x", "_x"), (".hidden", "hidden"),
                                       ("a/../../b", "a_.._.._b"), ("ticket-desk", "ticket-desk"), ("", "unknown_service")])
def test_serve_folder_name_cannot_escape_out_dir(name, want):
    from agentest.standards.serve import _service

    doc = {"resourceSpans": [{"resource": {"attributes": [{"key": "service.name", "value": {"stringValue": name}}]}}]}
    assert _service(doc) == want
