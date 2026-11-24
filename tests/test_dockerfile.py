"""The Dockerfile's default command is the README quickstart command, and the image installs from the repo."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_default_cmd_is_readme_quickstart():
    df = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    entry = json.loads(re.search(r"^ENTRYPOINT (\[.*\])$", df, re.M).group(1))
    cmd = json.loads(re.search(r"^CMD (\[.*\])$", df, re.M).group(1))
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert " ".join(entry + cmd) in readme
    assert "pip install --no-cache-dir ." in df and re.search(r"^USER \w+", df, re.M)


def test_dockerignore_excludes_local_state():
    ignored = (ROOT / ".dockerignore").read_text(encoding="utf-8").split()
    assert ".git" in ignored and ".venv" in ignored
