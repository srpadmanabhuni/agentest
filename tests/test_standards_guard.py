"""CI guard: tests stay agent-agnostic. No per-agent rule/expectation files; no agent names in check code."""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STD = ROOT / "src" / "agentest" / "standards"
SAMPLE_NAMES = ("leaky", "noop", "eager", "biased", "federation", "flaky_plan", "hallucinator", "overreach", "reflective",
                "refill", "expense_bot")
FORBIDDEN_KEYS = {"expect", "expectations", "applies", "defs", "metamorphic_key", "checks", "rules", "assert"}
ID_RX = re.compile(r"\b(T[1-7]|X)-\d{3}\b")


def _agent_dirs():
    for base in (ROOT / "agents", ROOT / "examples"):
        for card in base.rglob("agent-card.json"):
            yield card.parent


def test_no_profiles_dir():
    assert not (ROOT / "profiles").exists(), "per-agent YAML profiles are not allowed (v3)"
    assert not list((ROOT / "examples").rglob("*.yaml")), "per-agent YAML profiles are not allowed (v3)"


def _keys(o):
    if isinstance(o, dict):
        for k, v in o.items():
            yield k
            yield from _keys(v)
    elif isinstance(o, list):
        for v in o:
            yield from _keys(v)


def test_agent_metadata_has_no_rules_or_ids():
    for d in _agent_dirs():
        for f in d.glob("*.json"):
            assert not (FORBIDDEN_KEYS & set(_keys(json.loads(f.read_text())))), f
            # inputs.json may name a conformance-scenario input after the scenario it replays; nothing else may cite IDs
            if f.name != "inputs.json":
                assert not ID_RX.search(f.read_text()), f"{f}: catalogue IDs belong to tests, not agent metadata"
        assert not [p for p in d.iterdir() if p.suffix in (".yaml", ".yml")], d


def test_check_code_names_no_agent():
    agents = {d.name for d in _agent_dirs()}
    for f in sorted(STD.glob("*.py")) + [STD / "scenarios.yaml"]:
        src = f.read_text()
        assert not re.search(r"\ba\d{2}\b", src), f"{f.name}: reference-agent id literal"
        assert not re.search(r"\.id\s*(==|!=|in\b)", src), f"{f.name}: branching on agent id"
        for n in SAMPLE_NAMES + tuple(sorted(a for a in agents if "_" in a)):
            assert not re.search(rf"[\"']{re.escape(n)}[\"']", src), f"{f.name}: names agent {n!r}"
