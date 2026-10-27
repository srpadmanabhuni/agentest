"""Count regex-final checks in the rule modules: regular expressions that could decide a verdict on their own.

Every compiled pattern (``X = re.compile(...)``) and every inline ``re.search/match/fullmatch/findall/finditer/sub``
call with a literal pattern in ``agentest/standards/rules.py`` is classified. A pattern listed in ``FORMAT_VALIDATORS``
(machine formats: ids, emails, URLs, JSON fields) or ``PREFILTERS`` (narrows which spans are examined), or a local /
inline pattern whose statement carries a ``# rx: format`` or ``# rx: prefilter`` marker, is not regex-final; anything
else is counted. Target: 0.  Usage: python scripts/regex_final_count.py [--json]
"""
from __future__ import annotations

import ast
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RULES = ROOT / "src" / "agentest" / "standards" / "rules.py"
CALLS = {"search", "match", "fullmatch", "findall", "finditer", "sub", "subn", "split", "compile"}


def _tuple_names(tree: ast.Module, name: str) -> set[str]:
    for n in tree.body:
        if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == name for t in n.targets):
            return {e.value for e in getattr(n.value, "elts", []) if isinstance(e, ast.Constant)}
    return set()


def scan(path: Path = RULES) -> dict:
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
    kind = {n: ("format" if n in allowed["format"] else "prefilter" if n in allowed["prefilter"] else "regex-final") for n in compiled}
    final = sorted([f"{n} (line {compiled[n]})" for n, k in kind.items() if k == "regex-final"] + [f"inline re.* (line {ln})" for ln in inline])
    return {"compiled": len(compiled), "format_validators": sorted(n for n, k in kind.items() if k == "format"),
            "prefilters": sorted(n for n, k in kind.items() if k == "prefilter"), "regex_final": final,
            "regex_final_count": len(final), "inline_marked": marked, "declared_but_missing": sorted((allowed["format"] | allowed["prefilter"]) - set(compiled))}


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
