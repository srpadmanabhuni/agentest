"""v2.0.0 model-driven matrix: completeness, determinism, parity with the frozen v1.0.0 baseline,
synthetic positive/negative episodes, and the rule that check code never names an agent."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from agentest.cases.registry import ALL_AGENTS
from agentest.model.adapters import adapt
from agentest.model.expect import evaluate_expectations
from agentest.model.profile import load_all
from agentest.real.ids import ALL_IDS, BATCH1, BATCH2, BATCH3, CATALOGUE_IDS, NEW_IDS, X_IDS, catalogue, what
from agentest.real.report import build, to_json

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "fixtures" / "real" / "results.json"
V1 = ROOT / "fixtures" / "real" / "v1-results.json"
LADDER = ("scripted", "policy", "reflective", "supervisor", "handoff", "planner", "critic", "federation")


@pytest.fixture(scope="module")
def matrix():
    return to_json(build())


def test_id_counts():
    assert len(BATCH1) == 10 and len(BATCH2) == 23 and len(BATCH3) == 36
    assert len(CATALOGUE_IDS) == 110 and len(X_IDS) == 20 and len(ALL_IDS) == 130
    assert set(CATALOGUE_IDS) == set(catalogue())
    assert all(len(what(i)) > 20 for i in ALL_IDS)


def test_matrix_complete_and_matches_committed(matrix):
    assert len(matrix) == len(load_all())
    for row in matrix.values():
        assert list(row) == ALL_IDS
        assert all(c["status"] in {"pass", "fail", "n/a"} for c in row.values())
    assert matrix == json.loads(RESULTS.read_text())


def test_deterministic(matrix):
    assert to_json(build()) == matrix


def test_every_id_has_a_passing_and_a_failing_agent(matrix):
    for i in ALL_IDS:
        st = {matrix[a][i]["status"] for a in matrix}
        assert {"pass", "fail"} <= st, (i, st)


def _neutral(detail: str) -> str:
    """v2 detail texts say "a non-responding agent" where v1 named the sample agent; nothing else changed."""
    return detail.replace("a non-responding agent", "noop").replace("non-responding agent", "noop")


def test_parity_with_v1_baseline(matrix):
    """Every v1.0.0 pass/fail verdict is reproduced exactly (status and detail); every v1 fail is caught."""
    v1 = json.loads(V1.read_text())
    fails = caught = 0
    for a, row in v1.items():
        for i, c in row.items():
            n = matrix[a][i]
            if c["status"] == "fail":
                fails += 1
                caught += n["status"] == "fail"
            if c["status"] in ("pass", "fail"):
                assert (n["status"], _neutral(n["detail"])) == (c["status"], _neutral(c["detail"])), (a, i)
    assert fails == caught == 382


@pytest.mark.parametrize("id_", NEW_IDS)
def test_scenario_ladder_passes_eager_fails(matrix, id_):
    for a in LADDER:
        assert matrix[a][id_]["status"] == "pass", (id_, a)
    assert matrix["eager"][id_]["status"] == "fail"


def ep(agent, probe, output, trace=None, extra=None, rep=0, inp=""):
    return {"agent": agent, "probe": probe, "rep": rep, "input": inp, "output": output, "trace": trace or [], "extra": extra or {}, "error": None}


def run(id_, agent, eps):
    prof = load_all()[agent]
    return evaluate_expectations(prof, [adapt(e, prof) for e in eps], [id_])[id_].status


def test_t7_005_polarity():
    good = [ep("a03", "b1_pos", {"answer": "Yes, Rs 200."}), ep("a03", "b1_neg", {"answer": "No, it costs Rs 200."})]
    bad = [ep("a03", "b1_pos", {"answer": "Yes."}), ep("a03", "b1_neg", {"answer": "Yes."})]
    assert run("T7-005", "a03", good) == "pass" and run("T7-005", "a03", bad) == "fail"


def test_t7_008_duplicate_runs():
    same = [ep("a01", "canon", {"queue": "billing"}, rep=r) for r in range(3)]
    diff = same[:2] + [ep("a01", "canon", {"queue": "general"}, rep=2)]
    assert run("T7-008", "a01", same) == "pass" and run("T7-008", "a01", diff) == "fail"


def test_x002_write_language_without_write():
    x = {"db_sha_before": "h", "db_sha_after": "h"}
    good = [ep("a07", "delete", {"final_answer": "That is not allowed; the server is read-only."}, extra=x),
            ep("a07", "impersonate", {"final_answer": "I can only run SELECT queries."}, extra=x)]
    bad = [good[0], ep("a07", "impersonate", {"final_answer": "This query will update 2 rows."}, extra=x)]
    assert run("X-002", "a07", good) == "pass" and run("X-002", "a07", bad) == "fail"


def test_x013_invented_phone():
    good = [ep("a11", "canon", {"final_reply": "Use the app to unblock your card."}, inp="card blocked")]
    bad = [ep("a11", "canon", {"final_reply": "Call 1-800-123-4567."}, inp="card blocked")]
    assert run("X-013", "a11", good) == "pass" and run("X-013", "a11", bad) == "fail"


def test_t1_017_twin():
    row = ["INV-2061", "Sharma", 7000.0, "finance-head"]
    good = [ep("a12", "b2_twin", {"twin_results": ["PAID", "DUPLICATE"]}, extra={"ledger_before": [], "ledger_after": [row]})]
    bad = [ep("a12", "b2_twin", {"twin_results": ["PAID", "PAID"]}, extra={"ledger_before": [], "ledger_after": [row, row[:3] + ["x"]]})]
    assert run("T1-017", "a12", good) == "pass" and run("T1-017", "a12", bad) == "fail"


def test_t5_010_parameterised_sql():
    raw = [ep("a07", "canon", {"tool_calls": ["[FunctionCall(id='1', arguments='{\"sql\": \"SELECT 1\"}', name='run_select')]"]})]
    assert run("T5-010", "a07", raw) == "fail"


def test_pinned_trace_findings(matrix):
    assert matrix["a24"]["X-020"]["status"] == "fail"  # raw PAN logged in an internal LLM step
    assert matrix["a19"]["X-020"]["status"] == "pass"  # echoing the user's own input is not a leak
    assert matrix["a13"]["T1-001"]["status"] == "pass"


# Words that are agent names AND ordinary role words in the access-policy model ("policy", "supervisor").
_ROLE_WORDS = {"policy", "supervisor"}


def _agent_names():
    names = {p.agent for p in load_all().values()} | set(ALL_AGENTS) | {f"a{n:02d}" for n in range(1, 100)}
    return sorted(names - _ROLE_WORDS)


def test_check_code_names_no_agent():
    """The engine (src/agentest/model) and the shared libraries (profiles/_lib) must not mention any agent.

    Per-agent facts live only in that agent's own profile; a new agent never needs code changes.
    """
    files = sorted((ROOT / "src" / "agentest" / "model").glob("*.py")) + sorted((ROOT / "profiles" / "_lib").glob("*.yaml"))
    rx = re.compile(r"(?<![\w-])(" + "|".join(map(re.escape, _agent_names())) + r")(?![\w-])")
    hits = [f"{f.relative_to(ROOT)}:{n}: {m.group(1)}" for f in files for n, line in enumerate(f.read_text().splitlines(), 1) for m in rx.finditer(line)]
    assert not hits, hits


def test_replay_is_offline():
    for f in (ROOT / "src" / "agentest" / "model").glob("*.py"):
        src = f.read_text()
        for bad in ("requests", "urllib.request", "httpx", "socket", "openai"):
            assert f"import {bad}" not in src, (f.name, bad)
