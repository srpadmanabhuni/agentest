"""First-use assets: the Colab notebook, the offline demo script, and the links that point at them.

The OpenTelemetry snippet and the JUnit workflow already exist; this file checks those paths
instead of accepting a second copy. No network and no dataset download.
"""

from __future__ import annotations

import ast
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK = ROOT / "examples" / "colab_quickstart.ipynb"
SCRIPT = ROOT / "examples" / "colab_quickstart.py"
PATH_RE = re.compile(r"(?:examples|docs)/[A-Za-z0-9_./-]+\.(?:py|md|ipynb)")
FIRST_USE_DOCS = (
    "README.md",
    "docs/testers/QUICKSTART.md",
    "docs/GETTING-STARTED.md",
    "docs/FAQ.md",
    "docs/README.md",
    "llms.txt",
)


def _nb() -> dict:
    return json.loads(NOTEBOOK.read_text(encoding="utf-8"))


def _code(nb: dict) -> str:
    return "\n".join("".join(c["source"]) for c in nb["cells"] if c["cell_type"] == "code")


def _text(nb: dict) -> str:
    return "\n".join("".join(c["source"]) for c in nb["cells"])


def test_notebook_is_plain_python_and_names_real_files():
    nb = _nb()
    assert nb["nbformat"] == 4
    assert nb["metadata"]["kernelspec"]["name"] == "python3"
    assert "accelerator" not in nb["metadata"]
    code = _code(nb)
    assert "examples/colab_quickstart.py" in code
    assert "pyyaml" in code and "pip" in code
    assert "torch" not in code and "transformers" not in code
    for cell in nb["cells"]:
        if cell["cell_type"] != "code":
            continue
        assert cell["outputs"] == []
        src = "".join(cell["source"])
        assert not any(line.startswith(("!", "%")) for line in src.splitlines())
    blob = _text(nb) + SCRIPT.read_text(encoding="utf-8")
    missing = sorted({p for p in PATH_RE.findall(blob) if not (ROOT / p).exists()})
    assert not missing, missing
    host = "huggingface" + ".co"
    assert host not in SCRIPT.read_text(encoding="utf-8")
    assert "force_redownload" not in blob
    assert "srinivaspadmanabhuni/agentic-ai-test-checklist-110" in blob
    assert 'CATALOGUE_CONFIG = "all"' in SCRIPT.read_text(encoding="utf-8")
    assert 'CATALOGUE_SPLIT = "train"' in SCRIPT.read_text(encoding="utf-8")


def test_docs_link_the_notebook_and_do_not_depend_on_a_docs_site():
    for rel in FIRST_USE_DOCS:
        text = (ROOT / rel).read_text(encoding="utf-8")
        assert "examples/colab_quickstart.ipynb" in text, rel
        low = text.lower()
        assert "srpadmanabhuni.github.io" not in low, rel
        assert "mkdocs" not in low, rel
    quick = (ROOT / "docs/testers/QUICKSTART.md").read_text(encoding="utf-8")
    assert "# 3.0.0" not in quick
    assert "3.3.2" in quick
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "pinned catalogue **v1.3.1**" in readme
    assert "pinned catalogue **v1.2.1**" not in readme


def test_otel_snippet_and_junit_workflow_already_exist():
    emit = (ROOT / "examples/otel_plain/emit_trace.py").read_text(encoding="utf-8")
    mods = set()
    for node in ast.walk(ast.parse(emit)):
        if isinstance(node, ast.Import):
            mods.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            mods.add(node.module.split(".")[0])
    assert "opentelemetry" not in mods and "agentest" not in mods
    ci = (ROOT / "docs/developers/CI.md").read_text(encoding="utf-8")
    assert "--format junit" in ci
    assert "--format sarif" in ci
    for n in range(1, 6):
        assert list((ROOT / "docs/walkthroughs").glob(f"{n:02d}-*.md")), n


def test_quickstart_catalogue_url_is_the_readme_url():
    from tests.test_doc_links import HF_ALLOWED

    allowed = HF_ALLOWED["docs/testers/QUICKSTART.md"]
    text = (ROOT / "docs/testers/QUICKSTART.md").read_text(encoding="utf-8")
    assert allowed
    assert allowed <= HF_ALLOWED["README.md"]
    assert all(url in text for url in allowed)


def test_demo_script_is_offline(tmp_path, monkeypatch):
    monkeypatch.delenv("AGENTEST_COLAB_LOAD_DATASET", raising=False)
    monkeypatch.delenv("COLAB_RELEASE_TAG", raising=False)
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--no-dataset"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=120,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
    )
    assert proc.returncode == 0, (proc.stdout[-2000:], proc.stderr[-2000:])
    out = proc.stdout
    assert "refill_bot: 55 pass, 0 fail" in out
    assert "refill_bot_buggy: 41 pass, 16 fail" in out
    assert "Hub catalogue was not loaded" in out
    assert "| T2-001 | pass | fail |" in out
    assert "docs/walkthroughs/01-verify-before-acting.md" in out
    assert "examples/otel_plain/emit_trace.py" in out
    assert "docs/developers/CI.md" in out
    assert "n/a is not a pass" in out


@pytest.mark.skipif(not NOTEBOOK.is_file(), reason="notebook missing")
def test_notebook_cells_run_offline(monkeypatch, capsys):
    monkeypatch.delenv("AGENTEST_COLAB_LOAD_DATASET", raising=False)
    monkeypatch.delenv("COLAB_RELEASE_TAG", raising=False)
    monkeypatch.chdir(ROOT)
    ns: dict = {"__name__": "__main__"}
    for cell in _nb()["cells"]:
        if cell["cell_type"] != "code":
            continue
        exec(compile("".join(cell["source"]), "examples/colab_quickstart.ipynb", "exec"), ns, ns)
    out = capsys.readouterr().out
    assert "refill_bot: 55 pass, 0 fail" in out
    assert "refill_bot_buggy: 41 pass, 16 fail" in out
    assert "Hub catalogue was not loaded" in out
