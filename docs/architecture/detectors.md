# Detector modules

Unreleased r13. Not tagged and not released. This split does not change a verdict:
the 38-test scope, aggregation, thresholds, and the rule that an n/a on a labelled
defect is a miss are unchanged.

The universal checks live in `src/agentest/standards/detectors/`. `rules.py` is the
import path that existing callers use (`evaluate`, `RULES`, `rule`, `Ctx`). Loading
`rules` loads every detector and fills `RULES`.

## Interface

A detector is an object with three methods:

| Method | Contract |
|---|---|
| `applies(ctx) -> str or None` | `None` when the check can run. A string is the reason it does not apply; the runner reports `n/a` (`no standard signal: <reason>`) and does not call `evaluate`. |
| `evaluate(ctx) -> R` | The verdict. Raising `NA` is still an n/a, which is how the built-in checks report a missing signal without calling the judge twice. |
| `evidence() -> list` | What the last `evaluate` recorded. Empty before the first call. |

`ctx` is the same `Ctx` as before: the agent's published metadata and its runs.

Built-in checks are `FunctionDetector`s around the existing functions. `applies`
returns `None` and the function raises `NA` when the signal is absent, so judge
calls stay single-shot and the detail text is unchanged.

## Registry hook

```python
from agentest.standards.detectors.registry import register, get, Detector

class MyCheck(Detector):
    test_id = "T1-006"
    what = "one line"

    def applies(self, ctx):
        return None  # or "why this trace cannot be assessed"

    def evaluate(self, ctx):
        ...

    def evidence(self):
        return []

register(MyCheck())  # replaces the detector already bound to T1-006
```

`register(detector)` maps `detector.test_id` to that object and writes `RULES`,
which `evaluate` walks. The default `replace=True` means a later call wins.
`replace=False` keeps the detector already registered.

Load order:

1. Built-in family modules whose names start with `t1`…`t7` or `x_`, in alphabetical order.
2. Any other module in `detectors/` (except `_` names and `registry`), in alphabetical order.
3. Entry-point group `agentest.detectors`, when configuration loads plugins (`load_entry_points`), after the in-package modules.

A new module dropped into `detectors/` is imported on the next load. Name it so
it sorts after the built-in it replaces, or register it from the entry point,
and call `register` at import. No central list to edit.

`@rule("U-001", what="...")` on a function is the same hook: it registers one
`FunctionDetector` per id. Plugins and `rules_dir` keep using `@rule`.

## Layout

| Module | Checks |
|---|---|
| `t1.py` … `t7.py` | Catalogue families. A function registered for several ids lives with the first id. |
| `x_core.py` | Extensions X-001 through X-024 that are defined with the rules. |
| `x_grounding.py` | X-025 through X-039. |
| `x_process.py` | X-040 and later. |
| `trace_checks.py`, `packs.py` | X-021..X-024 and X-101..X-114, registered through the same `@rule` hook. |

## Shared primitives (`detectors/_core.py`)

These read only declared metadata and trace structure. Later detectors should call
them instead of re-deriving the same facts.

* `object_ledger(run)` — `(effect, object id, effect id)` for each executed state change. Object id is empty when the event names none.
* `state_diff(before, after)` — dotted paths whose value differs. A missing snapshot is empty.
* `turn_index(ctx)` — multi-turn dialogues in start order. One run is one turn. Runs that do not share `gen_ai.conversation.id` are left out.
* `classify_write(ctx, span)` — `read`, `write`, or `destructive`, from MCP `readOnlyHint` and `destructiveHint`.

`get(test_id)` returns the registered detector, or `None`.
