"""v4.1 generic evals: X-049 consistency across repeated runs (pass^k) and X-050 per-task budgets.
Each check has a passing and a failing reference case. Synthetic, neutral tool names."""
from __future__ import annotations

from agentest.standards import rules
from tests.test_v40_round7 import _run, _t
from tests.test_v40_round9_detections import _st


def _rep(tools, answer, rep, iid="task_1", ev=None):
    r = _run(tools, answer, iid)
    r.rep = rep
    if ev is not None:
        r.evaluations = [{"gen_ai.evaluation.name": "quality", "gen_ai.evaluation.score.label": ev[0], "gen_ai.evaluation.score.value": ev[1]}]
    return r


RD = _t("get_case", {"id": "CS-1"}, {"id": "CS-1", "payable_inr": 900})
PAY = _t("pay_case", {"id": "CS-1", "amount": 900, "decision": "approve"}, {"paid": True}, t=2)


def test_x049_pass_when_all_k_runs_agree():
    runs = [_rep([RD, PAY], "Paid 900 for CS-1.", i, ev=("pass", 0.9)) for i in range(3)]
    assert _st(runs, "X-049") == "pass"


def test_x049_fail_on_extra_write():
    runs = [_rep([RD, PAY], "Paid.", 0), _rep([RD, PAY, PAY], "Paid.", 1)]
    assert _st(runs, "X-049") == "fail"


def test_x049_fail_on_decision_flip():
    rej = _t("pay_case", {"id": "CS-1", "amount": 900, "decision": "reject"}, {"paid": False}, t=2)
    assert _st([_rep([RD, PAY], "Paid.", 0), _rep([RD, rej], "Rejected.", 1)], "X-049") == "fail"


def test_x049_fail_on_quality_drift():
    runs = [_rep([RD, PAY], "Paid.", 0, ev=("pass", 0.9)), _rep([RD, PAY], "Paid.", 1, ev=("pass", 0.5))]
    assert _st(runs, "X-049") == "fail"
    runs = [_rep([RD, PAY], "Paid.", 0, ev=("pass", 0.9)), _rep([RD, PAY], "Paid.", 1, ev=("pass", 0.85))]
    assert _st(runs, "X-049") == "pass"


def test_x049_na_when_k_below_2():
    assert _st([_rep([RD, PAY], "Paid.", 0)], "X-049") == "n/a"


def _timed(n_tools, secs=None, usage=None):
    r = _run([RD] * n_tools, "Done.")
    r.duration_s = secs
    r.usage = usage or []
    return r


def test_x050_pass_within_budget():
    assert _st([_timed(2, 3.0, [{"input": 500, "output": 100}])], "X-050") == "pass"


def test_x050_fail_over_each_limit():
    assert _st([_timed(2, 9999.0)], "X-050") == "fail"
    assert _st([_timed(2, 1.0, [{"input": 30000, "output": 10}])], "X-050") == "fail"
    assert _st([_timed(25, 1.0)], "X-050") == "fail"


def test_x050_limits_from_config_override():
    old = dict(rules.BUDGET)
    try:
        rules.BUDGET["task_seconds"] = 2.0
        assert _st([_timed(2, 3.0)], "X-050") == "fail"
    finally:
        rules.BUDGET.clear()
        rules.BUDGET.update(old)
    assert _st([_timed(2, 3.0)], "X-050") == "pass"


def test_x050_na_when_trace_lacks_fields():
    assert _st([_timed(2)], "X-050") == "n/a"


def test_x050_cli_override(tmp_path):
    """The CLI flags override the configured limits (every bundled agent in one example folder; none named)."""
    import json

    from agentest.cli import main
    from agentest.standards import ext

    args = ["std", "run", "--agents", "examples/pack_defects/agents", "--ids", "X-050", "--max-na", "1",
            "--max-task-seconds", "1e9", "--max-task-tokens", "1000000000"]
    old = dict(rules.BUDGET)
    try:
        main(args + ["--max-task-tool-calls", "1000", "--json", str(tmp_path / "a.json")])
        a = {k: v["X-050"]["status"] for k, v in json.loads((tmp_path / "a.json").read_text()).items()}
        assert a and set(a.values()) == {"pass"}, a
        main(args + ["--max-task-tool-calls", "0", "--json", str(tmp_path / "b.json")])
        b = {k: v["X-050"]["status"] for k, v in json.loads((tmp_path / "b.json").read_text()).items()}
        assert set(b.values()) == {"fail"}, b
    finally:
        ext.reset()
        rules.BUDGET.clear()
        rules.BUDGET.update(old)
