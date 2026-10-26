# Adding a universal rule

A rule is a Python function registered with `@rule` for one or more catalogue IDs (or your own IDs). It receives a
`Ctx` (the agent's metadata plus its runs) and returns `R(status, detail)`.

```python
from agentest.standards.rules import rule, ok, need

@rule("U-001", what="Every state-changing call is preceded by at least one read-only call in the same run.")
def _u001(c, tid):
    rs = [r for r in c.runs if c.writes(r)]
    need(rs, "no run with a write")                     # raises NA -> verdict n/a ("no standard signal")
    bad = [f"{r.input_id}#{r.rep}" for r in rs
           if not any(not c.a.is_write(t.name) for t in r.tools[: r.tools.index(c.writes(r)[0])])]
    return ok(not bad, f"blind writes: {bad[:5]}" if bad else f"{len(rs)} run(s) read before writing")
```

Where to put it, without forking:

- a **local directory**: `agentest std run --rules-dir my_rules/` (or `AGENTEST_RULES_DIR`, or `rules_dir` in the
  config file); every `*.py` there is imported;
- an **installed package** with an entry point:

  ```toml
  [project.entry-points."agentest.rules"]
  myrules = "mypkg.rules"
  ```

Both paths are tested in `tests/test_no_lock_in.py`.

## The rules of independence

A rule must work for any agent. `tests/test_agent_independence.py` enforces this; in code review check that a rule:

1. **Reads only standard fields**: OTel GenAI attributes, AgentCard fields, MCP annotations and input schemas, or
   documented governance-extension fields. Use `c.writes(r)` / `c.a.is_write(name)` (MCP `readOnlyHint`) to decide
   whether a call changes state, never the tool's name.
2. **Never names an agent, tool, host, amount or recipient.** Generic English vocabulary for claims and refusals
   is allowed and must be documented as a heuristic.
3. **Never branches on agent or skill identity** (`if agent.name == ...`).
4. **Returns n/a when its signal is missing**, via `need(...)`. A missing signal is not a pass.
5. **Is stable under renaming**: the mutation test renames every agent id and tool name consistently and requires
   identical verdicts.
6. **Has a test** with a synthetic agent built from standard artifacts only.

If a rule needs a fact that no standard carries, add an optional field to the governance extension, update the
[schema](../../src/agentest/standards/schemas/governance-extension.schema.json) and
[EXTENSION.md](../standards/EXTENSION.md), and keep the rule n/a when the field is absent.

## Overriding a catalogue rule

Registering `@rule("T5-006", ...)` in a plugin replaces the built-in rule for that ID. To switch a rule off, use
`disable: [T5-006]` in the config; it reports n/a with "disabled by config".
