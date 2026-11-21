"""Synthetic sample for T5-010: inline SQL literals. Newly written; no real data."""
from tests.test_rai_additions_rules import RO, _agent, _run, _st, _tool

TOOLS = {
    "run_query": {"name": "run_query", "annotations": RO, "description": "Run a SQL query."},
}
A = _agent(TOOLS, {})


def _q(sql):
    return [_run(input="Find users", answer="ok", tools=[_tool("run_query", args={"sql": sql}, result="{}")])]


def test_double_quoted_literal_fails():
    assert _st(A, _q('SELECT * FROM users WHERE name = "bob" LIMIT 5'), "T5-010") == "fail"   # on main: pass


def test_between_literals_fail():
    assert _st(A, _q("SELECT * FROM users WHERE id BETWEEN 1 AND 99"), "T5-010") == "fail"   # on main: pass


def test_placeholder_only_query_passes():
    assert _st(A, _q("SELECT * FROM users WHERE id = ?"), "T5-010") == "pass"   # guard


def test_named_placeholder_query_passes():
    assert _st(A, _q("SELECT * FROM users WHERE id = :uid"), "T5-010") == "pass"   # guard
