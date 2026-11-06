"""Run the bash blocks in walkthroughs 2–5 and check the evidence those pages name.

Walkthrough 1's synthetic CLI journey is covered in tests/test_contribute_trace.py.
These commands use the shipped refill traces. They do not install LangGraph.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
BLOCK = re.compile(r"^```bash\n(.*?)^```", re.S | re.M)
PAGES = {
    "docs/walkthroughs/02-instructions-hidden-in-tool-output.md": (
        "canary surfaced",
        "disallowed hosts",
        "injected recipients",
        "no warning",
    ),
    "docs/walkthroughs/03-claims-success-it-did-not-earn.md": (
        "social#0: claims success",
        "no policy_version",
    ),
    "docs/walkthroughs/04-personal-data-left-unmasked.md": (
        "unmasked: {'pii_base': ['email'], 'pii_para': ['email']}",
        "masked in 2 run(s)",
    ),
    "docs/walkthroughs/05-bring-your-own-log.md": (
        "0 fail",
    ),
}


def _run(script: str) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ, PATH=str(Path(sys.executable).parent) + os.pathsep + os.environ.get("PATH", ""))
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run(["bash", "-c", script], cwd=ROOT, env=env, text=True, capture_output=True, timeout=120)


@pytest.mark.skipif(not shutil.which("bash"), reason="needs bash")
@pytest.mark.parametrize("rel", list(PAGES))
def test_walkthrough_bash_block_matches_documented_evidence(rel):
    blocks = BLOCK.findall((ROOT / rel).read_text(encoding="utf-8"))
    assert blocks, rel
    proc = _run("set -euo pipefail\n" + "\n".join(blocks))
    assert proc.returncode == 0, (rel, proc.stdout[-1500:], proc.stderr[-1500:])
    for needle in PAGES[rel]:
        assert needle in proc.stdout, (rel, needle, proc.stdout[-1500:])
