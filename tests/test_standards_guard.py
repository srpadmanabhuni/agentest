"""CI guard: tests stay agent-agnostic. No per-agent rule/expectation files; no agent names in check code;
the legacy v1/v2 engine (per-agent YAML profiles, adapters, input-label files, v2 modules and CLI commands) never returns.
Its history is kept at the v1.0.0 and v2.0.0 tags."""

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


STANDARD_FILES = {"agent-card.json", "tools.json", "README.md"}
TRACE_SUFFIXES = (".otlp.json", ".otlp.jsonl", ".pb", ".binpb", ".json", ".jsonl")
V2_PATHS = ("model", "real", "cases", "samples", "oracles", "golden", "matrix", "byo.py", "check.py", "profiles", "episodes")
V2_CLI = ("run", "samples", "matrix", "real", "check", "golden", "byo")


def test_no_profiles_dir():
    assert not (ROOT / "profiles").exists(), "per-agent YAML profiles are not allowed (removed in v3.1)"
    for base in (ROOT / "agents", ROOT / "examples"):
        assert not list(base.rglob("*.yaml")) and not list(base.rglob("*.yml")), "per-agent YAML is not allowed (removed in v3.1)"


def test_agent_dirs_hold_standard_files_only():
    """An agent is an A2A AgentCard, an MCP tools/list and OTel traces. Nothing agent-specific beyond that."""
    for d in _agent_dirs():
        for p in d.iterdir():
            if p.name == "__pycache__":
                continue
            if p.is_dir():
                assert p.name == "traces", f"{p}: only a traces/ folder is allowed"
                bad = [q for q in p.iterdir() if not q.name.endswith(TRACE_SUFFIXES)]
                assert not bad, bad
            elif p.suffix == ".py" and ROOT / "examples" in p.parents:
                # an example's own agent/emitter script is the agent side: it must not be test glue
                assert p.name != "adapter.py" and not re.search(r"^\s*(from|import) agentest", p.read_text(), re.M), p
            else:
                assert p.name in STANDARD_FILES or p.name.endswith((".otlp.json", ".otlp.jsonl", ".pb", ".binpb")), \
                    f"{p}: not a standard artefact (adapter.json / inputs.json / profiles were removed in v3.1)"


def test_v2_engine_code_does_not_return():
    src = ROOT / "src" / "agentest"
    back = [n for n in V2_PATHS if (src / n).exists() or (src / "standards" / n).exists()]
    assert not back, f"legacy v1/v2 engine paths are back: {back} (history lives at tags v1.0.0 / v2.0.0)"
    code = "\n".join(f.read_text() for f in src.rglob("*.py"))
    assert not re.search(r"agentest\.(model|real|cases|samples|oracles|byo)\b", code), "import of a removed v2 module"
    assert not re.search(r"\bOTLP_ONLY\b|\.adapter\b|inputs\.json|adapter\.json|episodes\.jsonl", code), "v2 adapter/inputs path"


def test_v2_cli_commands_do_not_return():
    from agentest.cli import build_parser

    p = build_parser()
    cmds = set(next(a for a in p._actions if a.__class__.__name__ == "_SubParsersAction").choices)
    assert cmds == {"list", "version", "std"}, cmds
    assert not set(V2_CLI) & cmds


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
