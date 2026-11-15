"""Opt-in extension packs: checks that sit OUTSIDE the 110 catalogue tests and the 130 default checks.

A pack is a ``catalog/packs/<name>.jsonl`` file (one row per check: id, title, rule, family, references ...) plus the
rules in ``agentest.standards.packs.<name>``. Pack IDs have their own prefixes (MA-, PV-, RT-, BF-, EX-, DL-), are never
part of ``catalog.ALL_IDS`` and are never run by default: select them with ``--pack`` or ``--ids``.

This module only reads the catalogue files. It must not import ``rules`` (``rules`` imports it).
"""

from __future__ import annotations

import json
from functools import lru_cache

from agentest.paths import root

PACK_NAMES = ("ma", "pv", "rt", "bf", "ex", "dl")
PACK_TITLES = {
    "ma": "Multi-agent: delegation, roles, handoffs, loops, consensus, containment",
    "pv": "Privacy: health data, minimisation, consent withdrawal, cross-session leakage, erasure, secrets",
    "rt": "Red teaming: jailbreaks, refusal bypass, look-alike and poisoned tools, extraction, encoded payloads",
    "bf": "Bias and fairness: counterfactual pairs, group refusal rates, protected attributes, stereotypes",
    "ex": "Explainability: acted-on objects, honest tool-use reports, traceable calls, disclosed failures",
    "dl": "Data lineage: value provenance, data-class downflow, complete tool records, stable reads",
}


def _dir():
    return root() / "catalog" / "packs"


@lru_cache(maxsize=1)
def rows() -> dict[str, dict]:
    """Pack rows keyed by check ID (empty when the pack catalogue is not installed)."""
    out: dict[str, dict] = {}
    for n in PACK_NAMES:
        p = _dir() / f"{n}.jsonl"
        if p.is_file():
            for line in p.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    r = json.loads(line)
                    out[r["id"]] = r
    return out


@lru_cache(maxsize=1)
def references() -> dict[str, dict]:
    p = _dir() / "references.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else {}


PACK_IDS: frozenset[str] = frozenset(rows())
PACK_RULES: dict = {}  # id -> (what, fn(ctx)); filled by the pack modules. A separate registry: rules.RULES stays the 130 + 5 additions.


def pack_ids(name: str) -> list[str]:
    """IDs of one pack (``ma``, ``pv`` ...), ``packs`` (all packs) or ``rai`` (the five responsible-AI additions)."""
    name = name.lower()
    if name == "packs":
        return list(rows())
    if name == "rai":
        from agentest.standards.catalog import RAI_ADDITION_IDS

        return list(RAI_ADDITION_IDS)
    return [i for i, r in rows().items() if r["pack"] == name]


def known_packs() -> dict[str, list[str]]:
    out = {n: pack_ids(n) for n in PACK_NAMES}
    out["packs"] = pack_ids("packs")
    out["rai"] = pack_ids("rai")
    return out
