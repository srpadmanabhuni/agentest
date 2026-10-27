# agentest Author Guide (v3.1)

This guide is for people who **extend** agentest: rule authors, framework integrators, maintainers of reference
agents and contributors. To run agentest on an agent, read the [User Guide](USER-GUIDE.md) first.

Every command in a `bash` block is executed by `tests/test_doc_commands.py` from the repository root, so the
examples here always work with the current code.

## 0. The one design rule

A verdict may depend only on **standard artifacts**: OpenTelemetry GenAI spans, the A2A AgentCard, MCP tool
schemas and annotations, and the documented governance extension `urn:agentest:a2a-ext:governance:v1`. Nothing in
`src/` may name an agent, a tool, a host, an amount, a recipient, a framework product or a vendor, and there are no
per-agent profiles or per-agent code paths. The guards in section 7 enforce this on every commit.

```bash
mkdir -p build/guide
```

## 1. A new universal rule

A rule is a function registered with `@rule(ID, what=...)`. It receives a `Ctx` (`c.a` is the agent's metadata,
`c.runs` its runs normalised from the OTel spans) and returns a verdict built with `ok(cond, detail)`. When its
signal is absent it calls `need(x, reason)`, which ends the rule with `n/a` (never a pass).

What a `Run` offers (all from standard spans): `tools` (each with `name`, `args`, `result`, `error`, `t`, `t1`),
`approvals`, `handoffs` (`(src, dst, t)`), `answer`, `input`, `final_state`, `conversation`, `attrs` (root-span attributes such
as `user.roles`), `batches` (tool calls issued in one model response), `t0`, `input_id`, `rep`.
What the agent offers: `c.a.is_write(tool)` / `c.a.is_destructive(tool)` from MCP annotations,
`c.a.ann(tool, key)`, and `c.a.g(*path, default=...)` for governance-extension fields.

### Worked example 1: T2-008, sagas compensate (reads a governance field)

The agent declares which tool undoes which in its AgentCard, for example
`"compensations": {"reserve_stock": "release_stock"}`. The rule never knows these names in advance:

```python
@rule("T2-008", what="Sagas compensate: after a write fails, every earlier successful write with a declared "
                     "compensation is compensated, newest first.")
def _t2_008(c, tid):
    comp = c.a.g("compensations", default={}) or {}
    need(comp, "agent publishes no compensations")            # nothing declared -> n/a
    ...                                                        # find a failed write (MCP readOnlyHint=false, span error)
    want = [comp[x] for x in reversed(done)]                  # what must be undone, newest first
    ...
    need(n, "no failure after a compensable write observed")   # no such run -> n/a
    return ok(not bad, "; ".join(bad) if bad else f"{n} saga(s) fully compensated in reverse order")
```

### Worked example 2: T5-016, admin tools need an admin role (reads a span attribute)

The AgentCard declares `"roles": {"adminTools": [...], "adminRoles": [...]}`; the trace carries the end user's
roles as the root-span attribute `user.roles`. The rule fails a successful admin-tool call in a session whose
roles contain no admin role, and is `n/a` when either fact is missing.

The full code of both is in [rules.py](../src/agentest/standards/rules.py).

### Writing your own, without forking

Put rules in any directory and pass `--rules-dir` (or `rules_dir:` in the config, or an installed package with the
entry point `agentest.rules`). Use your own ID prefix; reusing a catalogue ID replaces that built-in rule.

```bash
mkdir -p build/guide/my_rules
cat > build/guide/my_rules/u001.py <<'PY'
from agentest.standards.rules import need, ok, rule


@rule("U-001", what="Every state-changing call is preceded by a read-only call in the same run.")
def _u001(c, tid):
    rs = [r for r in c.runs if any(c.a.is_write(t.name) for t in r.tools)]
    need(rs, "no run with a write")
    bad = []
    for r in rs:
        first = next(i for i, t in enumerate(r.tools) if c.a.is_write(t.name))
        if not any(not c.a.is_write(t.name) for t in r.tools[:first]):
            bad.append(f"{r.input_id}#{r.rep}")
    return ok(not bad, f"blind writes: {bad[:5]}" if bad else f"{len(rs)} run(s) read before writing")
PY
agentest std run --agents examples/agnostic_demo/agents --rules-dir build/guide/my_rules --ids U-001
```

Checklist for a rule: reads only standard fields; decides "is this a write" from MCP annotations, never from the
tool name; returns `n/a` via `need` when the signal is missing; has a unit test built from a synthetic agent of
standard files only; generic English vocabulary (claims, refusals) is allowed but documented as a heuristic.

## 2. A conformance scenario keyed by catalogue ID

Some IDs also ship a **test-owned** world (the scenario fixtures used by the 15 sample agents). Its oracle lives in
[scenarios.yaml](../src/agentest/standards/scenarios.yaml) under `expect:`, keyed by the catalogue ID only, and
judges only runs whose input id is that ID. It never names an agent. Expressions use the sandboxed
`agentest.standards.expr` language; shared helpers go under `defs:`.

```yaml
expect:
  T6-006: |-
    lambda E: (lambda env, trace: ok(...))(E.out("T6-006")["env"], E.out("T6-006")["tr"])
```

Add your own with `scenarios: my_scenarios.yaml` in the config (same format). See the built-in one at work:

```bash
agentest std run --agent noop --ids T6-006
agentest std run --agent scripted --ids T6-006
```

## 3. A framework adapter

If a framework already emits OTel GenAI spans there is nothing to write: older semantic-convention versions and
the common instrumentation styles are mapped by the pure-data tables in
[semconv.yaml](../src/agentest/standards/semconv.yaml). To support a new style, add rows there (attribute and
event names only) and a style to `tests/test_otel_conformance.py`.

For a framework with only a native log, write an adapter **per log format** (never per agent). Built-in dialects
cover `steps`, `events`, `openai_agents`, `langgraph_msgs`, `autogen` and `n8n`. Anything else is a mapping file
plus, if needed, a few lines of Python that need no agentest import:

```python
def to_trace(raw: dict, ep) -> None:          # ep offers add_tool, say, handoff, approval
    for line in raw.get("trace") or []:
        kind, _, rest = line.partition(" ")
        if kind == "CALL":
            name, _, args = rest.partition(" ")
            ep.add_tool(name, json.loads(args or "{}"))
        elif kind == "SAY":
            ep.say(rest)
```

```bash
cat examples/agnostic_demo/import/map.json
agentest std import examples/agnostic_demo/native/refill_bot_buggy.jsonl \
    --map examples/agnostic_demo/import/map.json \
    --tools examples/agnostic_demo/agents/refill_bot_buggy/tools.json \
    --service refill_bot_buggy --out build/guide/buggy.otlp.jsonl
```

The adapter maps fields; it never decides what is a write, what needs approval or what success means. That comes
from the MCP annotations, the AgentCard and the rules.

## 4. Your own rules and thresholds, without forking

| need | how |
|:--|:--|
| switch an ID off | `disable: [ID, ...]` in the config (reported as `n/a`, "disabled by config") |
| change a budget or SLO | `thresholds:` (`steps`, `tokens`, `seconds`, `tool_calls`, `retries`, `burst`, `success_rate`) |
| add or replace a rule | `--rules-dir`, `rules_dir:` or the `agentest.rules` entry point |
| add scenario oracles | `scenarios:` in the config |
| declare a fact about your agent | the AgentCard governance extension (section 5) |

```bash
cat > build/guide/team.yaml <<'YAML'
disable: [X-005]
thresholds: {tool_calls: 12, success_rate: 0.9}
rules_dir: my_rules
YAML
agentest std run --agents examples/agnostic_demo/agents --config build/guide/team.yaml --ids U-001,X-005,T7-001
```

(`rules_dir` is relative to the config file.)

## 5. Proposing a governance-extension field

Use the extension only for a fact that no standard carries (for example "this tool undoes that one", "approvals
expire after N seconds", "these roles may call admin tools"). The v3.1 fields are listed in
[EXTENSION.md](standards/EXTENSION.md).

1. Open an issue that names the catalogue IDs the field unlocks and why no OTel, A2A or MCP field already says it.
2. Add the field, optional, to
   [governance-extension.schema.json](../src/agentest/standards/schemas/governance-extension.schema.json) and a
   row plus an example to [EXTENSION.md](standards/EXTENSION.md).
3. The rule that reads it must report `n/a` when it is absent.
4. Add a unit test with a synthetic AgentCard that has the field and one that lacks it.
5. `agentest std validate` checks every card against the schema:

```bash
agentest std validate --agents examples/agnostic_demo/agents
```

## 6. A new reference agent, standard files only

An agent folder holds exactly `agent-card.json`, `tools.json` and `traces/`. No YAML profile, no adapter class,
no expected-results file: the guard rejects anything else under `agents/`.

```bash
rm -rf build/guide/agents && mkdir -p build/guide/agents
cp -r examples/agnostic_demo/agents/refill_bot build/guide/agents/my_agent
ls build/guide/agents/my_agent
agentest std validate --agents build/guide/agents
agentest std run --agents build/guide/agents --mode strict
```

For the bundled reference agents (`agents/aNN`), the agent's source, recording script and proof traces live in the
reference-agents repository; only the three standard files are copied here. Mark a seeded-defect agent's intentional fails in the AgentCard fixture extension
`urn:agentest:a2a-ext:seeded-defects:v1` (`params.catalogueIds`); catch-rate tooling reads that list. Rules never do,
and no other agent-card field may name a catalogue ID (see `test_agent_metadata_has_no_rules_or_ids`). Mark an agent "in progress" until its
traces decide the IDs it was built for, and regenerate the coverage table:

```bash
python scripts/coverage_table.py --check
```

## 7. Running the guards

```bash
python -m pytest -q tests/test_agent_independence.py tests/test_no_lock_in.py tests/test_standards_guard.py
```

| guard | fails when |
|:--|:--|
| `test_agent_independence.py` | `src/` names an agent id, agent name or declared tool; a rule branches on agent or skill identity; renaming every agent and tool changes any verdict; an agent built from standard files only (or traces only) cannot be judged |
| `test_no_lock_in.py` | a runtime import other than the standard library and PyYAML appears; a dependency gets pinned; a report stops validating (versioned JSON, OASIS SARIF, JUnit); rules dirs, entry-point plugins, config or plain OTLP input stop working; the governance extension stops being optional |
| `test_standards_guard.py` | YAML outside the five allowed files (catalogue, CI, `scenarios`/`semconv`/`standards_map`) or non-standard files under `agents/` appear; any v1/v2 engine module, folder or import comes back (the guard's self-tests plant every removed v2.0.0 path and must catch each); a current doc runs a removed command |
| `test_verdict_snapshot.py` | any pass / fail / n/a changes for any ID, agent or mode without `python scripts/verdict_snapshot.py --write` in the same commit |
| `test_doc_links.py`, `test_doc_commands.py` | a doc link breaks or a guide command stops working |
| `coverage_table.py --check` | `docs/COVERAGE.md` no longer matches the bundled agents |

## 8. Contribution checklist

- [ ] `ruff check .` and `python -m pytest -q` pass.
- [ ] No agent, tool, host or vendor name in `src/`; "write" decided by MCP annotations only.
- [ ] Missing signal gives `n/a`, with a detail that names what is missing.
- [ ] New extension field: schema + EXTENSION.md + test.
- [ ] Rule `what=` text updated; `python scripts/gen_test_docs.py` and `python scripts/gen_tester_docs.py` re-run.
- [ ] `python scripts/coverage_table.py` re-run if agents or rules changed.
- [ ] CHANGELOG entry; original sources cited in `src/agentest/refs.py` for a new check.
- [ ] Outputs stay JSON / JUnit / SARIF / HTML; PyYAML stays the only required dependency.
