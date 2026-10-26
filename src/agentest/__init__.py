"""agentest — open-core runner for Agentic AI Test Checklist 110."""

__version__ = "2.0.0.dev0"  # next version (v2.0.0-dev); v1.0.0 is the released line on main

from agentest.types import Outcome, Result, ToolCall, Trace

__all__ = ["Outcome", "Result", "ToolCall", "Trace", "__version__"]
