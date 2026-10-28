"""Extending and configuring agentest without forking.

* **Config file** (YAML or JSON, ``--config`` or ``AGENTEST_CONFIG``)::

    disable: [T7-004, X-005]          # reported as n/a ("disabled by config")
    thresholds:                       # override rule defaults
      steps: 20                       # BUDGET keys: steps, tokens, seconds, tool_calls, retries, burst
      success_rate: 0.8               # default task-success SLO when the agent publishes none
      max_na_share: 0.9               # instrumentation-coverage gate (v3.5, see instrumentation.py)
    rules_dir: my_rules/              # every *.py there is imported; use @rule("U-001", what=...) to add rules
    scenarios: my_scenarios.yaml      # extra conformance-scenario oracles (same format as scenarios.yaml)
    governance_fallback: mcp          # agents without the governance extension: derive approval / rateLimits
                                      # from MCP tool annotations (also AGENTEST_GOVERNANCE_FALLBACK=mcp)

* **Plugin entry point**: any installed package can declare
  ``[project.entry-points."agentest.rules"] myrules = "mypkg.rules"``; the module is imported and its
  ``@rule`` registrations take part in every run. Rule IDs you add should not reuse catalogue IDs unless you mean
  to replace that rule.
* **Local rules directory**: ``AGENTEST_RULES_DIR`` (or ``rules_dir`` in the config).
"""

from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path

ENTRY_POINT_GROUP = "agentest.rules"
_LOADED: set[str] = set()
CONFIG: dict = {}


def read_config(path: str | Path | None = None) -> dict:
    path = path or os.environ.get("AGENTEST_CONFIG")
    if not path:
        return {}
    text = Path(path).read_text()
    if str(path).endswith(".json"):
        return json.loads(text)
    import yaml

    return yaml.safe_load(text) or {}


def _import_file(f: Path) -> None:
    key = str(f.resolve())
    if key in _LOADED:
        return
    spec = importlib.util.spec_from_file_location(f"agentest_user_rules_{f.stem}", f)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    _LOADED.add(key)


def load_plugins(rules_dir: str | Path | None = None) -> list[str]:
    """Import rule plugins from the entry-point group and from a local rules directory. Returns what was loaded."""
    from importlib.metadata import entry_points

    done = []
    for ep in entry_points(group=ENTRY_POINT_GROUP):
        if ep.value not in _LOADED:
            ep.load()
            _LOADED.add(ep.value)
            done.append(ep.value)
    d = rules_dir or os.environ.get("AGENTEST_RULES_DIR")
    if d:
        for f in sorted(Path(d).glob("*.py")):
            _import_file(f)
            done.append(str(f))
    return done


def configure(cfg: dict | None = None, base: Path | None = None) -> dict:
    """Apply a config: thresholds, disabled IDs, plugins and extra scenarios. Idempotent; returns the config."""
    from agentest.standards import rules

    cfg = dict(cfg or {})
    base = base or Path.cwd()
    if not _DEFAULTS:
        _DEFAULTS.update(budget=dict(rules.BUDGET), tsr=rules.DEFAULT_TSR)
    th = cfg.get("thresholds") or {}
    for k, v in th.items():
        if k in rules.BUDGET:
            rules.BUDGET[k] = type(rules.BUDGET[k])(v)
    if "success_rate" in th:
        rules.DEFAULT_TSR = float(th["success_rate"])
    if cfg.get("rules_dir"):
        load_plugins(base / cfg["rules_dir"])
    else:
        load_plugins()
    if cfg.get("scenarios"):
        import yaml

        extra = yaml.safe_load((base / cfg["scenarios"]).read_text()) or {}
        lib = rules._scenarios()
        lib.setdefault("defs", {}).update(extra.get("defs", {}))
        lib.setdefault("expect", {}).update(extra.get("expect", {}))
    CONFIG.clear()
    CONFIG.update(cfg)
    return cfg


_DEFAULTS: dict = {}


def reset() -> None:
    """Restore the built-in thresholds and drop the config (plugins already imported stay registered)."""
    from agentest.standards import rules

    if _DEFAULTS:
        rules.BUDGET.clear()
        rules.BUDGET.update(_DEFAULTS["budget"])
        rules.DEFAULT_TSR = _DEFAULTS["tsr"]
    CONFIG.clear()


def disabled() -> set[str]:
    return set(CONFIG.get("disable") or [])
