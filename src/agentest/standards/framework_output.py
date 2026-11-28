"""Framework-owned output / structured-result tools.

Some frameworks record a structured-output call as an ``execute_tool`` span. That call is not an
agent-chosen action, so T5-001 and T5-018 must not treat it as an undeclared tool. The mark is
``agentest.tool.kind=framework_output``, set by the importer (or by ``record()`` / ``TraceBuilder``)
and, for native traces that omit it, recognised from the output *role* when the run is loaded.

The checks read only the mark, never a hard-coded tool name: a user tool that happens to share a
framework's default output-tool name still counts as undeclared when it is not in the output role.
"""

from __future__ import annotations

from typing import Any

FRAMEWORK_OUTPUT_KIND = "framework_output"

# Role signals used only when a native span has no agentest mark. Compared case-insensitively.
# The processed-result and default description strings are what one widely used output-tool
# instrumentation writes; a user tool with a different result or description is left alone.
_OUTPUT_PROCESSED = "final result processed."
_OUTPUT_DESCRIPTION = "the final response which ends this conversation"
_OUTPUT_LOGFIRE_PREFIX = "running output function:"
_DEFAULT_OUTPUT_TOOL = "final_result"


def is_framework_output_tool(tool: Any) -> bool:
    """True when the tool span is marked as a framework output / structured-result call."""
    kind = str((getattr(tool, "attrs", None) or {}).get("agentest.tool.kind") or "").strip().lower()
    return kind == FRAMEWORK_OUTPUT_KIND


def _default_output_name(name: str) -> bool:
    n = str(name or "")
    return n == _DEFAULT_OUTPUT_TOOL or n.startswith(_DEFAULT_OUTPUT_TOOL + "_")


def _resource_attrs(doc: dict | None) -> dict[str, Any]:
    if not doc:
        return {}
    out: dict[str, Any] = {}
    for rs in doc.get("resourceSpans") or []:
        for item in (rs.get("resource") or {}).get("attributes") or []:
            key, value = item.get("key"), item.get("value") or {}
            if not key:
                continue
            out[key] = next(iter(value.values()), "")
    return out


def _looks_like_typed_output_run(run: Any, resource: dict[str, Any]) -> bool:
    """True when the run already carries typed-output / structured-result instrumentation."""
    framework = str(resource.get("gen_ai.framework") or "").casefold()
    if "pydantic" in framework:
        return True
    attrs = getattr(run, "attrs", None) or {}
    if any(str(k).startswith("pydantic_ai.") for k in attrs):
        return True
    # The structured output itself is often recorded on the root span under this name.
    if "final_result" in attrs:
        return True
    return False


def in_output_role(tool: Any, run: Any = None, resource: dict | None = None) -> bool:
    """True when the span is a framework output call, by mark or by output-role signals."""
    if is_framework_output_tool(tool):
        return True
    attrs = getattr(tool, "attrs", None) or {}
    msg = str(attrs.get("logfire.msg") or "")
    if msg.casefold().startswith(_OUTPUT_LOGFIRE_PREFIX):
        return True
    desc = str(attrs.get("gen_ai.tool.description") or "")
    if desc.casefold().startswith(_OUTPUT_DESCRIPTION):
        return True
    result = str(getattr(tool, "result", "") or "").strip()
    if result.casefold() == _OUTPUT_PROCESSED:
        return True
    # Content was not recorded: accept the default output-tool name only on a typed-output run,
    # so a user tool of the same name with a real result is still judged as undeclared.
    if run is not None and _default_output_name(getattr(tool, "name", "")) and not result:
        return _looks_like_typed_output_run(run, resource or {})
    return False


def annotate_framework_output_tools(run: Any, doc: dict | None = None) -> None:
    """Stamp ``agentest.tool.kind=framework_output`` on output-role tools of one run (in memory)."""
    resource = _resource_attrs(doc)
    for tool in getattr(run, "tools", None) or []:
        if not in_output_role(tool, run, resource):
            continue
        tool.attrs = dict(getattr(tool, "attrs", None) or {})
        tool.attrs.setdefault("agentest.tool.kind", FRAMEWORK_OUTPUT_KIND)
