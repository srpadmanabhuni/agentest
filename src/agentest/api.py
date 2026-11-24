"""Public Python calls for the checks ``agentest std run`` already runs.

``run`` judges a trace file, an agent directory, or an in-memory OTLP document.
``record`` records tool calls and steps in-process into that same trace, then
``check`` runs those checks. ``assert_passes`` is the pytest assertion.
No extra package is required.
"""

from __future__ import annotations

import json
import os
import shutil
import tempfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# Passed through to run() by record() / Recorder.check(). `agent` is not here: on a recording it is
# the acting agent of a tool call, and the judged trace is the single otlp_agent `std run --otlp` uses.
_CHECK_KEYS = ("card", "tools", "ids", "mode", "strict", "config", "rules_dir")
_MODES = ("strict", "examples")


class RunError(ValueError):
    """The trace could not be judged. ``exit_code`` is 2, the same code the CLI returns for a bad input."""

    exit_code = 2


@dataclass(frozen=True)
class Verdict:
    """One check on one agent: the ``status`` and ``detail`` ``agentest std run --json`` writes."""

    id: str
    status: str
    detail: str
    agent: str


@dataclass(frozen=True)
class Result:
    """Verdicts from one ``run`` call, in the same shape as ``agentest std run --json``."""

    verdicts: dict[str, dict[str, dict[str, str]]]
    mode: str = "examples"
    strict: bool = False

    @property
    def exit_code(self) -> int:
        """0, or 1 when ``strict`` is true and any check failed. Same rule as ``agentest std run --strict``."""
        failed = any(cell["status"] == "fail" for row in self.verdicts.values() for cell in row.values())
        return 1 if self.strict and failed else 0

    @property
    def checks(self) -> tuple[Verdict, ...]:
        return tuple(
            Verdict(test_id, cell["status"], cell.get("detail", ""), agent)
            for agent, row in self.verdicts.items()
            for test_id, cell in row.items()
        )

    def __iter__(self):
        return iter(self.checks)

    def __getitem__(self, test_id: str) -> Verdict:
        hits = [check for check in self.checks if check.id == test_id]
        if not hits:
            raise KeyError(test_id)
        if len({check.agent for check in hits}) > 1:
            raise KeyError(f"{test_id} is in several agents; use result.verdicts[agent][{test_id!r}]")
        return hits[0]

    def __str__(self) -> str:
        """The summary lines ``agentest std run`` prints for these verdicts."""
        from agentest.standards.cli import format_run_summary

        return format_run_summary(self.verdicts, self.mode)


def _ids_arg(ids: str | Sequence[str] | None) -> str | None:
    if ids is None:
        return None
    if isinstance(ids, str):
        return ids or None
    text = ",".join(part.strip() for part in (str(item) for item in ids) if part.strip())
    return text or None


def _id_list(ids: str | Sequence[str] | None) -> list[str] | None:
    text = _ids_arg(ids)
    if text is None:
        return None
    return [part.strip() for part in text.split(",") if part.strip()]


def _configure(config: str | os.PathLike[str] | None, rules_dir: str | os.PathLike[str] | None) -> None:
    """Apply config the way ``agentest std`` does, including an empty config (it clears a previous one)."""
    from agentest.standards import ext

    ext.configure(ext.read_config(config), Path(config).parent if config else None)
    if rules_dir:
        ext.load_plugins(rules_dir)


def _as_json_file(value: Any, tmp: Path, name: str) -> str | None:
    if value is None:
        return None
    if isinstance(value, (str, os.PathLike)):
        return str(value)
    if isinstance(value, dict):
        dest = tmp / name
        dest.write_text(json.dumps(value), encoding="utf-8")
        return str(dest)
    raise RunError(f"{name} must be a path or a JSON object")


def _select_agent(ags: dict, agent: str | None) -> dict:
    if agent is None:
        return ags
    if agent not in ags:
        raise RunError(
            f"unknown agent {agent!r}; list folders under agents/ (or --agents). See agentest --help or the README first-run."
        )
    return {agent: ags[agent]}


def _stage_files(paths: Sequence[Path], card: str | None, tools: str | None) -> tuple[dict, list[Path]]:
    from types import SimpleNamespace

    from agentest.standards.cli import StdInputError, _otlp_agent

    args = SimpleNamespace(otlp=[str(p) for p in paths], card=card, tools=tools)
    try:
        ags = _otlp_agent(args)
    except StdInputError as e:
        raise RunError(str(e)) from e
    staged = [next(iter(ags.values())).dir.parent]
    return ags, staged


def _write_docs(docs: Sequence[Mapping], tmp: Path) -> Path:
    dest = tmp / "traces.otlp.jsonl"
    dest.write_text("".join(json.dumps(doc, ensure_ascii=False) + "\n" for doc in docs), encoding="utf-8")
    return dest


def _documents(trace: Any) -> list[dict] | None:
    """OTLP documents held in memory, or None when ``trace`` is a path or a list of paths."""
    from agentest.standards.emit import TraceBuilder

    if isinstance(trace, Recorder):
        return [trace.otlp()]
    if isinstance(trace, TraceBuilder):
        return [trace.build()]
    if isinstance(trace, dict):
        if "resourceSpans" not in trace:
            raise RunError("expected an OTLP trace (a document with resourceSpans) or a path to one")
        return [trace]
    if isinstance(trace, (list, tuple)):
        if not trace:
            raise RunError("expected at least one trace")
        if all(isinstance(item, dict) for item in trace):
            if any("resourceSpans" not in item for item in trace):
                raise RunError("expected OTLP trace documents (resourceSpans)")
            return list(trace)
        if all(isinstance(item, (str, os.PathLike)) and not isinstance(item, bytes) for item in trace):
            return None
        raise RunError("expected a list of trace paths or a list of OTLP documents")
    return None


def _load(trace: Any, card: str | None, tools: str | None, agent: str | None, tmp: Path) -> tuple[dict, list[Path]]:
    from agentest.standards.metadata import _is_agent_dir, load, load_all

    docs = _documents(trace)
    if docs is not None:
        ags, staged = _stage_files([_write_docs(docs, tmp)], card, tools)
        try:
            return _select_agent(ags, agent), staged
        except Exception:
            for folder in staged:
                shutil.rmtree(folder, ignore_errors=True)
            raise
    paths = [Path(item) for item in trace] if isinstance(trace, (list, tuple)) else [Path(trace)]
    if len(paths) == 1 and paths[0].is_dir():
        path = paths[0]
        if _is_agent_dir(path):
            return _select_agent({path.name: load(path)}, agent), []
        if any(child.is_dir() and _is_agent_dir(child) for child in path.iterdir()):
            return _select_agent(load_all(path), agent), []
        raise RunError(f"{path} is not a trace file or an agent directory")
    missing = [path for path in paths if not path.is_file()]
    if missing:
        raise RunError(
            f"{missing[0]} is not a file; pass an existing OTLP/JSON or JSONL trace, "
            "for example a path under agents/<id>/traces/"
        )
    ags, staged = _stage_files(paths, card, tools)
    return _select_agent(ags, agent), staged


def _judge(ags: dict, mode: str, ids: str | None) -> dict:
    from agentest.standards import runner
    from agentest.standards.cli import UnknownTestIds, restrict_ids

    res = runner.to_json(runner.run_all(ags, mode=mode))
    if ids:
        try:
            res = restrict_ids(res, ags, ids, mode)
        except UnknownTestIds as e:
            raise RunError(str(e)) from e
    return res


def run(
    trace_or_path: str | os.PathLike[str] | Mapping | Sequence[Any] | Recorder,
    *,
    card: str | os.PathLike[str] | dict | None = None,
    tools: str | os.PathLike[str] | dict | None = None,
    ids: str | Sequence[str] | None = None,
    mode: str = "examples",
    strict: bool = False,
    agent: str | None = None,
    config: str | os.PathLike[str] | None = None,
    rules_dir: str | os.PathLike[str] | None = None,
) -> Result:
    """Judge traces the same way ``agentest std run`` does.

    ``trace_or_path`` is an OTLP file (or a list of them), an agent directory, a directory
    of agent directories, an OTLP document, or a :class:`Recorder` from :func:`record`.
    A file is staged like ``--otlp`` (the agent name in the verdicts is ``otlp_agent``).
    An agent directory uses that directory's name, the same name ``--agent`` prints.
    ``card`` and ``tools`` are the optional AgentCard and MCP tools list (a path or the JSON object).
    ``ids`` uses the ``--ids`` selection. ``mode`` is ``examples`` (the default) or ``strict``.
    ``strict=True`` does not change a verdict; it sets :attr:`Result.exit_code` to 1 when any check failed.
    ``config`` and ``rules_dir`` apply to the process, the same way the CLI flags do.
    Unusable input raises :class:`RunError` (CLI exit 2). This function does not print and does not exit.
    """
    if mode not in _MODES:
        raise RunError("mode must be 'strict' or 'examples'")
    _configure(config, rules_dir)
    id_text = _ids_arg(ids)
    staged: list[Path] = []
    try:
        with tempfile.TemporaryDirectory(prefix="agentest-api-") as tmp:
            tmp_path = Path(tmp)
            card_path = _as_json_file(card, tmp_path, "agent-card.json")
            tools_path = _as_json_file(tools, tmp_path, "tools.json")
            ags, staged = _load(trace_or_path, card_path, tools_path, agent, tmp_path)
            verdicts = _judge(ags, mode, id_text)
    finally:
        for folder in staged:
            shutil.rmtree(folder, ignore_errors=True)
    return Result(verdicts, mode, strict)


def assert_passes(result: Result, ids: str | Sequence[str] | None = None) -> None:
    """Raise ``AssertionError`` unless the run passes.

    With no ``ids``, any ``fail`` fails the assertion and ``n/a`` does not
    (the same rule as ``agentest std run --strict``). With ``ids``, each named
    check must be ``pass``.
    """
    wanted = _id_list(ids)
    if wanted is None:
        bad = [check for check in result.checks if check.status == "fail"]
        missing: list[str] = []
    else:
        bad = []
        missing = []
        for test_id in wanted:
            hits = [check for check in result.checks if check.id == test_id]
            if not hits:
                missing.append(test_id)
            bad.extend(check for check in hits if check.status != "pass")
    if not missing and not bad:
        return
    lines = ["checks that did not pass:"]
    lines.extend(f"{test_id}: missing" for test_id in missing)
    lines.extend(f"{check.agent} {check.id}: {check.status}: {check.detail}" for check in bad)
    raise AssertionError("\n".join(lines))


class Recorder:
    """Tool calls and steps recorded as one OTLP trace. ``check`` runs the same checks as :func:`run`."""

    def __init__(self, service: str, input_text: str = "", defaults: dict | None = None, **trace: Any) -> None:
        from agentest.standards.emit import TraceBuilder

        self._builder = TraceBuilder(service, input_text=input_text, **trace)
        self._defaults = dict(defaults or {})
        self._cached: dict | None = None

    def _drop(self) -> None:
        self._cached = None

    def tool(
        self,
        name: str,
        arguments: dict | None = None,
        result: Any = None,
        error: bool = False,
        call_id: str = "",
        agent: str = "",
        reason: str = "",
        **extra: Any,
    ) -> str:
        """Record one tool call (an ``execute_tool`` span)."""
        self._drop()
        return self._builder.tool(name, arguments, result, error, call_id, agent, reason, **extra)

    def step(self, text: str = "", **extra: Any) -> str:
        """Record one agent step (a model reply on the trace)."""
        self._drop()
        return self._builder.chat(text, **extra)

    def answer(self, text: str) -> None:
        """Record the run's final answer."""
        self._drop()
        self._builder.answer(text)

    def agent(self, name: str, source: str = "") -> str:
        """Record an agent invocation. ``source`` is the agent that handed off."""
        self._drop()
        return self._builder.agent(name, source)

    def approval(self, action: str, granted: bool, form: str = "span", **kw: Any) -> None:
        self._drop()
        self._builder.approval(action, granted, form, **kw)

    def final_state(self, state: Any) -> None:
        self._drop()
        self._builder.final_state(state)

    def error(self, message: str) -> None:
        self._drop()
        self._builder.error(message)

    def otlp(self) -> dict:
        """The OTLP/JSON document ``agentest std run --otlp`` reads."""
        if self._cached is None:
            self._cached = self._builder.build()
        return self._cached

    def write(self, path: str | os.PathLike[str], append: bool = True) -> Path:
        """Write the trace as ``.otlp.jsonl`` (one line) or ``.json``."""
        dest = Path(path)
        dest.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(self.otlp(), ensure_ascii=False)
        if dest.suffix == ".jsonl":
            with dest.open("a" if append else "w", encoding="utf-8") as handle:
                handle.write(line + "\n")
        else:
            dest.write_text(line + "\n", encoding="utf-8")
        return dest

    def check(self, **kwargs: Any) -> Result:
        """Run the checks on this recording. Keyword arguments override those given to :func:`record`."""
        opts = {**self._defaults, **kwargs}
        return run(self.otlp(), **opts)


class record:
    """Record tool calls and steps, then run the same checks.

    As a context manager, call :meth:`Recorder.check` (or :func:`run`) when the block ends.
    As a decorator, the wrapped function takes the recorder as its first argument.
    After the function returns, the checks run and the :class:`Result` is ``function.result``.

    ``card``, ``tools``, ``ids``, ``mode``, ``strict``, ``config`` and ``rules_dir`` are forwarded
    to :meth:`Recorder.check`. Other keywords are trace fields (``input_id``, ``start_ns``, and
    root attributes with dots written as ``__``). Verdicts use the agent name ``otlp_agent``,
    the same name ``agentest std run --otlp`` prints.
    """

    def __init__(self, service: str, input_text: str = "", **kwargs: Any) -> None:
        self.service = service
        self.input_text = input_text
        self._defaults = {key: kwargs.pop(key) for key in list(kwargs) if key in _CHECK_KEYS}
        self._trace = kwargs

    def __enter__(self) -> Recorder:
        return Recorder(self.service, self.input_text, self._defaults, **self._trace)

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False

    def __call__(self, fn):
        import functools

        def wrapped(*args, **kwargs):
            wrapped.result = None
            with self as rec:
                out = fn(rec, *args, **kwargs)
            wrapped.result = rec.check()
            return out

        wrapped.result = None
        return functools.update_wrapper(wrapped, fn)
