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
# Scored-round case / scenario tokens (src/ only). Probe vocabulary such as b1_pos stays; function names such as _cf_sig do not match.
ROUND_CASE_RX = re.compile(r"(?<![\w.-])(?:c\d+-\d+|conv-\d+|(?:kn|bn|hi|ta)-big|cf_gender)(?![\w-])")


def round_case_hits(rel: str, line: str) -> list[str]:
    """Case and scenario ids from scored rounds are not allowed in src/."""
    if not rel.startswith("src/"):
        return []
    return [m.group(0) for m in ROUND_CASE_RX.finditer(line)]


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


def files():
    out = [p for p in (ROOT / "src" / "agentest").rglob("*") if p.suffix in (".py", ".yaml", ".yml", ".json")]
    out += list((ROOT / "tests").rglob("*.py"))
    out += [p for p in (ROOT / "scripts").glob("*.py") if p.name != "agent_vocab_guard.py"]
    out += list((ROOT / ".github" / "workflows").glob("*.y*ml"))
    skip = ("/fixtures/", "/schemas/", "snapshot", "__pycache__", ".egg-info")
    return [p for p in out if not any(s in str(p) for s in skip)]


def case_ids() -> dict[str, str]:
    """Scenario / case ids from already-scored rounds (input ids that are not plain words or catalogue ids).

    Detectors must not branch on these. Plain words and catalogue ids are left out: those strings are the
    shared input-family vocabulary, not a round's case name.
    """
    found: dict[str, str] = {}
    rx = re.compile(r"agentest\.input\.id.{0,160}?stringValue\"\s*:\s*\"([^\"]+)\"", re.S)
    cat = re.compile(r"^[TX]\d+-\d+$")
    for p in (ROOT / "docs" / "blind").glob("r*/agents/**/*"):
        if not p.is_file() or p.suffix not in {".json", ".jsonl"}:
            continue
        try:
            text = p.read_text(errors="ignore")
        except OSError:
            continue
        if "agentest.input.id" not in text:
            continue
        for m in rx.finditer(text):
            cid = m.group(1)
            if len(cid) >= 4 and re.search(r"[\d_-]", cid) and not cat.match(cid):
                found.setdefault(cid, f"case id in {p.relative_to(ROOT)}")
    return found


# --- round desk / scenario / case ids (r13). Each family's test calls the name it added. ---

_ROUND_BAND = range(127, 171)
_SPECIFIC_ID = re.compile(r"[\d_-]")
_INPUT_ID_RX = re.compile(r'"key"\s*:\s*"agentest\.input\.id"\s*,\s*"value"\s*:\s*\{\s*"stringValue"\s*:\s*"([^"]+)"')
_AGENT_NAME_RX = re.compile(r'"key"\s*:\s*"gen_ai\.agent\.name"\s*,\s*"value"\s*:\s*\{\s*"stringValue"\s*:\s*"([^"]+)"')
_CASE_RX = re.compile(r"\b[A-Z]{2,5}-\d{2,}\b")
ROUND_DIR = re.compile(r"^a1(?:2[7-9]|[3-6]\d|70)$")
CATALOGUE_RX = re.compile(r"^(?:T[1-7]|X)-\d{3}$")
SCENARIO_RX = re.compile(r"^[A-Za-z][A-Za-z0-9]*([_-][A-Za-z0-9]+)+$")


def _round_agent_dirs() -> list[Path]:
    return [d for d in AGENT_DIRS if re.fullmatch(r"a1\d\d", d.name) and int(d.name[1:]) in _ROUND_BAND]


def _specific_id(token: str) -> bool:
    return len(token) >= 3 and bool(_SPECIFIC_ID.search(token))


def round_specific_vocab() -> dict[str, str]:
    """Case ids, scenario ids and desk ids from rounds a127–a170."""
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
            for w, rx in word.items():
                if rx.search(line):
                    hits.append(f"{rel}:{i}: {w!r} ({v[w]})")
    return hits


def _distinctive(token: str) -> bool:
    return len(token) >= 4 and any(ch.isalpha() for ch in token) and any(ch.isdigit() or ch in "_-" for ch in token)


def _harness_ids() -> set[str]:
    try:
        from agentest.standards.inputs import BY_NAME, RELATIONS
    except Exception:
        return set()
    ids = set(BY_NAME)
    for _name, members, _kind in RELATIONS:
        ids.update(members)
    return ids


def round_identifiers() -> dict[str, str]:
    """Desk skill ids and case ids from already-scored rounds."""
    harness = _harness_ids()
    out: dict[str, str] = {}
    for card in ROOT.glob("docs/blind/*/agents/*/agent-card.json"):
        try:
            data = json.loads(card.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        for skill in data.get("skills") or []:
            sid = str(skill.get("id") or "")
            if _distinctive(sid) and sid not in harness:
                out.setdefault(sid, f"desk id ({card.parent.name})")
    for trace in ROOT.glob("docs/blind/*/agents/*/traces/*"):
        if trace.suffix not in (".json", ".jsonl"):
            continue
        try:
            text = trace.read_text(errors="ignore")
        except OSError:
            continue
        for found in re.findall(r'"key": "agentest\.input\.id", "value": \{"stringValue": "([^"]+)"\}', text):
            if _distinctive(found) and found not in harness:
                out.setdefault(found, f"case id ({trace.parent.parent.name})")
    return out


def line_hits(line: str, words: dict[str, str] | None = None) -> list[str]:
    V = vocab() if words is None else words
    found = []
    for m in re.finditer(r"(?<![\w.-])[Aa]\d{2,3}(?![\w-])", line):
        found.append(m.group(0))
    for w in V:
        if re.search(rf"(?<![\w.-]){re.escape(w)}(?![\w-])", line):
            found.append(w)
    return found


def round_agent_dirs() -> list[Path]:
    found = []
    for card in ROOT.rglob("agent-card.json"):
        rel = str(card.relative_to(ROOT))
        if "fresh-0911" in rel or "fresh-batch2" in rel:
            continue
        if ROUND_DIR.match(card.parent.name):
            found.append(card.parent)
    return found


def _harness_tokens() -> set[str]:
    chunks = []
    for rel in ("src/agentest/standards/inputs.py", "src/agentest/standards/scenarios.yaml"):
        p = ROOT / rel
        if p.is_file():
            chunks.append(p.read_text(errors="ignore"))
    return set(re.findall(r"[A-Za-z0-9][A-Za-z0-9_-]{2,}", "\n".join(chunks)))


def round_tokens() -> dict[str, str]:
    """Desk, scenario and case ids from rounds a127–a170."""
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
            for sid in _INPUT_ID_RX.findall(text):
                if CATALOGUE_RX.match(sid) or not SCENARIO_RX.match(sid) or sid in harness:
                    continue
                out.setdefault(sid, f"scenario id ({d.name})")
            for cid in _CASE_RX.findall(text):
                if cid not in harness:
                    out.setdefault(cid, f"case id ({d.name})")
    return out


def src_tree() -> list[Path]:
    return [p for p in (ROOT / "src" / "agentest").rglob("*") if p.suffix in (".py", ".yaml", ".yml", ".json")]


def round_hits(paths: list[Path] | None = None, tokens: dict[str, str] | None = None) -> list[str]:
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


def round_src_hits() -> list[str]:
    return round_hits(src_tree(), round_tokens())


def round_terms() -> dict[str, str]:
    from agentest.standards.inputs import BY_NAME

    terms: dict[str, str] = {}

    def keep(token: str, why: str) -> None:
        if not token or len(token) < 4 or re.fullmatch(r"[a-z]+", token) or token in BY_NAME:
            return
        terms.setdefault(token, why)

    for d in round_agent_dirs():
        if not (d / "agent-card.json").is_file():
            continue
        card = json.loads((d / "agent-card.json").read_text())
        gov = next((e.get("params") or {} for e in card.get("capabilities", {}).get("extensions", [])
                    if isinstance(e, dict) and "governance" in str(e.get("uri", ""))), {})
        roles = gov.get("roles") or {}
        for name in list(roles.get("orchestrators") or []) + list((roles.get("actors") or {}).keys()):
            keep(str(name), f"desk id ({d.name})")
        for trace in list((d / "traces").glob("*.json")) + list((d / "traces").glob("*.jsonl")):
            text = trace.read_text(errors="ignore")
            for scen in _INPUT_ID_RX.findall(text):
                keep(scen, f"scenario id ({d.name})")
            for case in _CASE_RX.findall(text):
                keep(case, f"case id ({d.name})")
    return terms


def _agent_num(name: str) -> int | None:
    if re.fullmatch(r"[Aa]\d{2,3}", name):
        return int(name[1:])
    return None


def round_vocab() -> dict[str, str]:
    """Scenario ids, case ids and desk ids from scored rounds a127-a170."""
    out: dict[str, str] = {}
    id_rx = re.compile(r"\b[A-Z]{2,5}-\d{3,}\b")
    for card in ROOT.glob("docs/blind/r*/agents/*/agent-card.json"):
        n = _agent_num(card.parent.name)
        if n is None or not 127 <= n <= 170:
            continue
        try:
            data = json.loads(card.read_text())
        except ValueError:
            continue
        for skill in data.get("skills") or []:
            sid = str(skill.get("id") or "")
            if re.search(r"[\d_-]", sid) and len(sid) >= 4:
                out.setdefault(sid, f"desk/skill id of {card.parent.name}")
        traces = card.parent / "traces"
        if not traces.is_dir():
            continue
        for trace in traces.iterdir():
            if trace.suffix not in {".json", ".jsonl"}:
                continue
            text = trace.read_text(errors="ignore")
            for sid in _INPUT_ID_RX.findall(text):
                if len(sid) >= 4 and re.search(r"[\d_-]", sid):
                    out.setdefault(sid, f"scenario id of {card.parent.name}")
            for case in id_rx.findall(text):
                out.setdefault(case, f"case id of {card.parent.name}")
    return out


def round_case_ids() -> dict[str, str]:
    """Input ids from already-scored rounds. A case or scenario id carries a letter and a digit, or an underscore."""
    out: dict[str, str] = {}
    root = ROOT / "docs" / "blind"
    if not root.is_dir():
        return out
    for path in list(root.glob("r*/agents/*/traces/*")) + list(root.rglob("*.otlp.jsonl")):
        if path.suffix not in {".json", ".jsonl"}:
            continue
        if "/agents/" not in str(path).replace("\\", "/"):
            continue
        try:
            text = path.read_text(errors="ignore")
        except OSError:
            continue
        for tok in _INPUT_ID_RX.findall(text):
            if len(tok) < 4:
                continue
            digit = any(ch.isdigit() for ch in tok)
            if not ((re.search(r"[A-Za-z]", tok) and digit) or "_" in tok):
                continue
            if re.fullmatch(r"[TX]\d?-\d+", tok) or re.fullmatch(r"T\d-\d{3}", tok) or CATALOGUE_RX.match(tok):
                continue
            out.setdefault(tok, "case id from a scored round")
    return out


def detector_round_ids() -> list[str]:
    """Scenario ids and case ids from scored-round traces must not appear in detectors/."""
    id_rx = re.compile(r'"key"\s*:\s*"agentest\.input\.id"\s*,\s*"value"\s*:\s*\{\s*"stringValue"\s*:\s*"([^"]+)"')
    case_rx = re.compile(r"\b[A-Z]{2,5}-\d{3,}\b")
    scen, cases = set(), set()
    for p in (ROOT / "docs" / "blind").glob("r*/agents/*/traces/*"):
        if not p.is_file():
            continue
        text = p.read_text(errors="ignore")
        scen.update(x for x in id_rx.findall(text) if len(x) >= 4 and re.search(r"[\d_#\-]", x))
        cases.update(case_rx.findall(text[:400_000]))
    det = ROOT / "src" / "agentest" / "standards" / "detectors"
    hits = []
    if not det.is_dir():
        return hits
    for f in det.rglob("*.py"):
        body = f.read_text(errors="ignore")
        rel = str(f.relative_to(ROOT))
        for i, line in enumerate(body.splitlines(), 1):
            for tok in scen:
                if re.search(rf"(?<![\w.-]){re.escape(tok)}(?![\w.-])", line):
                    hits.append(f"{rel}:{i}: round scenario id {tok!r}")
            for tok in case_rx.findall(line):
                if tok in cases:
                    hits.append(f"{rel}:{i}: round case id {tok!r}")
    return hits


def _src_word_hits(words: dict[str, str]) -> list[str]:
    if not words:
        return []
    word = {w: re.compile(rf"(?<![\w.-]){re.escape(w)}(?![\w-])") for w in words}
    hits = []
    for f in src_tree():
        rel = str(f.relative_to(ROOT))
        for i, line in enumerate(f.read_text(errors="ignore").splitlines(), 1):
            for w, rx in word.items():
                if rx.search(line):
                    hits.append(f"{rel}:{i}: {w!r} ({words[w]})")
    return hits


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
            hits += [f"{rel}:{i}: round case id {token!r}" for token in round_case_hits(rel, line)]
            for w, r in word_res.items():
                if r.search(line):
                    (allowed if (rel, w) in ORACLE_ALLOW else hits).append(f"{rel}:{i}: {w!r} ({V[w]})")
            m = MODEL_RX.search(line)
            if m and rel not in MODEL_ALLOW:
                hits.append(f"{rel}:{i}: model string {m.group(0)!r}")
    cases = case_ids()
    case_re = {w: re.compile(rf"(?<![\w.-]){re.escape(w)}(?![\w-])") for w in cases}
    src_files = [p for p in files() if str(p.relative_to(ROOT)).startswith("src/")]
    for f in src_files:
        rel = str(f.relative_to(ROOT))
        for i, line in enumerate(f.read_text(errors="ignore").splitlines(), 1):
            for w, r in case_re.items():
                if r.search(line):
                    hits.append(f"{rel}:{i}: case id {w!r} ({cases[w]})")
    hits.extend(src_round_hits())
    hits.extend(round_hits())
    hits.extend(_src_word_hits(round_identifiers()))
    hits.extend(_src_word_hits(round_terms()))
    hits.extend(_src_word_hits(round_vocab()))
    hits.extend(_src_word_hits(round_case_ids()))
    hits.extend(detector_round_ids())
    print(f"agent-vocab guard: {len(V)} agent identifiers from {len(AGENT_DIRS)} agents; {len(files())} files scanned "
          f"(src, tests, scripts, CI); model strings checked; {len(cases)} round case ids checked in src; "
          f"{len(hits)} hits; {len(allowed)} allow-listed CI oracle lines")
    for h in hits[:600]:
        print("  " + h)
    for h in allowed:
        print("  allowed (CI expected-verdict oracle): " + h)
    return 1 if hits else 0


if __name__ == "__main__":
    sys.exit(main())
