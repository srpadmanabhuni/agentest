"""pytest plugin: judge a trace with agentest checks from inside a test.

pytest loads this module through the ``pytest11`` entry point when agentest-ai is installed; there is nothing to
enable. It adds:

* the ``agentest_trace`` fixture: the trace under test, with ``.run()`` and ``.assert_checks([...])``
* the ``agentest_record`` fixture: a factory for an in-process :class:`agentest.Recorder` with the ini defaults
* the ``agentest`` marker: ``@pytest.mark.agentest(trace=..., checks=[...])`` asserts the checks after the test body
* the ini options ``agentest_trace``, ``agentest_card``, ``agentest_tools``, ``agentest_mode`` and the
  ``--agentest-trace`` command-line option

The checks, verdicts and ``n/a`` semantics are the engine's (:func:`agentest.run`); this module only wires them to pytest.
Opt out for one run with ``pytest -p no:agentest``. Guide: docs/integrations/pytest.md
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from agentest.api import CheckFailure, Recorder, Result, assert_checks, record, run

__all__ = ["AgentestTrace", "CheckFailure", "assert_checks"]

_MARK = "agentest"
_NO_TRACE = (
    "agentest: no trace for this test. Give it one of:\n"
    "  @pytest.mark.agentest(trace='path/to/trace.otlp.jsonl')\n"
    "  @pytest.mark.parametrize('agentest_trace', ['path/to/trace.otlp.jsonl'], indirect=True)\n"
    "  pytest --agentest-trace path/to/trace.otlp.jsonl     (or agentest_trace = ... under [pytest] in pytest.ini / pyproject.toml)"
)


@dataclass
class AgentestTrace:
    """A trace plus the AgentCard and tools list it is judged with."""

    source: Any
    card: Any = None
    tools: Any = None
    mode: str | None = None
    label: str | None = None

    def agentest_run_args(self) -> dict[str, Any]:
        args = {"trace": self.source, "card": self.card, "tools": self.tools, "mode": self.mode, "label": self.label}
        return {k: v for k, v in args.items() if v is not None}

    def run(self, ids: str | list[str] | None = None) -> Result:
        """Judge the trace; ``ids`` is the ``--ids`` selection. Never raises on a failing check."""
        args = self.agentest_run_args()
        args.pop("label", None)
        return run(args.pop("trace"), ids=ids, **args)

    def assert_checks(self, ids: str | list[str], *, allow_na: bool = False) -> Result:
        """Raise :class:`CheckFailure` unless every named check is ``pass``."""
        __tracebackhide__ = True
        return assert_checks(self, ids, allow_na=allow_na)


def pytest_addoption(parser: pytest.Parser) -> None:
    group = parser.getgroup("agentest", "agentest")
    group.addoption("--agentest-trace", dest="agentest_trace", default=None, metavar="PATH", help="trace file or agent directory the agentest_trace fixture uses by default")
    parser.addini("agentest_trace", "default trace file or agent directory for the agentest_trace fixture (relative to the rootdir)")
    parser.addini("agentest_card", "default AgentCard JSON (relative to the rootdir)")
    parser.addini("agentest_tools", "default MCP tools list JSON (relative to the rootdir)")
    parser.addini("agentest_mode", "examples (default) or strict", default="")


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "agentest(trace=None, card=None, tools=None, checks=None, mode=None, allow_na=False): judge a trace with agentest checks; "
        "with checks=[...], fail the test unless each named check is pass",
    )


def _here(item_or_request: Any) -> Path:
    path = getattr(item_or_request, "path", None) or Path(str(item_or_request.fspath))
    return Path(path).parent


def _path(value: Any, *roots: Path) -> Any:
    """A relative path is looked up beside the test file, then at the rootdir; anything else passes through."""
    if not isinstance(value, (str, os.PathLike)):
        return value
    p = Path(value)
    if p.is_absolute():
        return str(p)
    for root in roots:
        if (root / p).exists():
            return str(root / p)
    return str(roots[-1] / p)


def _ini(config: pytest.Config, name: str) -> str | None:
    value = config.getini(name)
    return str(value) if value else None


def _source(item: Any, param: Any = None) -> AgentestTrace:
    """Resolve the trace for a test: indirect parameter, then the marker, then ``--agentest-trace``, then the ini file."""
    config, here, root = item.config, _here(item), Path(str(item.config.rootpath))
    mark = item.get_closest_marker(_MARK)
    kw = dict(mark.kwargs) if mark else {}
    if isinstance(param, Mapping) and "resourceSpans" not in param:  # {"trace": ..., "card": ..., "tools": ...}
        kw = {**kw, **param}
        param = kw.get("trace")
    source = param if param is not None else kw.get("trace")
    cfg = False
    if source is None:
        source, cfg = config.getoption("agentest_trace") or _ini(config, "agentest_trace"), True
    if source is None:
        pytest.fail(_NO_TRACE, pytrace=False)
    if isinstance(source, (list, tuple)):
        source = [_path(p, here, root) for p in source]
    else:
        source = _path(source, root) if cfg else _path(source, here, root)
    card = kw.get("card") or _ini(config, "agentest_card")
    tools = kw.get("tools") or _ini(config, "agentest_tools")
    card = _path(card, here, root) if kw.get("card") else _path(card, root)
    tools = _path(tools, here, root) if kw.get("tools") else _path(tools, root)
    mode = kw.get("mode") or _ini(config, "agentest_mode")
    shown = None
    if isinstance(source, str):
        try:
            shown = Path(source).relative_to(root).as_posix()
        except ValueError:
            shown = source
    return AgentestTrace(source, card, tools, mode or None, shown)


@pytest.fixture
def agentest_trace(request: pytest.FixtureRequest) -> AgentestTrace:
    """The trace under test. Pass it to :func:`agentest.assert_checks`, or call ``.assert_checks([...])`` / ``.run()``."""
    return _source(request.node, getattr(request, "param", None))


@pytest.fixture
def agentest_record(request: pytest.FixtureRequest):
    """``agentest_record("service", input_text="...")`` returns a :class:`agentest.Recorder` with the ini defaults for card and tools."""
    config, here, root = request.config, _here(request.node), Path(str(request.config.rootpath))

    def make(service: str, input_text: str = "", **kwargs: Any) -> Recorder:
        for key, name in (("card", "agentest_card"), ("tools", "agentest_tools")):
            if kwargs.get(key) is None and _ini(config, name):
                kwargs[key] = _path(_ini(config, name), root)
            elif isinstance(kwargs.get(key), (str, os.PathLike)):
                kwargs[key] = _path(kwargs[key], here, root)
        if kwargs.get("mode") is None and _ini(config, "agentest_mode"):
            kwargs["mode"] = _ini(config, "agentest_mode")
        return record(service, input_text, **{k: v for k, v in kwargs.items() if v is not None}).__enter__()

    return make


def _force(outcome: Any, exc: BaseException) -> None:
    """Make the call phase fail with ``exc``. pluggy 1.1+ has force_exception; older pluggy (pytest 7.0) propagates a raise."""
    if hasattr(outcome, "force_exception"):
        outcome.force_exception(exc)
    else:
        raise exc


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_call(item: pytest.Item):
    """With ``@pytest.mark.agentest(checks=[...])``: once the test body passes, assert the checks on the trace."""
    outcome = yield
    mark = item.get_closest_marker(_MARK)
    if mark is None or not mark.kwargs.get("checks") or outcome.excinfo is not None:
        return
    failure: BaseException | None = None
    result = None
    try:
        trace = getattr(item, "funcargs", {}).get("agentest_trace") or _source(item)
        result = assert_checks(trace, mark.kwargs["checks"], allow_na=bool(mark.kwargs.get("allow_na")))
    except (KeyboardInterrupt, SystemExit):
        raise
    except CheckFailure as exc:
        item.user_properties.extend((f"agentest.{v.id}", v.status) for v in exc.failures)
        failure = _message_only(str(exc))
    except BaseException as exc:  # an unreadable trace or an unknown check id fails this test, not the session
        failure = exc
    if failure is not None:  # forced outside the except blocks, so the report is the message alone
        _force(outcome, failure)
        return
    item.user_properties.extend((f"agentest.{v.id}", v.status) for v in result.checks)


def _message_only(text: str) -> BaseException:
    """pytest's own failure that reports ``text`` without a traceback into this module."""
    try:
        pytest.fail(text, pytrace=False)
    except pytest.fail.Exception as failed:
        failed.__context__ = None  # built while the CheckFailure was being handled; that chain is noise in the report
        failed.__suppress_context__ = True
        return failed.with_traceback(None)
    raise AssertionError("unreachable")  # pragma: no cover
