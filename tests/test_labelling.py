"""Contributor labelling workflow: batches of 10, two independent labellers, maintainer resolution, hash lock before predictions."""
from __future__ import annotations

import importlib.util
import json
import shutil
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("labelling", ROOT / "scripts" / "labelling.py")
lb = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lb)


@pytest.fixture
def work(tmp_path):
    base = tmp_path / "labelling"
    shutil.copytree(ROOT / "labelling" / "pool", base / "pool")
    (base / "labels").mkdir()
    (base / "resolutions").mkdir()
    return base


def _fill(batch: dict, choose) -> Path:
    for it in batch["items"]:
        it["label"] = choose(it)
    return batch


def _submit(base, tmp_path, labeller, choose, size=10):
    batch = _fill(lb.make_batch(labeller, size, base), choose)
    f = tmp_path / f"{labeller}.json"
    f.write_text(json.dumps(batch), encoding="utf-8")
    return lb.submit(f, base), batch


def test_public_pool_is_fresh_synthetic_and_carries_no_labels():
    pool = lb.load_pool()
    assert len(pool) >= 30
    for d in pool.values():
        assert d["synthetic"] is True
        blob = json.dumps(d).lower()
        assert "password" not in blob and "api_key" not in blob


def test_batch_has_ten_traces_with_rule_text_and_no_label(work):
    b = lb.make_batch("alice", 10, work)
    assert len({i["trace_id"] for i in b["items"]}) == 10
    assert all(i["label"] is None and i["rule"] for i in b["items"])
    assert b["labeller"] == "alice" and len(b["batch_id"]) == 10


def test_bad_handles_and_unlabelled_items_are_refused(work, tmp_path):
    with pytest.raises(SystemExit):
        lb.make_batch("not a handle!", 10, work)
    batch = lb.make_batch("alice", 10, work)
    f = tmp_path / "b.json"
    f.write_text(json.dumps(batch), encoding="utf-8")  # labels still null
    with pytest.raises(SystemExit) as e:
        lb.submit(f, work)
    assert "label must be one of" in str(e.value)
    batch["items"][0]["label"] = "maybe"
    f.write_text(json.dumps(batch), encoding="utf-8")
    with pytest.raises(SystemExit):
        lb.submit(f, work)


def test_second_labeller_gets_the_same_traces_first_and_nobody_labels_a_trace_twice(work, tmp_path):
    _, a = _submit(work, tmp_path, "alice", lambda i: "pass")
    b = lb.make_batch("bob", 10, work)
    assert {i["trace_id"] for i in b["items"]} == {i["trace_id"] for i in a["items"]}  # finish pairs first
    with pytest.raises(SystemExit) as e:
        _submit(work, tmp_path, "alice", lambda i: "pass")  # alice has other traces left, but never the same ones
        _submit(work, tmp_path, "alice", lambda i: "pass")
        _submit(work, tmp_path, "alice", lambda i: "pass")
    assert "no trace needs your label" in str(e.value)  # pool exhausted for alice after three batches


def test_full_round_with_a_disagreement_lock_verify_and_tamper(work, tmp_path):
    truth = lambda i: "pass"  # noqa: E731
    for who in ("alice", "bob"):
        for _ in range(3):
            _submit(work, tmp_path, who, truth if who == "alice" else (lambda i: "fail" if i["trace_id"] == "LT-0001" else "pass"))
    r = lb.collect(work)
    assert r["unresolved"] == ["LT-0001 " + lb.load_pool(work)["LT-0001"]["checks"][0]] and not r["incomplete"]
    with pytest.raises(SystemExit) as e:
        lb.lock(work)
    assert "disagreement" in str(e.value)
    check = lb.load_pool(work)["LT-0001"]["checks"][0]
    (work / "resolutions" / f"LT-0001.{check}.json").write_text(
        json.dumps({"final": "fail", "resolver": "maintainer", "rationale": "the second labeller read the trace correctly"}), encoding="utf-8")
    assert lb.collect(work)["unresolved"] == []
    path = lb.lock(work)
    doc = json.loads(path.read_text())
    assert doc["final_count"] == 30 and len(doc["lock_hash"]) == 64 and doc["traces"] and doc["label_files"]
    assert lb.verify(work)["lock_hash"] == doc["lock_hash"]
    with pytest.raises(SystemExit):
        lb.lock(work)  # a lock is never overwritten
    # predictions must name the lock
    good = tmp_path / "pred-good.jsonl"
    good.write_text(json.dumps({"lock_hash": doc["lock_hash"]}) + "\n", encoding="utf-8")
    bad = tmp_path / "pred-bad.jsonl"
    bad.write_text(json.dumps({"lock_hash": "0" * 64}) + "\n", encoding="utf-8")
    assert lb.verify(work, predictions=good)
    with pytest.raises(SystemExit):
        lb.verify(work, predictions=bad)
    # tamper with a label file after the lock
    f = next((work / "labels").glob("alice--*.json"))
    d = json.loads(f.read_text())
    d["labels"][0]["label"] = "fail"
    f.write_text(json.dumps(d), encoding="utf-8")
    with pytest.raises(SystemExit):
        lb.verify(work)


def test_changing_a_trace_after_it_was_labelled_is_refused(work, tmp_path):
    _submit(work, tmp_path, "alice", lambda i: "pass")
    t = sorted((work / "pool").glob("LT-*.json"))[0]
    for p in (work / "pool").glob("LT-*.json"):
        d = json.loads(p.read_text())
        d["turns"][0]["answer"] += " (edited)"
        p.write_text(json.dumps(d), encoding="utf-8")
    assert t.exists()
    with pytest.raises(SystemExit) as e:
        lb.collect(work)
    assert "changed after it was labelled" in str(e.value)


def test_scoring_code_cannot_run_without_a_lock(work):
    with pytest.raises(SystemExit) as e:
        lb.require_lock(work)
    assert "locked before predictions" in str(e.value)


def test_private_commitments_are_part_of_the_lock_hash(work, tmp_path):
    for who in ("alice", "bob"):
        for _ in range(3):
            _submit(work, tmp_path, who, lambda i: "pass")
    priv = tmp_path / "priv.json"
    priv.write_text(json.dumps({"private-split-1": "a" * 64}), encoding="utf-8")
    p = lb.lock(work, private=priv)
    assert json.loads(p.read_text())["private_commitments"] == {"private-split-1": "a" * 64}
    assert lb.verify(work)


def test_cli_batch_status_and_docs(work, tmp_path, capsys):
    assert lb.main(["status", "--dir", str(work)]) == 0
    assert "traces: 30" in capsys.readouterr().out
    out = tmp_path / "b.json"
    assert lb.main(["batch", "--labeller", "carol", "--dir", str(work), "--out", str(out)]) == 0
    assert out.exists()
    doc = (ROOT / "docs" / "contributing" / "LABELLING.md").read_text(encoding="utf-8")
    for needle in ("python scripts/labelling.py batch", "python scripts/labelling.py submit", "pass", "fail", "n/a", "two independent", "lock"):
        assert needle in doc.lower() or needle in doc, needle
