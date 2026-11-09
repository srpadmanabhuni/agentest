"""Run the synthetic pass and fail example for one check.

Prints the verdict and the evidence detail for both trace dialects (native OTLP and
LangGraph) on the shelf vocabulary. The clinic vocabulary is the same fixture shape;
pytest covers both.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tests.fixtures.w10_conformance.suite import (  # noqa: E402
    CASES,
    DIALECTS,
    load_shapes,
    locked_map,
    verdict,
)


def _cases(test_id: str) -> dict[str, dict] | None:
    spec = locked_map().get(test_id) or {}
    if spec.get("source") == "core":
        return {case["kind"]: case for case in CASES if case["test"] == test_id and case["kind"] in ("pass", "fail")}
    if spec.get("source") == "shape":
        shapes = {item["name"]: item for item in load_shapes()}
        out = {}
        for kind in ("pass", "fail"):
            case = dict(shapes[spec[kind]])
            case.update(test=test_id, kind=kind, expect=kind)
            out[kind] = case
        return out
    return None


def run_check(test_id: str, vocabulary: str = "shelf") -> int:
    cases = _cases(test_id)
    print(f"== {test_id}")
    if cases is None:
        print("  no dialect-stable pass/fail pair is locked for this check")
        return 0
    bad = 0
    for kind in ("pass", "fail"):
        for dialect in DIALECTS:
            status, detail = verdict(cases[kind], vocabulary, dialect)
            print(f"  {kind:4} {dialect:10} {status}")
            print(f"       {detail[:200]}")
            if status != cases[kind]["expect"]:
                bad += 1
    return bad


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        print("usage: python examples/checks/<id>/demo.py", file=sys.stderr)
        return 2
    return 1 if run_check(argv[0]) else 0


if __name__ == "__main__":
    raise SystemExit(main())
