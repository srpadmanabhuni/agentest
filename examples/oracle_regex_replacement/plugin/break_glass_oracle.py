"""Worked example: replace the T3-012 break-glass regex pre-filter with a local embedding + SLM oracle.

T3-012 checks that every break-glass (emergency / override) access is audited. Without a published
``governance.breakGlass.tools`` list it finds such calls with the pre-filter ``BREAKGLASS_RX``
(``break[-_ ]?glass|emergency[-_ ]access``). The regex misses synonyms and other languages and fires on
negations ("do not use break-glass"). This plugin swaps it for the bundled closed-label oracle task
``break-glass`` (``agentest.standards.oracle``): a local embedding rejects clear routine calls, a local SLM
labels the rest, temperature 0, fixed seed, cached. The rule logic (approval + justification) is unchanged.

Use as a plugin (``rules_dir`` / ``AGENTEST_RULES_DIR``) with an oracle configured, e.g. fully offline from the
committed cache::

    AGENTEST_ORACLE_EMBED=replay AGENTEST_ORACLE_EMBED_MODEL=llamacpp:bge-m3-Q4_K_M.gguf \\
    AGENTEST_ORACLE_SLM=replay AGENTEST_ORACLE_SLM_MODEL=http:Qwen/Qwen2.5-7B-Instruct-GGUF:Q4_K_M \\
    AGENTEST_ORACLE_CACHE=examples/oracle_regex_replacement/oracle-cache.jsonl AGENTEST_ORACLE_OFFLINE=1 \\
    AGENTEST_RULES_DIR=examples/oracle_regex_replacement/plugin agentest std run ...

Without an oracle the plugin does nothing (the regex stays). A call the oracle cannot answer (cache miss offline,
abstain, endpoint down) falls back to the regex for that call and is counted in ``FALLBACKS``.
"""

from __future__ import annotations

from agentest.standards import oracle, rules

TASK = oracle.load_task("break-glass")
FALLBACKS: list[str] = []


def text_of(tool: str, args_json: str) -> str:
    """What the oracle sees: the tool name and its JSON arguments."""
    return f"{tool} {args_json}".strip()


def detect(args_json: str, tool: str = "", o: oracle.Oracle | None = None) -> bool:
    o = o or oracle.active()
    if o is None:
        return bool(rules.BREAKGLASS_RX.search(args_json))
    try:
        return o.classify(TASK, text_of(tool, args_json)).label == TASK.positive
    except oracle.OracleUnavailable as e:
        FALLBACKS.append(f"{tool}: {e}")
        return bool(rules.BREAKGLASS_RX.search(args_json))


def install(o: oracle.Oracle | None = None) -> bool:
    """Register the override when an oracle is available. Returns whether it was installed."""
    o = o or oracle.active() or oracle.configure()
    if o is None:
        return False
    rules.PREFILTER_OVERRIDES["BREAKGLASS_RX"] = lambda text, tool="", **_: detect(text, tool, o)
    return True


def uninstall() -> None:
    rules.PREFILTER_OVERRIDES.pop("BREAKGLASS_RX", None)


install()
