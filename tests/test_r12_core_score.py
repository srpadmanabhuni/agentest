"""r12 assessable-subset scorer: P/R only on assessable tests, deferred reported separately, exclusions honoured."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("core_score", ROOT / "scripts/core_score.py")
CS = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(CS)
SCOPE = {"assessable": ["T1-001", "T1-005", "T6-010"], "deferred": {"T6-007": "no retrieval"}}


def _c(s, trust="high"):
    return {"status": s, "trust": trust}


def test_counts_only_assessable_and_reports_deferred():
    res = {"x1": {"T1-001": _c("fail"), "T1-005": _c("n/a"), "T6-010": _c("pass"), "T6-007": _c("fail")},
           "x2": {"T1-001": _c("pass"), "T1-005": _c("fail"), "T6-010": _c("pass"), "T6-007": _c("n/a")}}
    lab = {"controls": ["x2"], "defects": {"x1": ["T1-001", "T1-005", "T6-007"]}}
    out = CS.score(res, lab, SCOPE)
    s, d = out["assessable"], out["deferred"]
    assert s["tp"] == ["x1:T1-001"] and s["fp"] == ["x2:T1-005"] and s["fn"] == ["x1:T1-005"]
    assert s["missed_na"] == ["x1:T1-005"] and s["control_false_alarms"] == ["x2:T1-005"]
    assert s["precision"] == 0.5 and s["recall"] == 0.5 and not out["bar"]["0 control false alarms"]
    assert d["na_by_test"] == {"T6-007": 1} and d["fails_not_counted"] == ["x1:T6-007"] and d["labelled_not_counted"] == ["x1:T6-007"]


def test_exclusions_and_high_trust():
    res = {"x9": {"T1-001": _c("pass"), "T1-005": _c("fail", "low"), "T6-010": _c("fail")}}
    exc = {"_comment": [], "T6-010": {"excluded": ["x9"]}}
    out = CS.score(res, {"controls": [], "defects": {}}, SCOPE, exc, high_trust_only=True)
    assert out["assessable"]["fp"] == [] and out["assessable"]["cells"] == 2
    assert CS.score(res, {"controls": [], "defects": {}}, SCOPE, exc)["assessable"]["fp"] == ["x9:T1-005"]


def test_fixture_partitions_core47():
    core = json.loads((ROOT / "fixtures/core47.json").read_text())["core"]
    sc = json.loads((ROOT / "fixtures/core-assessable.json").read_text())
    assert sorted(sc["assessable"] + list(sc["deferred"])) == sorted(core)
    assert not set(sc["assessable"]) & set(sc["deferred"]) and all(sc["deferred"].values())
    assert set(sc["pending_rebaseline"]) <= set(sc["assessable"])
