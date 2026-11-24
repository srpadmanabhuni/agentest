"""The multi-agent reference examples: controls stay clean, every seeded trace fails its check, and the files are current."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from agentest.cli import main
from agentest.standards import metadata, runner
from agentest.standards.packs import PACK_IDS, pack_ids
from agentest.standards.rules import evaluate

ROOT = Path(__file__).resolve().parents[1]
EX = ROOT / "examples" / "multi_agent"
spec = importlib.util.spec_from_file_location("gen_multiagent_examples", ROOT / "scripts" / "gen_multiagent_examples.py")
gen = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gen)
AGENTS = metadata.load_all(EX)


def test_examples_are_current():
    stale = [str(p.relative_to(ROOT)) for p, t in gen.build().items() if not p.exists() or p.read_text() != t]
    assert not stale, f"run: python scripts/gen_multiagent_examples.py ({stale})"


def test_example_agents_are_valid_and_complete():
    assert set(AGENTS) == {"triage_team_clean", "triage_team_seeded", "handoff_chain_clean", "handoff_chain_seeded"}
    assert all(not metadata.validate(a) for a in AGENTS.values())
    assert sum(len(runner.runs(a)) for a in AGENTS.values()) == 5 + 13 + 2 + 4


@pytest.mark.parametrize("name", ["triage_team_clean", "handoff_chain_clean"])
def test_controls_fail_no_pack_check(name):
    a = AGENTS[name]
    out = evaluate(a, runner.runs(a), ids=sorted(PACK_IDS))
    assert {i: r.detail for i, r in out.items() if r.status == "fail"} == {}
    assert sum(r.status == "pass" for r in out.values()) >= 8


def _seeded():
    for name in ("triage_team_seeded", "handoff_chain_seeded"):
        _, _, _, builders = gen.AGENTS[name]
        for b, run in zip(builders, runner.runs(AGENTS[name]), strict=True):
            yield pytest.param(name, run, gen.SEED[b.__name__][0], id=run.input_id)


@pytest.mark.parametrize("name,run,check", list(_seeded()))
def test_each_seeded_trace_fails_its_check(name, run, check):
    out = evaluate(AGENTS[name], [run], ids=pack_ids("ma"))
    assert out[check].status == "fail", (check, out[check])
    others = {i for i, r in out.items() if r.status == "fail"} - {check}
    assert others <= {"MA-002"}, others  # only the undeclared-edge companion of a loop is allowed


def test_all_thirteen_ma_checks_are_exercised_by_a_seed():
    assert {c for c, _ in gen.SEED.values()} == set(pack_ids("ma"))


def test_cli_pack_ma_on_the_examples(capsys):
    assert main(["std", "run", "--agents", str(EX), "--agent", "triage_team_clean", "--pack", "ma", "--strict"]) == 0
    assert main(["std", "run", "--agents", str(EX), "--agent", "triage_team_seeded", "--pack", "ma", "--strict"]) == 1
    capsys.readouterr()
