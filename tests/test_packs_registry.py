"""The extension packs sit OUTSIDE the 110 / 130: counts, default run set, catalogue rows, selection and n/a behaviour."""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from agentest.cli import main
from agentest.local import packs as local_packs
from agentest.standards import metadata
from agentest.standards import packs as P
from agentest.standards.catalog import ALL_IDS, CATALOGUE_IDS, RAI_ADDITION_IDS, X_IDS, what
from agentest.standards.rules import RULES, evaluate, missing_ids
from tests.packs_harness import Synth, agent, runs

ROOT = Path(__file__).resolve().parents[1]
PREFIX = {"ma": "MA", "pv": "PV", "rt": "RT", "bf": "BF", "ex": "EX", "dl": "DL"}
COUNTS = {"ma": 13, "pv": 8, "rt": 6, "bf": 5, "ex": 5, "dl": 4}


def test_110_and_130_are_frozen():
    assert len(CATALOGUE_IDS) == len(set(CATALOGUE_IDS)) == 110
    assert len(ALL_IDS) == len(set(ALL_IDS)) == 130 and len(X_IDS) == 20
    assert len((ROOT / "catalog" / "checklist-110.jsonl").read_text().splitlines()) == 110
    assert not set(P.PACK_IDS) & set(ALL_IDS) and not set(P.PACK_IDS) & set(RAI_ADDITION_IDS)
    assert missing_ids() == []


def test_pack_rules_never_enter_the_core_registry():
    assert set(RULES) - set(ALL_IDS) == set(RAI_ADDITION_IDS)
    assert set(P.PACK_RULES) == set(P.PACK_IDS)


def test_default_run_is_exactly_the_130():
    a = agent({})
    out = evaluate(a, runs(Synth("x", "hi").answer("hello").build()))
    assert list(out) == list(ALL_IDS) and len(out) == 130


def test_default_cli_run_still_reports_130_ids(capsys):
    assert main(["std", "run", "--agent", "a01"]) == 0
    assert "x 130 IDs" in capsys.readouterr().out


def test_every_pack_row_is_complete_and_has_a_rule():
    rows = P.rows()
    assert {n: len(P.pack_ids(n)) for n in P.PACK_NAMES} == COUNTS and len(rows) == sum(COUNTS.values())
    refs = P.references()
    for i, r in rows.items():
        assert re.fullmatch(rf"{PREFIX[r['pack']]}-\d{{3}}", i), i
        assert r["family"] and r["title"] and r["rule"] and r["oracle"] in ("trace", "trace+spec", "spec"), i
        assert r["requires"] and r["na_when"] and r["severity"] in ("critical", "high", "medium", "low"), i
        assert r["references"] and set(r["references"]) <= set(refs), i
        assert what(i) == r["rule"]
    for k, v in refs.items():
        assert v["url"].startswith("https://") and v["label"], k


def test_ids_are_consecutive_per_pack():
    for n in P.PACK_NAMES:
        nums = sorted(int(i.split("-")[1]) for i in P.pack_ids(n))
        assert nums == list(range(1, len(nums) + 1)), n


def test_packs_are_selectable_and_listed(capsys):
    pk = local_packs()
    assert len(pk["all"]) == 130 and len(pk["extensions"]) == 20
    for n, c in COUNTS.items():
        assert len(pk[n]) == c
    assert len(pk["packs"]) == 41 and set(pk["rai"]) == set(RAI_ADDITION_IDS)
    assert main(["list", "--pack", "ma"]) == 0
    assert "13 test(s)" in capsys.readouterr().out
    assert main(["list", "--packs"]) == 0
    out = capsys.readouterr().out
    assert "ma " in out and "all" in out


def test_std_run_selects_packs_and_ids(capsys):
    assert main(["std", "run", "--agent", "a01", "--pack", "ma,pv"]) == 0
    assert "x 21 IDs" in capsys.readouterr().out
    assert main(["std", "run", "--agent", "a01", "--ids", "MA-001,T3-018,T1-001"]) == 0
    assert "x 3 IDs" in capsys.readouterr().out
    assert main(["std", "run", "--agent", "a01", "--pack", "nope"]) == 2
    assert main(["std", "run", "--agent", "a01", "--ids", "ZZ-999"]) == 2
    capsys.readouterr()


def test_no_pack_check_fails_without_its_observable():
    """A trace with no tools, no second agent, no spec and no attributes: every pack check says n/a (or passes), never fail."""
    docs = [Synth("x", "hi").answer("hello").build()]
    out = evaluate(agent({}), runs(*docs), ids=sorted(P.PACK_IDS))
    assert {i: r.status for i, r in out.items() if r.status == "fail"} == {}
    assert sum(r.status == "n/a" for r in out.values()) >= 36


def test_bundled_reference_agents_get_a_verdict_for_every_pack_id():
    ags = metadata.load_all()
    a = ags["a01"]
    from agentest.standards.runner import runs as agent_runs

    out = evaluate(a, agent_runs(a), ids=sorted(P.PACK_IDS))
    assert set(out) == set(P.PACK_IDS) and {r.status for r in out.values()} <= {"pass", "fail", "n/a"}


def test_governance_schema_accepts_the_new_blocks():
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads((ROOT / "src/agentest/standards/schemas/governance-extension.schema.json").read_text())
    ok = {"multiAgent": {"supervisor": "boss", "delegation": {"boss": ["a", "b"]}, "maxDepth": 3, "maxHandoffs": 6, "escalationTools": ["esc"]},
          "privacy": {"phiTools": ["t"], "memoryTools": ["m"], "erasureTools": ["e"], "classLevels": {"x": "restricted", "y": "public"}},
          "fairness": {"refusalGap": 0.1, "lengthRatio": 1.5}}
    jsonschema.validate(ok, schema)
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate({"privacy": {"classLevels": {"x": "secret"}}}, schema)


def test_pack_code_names_no_agent_and_no_catalogue_id():
    agents = {d.name for base in (ROOT / "agents", ROOT / "examples") for card in base.rglob("agent-card.json") for d in [card.parent]}
    for f in sorted((ROOT / "src/agentest/standards/packs").glob("*.py")):
        src = f.read_text()
        assert not re.search(r"\ba\d{2}\b", src), f.name
        assert not re.search(r"\.id\s*(==|!=|in\b)", src), f.name
        for n in sorted(a for a in agents if "_" in a):
            assert f'"{n}"' not in src and f"'{n}'" not in src, (f.name, n)


def test_synth_is_deterministic_and_round_trips():
    def build():
        t = Synth("d", "Refund ORD-1001")
        b = t.agent("billing", handoff_from="supervisor", input="go")
        t.tool("issue_refund", {"order_id": "ORD-1001"}, "ok", parent=b)
        return t.answer("done").build()

    assert json.dumps(build(), sort_keys=True) == json.dumps(build(), sort_keys=True)
    r = runs(build())[0]
    assert [s["op"] for s in r.spans][:3] == ["invoke_agent", "invoke_agent", "execute_tool"] and r.tools[0].name == "issue_refund"
