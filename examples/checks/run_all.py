"""Run the synthetic pass/fail demo for every registered check."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agentest.standards.catalog import ALL_IDS  # noqa: E402


def _demo():
    import importlib.util

    spec = importlib.util.spec_from_file_location("check_demo", ROOT / "examples" / "checks" / "_demo.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    demo = _demo()
    bad = 0
    for test_id in ALL_IDS:
        bad += demo.run_check(test_id)
    locked = sum(1 for test_id in ALL_IDS if (ROOT / "examples" / "checks" / test_id / "demo.py").is_file())
    print(f"demos {locked}  mismatched verdicts {bad}")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
