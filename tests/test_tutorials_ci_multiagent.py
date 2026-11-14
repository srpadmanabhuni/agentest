"""Tutorials 4 and 5 stay true: their bash blocks run from the repo root and the CI example is valid."""
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
BLOCK = re.compile(r"^```bash\n(.*?)^```", re.S | re.M)


@pytest.mark.parametrize("doc", ["docs/tutorials/05-multi-agent-handoffs.md", "docs/tutorials/04-ci-cd-github-actions.md"])
def test_tutorial_commands_run(doc, tmp_path):
    env = dict(os.environ, PATH=str(Path(sys.executable).parent) + os.pathsep + os.environ.get("PATH", ""))
    for block in BLOCK.findall((ROOT / doc).read_text()):
        if "git clone" in block:
            continue
        # strict gates exit 1 on the buggy agent on purpose; the tutorial says so
        script = block.replace("--strict", "--strict || true") if "echo $?" not in block else block
        p = subprocess.run(["bash", "-c", "set -e\n" + script], cwd=ROOT, env=env, capture_output=True, text=True, timeout=300)
        for f in ("agentest.xml", "agentest.sarif"):
            (ROOT / f).unlink(missing_ok=True)
        assert p.returncode == 0, (block, p.stdout[-1500:], p.stderr[-1500:])


def test_ci_example_is_valid_and_pins_a_ref():
    wf = yaml.safe_load((ROOT / "examples/integrations/github-actions-gate.yml").read_text())
    steps = wf["jobs"]["gate"]["steps"]
    run = "\n".join(s.get("run", "") for s in steps)
    assert "--strict" in run and "agentest std validate" in run
    assert re.fullmatch(r"v\d+\.\d+\.\d+|[0-9a-f]{7,40}", wf["env"]["AGENTEST_REF"])
    assert wf["permissions"] == {"contents": "read"}
