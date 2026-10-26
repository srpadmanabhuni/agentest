"""Model-driven (v2.0.0-dev) checks: trace schema, adapters, profiles, generic checks, generator, parity."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

pytest.importorskip("yaml")

from agentest.cli import main  # noqa: E402
from agentest.model.adapters import adapt  # noqa: E402
from agentest.model.generator import generate  # noqa: E402
from agentest.model.generic import PORTED_IDS, evaluate  # noqa: E402
from agentest.model.profile import Profile, get_path, load, load_all  # noqa: E402
from agentest.model.runner import parity, run_all, traces, v1_results  # noqa: E402
from agentest.model.trace import Episode, validate  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
EX = ROOT / "examples" / "model_driven"


@pytest.fixture(scope="module")
def profiles():
    return load_all()


@pytest.fixture(scope="module")
def gen(profiles):
    return run_all(profiles)


def test_one_profile_per_agent(profiles):
    assert len(profiles) == 40
    assert {f"a{i:02d}" for i in range(1, 26)} <= set(profiles)


def test_every_episode_converts_and_validates(profiles):
    n = 0
    for p in profiles.values():
        for e in traces(p):
            n += 1
            assert validate(e.to_dict()) == [], (p.agent, e.probe)
            assert Episode.from_dict(json.loads(json.dumps(e.to_dict(), default=str))).probe == e.probe
    assert n > 300


@pytest.mark.parametrize("agent,tool", [("a05", "request_refund"), ("a06", "send_email"), ("a07", "run_select"), ("a13", "issue_credit_note"), ("a16", "get_stock"), ("a25", "runbook_execute")])
def test_adapters_extract_tool_calls(profiles, agent, tool):
    names = {c.name for e in traces(profiles[agent]) for c in e.tool_calls}
    assert tool in names


def test_side_effect_from_profile(profiles):
    e = traces(profiles["a05"])[0]
    assert {c.name: c.side_effect for c in e.tool_calls}["request_refund"] == "write"


def test_generic_checks_have_no_agent_ids():
    src = (ROOT / "src" / "agentest" / "model" / "generic.py").read_text()
    for i in range(1, 26):
        assert f'"a{i:02d}"' not in src


def test_matrix_shape(gen):
    assert all(set(r) == set(PORTED_IDS) for r in gen.values())
    assert len(PORTED_IDS) >= 15


def test_known_defects_still_caught(gen):
    assert gen["eager"]["T2-003"].status == "fail"
    assert gen["eager"]["T1-013"].status == "fail"
    assert gen["leaky"]["T4-009"].status == "fail"
    assert gen["scripted"]["T4-009"].status == "pass"


def test_parity_agreement_floor(gen):
    par = parity(gen, v1_results())
    assert par["tally"]["agree"] / par["comparable"] >= 0.9


def test_new_agent_with_only_yaml():
    p = load(EX / "expense_bot.yaml")
    r = evaluate(p, traces(p))
    assert r["T1-001"].status == "pass"
    assert r["T3-001"].status == "fail"  # deliberate defect in the example
    assert r["T2-004"].status == "fail"
    assert r["T6-007"].status == "n/a"  # no retrieval capability -> N/A automatically


def test_capability_drives_applicability():
    p = Profile(agent="x", adapter="steps")
    r = evaluate(p, [adapt({"agent": "x", "probe": "canon", "trace": [], "output": {}}, p)])
    assert {v.status for v in r.values()} == {"n/a"}


def test_generator_covers_profile():
    p = load(EX / "expense_bot.yaml")
    cases = generate(p, ["File my taxi expense of INR 640."])
    roles = {c["role"] for c in cases}
    assert {"metamorphic", "injection", "social", "limit", "empty", "pii"} <= roles
    assert any("CANARY-EXP" in c["input"] for c in cases)


def test_get_path():
    assert get_path({"a": [{"b": 1}]}, "a.0.b") == 1
    assert get_path({"a": [1, 2]}, "a.-1") == 2
    assert get_path({}, "x.y") is None


def test_unknown_profile_key_rejected(tmp_path):
    f = tmp_path / "bad.yaml"
    f.write_text("agent: z\nadapter: steps\ntypo_key: 1\n")
    with pytest.raises(ValueError):
        load(f)


def test_cli(tmp_path, capsys):
    assert main(["model", "validate"]) == 0
    assert main(["model", "run", "--profiles", str(EX), "--json", str(tmp_path / "r.json")]) == 0
    assert json.loads((tmp_path / "r.json").read_text())["expense_bot"]["T3-001"]["status"] == "fail"
    assert main(["model", "generate", "--profiles", str(EX), "--agent", "expense_bot", "--seed", "hi"]) == 0
