"""Count regex-final checks in the rule modules: regular expressions that could decide a verdict on their own.

Every compiled pattern (``X = re.compile(...)``) and every inline ``re.search/match/fullmatch/findall/finditer/sub``
call with a literal pattern in ``agentest/standards/rules.py``, ``agentest/standards/detectors/*.py`` and ``packs.py``
is classified. A pattern listed in ``FORMAT_VALIDATORS`` (machine formats: ids, emails, URLs, JSON fields) or
``PREFILTERS`` (narrows which spans are examined), or a local / inline pattern whose statement carries a ``# rx: format``
or ``# rx: prefilter`` marker, is not regex-final; anything else is counted. Target: 0.
Usage: python scripts/regex_final_count.py [--json]
"""
from __future__ import annotations

import ast
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RULES = ROOT / "src" / "agentest" / "standards" / "rules.py"
PACKS = ROOT / "src" / "agentest" / "standards" / "packs.py"  # v4.0-packs: scanned too, same markers
CALLS = {"search", "match", "fullmatch", "findall", "finditer", "sub", "subn", "split", "compile"}


def _tuple_names(tree: ast.Module, name: str) -> set[str]:
    for n in tree.body:
        if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == name for t in n.targets):
            return {e.value for e in getattr(n.value, "elts", []) if isinstance(e, ast.Constant)}
    return set()


def rule_paths() -> list[Path]:
    """Rule modules the classifier walks: the facade, every detector module, and the packs."""
    det = RULES.parent / "detectors"
    paths = [RULES]
    if det.is_dir():
        paths += sorted(p for p in det.glob("*.py") if p.name != "__init__.py")
    if PACKS.exists() and PACKS not in paths:
        paths.append(PACKS)
    return paths


def _scan_one(path: Path) -> dict:
    src = path.read_text(encoding="utf-8")
    lines = src.split("\n")
    tree = ast.parse(src)

    def tag(n) -> str:  # a "# rx: format" / "# rx: prefilter" marker on the statement classifies a local/inline pattern
        txt = " ".join(lines[n.lineno - 1:(n.end_lineno or n.lineno)])
        return "format" if "rx: format" in txt else "prefilter" if "rx: prefilter" in txt else ""
    allowed = {"format": _tuple_names(tree, "FORMAT_VALIDATORS"), "prefilter": _tuple_names(tree, "PREFILTERS")}
    compiled, inline, marked = {}, [], {"format": 0, "prefilter": 0}
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
            f = node.value.func
            if isinstance(f, ast.Attribute) and f.attr == "compile" and getattr(f.value, "id", "") == "re":
                for t in node.targets:
                    if isinstance(t, ast.Name):
                        compiled[t.id] = node.lineno
                        if tag(node):
                            allowed[tag(node)].add(t.id)
        elif isinstance(node, ast.Call):
            f = node.func
            if (isinstance(f, ast.Attribute) and f.attr in CALLS and f.attr != "compile" and getattr(f.value, "id", "") == "re"
                    and node.args and isinstance(node.args[0], ast.Constant)):
                if tag(node):
                    marked[tag(node)] += 1
                else:
                    inline.append(node.lineno)
    return {"_file": path.name, "_compiled": compiled, "_inline": inline, "inline_marked": marked,
            "_allowed_format": set(allowed["format"]), "_allowed_prefilter": set(allowed["prefilter"])}


def _report(parts: list[dict]) -> dict:
    """Classify compiled names against the union of declarations, so a pattern declared in one module and compiled in another is not regex-final."""
    fmt_names = set().union(*(p["_allowed_format"] for p in parts)) if parts else set()
    pre_names = set().union(*(p["_allowed_prefilter"] for p in parts)) if parts else set()
    found, fmt, pre, final = set(), [], [], []
    marked = {"format": 0, "prefilter": 0}
    for p in parts:
        for n, ln in p["_compiled"].items():
            found.add(n)
            if n in fmt_names:
                fmt.append(n)
            elif n in pre_names:
                pre.append(n)
            else:
                final.append(f"{p['_file']}: {n} (line {ln})")
        final += [f"{p['_file']}: inline re.* (line {ln})" for ln in p["_inline"]]
        for k in marked:
            marked[k] += p["inline_marked"][k]
    return {"compiled": sum(len(p["_compiled"]) for p in parts), "format_validators": sorted(fmt),
            "prefilters": sorted(pre), "regex_final": sorted(final), "regex_final_count": len(final),
            "inline_marked": marked, "declared_but_missing": sorted((fmt_names | pre_names) - found)}


def scan(path: Path | None = None) -> dict:
    """Classify one module, or every rule module when ``path`` is omitted."""
    paths = [path] if path is not None else rule_paths()
    return _report([_scan_one(p) for p in paths if p.exists()])


if __name__ == "__main__":
    r = scan()
    if "--json" in sys.argv:
        print(json.dumps(r, indent=2))
    else:
        print(f"compiled patterns: {r['compiled']}  format validators: {len(r['format_validators'])}  "
              f"pre-filters: {len(r['prefilters'])}  regex-final: {r['regex_final_count']}")
        for x in r["regex_final"]:
            print("  regex-final:", x)
    sys.exit(1 if r["regex_final_count"] else 0)
