"""CI guard: agentest code and test logic must not depend on any specific agent.

Also rejects, inside src/ only, a desk id, scenario id or case id taken from rounds a127–a170
(and from any later round folder of that shape that is present in the tree). Tool names of those
rounds are already covered by the agent-card vocabulary below. The harness's own input-family
names (standards/inputs.py, scenarios.yaml) are not round-specific and are not flagged.


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


ROUND_DIR = re.compile(r"^a1(?:2[7-9]|[3-6]\d|70)$")
CASE_RX = re.compile(r"\b[A-Z]{2,5}-\d{2,}\b")
CATALOGUE_RX = re.compile(r"^(?:T[1-7]|X)-\d{3}$")
SCENARIO_RX = re.compile(r"^[A-Za-z][A-Za-z0-9]*([_-][A-Za-z0-9]+)+$")
_INPUT_ID = re.compile(r'agentest\.input\.id"\s*,\s*"value"\s*:\s*\{\s*"stringValue"\s*:\s*"([^"]+)"')


def round_agent_dirs() -> list[Path]:
    """Agent folders a127–a170. Held-out pools are included when they are in the tree; fresh collections are not sought."""
    found = []
    for card in ROOT.rglob("agent-card.json"):
        rel = str(card.relative_to(ROOT))
        if "fresh-0911" in rel or "fresh-batch2" in rel:
            continue
        if ROUND_DIR.match(card.parent.name):
            found.append(card.parent)
    return found


def _harness_tokens() -> set[str]:
    """Input-family names the harness itself declares. They are not a round's private vocabulary."""
    chunks = []
    for rel in ("src/agentest/standards/inputs.py", "src/agentest/standards/scenarios.yaml"):
        p = ROOT / rel
        if p.is_file():
            chunks.append(p.read_text(errors="ignore"))
    return set(re.findall(r"[A-Za-z0-9][A-Za-z0-9_-]{2,}", "\n".join(chunks)))


def round_tokens() -> dict[str, str]:
    """Desk ids, scenario ids and case ids from rounds a127–a170."""
    harness = _harness_tokens()
    out: dict[str, str] = {}
    for d in round_agent_dirs():
        try:
            card = json.loads((d / "agent-card.json").read_text())
        except (OSError, ValueError):
            continue
        gov: dict = {}
        for ext in ((card.get("capabilities") or {}).get("extensions") or []):
            if isinstance(ext, dict) and "governance" in str(ext.get("uri", "")):
                gov = ext.get("params") or {}
        roles = gov.get("roles") or {}
        names = list(roles.get("orchestrators") or []) + list(roles.get("actors") or {})
        for name in names:
            if isinstance(name, str) and ("-" in name or "_" in name) and len(name) >= 5 and name not in harness:
                out.setdefault(name, f"desk id ({d.name})")
        traces = d / "traces"
        if not traces.is_dir():
            continue
        for f in traces.iterdir():
            if not f.is_file():
                continue
            text = f.read_text(errors="ignore")
            for sid in _INPUT_ID.findall(text):
                if CATALOGUE_RX.match(sid) or not SCENARIO_RX.match(sid) or sid in harness:
                    continue
                out.setdefault(sid, f"scenario id ({d.name})")
            for cid in CASE_RX.findall(text):
                if cid not in harness:
                    out.setdefault(cid, f"case id ({d.name})")
    return out


def src_tree() -> list[Path]:
    return [p for p in (ROOT / "src" / "agentest").rglob("*") if p.suffix in (".py", ".yaml", ".yml", ".json")]


def round_hits(paths: list[Path] | None = None, tokens: dict[str, str] | None = None) -> list[str]:
    """Lines in src/ that name a round's desk, scenario or case id. Harness vocabulary files are skipped."""
    tokens = round_tokens() if tokens is None else tokens
    skip = {"src/agentest/standards/inputs.py", "src/agentest/standards/scenarios.yaml"}
    word = {w: re.compile(rf"(?<![\w.-]){re.escape(w)}(?![\w-])") for w in tokens}
    hits = []
    for f in paths if paths is not None else src_tree():
        try:
            rel = str(f.relative_to(ROOT))
        except ValueError:
            rel = str(f)
        if rel in skip:
            continue
        try:
            lines = f.read_text(errors="ignore").splitlines()
        except OSError:
            continue
        for i, line in enumerate(lines, 1):
            for w, rx in word.items():
                if rx.search(line):
                    hits.append(f"{rel}:{i}: {w!r} ({tokens[w]})")
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
    round_v = round_tokens()
    rh = round_hits(src_tree(), round_v)
    hits += rh
    print(f"agent-vocab guard: {len(V)} agent identifiers from {len(AGENT_DIRS)} agents; {len(files())} files scanned "
          f"(src, tests, scripts, CI); model strings checked; {len(round_v)} round desk/scenario/case ids checked in src; "
          f"{len(hits)} hits; {len(allowed)} allow-listed CI oracle lines")
    for h in hits[:600]:
        print("  " + h)
    for h in allowed:
        print("  allowed (CI expected-verdict oracle): " + h)
    return 1 if hits else 0


if __name__ == "__main__":
    sys.exit(main())
