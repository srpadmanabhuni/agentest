"""CI guard: agentest code and test logic must not depend on any specific agent.

Fails when src/agentest/**/*.py|yaml|json or tests/**/*.py (test logic) contain an agent ID token (A\\d+ / a\\d+), an agent
folder name, an agent's card name, or a tool name declared by a bundled/example/blind agent. Data fixtures and
snapshots are excluded (tests/fixtures/, tests/schemas/, *snapshot*, fixtures/), as is this script.
29 Oct audit extension:
- scripts/*.py (generators, snapshot and blind-scoring scripts) and .github/workflows/*.yml are scanned too;
- the model families used to drive agents under test (gemma, qwen, moonlight, kimi, llama - not llama.cpp the
  runtime - mistral, phi, deepseek) must not appear in any scanned file, except the judge / oracle configuration
  (MODEL_ALLOW), where the model is the evaluator and is identical for every agent;
- CI may name a bundled example agent only in an expected-verdict assertion listed in ORACLE_ALLOW (a regression oracle
  says what the rules must output for a fixture; it changes nothing about how a rule evaluates);
- --agents-glob DIR/* adds extra agent folders (e.g. an unpublished blind round) to the vocabulary, read-only.
Usage: python scripts/agent_vocab_guard.py [--agents-glob GLOB ...]   (exit 1 on any hit)
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AGENT_DIRS = [p for g in ("agents/*", "examples/*/agents/*", "examples/*", "docs/blind/*/agents/*") for p in ROOT.glob(g)
              if (p / "agent-card.json").is_file()]
GENERIC = {"search", "lookup", "run", "get", "read", "write", "query", "send", "fetch", "handoff", "tool", "echo", "calc",
           "calculator", "add", "delete", "update", "list", "status", "approve", "reject", "transfer", "refund", "book"}


IDENT = re.compile(r"[a-z0-9]+(?:[_.][a-z0-9]+)+|[a-z]+[A-Z]\w*")  # identifier-shaped: snake_case, dotted, camelCase


def world_tools() -> set[str]:
    """Tools of agentest's own scenario worlds (standards/scenarios.yaml): agentest defines them and feeds them to every
    agent under test, so they belong to the test harness, not to any agent."""
    import yaml
    doc = yaml.safe_load((ROOT / "src/agentest/standards/scenarios.yaml").read_text())
    out: set[str] = set()
    def walk(x):
        if isinstance(x, dict):
            for k, v in x.items():
                walk(v)
                if isinstance(k, str):
                    out.add(k)
        elif isinstance(x, list):
            for v in x:
                walk(v)
        elif isinstance(x, str):
            out.update(re.findall(r"[A-Za-z_][\w.]*", x))
    walk(doc)
    return out


def vocab() -> dict[str, str]:
    v: dict[str, str] = {}
    W = world_tools()
    for d in AGENT_DIRS:
        card = json.loads((d / "agent-card.json").read_text())
        if IDENT.fullmatch(d.name) or re.search(r"\d", d.name):
            v.setdefault(d.name, f"agent folder {d.relative_to(ROOT)}")
        nm = card.get("name", "")
        if len(nm) > 3 and (" " in nm or IDENT.fullmatch(nm)):
            v.setdefault(nm, f"agent name ({d.name})")
        tj = d / "tools.json"
        if tj.is_file():
            data = json.loads(tj.read_text())
            for t in data.get("tools", data) if isinstance(data, dict) else data:
                n = t.get("name") if isinstance(t, dict) else None
                if n and n not in W and IDENT.fullmatch(n):
                    v.setdefault(n, f"tool of {d.name}")
    return v


MODEL_RX = re.compile(r"(?i)(?<![\w-])(gemma|qwen|moonlight|kimi|llama(?![\w.-]?cpp|index)|mistral|phi-?\d|deepseek)")
# the evaluator's own model (judge / oracle defaults, their CLI help, citations and docs); the same for every agent
MODEL_ALLOW = {"src/agentest/standards/judge.py", "src/agentest/standards/oracle.py", "src/agentest/cli.py",
               "src/agentest/refs.py", "scripts/gen_test_docs.py", "tests/test_v35_oracle_example.py"}
# CI only: which bundled example fixture to run and the verdicts the frozen rules must output for it (regression
# oracles); never an input to a rule
ORACLE_ALLOW = {(".github/workflows/ci.yml", w) for w in ("kyc_bot", "kyc_bot_buggy", "refill_bot", "refill_bot_buggy", "a09", "a10", "a14", "a19", "otel_plain")}


# Identifier-shaped case / scenario / desk ids from scored rounds a127–a170 (a digit, underscore or hyphen).
# Plain dictionary words that happen to be an input id are shared language and are not banned.
# Fresh held-out collections are not in this tree and are not read; --agents-glob adds a local pool.
_ROUND_BAND = range(127, 171)
_INPUT_ID_RX = re.compile(r'"key"\s*:\s*"agentest\.input\.id"\s*,\s*"value"\s*:\s*\{\s*"stringValue"\s*:\s*"([^"]+)"')
_AGENT_NAME_RX = re.compile(r'"key"\s*:\s*"gen_ai\.agent\.name"\s*,\s*"value"\s*:\s*\{\s*"stringValue"\s*:\s*"([^"]+)"')
_SPECIFIC_ID = re.compile(r"[\d_-]")


def _round_agent_dirs() -> list[Path]:
    out = []
    for d in AGENT_DIRS:
        if re.fullmatch(r"a1\d\d", d.name) and int(d.name[1:]) in _ROUND_BAND:
            out.append(d)
    return out


def _specific_id(token: str) -> bool:
    return len(token) >= 3 and bool(_SPECIFIC_ID.search(token))


def round_specific_vocab() -> dict[str, str]:
    """Case ids, scenario ids and desk ids from rounds a127–a170 that must not appear in src/.

    Agent ids and tool names are already in :func:`vocab`. This adds the identifier-shaped
    input ids (the harness case / scenario id) and hyphenated actor names (the desk id)
    recorded on those rounds. Shared probe names (``inputs.BY_NAME``) are excluded.
    """
    from agentest.standards.inputs import BY_NAME

    shared = set(BY_NAME)
    v: dict[str, str] = {}
    for d in _round_agent_dirs():
        traces = list((d / "traces").glob("*.jsonl")) + list((d / "traces").glob("*.json"))
        for t in traces:
            text = t.read_text(errors="ignore")
            for tok in _INPUT_ID_RX.findall(text):
                if _specific_id(tok) and tok not in shared:
                    v.setdefault(tok, f"case/scenario id of {d.name}")
            for tok in _AGENT_NAME_RX.findall(text):
                if tok != d.name and _specific_id(tok) and tok not in shared:
                    v.setdefault(tok, f"desk id of {d.name}")
    return v


def src_round_hits(vocab_map: dict[str, str] | None = None) -> list[str]:
    """Lines under src/ that name a round-specific case, scenario or desk id."""
    v = round_specific_vocab() if vocab_map is None else vocab_map
    if not v:
        return []
    word = {w: re.compile(rf"(?<![\w.-]){re.escape(w)}(?![\w-])") for w in v}
    hits = []
    for f in files():
        rel = str(f.relative_to(ROOT))
        if not rel.startswith("src/"):
            continue
        for i, line in enumerate(f.read_text(errors="ignore").splitlines(), 1):
            for w, r in word.items():
                if r.search(line):
                    hits.append(f"{rel}:{i}: {w!r} ({v[w]})")
    return hits


def files():
    out = [p for p in (ROOT / "src" / "agentest").rglob("*") if p.suffix in (".py", ".yaml", ".yml", ".json")]
    out += list((ROOT / "tests").rglob("*.py"))
    out += [p for p in (ROOT / "scripts").glob("*.py") if p.name != "agent_vocab_guard.py"]
    out += list((ROOT / ".github" / "workflows").glob("*.y*ml"))
    skip = ("/fixtures/", "/schemas/", "snapshot", "__pycache__", ".egg-info")
    return [p for p in out if not any(s in str(p) for s in skip)]


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--agents-glob", action="append", default=[])
    ns = ap.parse_args()
    for g in ns.agents_glob:
        AGENT_DIRS.extend(p for p in sorted(Path().glob(g) if not Path(g).is_absolute() else Path("/").glob(g.lstrip("/")))
                          if (p / "agent-card.json").is_file())
    V = vocab()
    hits, allowed = [], []
    id_re = re.compile(r"(?<![\w.-])[Aa]\d{2,3}(?![\w-])")
    word_res = {w: re.compile(rf"(?<![\w.-]){re.escape(w)}(?![\w-])") for w in V}
    for f in files():
        rel = str(f.relative_to(ROOT))
        for i, line in enumerate(f.read_text(errors="ignore").splitlines(), 1):
            for m in id_re.finditer(line):
                (allowed if (rel, m.group(0)) in ORACLE_ALLOW else hits).append(f"{rel}:{i}: agent id {m.group(0)!r}")
            for w, r in word_res.items():
                if r.search(line):
                    (allowed if (rel, w) in ORACLE_ALLOW else hits).append(f"{rel}:{i}: {w!r} ({V[w]})")
            m = MODEL_RX.search(line)
            if m and rel not in MODEL_ALLOW:
                hits.append(f"{rel}:{i}: model string {m.group(0)!r}")
    round_vocab = round_specific_vocab()
    round_hits = src_round_hits(round_vocab)
    hits.extend(round_hits)
    print(f"agent-vocab guard: {len(V)} agent identifiers from {len(AGENT_DIRS)} agents; {len(files())} files scanned "
          f"(src, tests, scripts, CI); model strings checked; {len(round_vocab)} round case/desk ids checked in src/; "
          f"{len(hits)} hits; {len(allowed)} allow-listed CI oracle lines")
    for h in hits[:600]:
        print("  " + h)
    for h in allowed:
        print("  allowed (CI expected-verdict oracle): " + h)
    return 1 if hits else 0


if __name__ == "__main__":
    sys.exit(main())
