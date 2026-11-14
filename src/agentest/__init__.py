"""agentest: 130 universal, standards-based checks for tool-using LLM agents (OpenTelemetry GenAI + A2A + MCP)."""

from importlib.metadata import PackageNotFoundError, version

# Source fallback when the distribution is not installed (a plain checkout).
# scripts/check_versions.py pins this literal to RELEASE and pyproject.toml.
__version__ = "3.3.2"


def package_version(fallback: str = __version__) -> str:
    """Installed ``agentest-ai`` version, or ``fallback`` when it is not installed."""
    try:
        return version("agentest-ai")
    except PackageNotFoundError:
        return fallback


__version__ = package_version()

__all__ = ["__version__"]
