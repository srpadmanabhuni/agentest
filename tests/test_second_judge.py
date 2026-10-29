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
    assert set(RU.SECOND_SIGNAL) == {"T1-001", "T1-018", "X-020", "X-028", "X-033"}
    assert "defect-confirm" in J.guides()


def test_configure2_needs_model(monkeypatch):
    for k in ("AGENTEST_JUDGE2_URL", "AGENTEST_JUDGE2_MODEL", "AGENTEST_JUDGE2_OFFLINE"):
        monkeypatch.delenv(k, raising=False)
    assert J.configure2("http://127.0.0.1:9/v1", None) is None
    j = J.configure2("http://127.0.0.1:9/v1", "m2", "/tmp/_j2.jsonl")
    assert j is not None and j.model == "m2"
    J.configure2("off", None)
