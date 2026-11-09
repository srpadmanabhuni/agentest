"""Coverage of every registered check, counted from the repo.

Writes docs/checks-coverage.csv and docs/checks-coverage.md.
Columns: check id, family, core-38, implementation, detector module,
pass fixture, fail fixture, docs page, demo.
"""
from __future__ import annotations

import csv
import inspect
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from agentest.standards.catalog import ALL_IDS, catalogue  # noqa: E402
from agentest.standards.rules import RULES  # noqa: E402

CORE = set(json.loads((ROOT / "fixtures" / "core-assessable.json").read_text())["assessable"])
OUT_CSV = ROOT / "docs" / "checks-coverage.csv"
OUT_MD = ROOT / "docs" / "checks-coverage.md"
FIELDS = [
    "check_id", "family", "core_38", "implementation", "detector_module",
    "pass_fixture", "fail_fixture", "docs_page", "demo",
]


def _detector(test_id: str) -> tuple[str, str]:
    """(implementation, module file) from the registered callable. stub when no rule is registered."""
    if test_id not in RULES:
        return "stub", ""
    fn = RULES[test_id][1]
    target = fn
    for cell in fn.__closure__ or ():
        inner = cell.cell_contents
        if inspect.isfunction(inner) and getattr(inner, "__module__", "").startswith("agentest."):
            target = inner
            break
    path = Path(target.__code__.co_filename)
    try:
        module = path.relative_to(ROOT).as_posix()
    except ValueError:
        module = path.name
    source = inspect.getsource(target)
    stub = "NotImplementedError" in source and source.count("\n") < 8
    return ("stub" if stub else "implemented"), module


def _family(test_id: str) -> str:
    row = catalogue().get(test_id) or {}
    if row.get("class_name"):
        return str(row["class_name"])
    page = ROOT / "docs" / "tests" / f"{test_id}.md"
    if page.is_file():
        for line in page.read_text(encoding="utf-8").splitlines():
            if line.startswith("*Repo extension"):
                if "pack" in line:
                    words = line.replace("*", "").replace(",", " ").split()
                    if "pack" in words:
                        return words[words.index("pack") - 1]
                return "extension"
    return "extension"


def _fixture_flags() -> dict[str, set[str]]:
    from tests.fixtures.w10_conformance.suite import all_fixtures

    flags: dict[str, set[str]] = {}
    for row in all_fixtures():
        if row["expect"] in ("pass", "fail"):
            flags.setdefault(row["test"], set()).add(row["expect"])
    return flags


def rows() -> list[dict[str, str]]:
    flags = _fixture_flags()
    out = []
    for test_id in ALL_IDS:
        implementation, module = _detector(test_id)
        got = flags.get(test_id, set())
        out.append({
            "check_id": test_id,
            "family": _family(test_id),
            "core_38": "yes" if test_id in CORE else "no",
            "implementation": implementation,
            "detector_module": module,
            "pass_fixture": "yes" if "pass" in got else "no",
            "fail_fixture": "yes" if "fail" in got else "no",
            "docs_page": "yes" if (ROOT / "docs" / "tests" / f"{test_id}.md").is_file() else "no",
            "demo": "yes" if (ROOT / "examples" / "checks" / test_id / "demo.py").is_file() else "no",
        })
    return out


def render_md(data: list[dict[str, str]]) -> str:
    lines = [
        "# Check coverage",
        "",
        "Counted from the registered checks, the synthetic fixtures, `docs/tests/`, and `examples/checks/`.",
        "Unreleased r13. Detector logic is unchanged.",
        "",
        "| " + " | ".join(FIELDS) + " |",
        "|" + "|".join("---" for _ in FIELDS) + "|",
    ]
    for row in data:
        lines.append("| " + " | ".join(row[field] for field in FIELDS) + " |")
    both = sum(row["pass_fixture"] == "yes" and row["fail_fixture"] == "yes" for row in data)
    lines += ["", f"{len(data)} checks. {both} have both a pass and a fail fixture.", ""]
    return "\n".join(lines)


def main() -> int:
    data = rows()
    with OUT_CSV.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(data)
    OUT_MD.write_text(render_md(data))
    print(f"wrote {OUT_CSV.relative_to(ROOT)} and {OUT_MD.relative_to(ROOT)} ({len(data)} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
