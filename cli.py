"""Run agentest straight from a git clone: ``python cli.py --help`` (same as ``python -m agentest``)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from agentest.cli import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
