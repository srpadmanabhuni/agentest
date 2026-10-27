"""Safe expression language for the test-owned scenario oracles (``scenarios.yaml``).

Scenario oracles state per-input expectations as small side-effect-free expressions, in the
spirit of Google's Common Expression Language (CEL, https://cel.dev) and JSONLogic:
a Python-syntax *expression* subset is parsed with :mod:`ast`, every node and name is
checked against an allow-list, and it is evaluated with no builtins beyond the ones
listed in :data:`FUNCS`. No statements, imports, attribute access to dunders,
assignment or I/O are possible. Dicts read in expressions are wrapped so that
``o.field`` and ``o["field"]`` both work and a missing key reads as ``None``.
"""

from __future__ import annotations

import ast
import base64
import hashlib
import json
import posixpath
import re
from collections import Counter
from types import SimpleNamespace
from typing import Any
from urllib.parse import urlparse

_ALLOWED = (
    ast.Expression, ast.BoolOp, ast.And, ast.Or, ast.BinOp, ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv, ast.Mod,
    ast.Pow, ast.UnaryOp, ast.Not, ast.USub, ast.UAdd, ast.Compare, ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE,
    ast.In, ast.NotIn, ast.Is, ast.IsNot, ast.IfExp, ast.Call, ast.keyword, ast.Attribute, ast.Subscript, ast.Slice,
    ast.Name, ast.Load, ast.Store, ast.Constant, ast.List, ast.Tuple, ast.Dict, ast.Set, ast.ListComp, ast.SetComp,
    ast.DictComp, ast.GeneratorExp, ast.comprehension, ast.Lambda, ast.arguments, ast.arg, ast.JoinedStr,
    ast.FormattedValue, ast.Starred, ast.BitOr, ast.BitAnd, ast.BitXor, ast.NamedExpr,
)


class D(dict):
    """dict with attribute reads; missing keys read as None."""

    def __getattr__(self, k: str) -> Any:
        if k.startswith("_"):
            raise AttributeError(k)
        return self.get(k)


def wrap(x: Any) -> Any:
    if isinstance(x, D):
        return x
    if isinstance(x, dict):
        return D({k: wrap(v) for k, v in x.items()})
    if isinstance(x, list):
        return [wrap(v) for v in x]
    return x


def _pii(text: Any, kinds=("email", "card", "pan", "acct")) -> list[str]:
    return [k for k in kinds if k in PII_RX and PII_RX[k].search(str(text or ""))]


PII_RX = {
    "email": re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+"),
    "card": re.compile(r"\b(?:\d{4}[ -]?){3}\d{4}\b"),
    "pan": re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b"),
    "acct": re.compile(r"\b\d{9,18}\b"),
    "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    "phone": re.compile(r"\b(?:\+?\d{1,3}[-. ]?)?\(?\d{3}\)?[-. ]?\d{3}[-. ]?\d{4}\b"),
}


_Re = SimpleNamespace(
    search=re.search, match=re.match, fullmatch=re.fullmatch, findall=re.findall, finditer=re.finditer,
    sub=re.sub, split=re.split, compile=re.compile, escape=re.escape,
    I=re.I, IGNORECASE=re.I, S=re.S, DOTALL=re.S, M=re.M, MULTILINE=re.M, X=re.X, VERBOSE=re.X,
)


def _loads(s: Any) -> Any:
    return wrap(json.loads(s))


def _json_or(s: Any, fallback: Any) -> Any:
    """``json.loads(s)``, or ``fallback`` when ``s`` is not valid JSON."""
    try:
        return wrap(json.loads(s))
    except (ValueError, TypeError):
        return fallback


def _sha256(x: Any) -> str:
    return hashlib.sha256(x.encode() if isinstance(x, str) else bytes(x)).hexdigest()


_Json = SimpleNamespace(dumps=json.dumps, loads=_loads)
_Posix = SimpleNamespace(normpath=posixpath.normpath, join=posixpath.join, basename=posixpath.basename, dirname=posixpath.dirname)
_Hash = SimpleNamespace(sha256=hashlib.sha256, md5=hashlib.md5)


def get_path(d: Any, path: str) -> Any:
    """Dotted lookup (``output.a.b``; integer parts index lists); missing -> None."""
    cur = d
    for part in path.split("."):
        if isinstance(cur, dict):
            cur = cur.get(part)
        elif isinstance(cur, list) and part.lstrip("-").isdigit():
            i = int(part)
            cur = cur[i] if -len(cur) <= i < len(cur) else None
        else:
            return None
    return cur


class R:
    """A verdict: status (pass/fail/n/a) and evidence detail."""

    def __init__(self, status: str, detail: str = "") -> None:
        self.status, self.detail = status, detail

    def __repr__(self) -> str:  # pragma: no cover
        return f"R({self.status!r}, {self.detail!r})"


def ok(cond: Any, detail: str = "") -> R:
    return R("pass" if cond else "fail", detail)


def _strip_all(text: str, parts: list) -> str:
    for x in parts:
        text = text.replace(x, "")
    return text


_FIXTURE_CACHE: dict[str, Any] = {}


def _fixture(rel: str) -> Any:
    """Read-only JSON data shipped under ``fixtures/`` (e.g. pinned artifact hashes); ``{}`` if absent."""
    if rel not in _FIXTURE_CACHE:
        from agentest.paths import root

        base = (root() / "fixtures").resolve()
        f = (base / rel).resolve()
        if base not in f.parents:
            raise ExprError(f"fixture path {rel!r} escapes fixtures/")
        _FIXTURE_CACHE[rel] = json.loads(f.read_text()) if f.exists() else {}
    return _FIXTURE_CACHE[rel]


def _read_texts(pattern: str) -> str:
    """Concatenated text of repo files matching ``pattern`` (read-only; must stay inside the repo)."""
    from agentest.paths import root

    base = root().resolve()
    parts = []
    for f in sorted(base.glob(pattern)):
        if base in f.resolve().parents and f.is_file():
            parts.append(f.read_text())
    return " ".join(parts)


FUNCS: dict[str, Any] = {
    "len": len, "any": any, "all": all, "sum": sum, "min": min, "max": max, "abs": abs, "round": round,
    "sorted": sorted, "reversed": reversed, "set": set, "frozenset": frozenset, "list": list,
    "tuple": tuple, "dict": dict, "str": str, "int": int, "float": float, "bool": bool,
    "enumerate": enumerate, "zip": zip, "range": range, "next": next, "iter": iter, "map": map, "filter": filter,
    "isinstance": isinstance, "repr": repr, "Counter": Counter, "None": None, "True": True, "False": False,
    "re": _Re, "json": _Json, "hashlib": _Hash, "pii": _pii, "pii_hits": _pii, "PII_RX": None, "sha256": _sha256,
    "D": D, "R": R, "ok": ok, "json_or": _json_or, "strip_all": _strip_all, "fixture": _fixture, "read_texts": _read_texts,
    "urlparse": urlparse, "posixpath": _Posix, "b64encode": base64.b64encode, "b64decode": base64.b64decode, "ValueError": ValueError,
}
FUNCS["PII_RX"] = PII_RX
_BLOCKED_ATTRS = {"gi_frame", "gi_code", "cr_frame", "cr_code", "ag_frame", "ag_code", "f_globals", "f_locals",
                  "f_builtins", "f_back", "f_code", "tb_frame", "tb_next", "mro", "format_map"}


class ExprError(ValueError):
    pass


_CACHE: dict[str, Any] = {}


def compile_expr(src: str):
    if src in _CACHE:
        return _CACHE[src]
    try:
        tree = ast.parse(src.strip(), mode="eval")
    except SyntaxError as e:
        raise ExprError(f"syntax error in expression {src!r}: {e}") from e
    for n in ast.walk(tree):
        if not isinstance(n, _ALLOWED):
            raise ExprError(f"{type(n).__name__} not allowed in expression {src[:80]!r}")
        if isinstance(n, ast.Attribute) and (n.attr.startswith("_") or n.attr in _BLOCKED_ATTRS):
            raise ExprError(f"private attribute {n.attr!r} not allowed")
        if isinstance(n, ast.Name) and n.id.startswith("__"):
            raise ExprError(f"name {n.id!r} not allowed")
    code = compile(tree, "<expect>", "eval")
    _CACHE[src] = code
    return code


def evaluate(src: str, env: dict[str, Any]) -> Any:
    """Evaluate ``src`` with ``env`` (names) + :data:`FUNCS`; nothing else is reachable."""
    g = env if "__builtins__" in env else {"__builtins__": {}, **FUNCS, **env}
    return eval(compile_expr(src), g)  # noqa: S307 - AST allow-listed above, no builtins


def bind(defs: list | dict, env: dict[str, Any] | None = None) -> dict[str, Any]:
    """Evaluate ordered ``let`` bindings into ONE shared namespace, so a lambda sees later definitions."""
    g: dict[str, Any] = {"__builtins__": {}, **FUNCS, **(env or {})}
    items = defs.items() if isinstance(defs, dict) else [tuple(x) for x in defs]
    for name, src in items:
        g[name] = evaluate(str(src), g)
    return g
