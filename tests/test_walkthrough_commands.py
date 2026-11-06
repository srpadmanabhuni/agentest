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
    "docs/walkthroughs/05-bring-your-own-log.md": (),
}
# Digits immediately before "fail" are the count. "0 fail" is a substring of "10 fail" and "20 fail".
FAIL_COUNT = re.compile(r"(?<!\d)(\d+) fail\b")


def fail_counts(text: str) -> list[int]:
    return [int(n) for n in FAIL_COUNT.findall(text)]


def test_fail_count_rejects_ten_and_twenty():
    assert fail_counts("55 pass, 0 fail, 75 n/a") == [0]
    assert fail_counts("10 fail") == [10]
    assert fail_counts("20 fail") == [20]
    assert "0 fail" in "10 fail" and "0 fail" in "20 fail"
    assert 0 not in fail_counts("10 fail")
    assert 0 not in fail_counts("20 fail")


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
    if rel.endswith("05-bring-your-own-log.md"):
        counts = fail_counts(proc.stdout)
        assert counts and set(counts) == {0}, counts


@pytest.mark.skipif(not shutil.which("bash"), reason="needs bash")
def test_walkthrough_3_fixed_agent_passes_claim_checks():
    """The page says the fixed refill agent passes T1-002 and T1-018 over 8 runs. That command is not in the fence."""
    proc = _run(
        "agentest std run --agents examples/agnostic_demo/agents --agent refill_bot "
        "--ids T1-002,T1-018 --format md"
    )
    assert proc.returncode == 0, proc.stderr
    assert "T1-002 | pass | claims consistent over 8 run(s)" in proc.stdout
    assert "T1-018 | pass | claims consistent over 8 run(s)" in proc.stdout
