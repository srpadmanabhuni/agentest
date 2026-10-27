"""Agent-independence gates (docs/standards/AGENT-INDEPENDENCE-AUDIT.md).

1. Mutation: rename every agent ID, agent name and tool name to random tokens, consistently across the metadata
   (AgentCard, governance extension, MCP tools) and the OTLP traces. Every verdict must be identical.
2. Static scan: no agent ID, agent name or declared tool name occurs in the rule engine.
3. Onboarding: a new agent made only of standard artefacts gets verdicts with no code change.
"""

from __future__ import annotations

import json
import random
import re
from pathlib import Path

import pytest

from agentest.standards import metadata, rules, runner
from agentest.standards.catalog import ALL_IDS

SRC = Path(__file__).resolve().parents[1] / "src" / "agentest"
ENGINE = sorted((SRC / "standards").glob("*.py")) + [SRC / "standards" / "semconv.yaml"]


ID_ATTRS = {"gen_ai.tool.name", "gen_ai.agent.name", "gen_ai.agent.id", "agentest.approval.action", "agentest.handoff.source", "service.name"}


def _rename_otlp(x, m: dict[str, str]):
    """Rename identifiers where OTel carries them: identifier attributes and span names. Payloads are left alone."""
    if isinstance(x, dict):
        if x.get("key") in ID_ATTRS and isinstance(x.get("value", {}).get("stringValue"), str):
            v = x["value"]["stringValue"]
            return {"key": x["key"], "value": {"stringValue": m.get(v, v)}}
        out = {k: _rename_otlp(v, m) for k, v in x.items()}
        if isinstance(out.get("name"), str) and "spanId" in out:
            op, _, rest = out["name"].partition(" ")
            out["name"] = f"{op} {m.get(rest, rest)}" if rest else m.get(op, op)
        return out
    if isinstance(x, list):
        return [_rename_otlp(v, m) for v in x]
    return x


def _rename_meta(x, m: dict[str, str], parent: str = ""):
    """Rename identifiers in metadata: tool/agent names as string values, and the keys of name-keyed maps
    (governance prerequisites, roles.actors). Published success criteria (postconditions) are payload, not identifiers."""
    if isinstance(x, dict):
        return {(m.get(k, k) if parent in ("prerequisites", "actors") else k): (v if k == "postconditions" else _rename_meta(v, m, k))
                for k, v in x.items()}
    if isinstance(x, list):
        return [_rename_meta(v, m, parent) for v in x]
    if isinstance(x, str):
        return m.get(x, x)
    return x


def _mutate(a: metadata.Agent, out: Path, rng: random.Random) -> tuple[str, dict[str, str]]:
    docs = runner.otlp_docs(a)
    # tools of the agentest scenario fixture worlds belong to the test, not to the agent: keep them
    fixture = {r.name for d in docs for r in runner.from_otlp(json.loads(json.dumps(d))).tools
               if runner.from_otlp(json.loads(json.dumps(d))).input_id in ALL_IDS}
    names = set(a.tools) | {t.name for d in docs for t in runner.from_otlp(json.loads(json.dumps(d))).tools}
    used: set[str] = set(names) | {a.id, a.card.get("name", "")}

    def fresh(old: str) -> str:  # same length keeps size-based measures (token estimates) identical
        while True:
            x = "".join(rng.choice("abcdefghijklmnopqrstuvwxyz") for _ in old)
            if x not in used:
                used.add(x)
                return x
    m = {n: fresh(n) for n in sorted(names - fixture) if n}
    new_id = fresh(a.id)
    m[a.id] = new_id
    if a.card.get("name"):
        m[a.card["name"]] = fresh(a.card["name"])
    d = out / new_id
    d.mkdir(parents=True)
    (d / "agent-card.json").write_text(json.dumps(_rename_meta(a.card, m)))
    (d / "tools.json").write_text(json.dumps({"tools": _rename_meta(list(a.tools.values()), m)}))
    (d / "traces.otlp.jsonl").write_text("".join(json.dumps(_rename_otlp(x, m)) + "\n" for x in docs))
    return new_id, m


def _unmap(detail: str, m: dict[str, str]) -> str:
    for old, new in sorted(m.items(), key=lambda kv: -len(kv[1])):
        detail = detail.replace(new, old) if len(new) >= 4 else re.sub(rf"(?<![A-Za-z0-9]){re.escape(new)}(?![A-Za-z0-9])", old, detail)
    return detail


AGENTS = metadata.load_all()


@pytest.mark.parametrize("aid", sorted(AGENTS))
def test_mutation_renaming_agent_and_tools_changes_no_verdict(aid, tmp_path):
    a = AGENTS[aid]
    rng = random.Random(f"agentest-mutation-{aid}")
    want = rules.evaluate(a, runner.runs(a))
    new_id, m = _mutate(a, tmp_path, rng)
    b = metadata.load(tmp_path / new_id)
    got = rules.evaluate(b, runner.runs(b))
    sd = {i: (want[i].status, got[i].status, want[i].detail[:90], got[i].detail[:90]) for i in want if want[i].status != got[i].status}
    assert not sd, sd
    diff = {i: (want[i].detail, _unmap(got[i].detail, m)) for i in want if want[i].detail != _unmap(got[i].detail, m)}
    assert not diff, list(diff.items())[:3]


def _words(a: metadata.Agent) -> set[str]:
    return {a.id, a.card.get("name", ""), *a.tools} - {""}


def test_engine_names_no_agent_id_name_or_declared_tool():
    """Rules and mappings may use generic vocabulary only. The scenario oracles (scenarios.yaml) are exempt by design:
    they name the tools of agentest's own fixture worlds, keyed by catalogue ID."""
    vocab = set().union(*(_words(a) for a in AGENTS.values()))
    vocab |= set().union(*(_words(a) for a in metadata.load_all(Path(__file__).resolve().parents[1] / "examples" / "agnostic_demo" / "agents").values()))
    vocab = {w for w in vocab if len(w) > 3 and not re.fullmatch(r"[a-z]+", w)}  # single plain words (search, review) are generic vocabulary
    code = "\n".join(re.sub(r'"""[\s\S]*?"""|#[^\n]*', "", f.read_text()) for f in ENGINE)
    hits = sorted(w for w in vocab if re.search(rf"(?<![\w.-]){re.escape(w)}(?![\w-])", code))
    assert not hits, hits


def test_no_branch_on_agent_or_skill_identity():
    code = "\n".join(f.read_text() for f in ENGINE)
    assert not re.search(r"\.id\s*==|agent\s*==\s*['\"]|skill\w*\s*==\s*['\"]|['\"]a\d\d['\"]", code)


def test_onboard_new_agent_with_standard_artifacts_only(tmp_path):
    """A brand-new agent: an A2A AgentCard, MCP tools/list and an OTLP/JSON trace file. No mapping file, no code."""
    d = tmp_path / "agents" / "newcomer"
    d.mkdir(parents=True)
    (d / "agent-card.json").write_text(json.dumps({
        "protocolVersion": "0.3.0", "name": "Newcomer", "description": "files support tickets", "url": "https://agent.invalid/",
        "version": "1.0.0", "capabilities": {}, "defaultInputModes": ["text/plain"], "defaultOutputModes": ["text/plain"],
        "skills": [{"id": "ticket", "name": "File ticket", "description": "files a ticket", "tags": ["support"]}]}))
    (d / "tools.json").write_text(json.dumps({"tools": [
        {"name": "lookup", "description": "read a record", "inputSchema": {"type": "object", "properties": {"id": {"type": "string"}}},
         "annotations": {"readOnlyHint": True}},
        {"name": "file_ticket", "description": "create a ticket", "inputSchema": {"type": "object", "properties": {"queue": {"type": "string", "enum": ["billing", "tech"]}}},
         "annotations": {"readOnlyHint": False, "destructiveHint": False, "idempotentHint": False}}]}))
    (d / "trace.otlp.json").write_text(json.dumps(_trace([("lookup", {"id": "T-1"}), ("file_ticket", {"queue": "billing"}),
                                                           ("file_ticket", {"queue": "billing"})])))
    a = metadata.load_all(tmp_path / "agents")["newcomer"]
    assert not metadata.validate(a)
    res = rules.evaluate(a, runner.runs(a))
    assert set(res) == set(ALL_IDS)
    assert res["T1-006"].status == "fail"  # the duplicate non-idempotent write is caught from the MCP annotation alone
    assert res["T1-010"].status == "pass"  # enum arguments respected (JSON Schema)
    assert res["T2-004"].status == "n/a"   # no governance extension: approval rules degrade to n/a


def test_traces_only_agent_degrades_gracefully(tmp_path):
    """Nothing but an OTLP/JSON export from any collector: no AgentCard, no tools.json, no extension."""
    d = tmp_path / "agents" / "bare"
    d.mkdir(parents=True)
    (d / "export.otlp.json").write_text(json.dumps(_trace([("search", {"q": "x"}), ("search", {"q": "x"}), ("search", {"q": "x"}),
                                                            ("search", {"q": "x"}), ("search", {"q": "x"}), ("search", {"q": "x"})], traces=2)))
    a = metadata.load_all(tmp_path / "agents")["bare"]
    rs = runner.runs(a)
    assert len(rs) == 2  # two traces in one export file
    res = rules.evaluate(a, rs)
    assert set(res) == set(ALL_IDS) and {r.status for r in res.values()} <= {"pass", "fail", "n/a"}
    assert res["T5-009"].status == "fail"  # a retry storm needs only spans
    for i in ("T2-004", "T3-011", "T4-002", "T2-001"):  # governance-dependent IDs say n/a, never a guessed fail
        assert res[i].status == "n/a", (i, res[i])


def _trace(calls, traces: int = 1) -> dict:
    """A plain OTLP/JSON export as any OTel SDK would write it (GenAI semantic conventions only)."""
    def s(k, v):
        return {"key": k, "value": {"stringValue": v}}
    spans = []
    for n in range(traces):
        tid = f"{n + 1:032x}"
        spans.append({"traceId": tid, "spanId": f"{n:08x}00000000", "name": "invoke_agent", "kind": 1, "startTimeUnixNano": "1",
                      "endTimeUnixNano": "100", "attributes": [s("gen_ai.operation.name", "invoke_agent"),
                      s("gen_ai.input.messages", json.dumps([{"role": "user", "parts": [{"type": "text", "content": "file a billing ticket"}]}])),
                      s("gen_ai.output.messages", json.dumps([{"role": "assistant", "parts": [{"type": "text", "content": "Filed."}]}]))]})
        for i, (name, args) in enumerate(calls):
            spans.append({"traceId": tid, "spanId": f"{n:08x}{i + 1:08x}", "parentSpanId": f"{n:08x}00000000", "name": f"execute_tool {name}",
                          "kind": 1, "startTimeUnixNano": str(10 + i), "endTimeUnixNano": str(11 + i),
                          "attributes": [s("gen_ai.operation.name", "execute_tool"), s("gen_ai.tool.name", name),
                                         s("gen_ai.tool.call.arguments", json.dumps(args)), s("gen_ai.tool.call.result", "{}")]})
    return {"resourceSpans": [{"resource": {"attributes": [s("service.name", "any-agent")]}, "scopeSpans": [{"scope": {"name": "any-sdk"}, "spans": spans}]}]}


def test_mutation_covers_every_agent():
    assert len(AGENTS) >= 80
