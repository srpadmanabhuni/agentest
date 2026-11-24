"""The README 'Judge your own agent' Python block runs as written and prints the output shown under it."""
import contextlib
import io
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SECTION = (ROOT / "README.md").read_text(encoding="utf-8").split("## Judge your own agent", 1)[1].split("\n## ", 1)[0]


def test_record_block_prints_the_shown_output():
    code = re.search(r"```python\n(.*?)```", SECTION, re.S).group(1)
    shown = re.search(r"```text\n(.*?)```", SECTION, re.S).group(1)
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        exec(compile(code, "README.md", "exec"), {})
    assert out.getvalue() == shown


def test_readme_quickstart_order_and_rules():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    first = readme.split("## Judge your own agent", 1)[0]
    assert "Python 3.11 or newer" in first
    assert first.index("```bash\npip install agentest-ai\n```") < first.index("```bash\nagentest demo\n```")
    assert readme.count("colab.research.google.com") == 1
    assert "AiEnsured agentest, an Agentic AI Testing platform" in readme
    assert "## What are agentic evals?" in readme
