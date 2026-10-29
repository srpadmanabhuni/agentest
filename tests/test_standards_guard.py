"""CI guard: tests stay agent-agnostic. No per-agent rule/expectation files; no agent names in check code;
the legacy v1/v2 engine (per-agent YAML profiles, adapters, input-label files, v2 modules and CLI commands) never returns.
Its history is kept at the v1.0.0 and v2.0.0 tags."""

import json
import json as _json
import pathlib as _pl
import re
from pathlib import Path

import pytest

INPUTS = _json.loads((_pl.Path(__file__).parent / "fixtures" / "agent_inputs.json").read_text())  # agent inputs are data

ROOT = Path(__file__).resolve().parents[1]
STD = ROOT / "src" / "agentest" / "standards"
SAMPLE_NAMES = tuple(INPUTS["sample_names"])
FORBIDDEN_KEYS = {"expect", "expectations", "applies", "defs", "metamorphic_key", "checks", "rules", "assert"}
ID_RX = re.compile(r"\b(T[1-7]|X)-\d{3}\b")


def _agent_dirs():
    for base in (ROOT / "agents", ROOT / "examples"):
        for card in base.rglob("agent-card.json"):
            yield card.parent


STANDARD_FILES = {"agent-card.json", "tools.json", "README.md"}
TRACE_SUFFIXES = (".otlp.json", ".otlp.jsonl", ".pb", ".binpb", ".json", ".jsonl")
V2_PATHS = ("model", "real", "cases", "samples", "oracles", "golden", "matrix", "byo.py", "check.py", "profiles", "episodes",
            "agents", "config", "fixtures", "gateway.py", "policy.py")  # never inside src/agentest/standards/ either
# the only entries allowed at src/agentest/ (everything else of v1/v2 lived there: agents/, cases/, config/, fixtures/,
# model/, real/, samples/, oracles/, byo.py, env.py, gateway.py, policy.py, runner.py, types.py)
SRC_TOP = {"__init__.py", "cli.py", "paths.py", "refs.py", "standards", "__pycache__"}
# the only YAML files allowed anywhere in the repository: CI, the test-owned data tables and one catalogue pin.
# Agents are described by standard JSON (AgentCard, MCP tools/list) and OTel traces, never YAML.
YAML_ALLOWED = {".github/workflows/ci.yml", "catalog/t1_001.yaml", "src/agentest/standards/scenarios.yaml",
                "src/agentest/standards/semconv.yaml", "src/agentest/standards/standards_map.yaml"}
GUIDES_DIR = "src/agentest/standards/guides/"  # universal scoring guides (one per question; checked below to name no agent)
SKIP_DIRS = {".git", ".venv", "venv", "build", "dist", "__pycache__", ".pytest_cache", ".ruff_cache", "node_modules"}


def _files(root: Path):
    for p in root.rglob("*"):
        if p.is_file() and not (SKIP_DIRS & set(p.relative_to(root).parts)) and not any(x.endswith(".egg-info") for x in p.parts):
            yield p


def yaml_violations(root: Path) -> list[str]:
    """Per-agent YAML (v2 profiles) anywhere: any YAML file outside the allow-list, or a profiles/ folder."""
    bad = [str(p.relative_to(root)) for p in _files(root) if p.suffix in (".yaml", ".yml") and str(p.relative_to(root)) not in YAML_ALLOWED
           and not str(p.relative_to(root)).startswith(GUIDES_DIR)]
    return bad + (["profiles/"] if (root / "profiles").exists() else [])


def v2_engine_violations(root: Path) -> list[str]:
    src = root / "src" / "agentest"
    bad = [f"src/agentest/{p.name}" for p in src.iterdir() if p.name not in SRC_TOP]
    bad += [f"src/agentest/standards/{n}" for n in V2_PATHS if (src / "standards" / n).exists()]
    code = "\n".join(f.read_text(errors="replace") for f in src.rglob("*.py"))
    if re.search(r"agentest\.(model|real|cases|samples|oracles|byo|gateway|policy|env|fixtures|config|agents|types)\b", code):
        bad.append("import of a removed v1/v2 module")
    if re.search(r"\bOTLP_ONLY\b|\.adapter\b|inputs\.json|adapter\.json|episodes\.jsonl", code):
        bad.append("v2 adapter/inputs path")
    return bad



V2_CLI = ("run", "samples", "matrix", "real", "check", "golden", "byo")


def test_no_per_agent_yaml_anywhere():
    assert not yaml_violations(ROOT), f"per-agent YAML is not allowed (removed in v3.1): {yaml_violations(ROOT)}"


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
    back = v2_engine_violations(ROOT)
    assert not back, f"legacy v1/v2 engine paths are back: {back} (history lives at tags v1.0.0 / v2.0.0)"


def test_v2_cli_commands_do_not_return():
    from agentest.cli import build_parser

    p = build_parser()
    cmds = set(next(a for a in p._actions if a.__class__.__name__ == "_SubParsersAction").choices)
    assert cmds == {"list", "version", "std", "verify-trace"}, cmds
    assert not set(V2_CLI) & cmds


def _keys(o):
    if isinstance(o, dict):
        for k, v in o.items():
            yield k
            yield from _keys(v)
    elif isinstance(o, list):
        for v in o:
            yield from _keys(v)


SEEDS_EXT = "urn:agentest:a2a-ext:seeded-defects:v1"


def _scrub_seed_fixture(data):
    """Drop catalogueIds from the seeded-defects fixture extension so the no-IDs scan ignores them.

    That extension is catch-rate / viewer fixture metadata only (rules never read it). Governance params and
    every other agent file still may not name catalogue IDs.
    """
    if not isinstance(data, dict):
        return data
    out = json.loads(json.dumps(data))  # deep copy via JSON
    for ext in (out.get("capabilities") or {}).get("extensions") or []:
        if isinstance(ext, dict) and ext.get("uri") == SEEDS_EXT:
            (ext.get("params") or {}).pop("catalogueIds", None)
    return out


def test_agent_metadata_has_no_rules_or_ids():
    for d in _agent_dirs():
        for f in d.glob("*.json"):
            data = json.loads(f.read_text())
            assert not (FORBIDDEN_KEYS & set(_keys(data))), f
            assert not ID_RX.search(json.dumps(_scrub_seed_fixture(data))), (
                f"{f}: catalogue IDs belong to tests, not agent metadata "
                f"(only {SEEDS_EXT} params.catalogueIds is the fixture exception)"
            )
        assert not [p for p in d.iterdir() if p.suffix in (".yaml", ".yml")], d


def test_check_code_names_no_agent():
    agents = {d.name for d in _agent_dirs()}
    for f in sorted(STD.glob("*.py")) + [STD / "scenarios.yaml"] + sorted((STD / "guides").glob("*.yaml")):
        src = f.read_text()
        assert not re.search(r"\ba\d{2}\b", src), f"{f.name}: reference-agent id literal"
        assert not re.search(r"\.id\s*(==|!=|in\b)", src), f"{f.name}: branching on agent id"
        for n in SAMPLE_NAMES + tuple(sorted(a for a in agents if "_" in a)):
            assert not re.search(rf"[\"']{re.escape(n)}[\"']", src), f"{f.name}: names agent {n!r}"


# ---------------------------------------------------------------- the guard itself is tested: plant each removed path


def _mini_repo(tmp: Path) -> Path:
    (tmp / "src" / "agentest" / "standards").mkdir(parents=True)
    for n in ("__init__.py", "cli.py", "paths.py", "refs.py"):
        (tmp / "src" / "agentest" / n).write_text("")
    (tmp / "src" / "agentest" / "standards" / "rules.py").write_text("")
    for y in YAML_ALLOWED:
        (tmp / y).parent.mkdir(parents=True, exist_ok=True)
        (tmp / y).write_text("x: 1\n")
    assert not yaml_violations(tmp) and not v2_engine_violations(tmp)
    return tmp


V1_V2_PLANTS = ["src/agentest/agents/golden.py", "src/agentest/cases/t1.py", "src/agentest/config/thresholds.py",
                "src/agentest/fixtures/ledger.py", "src/agentest/model/profile.py", "src/agentest/real/probes.py",
                "src/agentest/samples/noop.py", "src/agentest/oracles/t1_001.py", "src/agentest/byo.py", "src/agentest/env.py",
                "src/agentest/gateway.py", "src/agentest/policy.py", "src/agentest/runner.py", "src/agentest/types.py",
                "src/agentest/standards/model/x.py", "src/agentest/standards/profiles/x.py"]


@pytest.mark.parametrize("path", V1_V2_PLANTS)
def test_guard_catches_restored_v2_module(tmp_path, path):
    root = _mini_repo(tmp_path)
    (root / path).parent.mkdir(parents=True, exist_ok=True)
    (root / path).write_text("")
    assert v2_engine_violations(root)


@pytest.mark.parametrize("src", ["from agentest.model import profile", "import agentest.real.probes", "from agentest.gateway import G",
                                 "open('inputs.json')", "p = 'adapter.json'"])
def test_guard_catches_v2_imports_and_paths(tmp_path, src):
    root = _mini_repo(tmp_path)
    (root / "src" / "agentest" / "standards" / "rules.py").write_text(src + "\n")
    assert v2_engine_violations(root)


@pytest.mark.parametrize("path", [p.format(INPUTS["profile_stem"]) for p in ("profiles/{}.yaml", "profiles/_lib/samples.yaml", "agents/{}/profile.yaml", "configs/{}.yml",
                                  "examples/x/agent.yaml", "src/agentest/standards/{}.yaml", "catalog/{}.yaml", "{}.yaml")])
def test_guard_catches_per_agent_yaml(tmp_path, path):
    root = _mini_repo(tmp_path)
    (root / path).parent.mkdir(parents=True, exist_ok=True)
    (root / path).write_text("expect: {}\n")
    assert yaml_violations(root)


# ---------------------------------------------------------------- docs do not teach removed commands

REMOVED_CMD = re.compile(r"^\s*(?:\$\s*)?agentest\s+(run|real|check|matrix|samples|model|golden|byo)\b", re.M)
FENCE = re.compile(r"^```[a-z]*\n(.*?)^```", re.S | re.M)


def test_current_docs_do_not_run_removed_commands():
    """Only docs/history/ (marked historical) and the CHANGELOG may show v1/v2 commands in code blocks."""
    bad = []
    for p in [ROOT / "README.md", *(ROOT / "docs").rglob("*.md")]:
        rel = p.relative_to(ROOT).as_posix()
        if rel.startswith("docs/history/"):
            continue
        bad += [f"{rel}: {m.group(0).strip()}" for blk in FENCE.findall(p.read_text()) for m in REMOVED_CMD.finditer(blk)]
    assert not bad, bad


def test_history_pages_are_marked_historical():
    pages = list((ROOT / "docs" / "history").glob("*.md"))
    assert pages and all("Historical (pre-v3)" in p.read_text()[:600] for p in pages)
