"""Catalogue pin and version-stamp checks stay green, and the pin check catches retracted control_refs."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_catalog_pins_pass():
    assert _load("check_catalog_pins").main([]) == 0


def test_retracted_tokens_detected():
    pins = _load("check_catalog_pins")
    for bad in ("ISO42001:A.8", "NIST-AI-RMF:MEASURE-2.3", "OWASP-ASI:PromptInjection"):
        assert any(rx.search(bad) for rx in pins.RETRACTED), bad
    for ok in ("OWASP-ASI:ASI01", "NIST-AI-RMF:MEASURE", "EU-AIA:Art9"):
        assert not any(rx.search(ok) for rx in pins.RETRACTED), ok


def test_version_stamps_match_release():
    assert _load("check_versions").main([]) == 0
