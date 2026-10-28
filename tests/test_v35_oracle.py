"""v3.5 optional offline oracle: determinism, caching, offline replay, label validation, routing between the embedding
pre-filter and the SLM, backend parsing and the loopback guard. No model needed: the built-in hashing backend and
in-test fake backends stand in for llama.cpp / ONNX."""
from __future__ import annotations

import json

import pytest

from agentest.standards import oracle as O
from agentest.standards.judge import NotAssessed


class FakeEmbed(O.Backend):
    """Maps a text to a fixed 2-d direction by the first matching key (test double, not a heuristic in the product)."""

    model_id = "fake-embed"

    def __init__(self, table: dict[str, list[float]]):
        self.table, self.calls = table, 0

    def embed(self, texts):
        self.calls += len(texts)
        return [next((v for k, v in self.table.items() if k in t), [0.0, 1.0]) for t in texts]


class FakeSLM(O.Backend):
    model_id = "fake-slm"

    def __init__(self, answer: str):
        self.answer, self.calls = answer, 0

    def generate(self, prompt, labels):
        self.calls += 1
        return self.answer


TASK = O.Task(id="t", version=1, positive="yes", labels={"yes": ["POS"], "no": ["NEG"]}, question="{labels}: {text}",
              reject_margin=0.5, abstain=0.1)


def test_hash_backend_is_deterministic_and_normalised(tmp_path):
    o = O.Oracle(O.HashBackend(), cache=tmp_path / "c.jsonl")
    a, b = o.vectors(["Emergency access"]), O.Oracle(O.HashBackend(), cache=tmp_path / "d.jsonl").vectors(["Emergency access"])
    assert a == b and abs(sum(x * x for x in a[0]) - 1) < 1e-4
    assert o.vectors(["other text"]) != a


def test_vectors_are_cached_and_replayed_offline(tmp_path):
    cache = tmp_path / "c.jsonl"
    fe = FakeEmbed({"POS": [1.0, 0.0]})
    o = O.Oracle(fe, cache=cache)
    v = o.vectors(["POS here"])
    o.vectors(["POS here"])
    assert fe.calls == 1  # second call from the cache
    replay = O.Oracle(O.backend("replay", "fake-embed"), cache=cache, offline=True)
    assert replay.vectors(["POS here"]) == v
    with pytest.raises(O.OracleUnavailable):
        replay.vectors(["never seen"])


def test_offline_miss_is_not_assessed_never_a_fallback(tmp_path):
    o = O.Oracle(FakeEmbed({}), FakeSLM("yes"), cache=tmp_path / "c.jsonl", offline=True)
    with pytest.raises(NotAssessed):  # OracleUnavailable is a NotAssessed: rules report not-assessed
        o.classify(TASK, "anything")


def test_no_backend_configured_is_not_assessed(tmp_path):
    with pytest.raises(O.OracleUnavailable):
        O.Oracle(cache=tmp_path / "c.jsonl").vectors(["x"])
    with pytest.raises(O.OracleUnavailable):
        O.Oracle(cache=tmp_path / "c.jsonl").ask(TASK, "x")


def test_cache_key_depends_on_model_and_task_version(tmp_path):
    cache = tmp_path / "c.jsonl"
    O.Oracle(slm=FakeSLM("yes"), cache=cache).ask(TASK, "x")
    other_model = FakeSLM("no")
    other_model.model_id = "fake-slm-2"
    assert O.Oracle(slm=other_model, cache=cache).ask(TASK, "x") == "no"
    v2 = O.Task(**{**TASK.__dict__, "version": 2, "meta": {}})
    s = FakeSLM("no")
    assert O.Oracle(slm=s, cache=cache).ask(v2, "x") == "no" and s.calls == 1


def test_slm_answer_outside_label_set_is_rejected(tmp_path):
    o = O.Oracle(slm=FakeSLM("maybe"), cache=tmp_path / "c.jsonl")
    with pytest.raises(O.OracleUnavailable):
        o.ask(TASK, "x")


def test_slm_answer_is_normalised(tmp_path):
    assert O.Oracle(slm=FakeSLM(' "Yes." '), cache=tmp_path / "c.jsonl").ask(TASK, "x") == "yes"


def test_embedding_prefilter_decides_clear_negatives_without_the_slm(tmp_path):
    slm = FakeSLM("yes")
    o = O.Oracle(FakeEmbed({"POS": [1.0, 0.0], "NEG": [0.0, 1.0]}), slm, cache=tmp_path / "c.jsonl")
    d = o.classify(TASK, "NEG request")
    assert d.label == "no" and d.via == "embedding" and slm.calls == 0


def test_candidates_go_to_the_slm_which_decides(tmp_path):
    slm = FakeSLM("no")  # the SLM may overrule a lexical look-alike that the embedding finds close to the positives
    o = O.Oracle(FakeEmbed({"POS": [1.0, 0.0], "NEG": [0.0, 1.0]}), slm, cache=tmp_path / "c.jsonl")
    d = o.classify(TASK, "POS look-alike")
    assert d.label == "no" and d.via == "slm" and slm.calls == 1


def test_embedding_only_method_abstains_inside_the_band(tmp_path):
    t = O.Task(**{**TASK.__dict__, "method": "embedding", "meta": {}})
    o = O.Oracle(FakeEmbed({"POS": [1.0, 0.0], "NEG": [0.0, 1.0], "MID": [0.7071, 0.7071]}), cache=tmp_path / "c.jsonl")
    assert o.classify(t, "POS").label == "yes"
    with pytest.raises(O.OracleUnavailable):
        o.classify(t, "MID")


def test_slm_only_method(tmp_path):
    t = O.Task(**{**TASK.__dict__, "method": "slm", "meta": {}})
    assert O.Oracle(slm=FakeSLM("yes"), cache=tmp_path / "c.jsonl").classify(t, "x").via == "slm"


def test_backend_specs_and_loopback_guard(monkeypatch):
    assert O.backend(None) is None and O.backend("off") is None
    assert isinstance(O.backend("hash"), O.HashBackend)
    assert O.backend("llamacpp:/m/x.gguf").model_id == "llamacpp:x.gguf"  # lazy: nothing imported until used
    assert O.backend("onnx:/m/minilm").model_id == "onnx:minilm"
    assert O.backend("http://127.0.0.1:8080/v1", "m").model_id == "http:m"
    monkeypatch.delenv("AGENTEST_ORACLE_ALLOW_REMOTE", raising=False)
    with pytest.raises(ValueError):
        O.backend("https://api.example.com/v1")
    with pytest.raises(ValueError):
        O.backend("cloud:whatever")


def test_unreachable_local_endpoint_is_not_assessed(tmp_path):
    o = O.Oracle(O.HttpBackend("http://127.0.0.1:9", timeout=1), cache=tmp_path / "c.jsonl")
    with pytest.raises(O.OracleUnavailable):
        o.vectors(["x"])


def test_bundled_task_loads_and_configure_from_env(monkeypatch, tmp_path):
    t = O.load_task("break-glass")
    assert t.positive in t.labels and len(t.labels) == 2 and "{text}" in t.question and "{labels}" in t.question
    monkeypatch.setenv("AGENTEST_ORACLE_EMBED", "hash")
    monkeypatch.setenv("AGENTEST_ORACLE_CACHE", str(tmp_path / "c.jsonl"))
    try:
        assert O.configure() is not None and O.describe()["oracle"]["embed"] == "hash-trigram-512"
    finally:
        monkeypatch.delenv("AGENTEST_ORACLE_EMBED")
        O.configure()
    assert O.active() is None and O.describe() == {"oracle": None}


def test_cache_file_is_json_lines_with_provenance(tmp_path):
    cache = tmp_path / "c.jsonl"
    O.Oracle(slm=FakeSLM("yes"), cache=cache).ask(TASK, "x")
    row = json.loads(cache.read_text().splitlines()[0])
    assert row["model"] == "fake-slm" and row["task"] == "t@1" and row["value"] == "yes" and len(row["key"]) == 64
