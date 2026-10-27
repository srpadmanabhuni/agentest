"""Every command in a ```bash block of the User Guide and the Author Guide runs, from the repository root.

Blocks fenced as ```shell (installing from a clone or a wheel) are shown only; the CI fresh-clone and wheel jobs run
them. Blocks of one guide run in order in one shell, so a later block can use files an earlier one wrote.
"""
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
GUIDES = ["docs/USER-GUIDE.md", "docs/AUTHOR-GUIDE.md"]
BLOCK = re.compile(r"^```bash\n(.*?)^```", re.S | re.M)


def blocks(guide: str) -> list[str]:
    return BLOCK.findall((ROOT / guide).read_text())


@pytest.mark.parametrize("guide", GUIDES)
def test_guide_has_runnable_commands(guide):
    assert len(blocks(guide)) >= 4


@pytest.mark.skipif(not shutil.which("bash"), reason="needs bash")
@pytest.mark.parametrize("guide", GUIDES)
def test_guide_commands_run(guide):
    shutil.rmtree(ROOT / "build" / "guide", ignore_errors=True)
    env = dict(os.environ, PATH=str(Path(sys.executable).parent) + os.pathsep + os.environ.get("PATH", ""))
    script = "set -euo pipefail\n" + "\n".join(blocks(guide))
    p = subprocess.run(["bash", "-c", script], cwd=ROOT, env=env, capture_output=True, text=True, timeout=900)
    assert p.returncode == 0, (p.stdout[-3000:], p.stderr[-3000:])
