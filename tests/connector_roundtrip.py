"""Shared round trip for importer connectors (trace format 1.0.0).

A native log is imported twice: as before, and with ``"trace_format": "1.0.0"``. The second import must validate
against the trace-format schema, carry the run-level attributes on the resource only, read back as the same runs and
get the same verdicts on all default checks. Nothing here is framework-specific."""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema

from agentest.standards.catalog import ALL_IDS
from agentest.standards.importers import TRACE_FORMAT_VERSION, to_docs
from agentest.standards.metadata import Agent
from agentest.standards.otel import from_otlp
from agentest.standards.rules import evaluate

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = json.loads((ROOT / "src/agentest/standards/schemas/trace-format.schema.json").read_text(encoding="utf-8"))
RUN_LEVEL = {"agentest.trace_format.version", "agentest.run.id", "user.id", "agentest.source.start_time_unix_nano"}


def resource(doc: dict) -> dict:
    return {a["key"]: next(iter(a["value"].values())) for a in doc["resourceSpans"][0]["resource"]["attributes"]}


def run_key(doc: dict) -> tuple:
    r = from_otlp(json.loads(json.dumps(doc)))
    return (r.input_id, r.rep, r.input, r.answer, json.dumps(r.final_state, sort_keys=True, default=str), r.error, r.conversation,
            [(t.name, json.dumps(t.args, sort_keys=True, default=str), str(t.result), t.error, t.actor) for t in r.tools],
            json.dumps(r.approvals, sort_keys=True, default=str), json.dumps(r.effects, sort_keys=True, default=str),
            [h[:2] for h in r.handoffs], json.dumps(r.attrs, sort_keys=True, default=str), r.span_blobs, r.times)


def verdicts(agent: Agent, docs: list[dict]) -> dict:
    runs = [from_otlp(json.loads(json.dumps(d))) for d in docs]
    return {k: r.status for k, r in evaluate(agent, runs, ids=list(ALL_IDS), mode="examples").items()}


def check(raws: list[dict], mapping: dict, service: str, agent: Agent, is_write=None) -> tuple[list[dict], dict]:
    """Assert the trace-format import is a pure resource addition. Returns the new docs and their verdicts."""
    before = to_docs(raws, dict(mapping), service, is_write)
    after = to_docs(raws, {**mapping, "trace_format": TRACE_FORMAT_VERSION}, service, is_write)
    assert len(before) == len(after) == len(raws)
    v = jsonschema.Draft202012Validator(SCHEMA)
    for b, a in zip(before, after, strict=True):
        v.validate(a)
        assert a["resourceSpans"][0]["scopeSpans"] == b["resourceSpans"][0]["scopeSpans"]  # spans byte-identical
        rb, ra = resource(b), resource(a)
        assert ra["agentest.trace_format.version"] == TRACE_FORMAT_VERSION
        assert set(ra) - set(rb) <= RUN_LEVEL and all(ra[k] == rb[k] for k in rb)
        assert run_key(a) == run_key(b)
    got, want = verdicts(agent, after), verdicts(agent, before)
    assert len(want) == len(ALL_IDS) == 130
    assert got == want, {k: (got.get(k), w) for k, w in want.items() if got.get(k) != w}
    return after, got
