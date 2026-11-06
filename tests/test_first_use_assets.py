"""First-use assets: the Colab notebook, the offline demo script, and the links that point at them.

The OpenTelemetry snippet and the JUnit workflow already exist; this file checks those paths
instead of accepting a second copy. No network and no dataset download.
"""

from __future__ import annotations

import ast
import builtins
import importlib.util
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
    assert "datasets" not in code  # the notebook must not pip-install the optional catalogue package
    run_cells = ["".join(c["source"]) for c in nb["cells"] if c["cell_type"] == "code" and "runpy" in "".join(c["source"])]
    assert run_cells and "exc.code not in (0, None)" in run_cells[0]
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


def _exec_notebook(monkeypatch) -> None:
    monkeypatch.chdir(ROOT)
    ns: dict = {"__name__": "__main__"}
    for cell in _nb()["cells"]:
        if cell["cell_type"] != "code":
            continue
        exec(compile("".join(cell["source"]), "examples/colab_quickstart.ipynb", "exec"), ns, ns)


@pytest.mark.skipif(not NOTEBOOK.is_file(), reason="notebook missing")
def test_notebook_cells_run_offline(monkeypatch, capsys):
    monkeypatch.delenv("AGENTEST_COLAB_LOAD_DATASET", raising=False)
    monkeypatch.delenv("COLAB_RELEASE_TAG", raising=False)
    _exec_notebook(monkeypatch)
    out = capsys.readouterr().out
    assert "refill_bot: 55 pass, 0 fail" in out
    assert "refill_bot_buggy: 41 pass, 16 fail" in out
    assert "Hub catalogue was not loaded" in out


def _script():
    spec = importlib.util.spec_from_file_location("colab_quickstart_under_test", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _block_datasets(monkeypatch) -> None:
    """Make ``import datasets`` raise ImportError even when the package is installed."""
    monkeypatch.delitem(sys.modules, "datasets", raising=False)
    real = builtins.__import__

    def blocked(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "datasets" or name.startswith("datasets."):
            raise ImportError("datasets blocked for test")
        return real(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", blocked)


def _run_blocked(argv: list[str], env_extra: dict[str, str]) -> subprocess.CompletedProcess[str]:
    """Run the quickstart as __main__ with ``import datasets`` forced to fail. No network."""
    code = (
        "import sys\n"
        "class _BlockDatasets:\n"
        "    def find_spec(self, fullname, path, target=None):\n"
        "        if fullname == 'datasets' or fullname.startswith('datasets.'):\n"
        "            raise ImportError('datasets blocked for test')\n"
        "        return None\n"
        "sys.meta_path.insert(0, _BlockDatasets())\n"
        f"sys.argv = {argv!r}\n"
        "import runpy\n"
        f"runpy.run_path({str(SCRIPT)!r}, run_name='__main__')\n"
    )
    env = os.environ.copy()
    env.pop("AGENTEST_COLAB_LOAD_DATASET", None)
    env.pop("COLAB_RELEASE_TAG", None)
    env.update(env_extra)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run(
        [sys.executable, "-c", code], cwd=ROOT, env=env, text=True, capture_output=True, timeout=120,
    )


def test_load_mode_precedence(monkeypatch):
    mod = _script()
    monkeypatch.setattr(mod, "_invoked_as_script", lambda: True)
    monkeypatch.delenv("AGENTEST_COLAB_LOAD_DATASET", raising=False)
    monkeypatch.setenv("COLAB_RELEASE_TAG", "2026.11")
    monkeypatch.setattr(sys, "argv", ["colab_quickstart.py"])
    assert mod.dataset_load_mode() == "implicit"
    monkeypatch.setattr(sys, "argv", ["colab_quickstart.py", "--load-dataset"])
    assert mod.dataset_load_mode() == "explicit"
    monkeypatch.setattr(sys, "argv", ["colab_quickstart.py", "--no-dataset", "--load-dataset"])
    assert mod.dataset_load_mode() == "off"
    monkeypatch.setattr(sys, "argv", ["colab_quickstart.py"])
    monkeypatch.setenv("AGENTEST_COLAB_LOAD_DATASET", "1")
    assert mod.dataset_load_mode() == "explicit"
    monkeypatch.setenv("AGENTEST_COLAB_LOAD_DATASET", "0")
    assert mod.dataset_load_mode() == "off"
    monkeypatch.delenv("AGENTEST_COLAB_LOAD_DATASET", raising=False)
    monkeypatch.delenv("COLAB_RELEASE_TAG", raising=False)
    assert mod.dataset_load_mode() == "off"


def test_colab_tag_soft_skips_when_datasets_missing():
    proc = _run_blocked(["colab_quickstart.py"], {"COLAB_RELEASE_TAG": "2026.11"})
    assert proc.returncode == 0, (proc.stdout[-2000:], proc.stderr[-2000:])
    assert "refill_bot: 55 pass, 0 fail" in proc.stdout
    assert "refill_bot_buggy: 41 pass, 16 fail" in proc.stdout
    assert "Hub catalogue load skipped: the datasets package is not installed" in proc.stdout
    assert "Hub config all" not in proc.stdout
    assert proc.stderr == ""


def test_explicit_flag_exits_when_datasets_missing():
    proc = _run_blocked(["colab_quickstart.py", "--load-dataset"], {})
    assert proc.returncode == 2, (proc.stdout[-1500:], proc.stderr[-1500:])
    assert "refill_bot_buggy: 41 pass, 16 fail" in proc.stdout
    assert "pip install datasets" in proc.stderr
    assert "Hub catalogue load skipped" not in proc.stdout


def test_explicit_env_exits_when_datasets_missing():
    proc = _run_blocked(["colab_quickstart.py"], {"AGENTEST_COLAB_LOAD_DATASET": "1", "COLAB_RELEASE_TAG": "2026.11"})
    assert proc.returncode == 2, (proc.stdout[-1500:], proc.stderr[-1500:])
    assert "pip install datasets" in proc.stderr
    assert "Hub catalogue load skipped" not in proc.stdout


@pytest.mark.skipif(not NOTEBOOK.is_file(), reason="notebook missing")
def test_notebook_colab_tag_soft_skips_when_datasets_missing(monkeypatch, capsys):
    monkeypatch.delenv("AGENTEST_COLAB_LOAD_DATASET", raising=False)
    monkeypatch.setenv("COLAB_RELEASE_TAG", "2026.11")
    _block_datasets(monkeypatch)
    _exec_notebook(monkeypatch)
    captured = capsys.readouterr()
    out, err = captured.out, captured.err
    assert "refill_bot: 55 pass, 0 fail" in out
    assert "refill_bot_buggy: 41 pass, 16 fail" in out
    assert "Hub catalogue load skipped: the datasets package is not installed" in out
    assert "Hub config all" not in out
    assert "pip install datasets" not in err
