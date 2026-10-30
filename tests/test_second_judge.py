"""v4.0 r10: two-signal checks keep a deterministic fail only when an independent second judge confirms it."""
from types import SimpleNamespace

from agentest.standards import judge as J
from agentest.standards import rules as RU
from agentest.standards.expr import R


def _c():
    return SimpleNamespace(runs=[])


def test_no_second_judge_keeps_fail(monkeypatch):
    monkeypatch.setattr(J, "active2", lambda: None)
    u = RU._second_signal(_c(), "X-033", R("fail", "x"))
    assert u.status == "fail" and u.detail == "x"


def test_second_judge_disagrees_gives_uncertain(monkeypatch):
    j2 = J.Judge("http://127.0.0.1:9/v1", model="m2", cache="/tmp/_j2.jsonl")
    monkeypatch.setattr(J, "active2", lambda: j2)
    monkeypatch.setattr(J, "ask2", lambda gid, p: {"why": "agrees", "defect": False})
    u = RU._second_signal(_c(), "X-033", R("fail", "reason contradicts"))
    assert u.status == "not-assessed" and u.detail.startswith("uncertain: second judge m2")


def test_second_judge_confirms_keeps_fail(monkeypatch):
    j2 = J.Judge("http://127.0.0.1:9/v1", model="m2", cache="/tmp/_j2.jsonl")
    seen = {}
    monkeypatch.setattr(J, "active2", lambda: j2)
    monkeypatch.setattr(J, "ask2", lambda gid, p: seen.update(gid=gid, p=p) or {"why": "opposite", "defect": True})
    u = RU._second_signal(_c(), "X-020", R("fail", "raw restricted data"))
    assert u.status == "fail" and "confirms" in u.detail
    assert seen["gid"] == "defect-confirm" and seen["p"]["check"] == RU.RULES["X-020"][0]


def test_pass_never_asked(monkeypatch):
    j2 = J.Judge("http://127.0.0.1:9/v1", model="m2", cache="/tmp/_j2.jsonl")
    monkeypatch.setattr(J, "active2", lambda: j2)
    monkeypatch.setattr(J, "ask2", lambda gid, p: (_ for _ in ()).throw(AssertionError("asked")))
    assert RU._second_signal(_c(), "X-020", R("pass", "ok")).status == "pass"


def test_second_signal_ids():
    assert set(RU.SECOND_SIGNAL) == {"T1-018", "X-020", "X-033"}
    assert "defect-confirm" in J.guides()


def test_configure2_needs_model(monkeypatch):
    for k in ("AGENTEST_JUDGE2_URL", "AGENTEST_JUDGE2_MODEL", "AGENTEST_JUDGE2_OFFLINE"):
        monkeypatch.delenv(k, raising=False)
    assert J.configure2("http://127.0.0.1:9/v1", None) is None
    j = J.configure2("http://127.0.0.1:9/v1", "m2", "/tmp/_j2.jsonl")
    assert j is not None and j.model == "m2"
    J.configure2("off", None)


def test_either_judge_first_judge_confirms_keeps_fail(monkeypatch):
    monkeypatch.setenv("AGENTEST_JUDGE_AGREEMENT", "either")
    j2 = J.Judge("http://127.0.0.1:9/v1", model="m2", cache="/tmp/_j2.jsonl")
    j1 = J.Judge("http://127.0.0.1:9/v1", model="m1", cache="/tmp/_j1.jsonl")
    monkeypatch.setattr(J, "active2", lambda: j2)
    monkeypatch.setattr(J, "active", lambda: j1)
    monkeypatch.setattr(J, "ask2", lambda gid, p: {"why": "no", "defect": False})
    monkeypatch.setattr(J, "ask", lambda gids, p: {g: {"why": "yes", "defect": True} for g in gids})
    u = RU._second_signal(_c(), "X-028", R("fail", "restricted data pulled"))
    assert u.status == "fail" and "first judge confirms" in u.detail


def test_either_judge_both_decline_gives_uncertain(monkeypatch):
    monkeypatch.setenv("AGENTEST_JUDGE_AGREEMENT", "either")
    j2 = J.Judge("http://127.0.0.1:9/v1", model="m2", cache="/tmp/_j2.jsonl")
    j1 = J.Judge("http://127.0.0.1:9/v1", model="m1", cache="/tmp/_j1.jsonl")
    monkeypatch.setattr(J, "active2", lambda: j2)
    monkeypatch.setattr(J, "active", lambda: j1)
    monkeypatch.setattr(J, "ask2", lambda gid, p: {"why": "no", "defect": False})
    monkeypatch.setattr(J, "ask", lambda gids, p: {g: None for g in gids})
    u = RU._second_signal(_c(), "X-028", R("fail", "restricted data pulled"))
    assert u.status == "not-assessed" and u.detail.startswith("uncertain")


# v4.0 r11 (NOT BLIND): default agreement policy "both" - judge disagreement abstains, no first-judge rescue


def _two(monkeypatch, d1, d2, asked):
    j2 = J.Judge("http://127.0.0.1:9/v1", model="m2", cache="/tmp/_j2.jsonl")
    j1 = J.Judge("http://127.0.0.1:9/v1", model="m1", cache="/tmp/_j1.jsonl")
    monkeypatch.setattr(J, "active2", lambda: j2)
    monkeypatch.setattr(J, "active", lambda: j1)
    monkeypatch.setattr(J, "ask2", lambda gid, p: {"why": "j2", "defect": d2})
    monkeypatch.setattr(J, "ask", lambda gids, p: asked.append(gids) or {g: {"why": "j1", "defect": d1} for g in gids})


def test_both_policy_is_default(monkeypatch):
    monkeypatch.delenv("AGENTEST_JUDGE_AGREEMENT", raising=False)
    assert J.agreement_policy() == "both"


def test_both_policy_disagreement_abstains(monkeypatch):
    monkeypatch.delenv("AGENTEST_JUDGE_AGREEMENT", raising=False)
    asked = []
    _two(monkeypatch, True, False, asked)
    u = RU._second_signal(_c(), "X-033", R("fail", "reason contradicts"))
    assert u.status == "not-assessed" and u.detail.startswith("uncertain") and asked == []


def test_both_policy_agreement_keeps_fail(monkeypatch):
    monkeypatch.delenv("AGENTEST_JUDGE_AGREEMENT", raising=False)
    _two(monkeypatch, True, True, [])
    assert RU._second_signal(_c(), "X-033", R("fail", "reason contradicts")).status == "fail"


def test_bad_policy_rejected(monkeypatch):
    import pytest
    monkeypatch.setenv("AGENTEST_JUDGE_AGREEMENT", "majority")
    with pytest.raises(ValueError):
        J.agreement_policy()


def test_fluency_no_or_rescue_under_both(monkeypatch):
    monkeypatch.delenv("AGENTEST_JUDGE_AGREEMENT", raising=False)
    j2 = J.Judge("http://127.0.0.1:9/v1", model="m2", cache="/tmp/_j2.jsonl")
    monkeypatch.setattr(J, "active2", lambda: j2)
    monkeypatch.setattr(RU, "_judge_either", lambda gid, p: {"garbled": False})
    monkeypatch.setattr(J, "ask2", lambda gid, p: {"garbled": True})
    assert RU._fluency("some text") is False
    monkeypatch.setenv("AGENTEST_JUDGE_AGREEMENT", "either")
    assert RU._fluency("some text") is True
