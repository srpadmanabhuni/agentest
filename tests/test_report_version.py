"""Reports stamp the same version as ``agentest --version`` and the installed package."""

import subprocess
import sys
import tomllib
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from xml.etree import ElementTree as ET

from agentest import __version__, package_version
from agentest.cli import main
from agentest.standards import VERSION
from agentest.standards.reports import to_html, to_junit, to_markdown, to_otlp_verdicts, to_sarif, to_versioned_json

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = {"demo": {"T1-001": {"status": "pass", "detail": "ok"}}}


def _attr(span: dict, key: str) -> str:
    return next(a["value"]["stringValue"] for a in span["attributes"] if a["key"] == key)


def test_report_header_matches_agentest_dash_version():
    """The markdown report header shows the same version as ``agentest --version``."""
    script = Path(sys.executable).with_name("agentest")
    proc = subprocess.run([str(script), "--version"], cwd=ROOT, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    cli = proc.stdout.strip()
    header = to_markdown(SAMPLE, "examples").splitlines()[0]
    assert header == f"# agentest {cli} report (examples mode)"


def test_report_version_matches_cli_and_package(capsys):
    declared = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["version"]
    installed = version("agentest-ai")
    assert main(["version"]) == 0
    cli = capsys.readouterr().out.strip()
    assert VERSION == __version__ == cli == installed == declared
    assert "3.1.1" not in VERSION

    md = to_markdown(SAMPLE, "strict")
    html = to_html(SAMPLE, "strict")
    junit = ET.fromstring(to_junit(SAMPLE, "strict").split("?>", 1)[-1])
    sarif = to_sarif(SAMPLE, "strict")
    otlp = to_otlp_verdicts(SAMPLE, "strict")
    span = otlp["resourceSpans"][0]["scopeSpans"][0]["spans"][0]
    resource = otlp["resourceSpans"][0]["resource"]["attributes"]
    scope = otlp["resourceSpans"][0]["scopeSpans"][0]["scope"]

    assert md.startswith(f"# agentest {installed} report (strict mode)")
    assert f"<title>agentest {installed}</title>" in html
    assert f"<h1>agentest {installed} (strict mode)</h1>" in html
    assert to_versioned_json(SAMPLE, "strict")["tool"]["version"] == installed
    assert junit.get("name") == f"agentest {installed} (strict)"
    assert sarif["runs"][0]["tool"]["driver"]["version"] == installed
    assert _attr(span, "agentest.version") == installed
    assert next(a["value"]["stringValue"] for a in resource if a["key"] == "service.version") == installed
    assert scope["version"] == installed


def test_package_version_falls_back_when_not_installed(monkeypatch):
    import agentest

    def missing(_name: str) -> str:
        raise PackageNotFoundError

    monkeypatch.setattr(agentest, "version", missing)
    assert package_version("9.9.9") == "9.9.9"


def test_package_version_reads_distribution_metadata(monkeypatch):
    import agentest

    monkeypatch.setattr(agentest, "version", lambda name: "9.8.7" if name == "agentest-ai" else "other")
    assert package_version("0.0.0") == "9.8.7"
