"""Agent-independence, round-9 audit (29 Oct): the verdicts must not depend on WHICH agent is under test.

1. Bundled agents (agents/, examples/*/agents) AND unseen agents (every blind round's agents under docs/blind/*/agents,
   none of which existed when their rules were frozen) are renamed together with one consistent random map: agent IDs,
   folder names, card names, actor names (gen_ai.agent.name / handoff source), service.name and tool names. They are
   written into ONE folder and evaluated in a shuffled order. Every status and (un-mapped) detail must be identical.
2. A brand-new synthetic multi-agent desk with random names, generated fresh on every run, is evaluated with no
   registration, mapping file or code change, and renaming it changes nothing.
3. The blind-scoring path (scripts/blind_anon.py) hides agent identity behind opaque IDs before agentest runs and maps
   back afterwards; with the judge replaying a round's frozen cache, every verdict matches the direct run, which shows
   the judge payloads carry no agent identity either.
"""
from __future__ import annotations

import importlib.util
import json
import os
import random
import re
import secrets
import subprocess
import sys
from pathlib import Path

import pytest

from agentest.standards import metadata, rules, runner
from agentest.standards.catalog import ALL_IDS
from tests.judge_stub import no_judge
from tests.test_agent_independence import _rename_meta, _rename_otlp, _trace, _unmap

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("blind_anon", ROOT / "scripts" / "blind_anon.py")
blind_anon = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(blind_anon)


def _population() -> dict[str, metadata.Agent]:
    out: dict[str, metadata.Agent] = {}
    dirs = [ROOT / "agents", *sorted(ROOT.glob("examples/*/agents")), *sorted(ROOT.glob("docs/blind/*/agents"))]
    for d in dirs:
        for aid, a in metadata.load_all(d).items():
            out[f"{d.relative_to(ROOT)}/{aid}"] = a
    return out


def _identifiers(a: metadata.Agent) -> tuple[set[str], set[str]]:
    """(renamable identifiers, scenario-fixture tool names that belong to agentest itself)."""
    rs = runner.runs(a)
    fixture = {t.name for r in rs if r.input_id in ALL_IDS for t in r.tools}
    names = set(a.tools) | {t.name for r in rs for t in r.tools} | {t.actor for r in rs for t in r.tools}
    names |= {h[0] for r in rs for h in r.handoffs} | {h[1] for r in rs for h in r.handoffs}
    names |= blind_anon.identity_strings(a)
    fixture |= WORLD  # agentest's own scenario-world vocabulary (tools, state keys) belongs to the harness, not the agent
    return ({n for n in names if n} - fixture) | {a.id}, fixture  # the folder / agent ID is always renamed


def _write_renamed(a: metadata.Agent, out: Path, rng: random.Random, used: set[str]) -> tuple[str, dict[str, str]]:
    names, _ = _identifiers(a)
    used |= names

    def fresh(old: str) -> str:
        # same length (size-based measures such as token estimates stay identical) and same lexical shape: letters stay
        # letters of the same case, digits stay digits, separators (_ - . space) stay put. Rules may use the SHAPE of an
        # identifier (e.g. "has a separator, so it is an identifier, not an English word"), never its spelling.
        def ch(o: str) -> str:
            if o.isdigit():
                return rng.choice("0123456789")
            if o.isalpha() and o.isascii():
                c = rng.choice("abcdefghijklmnopqrstuvwxyz")
                return c.upper() if o.isupper() else c
            return o
        while True:
            x = "".join(ch(o) for o in old)
            if x not in used:
                used.add(x)
                return x
    m = {n: fresh(n) for n in sorted(names)}
    new_id = m[a.id]
    d = out / new_id
    (d / "traces").mkdir(parents=True)
    (d / "agent-card.json").write_text(json.dumps(_retext(_rename_meta(a.card, m), m)))
    (d / "tools.json").write_text(json.dumps({"tools": _retext(_rename_meta(list(a.tools.values()), m), m)}))
    (d / "traces" / "renamed.otlp.jsonl").write_text("".join(json.dumps(_retext(_rename_otlp(x, m), m)) + "\n" for x in runner.otlp_docs(a)))
    return new_id, m


def _retext(x, m: dict[str, str]):
    """The agent under a different name also SAYS the different name: rename identifier-shaped names (tool, actor,
    agent) inside message text, arguments, results and postconditions too, whole-word only, so text-vs-trace rules stay
    consistent. Declared prose (MCP tool description / title) is the publisher's semantics and is kept: rules read the
    meaning of a tool from its description, never from its name."""
    ids = {k: v for k, v in m.items() if len(k) >= 4 and re.search(r"[_\-.]|[a-z][A-Z]|\d", k)}
    if not ids:
        return x
    pat = re.compile(r"(?<![\w-])(" + "|".join(re.escape(k) for k in sorted(ids, key=len, reverse=True)) + r")(?![\w-])")
    def walk(v):
        if isinstance(v, dict):
            return {k: (w if k in ("description", "title") else walk(w)) for k, w in v.items()}  # declared prose stays
        if isinstance(v, list):
            return [walk(w) for w in v]
        if isinstance(v, str):
            return pat.sub(lambda g: ids[g.group(1)], v)
        return v
    return walk(x)


_gspec = importlib.util.spec_from_file_location("agent_vocab_guard", ROOT / "scripts" / "agent_vocab_guard.py")
_guard = importlib.util.module_from_spec(_gspec)
_gspec.loader.exec_module(_guard)
WORLD = _guard.world_tools()
POP = _population()
# Statuses must always match exactly. Details must match exactly too once v4.0-indep's ordering fixes land at the next
# freeze: T7-009 / X-026 / X-029 picked or listed tool names in set or spelling order, so a rename (or a different
# PYTHONHASHSEED) could reorder them or report a different one of several equally-bad tools. Until then a detail may
# differ only in which/what order of the agent's own declared identifiers it names.
STRICT_DETAIL = False


def _same_detail(a: str, b: str, idents: set[str] = frozenset()) -> bool:
    if STRICT_DETAIL:
        return a == b
    def norm(x: str) -> list[str]:
        return sorted("<id>" if w in idents else w for w in re.findall(r"[\w'-]+", x))
    return norm(a) == norm(b)


def test_population_includes_unseen_blind_agents():
    assert sum(k.startswith("docs/blind/") for k in POP) >= 20 and len(POP) >= 100


def test_rename_everything_and_shuffle_changes_no_verdict(tmp_path):
    rng = random.Random("agentest-independence-shuffle")
    used: set[str] = set()
    keys = sorted(POP)
    with no_judge():
        want = {k: rules.evaluate(POP[k], runner.runs(POP[k])) for k in reversed(keys)}
        maps = {}
        for k in keys:
            new_id, m = _write_renamed(POP[k], tmp_path, rng, used)
            maps[new_id] = (k, m)
        renamed = metadata.load_all(tmp_path)
        order = list(renamed)
        rng.shuffle(order)
        got = {maps[n][0]: (rules.evaluate(renamed[n], runner.runs(renamed[n])), maps[n][1]) for n in order}
    assert set(got) == set(want)
    bad = []
    for k in keys:
        g, m = got[k]
        for i in want[k]:
            if want[k][i].status != g[i].status or not _same_detail(want[k][i].detail, _unmap(g[i].detail, m), set(m)):
                bad.append((k, i, want[k][i].status, g[i].status, want[k][i].detail, _unmap(g[i].detail, m)))
    assert not bad, bad[:5]


def _synthetic(d: Path, rng: random.Random) -> dict:
    def w(n=7):
        return "".join(rng.choice("bcdfghjklmnpqrstvz") + rng.choice("aeiou") for _ in range(n // 2 + 1))
    read, write, lead, clerk = f"{w()}_{w(5)}", f"{w()}_{w(5)}", f"{w(6)}-{w(4)}", f"{w(6)}-{w(4)}"
    d.mkdir(parents=True)
    (d / "agent-card.json").write_text(json.dumps({
        "protocolVersion": "0.3.0", "name": f"{w()} {w()} desk", "description": "handles a request", "url": "https://agent.invalid/",
        "version": "0.0.1", "capabilities": {}, "defaultInputModes": ["text/plain"], "defaultOutputModes": ["text/plain"],
        "skills": [{"id": w(4), "name": w(), "description": "does the job", "tags": [w(4)]}]}))
    (d / "tools.json").write_text(json.dumps({"tools": [
        {"name": read, "description": "read a record", "inputSchema": {"type": "object", "properties": {"id": {"type": "string"}}},
         "annotations": {"readOnlyHint": True}},
        {"name": write, "description": "create an entry", "inputSchema": {"type": "object", "properties": {"kind": {"type": "string", "enum": ["a", "b"]}}},
         "annotations": {"readOnlyHint": False, "destructiveHint": False, "idempotentHint": False}}]}))
    doc = _trace([(read, {"id": "R-1"}), (write, {"kind": "a"}), (write, {"kind": "a"})])
    spans = doc["resourceSpans"][0]["scopeSpans"][0]["spans"]
    for s in spans[1:]:  # the calls are made by a sub-agent the lead handed off to
        s["attributes"].append({"key": "gen_ai.agent.name", "value": {"stringValue": clerk}})
    spans[0]["attributes"].append({"key": "gen_ai.agent.name", "value": {"stringValue": lead}})
    (d / "trace.otlp.json").write_text(json.dumps(doc))
    return {"read": read, "write": write}


def test_brand_new_synthetic_agent_needs_no_registration(tmp_path):
    seed = secrets.token_hex(8)  # a never-seen agent on every CI run; the seed is in the failure message
    rng = random.Random(seed)
    aid = "n" + secrets.token_hex(4)
    _synthetic(tmp_path / "agents" / aid, rng)
    with no_judge():
        a = metadata.load_all(tmp_path / "agents")[aid]
        assert not metadata.validate(a), seed
        res = rules.evaluate(a, runner.runs(a))
        assert set(res) == set(ALL_IDS), seed
        assert res["T1-006"].status == "fail", (seed, res["T1-006"])  # duplicate non-idempotent write, from MCP annotations only
        assert res["T1-010"].status == "pass", (seed, res["T1-010"])
        new_id, m = _write_renamed(a, tmp_path / "renamed", rng, set())
        b = metadata.load(tmp_path / "renamed" / new_id)
        got = rules.evaluate(b, runner.runs(b))
    assert {i: r.status for i, r in res.items()} == {i: r.status for i, r in got.items()}, seed


@pytest.mark.parametrize("rnd", ["r7", "r8"])
def test_blind_scoring_hides_identity_and_maps_back(rnd, tmp_path):
    """Direct run vs the anonymised blind-scoring path, both with the round's frozen judge cache in offline replay."""
    agents, cache = ROOT / f"docs/blind/{rnd}/agents", ROOT / f"docs/blind/{rnd}-judge-cache.jsonl"
    if not agents.is_dir() or not cache.is_file():
        pytest.skip(f"no {rnd} round bundled")
    env = {**os.environ, "AGENTEST_JUDGE_OFFLINE": "1"}
    common = ["--max-na", "1", "--judge", "http://127.0.0.1:9/v1"]
    c1, c2 = tmp_path / "c1.jsonl", tmp_path / "c2.jsonl"
    c1.write_bytes(cache.read_bytes())
    c2.write_bytes(cache.read_bytes())
    subprocess.run([sys.executable, "-m", "agentest.cli", "std", "run", "--agents", str(agents), *common, "--judge-cache", str(c1),
                    "--json", str(tmp_path / "direct.json")], env=env, capture_output=True)
    subprocess.run([sys.executable, str(ROOT / "scripts/blind_anon.py"), "--agents", str(agents), "--json", str(tmp_path / "anon.json"),
                    "--map-out", str(tmp_path / "map.json"), "--", *common, "--judge-cache", str(c2)], env=env, capture_output=True)
    a, b = json.loads((tmp_path / "direct.json").read_text()), json.loads((tmp_path / "anon.json").read_text())
    maps = json.loads((tmp_path / "map.json").read_text())
    assert sorted(a) == sorted(b) == sorted(v["id"] for v in maps.values())
    assert all(k.startswith("x") and len(k) == 9 and k not in a for k in maps)  # agentest only ever saw opaque IDs
    idents = set().union(*(set(x.tools) | blind_anon.identity_strings(x) for x in metadata.load_all(agents).values()))
    bad = [(k, i, a[k][i], b[k][i]) for k in a for i in a[k] if a[k][i]["status"] != b[k][i]["status"]
           or not _same_detail(a[k][i].get("detail", ""), b[k][i].get("detail", ""), idents)]
    assert not bad, bad[:3]
