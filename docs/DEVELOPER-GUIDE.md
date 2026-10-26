# Developer guide — run the checklist runner from GitHub alone

> **Status: early / noop implementations.** Oracles are reference implementations exercised against scripted mock agents and a mock tool gateway; they are not production-grade evaluators. Real-agent adapters, richer oracles and more packs (e.g. security) are being added incrementally.

This guide is for engineers who clone
[`srpadmanabhuni/agentest`](https://github.com/srpadmanabhuni/agentest)
and want to run checklist tests **without any external service**, plug in their own
agent, and (optionally) extend suites later.

**Audience:** developers who have only the GitHub link.  
**Runner version:** `0.9.3a0` (see `pyproject.toml`).  
**Pinned catalogue:** catalogue `v1.1.2` packs vendored under `catalog/` (see
`catalog/VERSION`).  
catalogue-first narrative (same packs): USER-GUIDE.md.

Related short docs: [`ARCHITECTURE.md`](ARCHITECTURE.md),
[`SAMPLE-AGENTS.md`](SAMPLE-AGENTS.md), [`ORCHESTRATION.md`](ORCHESTRATION.md).

---

## 1. What this repo is

**agentest** is an open-core **runner**: a thin CLI, mock tool gateway, scripted
oracles, and teaching sample agents. It executes Agentic AI checklist IDs
against an agent and reports Pass / Fail / Unverified.

| Piece | Role |
|:------|:-----|
| **This GitHub repo** | Runnable harness. Cases live in Python; pack CSVs are **vendored** in `catalog/`. |
| **published catalogue** | Optional **catalogue source of truth** for authors who edit pack CSVs. |

**You do not need any online service to install, run tests, or evaluate your agent.**
No catalogue account, token, or network download is required at runtime. Runtime
dependencies are Python ≥ 3.11 and (for `.[dev]`) pytest.

catalogue remains useful only if you *author* catalogue changes: edit packs there
first, then sync CSVs into `catalog/` (see §7).

---

## 2. Install (offline)

```bash
git clone https://github.com/srpadmanabhuni/agentest.git
cd agentest

python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

python -m pip install -e ".[dev]"
```

Check that the CLI is on your path:

```bash
agentest --help
python -c "import agentest; print(agentest.__file__)"
```

There is no catalogue-download dependency in `pyproject.toml`. You never set
`HF_TOKEN` for normal use.

---

## 3. First run

### Oracle fixtures (golden / broken)

Every implemented checklist ID has a **golden** agent (must Pass) and a
**broken** agent (must Fail). That contract is the harness’s correctness bar.

```bash
agentest run --suite functional --agent golden       # exit 0
agentest run --suite functional --agent broken       # exit 1

agentest run --suite privacy --agent golden
agentest run --suite explainability --agent golden
agentest run --suite bias_fairness --agent golden    # alias: --suite bias
agentest run --suite orchestration --agent golden    # alias: --suite orch
```

Single ID:

```bash
agentest run --suite functional --ids T1-001 --agent golden
agentest run --suite functional --ids T1-001,T1-004 --agent golden --json
```

### Teaching sample agents

```bash
agentest samples
# name           cx  title
# noop            1  Noop (claim-only)
# …               …
# federation     10  …
# leaky          11  Leaky (privacy anti-pattern)
# … flaky_plan   15  …

agentest samples --failing   # cx 11–15 only

agentest run --suite functional --agent scripted
agentest run --suite privacy --agent leaky
agentest matrix
# Exit 0 iff scripted…federation/(golden) all-pass.
# noop/eager + expected-fail scenarios (leaky…flaky_plan) do not fail the process.
```

### Pytest (same suites CI runs)

```bash
pytest -q
```

---

## 4. Mental model

One checklist ID is one **case**. The runner builds a fresh mock world, lets
the agent act through the gateway, then asks an oracle to judge the result.

```
make_env()  →  Env
                │
                ▼
         agent.handle(id, env)  ──or──  golden(env) / broken(env)
                │
                │  tool calls via ToolGateway → Trace
                ▼
         oracle(env, trace)  →  Result (pass | fail | unverified)
```

### Core types

| Type | Module | Meaning |
|:-----|:-------|:--------|
| `Env` | `agentest.env` | Mock systems of record (ledger, contacts, tenants, approvals, clock, …). |
| `ToolGateway` | `agentest.gateway` | Allowlisted tools; records every call on a `Trace`. Prefer this over mutating `Env` by hand. |
| `Trace` / `ToolCall` | `agentest.types` | Ordered tool history + success/explanation fields. |
| `Result` / `Outcome` | `agentest.types` | Oracle verdict: `pass`, `fail`, or `unverified`. |
| `CaseSpec` | `agentest.cases.registry` | `checklist_id`, `make_env`, `golden`, `broken`, `oracle`. |

`CaseSpec.run(agent_name)` (in `registry.py`) chooses golden/broken callables
or `get_sample(agent_name).handle(checklist_id, env)`. Multi-run IDs
`T1-002` and `T1-003` bypass the single-shot path and loop inside
`cases.multi_run` (see §5).

### Suites ↔ catalogue IDs

Suites are lists of catalogue checklist IDs in `runner.SUITE_IDS` /
`cases.registry`:

| Suite CLI | Alias | Count | ID list constant |
|:----------|:------|------:|:-----------------|
| `functional` | — | 18 | `FUNCTIONAL_IDS` |
| `privacy` | — | 8 | `PRIVACY_IDS` |
| `explainability` | — | 5 | `EXPLAINABILITY_IDS` |
| `bias_fairness` | `bias` | 3 | `BIAS_FAIRNESS_IDS` |
| `orchestration` | `orch` | 8 | `ORCHESTRATION_IDS` |

`orchestration` is a **runner theme pack** (multi-agent handoff / HITL). catalogue
has no `eval_group=orchestration`; the IDs still come from the catalogue dataset
and are vendored as `catalog/orchestration.csv`. `T3-006` is listed in
orchestration for thematic runs but its `CaseSpec` lives in
`cases/explainability.py` (one registration only).

Vendored pack CSVs under `catalog/` mirror catalogue for documentation and sync;
**oracles and cases are Python**, not CSV parsers.

### What the agent must not do

- Do not call third-party eval frameworks (DeepEval, Giskard, Ragas, …) —
  this is an explicit non-goal of the repo.
- Do not invent tool names outside `ToolGateway`; unknown names fail at
  dispatch.
- Prefer gateway writes so oracles see real `Trace.calls` and
  `ToolCall.succeeded`.

---

## 5. Bring your own agent

This is the core workflow if you want to test **your** implementation.

> Note: there is no ready-made adapter for live LLM agent frameworks yet. Your wrapper must drive the in-memory `Env` and mock `ToolGateway` for each checklist ID; real-agent adapters are planned.

### 5.1 Protocol

Implement `SampleAgent` from `agentest.samples.base`:

```python
from agentest.env import Env
from agentest.samples.base import SampleAgent
from agentest.types import Trace

class MyAgent(SampleAgent):
    name = "myagent"           # CLI --agent value
    title = "My agent"
    complexity = 3             # teaching scale 1–15 (11–15 = expected-fail)
    description = "Short learner-facing blurb."

    def handle(self, checklist_id: str, env: Env) -> Trace:
        """Run one episode for checklist_id against a fresh env."""
        ...
```

The only required behaviour is:

```text
handle(checklist_id: str, env: Env) -> Trace
```

`CaseSpec.run` and `multi_run` call that method. Class attributes
`name` / `title` / `complexity` / `description` power `agentest samples`.

### 5.2 What a correct `Trace` must include

From `agentest.types.Trace`:

| Field | When it matters |
|:------|:----------------|
| `calls` | Filled automatically if you use `ToolGateway.call(...)`. |
| `claims_success` | Many oracles fail **false completion**: claiming success when postconditions are unmet. Set `True` only when the world state matches the task. |
| `message` | Optional human string; usually not scored. |
| `api_success` | Explainability (e.g. T1-018): align with real tool/API outcome. |
| `explanation` | Explainability: natural-language account of what happened. |
| `cited_steps` | Tool / handover names you claim in the explanation (must match the trace). |
| `memory_citations` | Memory keys you actually used (e.g. via `memory.read`). |

Minimal pattern (tools + claim):

```python
from agentest.gateway import ToolGateway
from agentest.types import Trace

tr = Trace()
gw = ToolGateway(env, tr)
gw.call("ledger.set_status", record_id="R1", status="APPROVED")
tr.claims_success = True
tr.message = "done"
return tr
```

**Do not** mutate `env` behind the gateway and pretend tools ran: several
oracles require both world state *and* matching `Trace.calls` /
`succeeded` flags. The teaching `noop` agent deliberately breaks that
contract so learners can see Failures.

### 5.3 Multi-run IDs (`T1-002`, `T1-003`)

For these IDs, `handle` runs **one episode**. The harness loops `k` times in
`cases/multi_run.py` with a fresh high-risk env each time
(`ledger` seed `R1=PENDING`; success means `R1=APPROVED`).

`MULTI_RUN_EPISODE_IDS` in `samples/base.py` is `{"T1-002", "T1-003"}`.
Teaching agents that pass the matrix typically approve `R1` once per call
(see `ScriptedAgent`). You do **not** loop inside `handle` yourself.

### 5.4 Register the agent (CLI + matrix)

Wire the name in **three** places so `--agent` and the matrix see it:

1. **`src/agentest/samples/<your_file>.py`** — class as above.
2. **`src/agentest/samples/__init__.py`**
   - Import the class.
   - Append the name to `SAMPLE_AGENT_NAMES`.
   - Instantiate it in `_build()`.
   - If it should keep `agentest matrix` green, add the name to
     `MATRIX_MUST_PASS`.
3. **`src/agentest/cases/registry.py`**
   - Append the name to `SAMPLE_AGENTS` (this feeds `ALL_AGENTS` and CLI
     `--agent` choices).

Reinstall is usually unnecessary with `pip install -e .`, but restart any
long-lived Python process after edits.

Then:

```bash
agentest samples
agentest run --suite functional --agent myagent
agentest run --suite functional --ids T1-001 --agent myagent --json
agentest matrix   # only if you added myagent to MATRIX_MUST_PASS and it truly all-passes
```

### 5.5 Worked example — pass `T1-001`, delegate the rest

`T1-001` expects: approve ledger `R1`–`R3`, reject `R4`, leave `R5`
untouched, and set `claims_success` only when postconditions hold (see
`agents/golden.py` and the T1-001 expectation in `profiles/_lib/samples.yaml`).

Create `src/agentest/samples/learner.py`:

```python
"""Example learner agent: implements T1-001; delegates unknown IDs to scripted."""

from __future__ import annotations

from agentest.env import APPROVED, REJECTED, Env
from agentest.gateway import ToolGateway
from agentest.samples.base import MULTI_RUN_EPISODE_IDS, SampleAgent
from agentest.types import Trace

_T1_001_ACTIONS = [
    ("R1", APPROVED),
    ("R2", APPROVED),
    ("R3", APPROVED),
    ("R4", REJECTED),
]


class LearnerAgent(SampleAgent):
    name = "learner"
    title = "Learner (T1-001 + scripted fallback)"
    complexity = 3
    description = (
        "Implements T1-001 via ToolGateway; for other IDs reuses ScriptedAgent "
        "so you can grow coverage ID by ID."
    )

    def handle(self, checklist_id: str, env: Env) -> Trace:
        if checklist_id == "T1-001":
            tr = Trace()
            gw = ToolGateway(env, tr)
            for record_id, status in _T1_001_ACTIONS:
                gw.call("ledger.set_status", record_id=record_id, status=status)
            tr.claims_success = True
            tr.message = "Approved R1–R3, rejected R4"
            return tr

        if checklist_id in MULTI_RUN_EPISODE_IDS:
            tr = Trace()
            gw = ToolGateway(env, tr)
            gw.call("ledger.set_status", record_id="R1", status=APPROVED)
            tr.claims_success = True
            return tr

        # Grow later: replace this fallback with your own rules per ID.
        from agentest.samples.scripted import ScriptedAgent

        return ScriptedAgent().handle(checklist_id, env)
```

Register (sketch — match existing style in those files):

```python
# samples/__init__.py — add to imports, SAMPLE_AGENT_NAMES, _build(), and
# optionally MATRIX_MUST_PASS if you keep the scripted fallback for all IDs.

# cases/registry.py — add "learner" to SAMPLE_AGENTS tuple.
```

Verify:

```bash
agentest run --suite functional --ids T1-001 --agent learner
# T1-001  PASS  agent=learner  ...
```

**Tip:** start by delegating unknown IDs to `ScriptedAgent` (as above) or to
`get_case(checklist_id).golden(env)` so the matrix stays green while you
replace IDs one at a time. That is exactly what complexity-3 `scripted` does
for every ID.

### 5.6 Testing without registering (library use)

You can also drive a case from Python without CLI registration:

```python
from agentest.cases.registry import get_case
from agentest.samples.learner import LearnerAgent  # your module

case = get_case("T1-001")
env = case.make_env()
trace = LearnerAgent().handle("T1-001", env)
result = case.oracle(env, trace)
assert result.ok, result.reason
```

For multi-run IDs, prefer `cases.multi_run.run_multi("T1-002", "scripted")`
(or extend `_PASSING_MULTI` / `_once_fn` if you add a new name that must pass
those loops). New agents that are not listed in `_PASSING_MULTI` need an
update in `multi_run.py` if you expect `T1-002`/`T1-003` to call
`handle` correctly under the multi-run path — today that set is
`golden`, `scripted`, `policy`, `reflective`, `supervisor`, `handoff`, `planner`, `critic`, `federation`.

---

## 6. Testing your agent against all packs

```bash
for suite in functional privacy explainability bias_fairness orchestration; do
  echo "=== $suite ==="
  agentest run --suite "$suite" --agent myagent || true
done

agentest matrix
```

Expected teaching behaviour (full matrix totals sum all five suites;
`T3-006` appears in both explainability and orchestration lists, one
`CaseSpec`):

| Agent | cx | Expected |
|:------|---:|:---------|
| `noop` | 1 | matrix 8/42 pass (32 FAIL, 8 vacuous PASS, 1 UNVERIFIED over 41 unique IDs) (claims success, no real tools) |
| `eager` | 2 | FAIL on all 41, matrix 0/42 (tools without rules / HITL / TTL) |
| `scripted` | 3 | **All PASS** (case goldens) |
| `policy` | 4 | **All PASS** (rule engine) |
| `reflective` | 5 | **All PASS** (+ explain / bias fields) |
| `supervisor` | 6 | **All PASS** (HITL grantor / handoff contract) |
| `handoff` | 7 | **All PASS** (receiver / independent authz) |
| `planner` | 8 | **All PASS** (plan-then-act / DEPENDS_ON + HITL) |
| `critic` | 9 | **All PASS** (generate–critique–repair) |
| `federation` | 10 | **All PASS** (tenant + TTL + single-use federation) |
| `leaky` | 11 | **Partial FAIL** (privacy IDs) — expected-fail |
| `hallucinator` | 12 | **Partial FAIL** (explainability IDs) — expected-fail |
| `biased` | 13 | **Partial FAIL** (bias_fairness IDs) — expected-fail |
| `overreach` | 14 | **Partial FAIL** (orchestration IDs) — expected-fail |
| `flaky_plan` | 15 | **Partial FAIL** (plan/DEPENDS_ON/HITL subset) — expected-fail |
| `golden` | — | **All PASS** (oracle fixture) |
| `broken` | — | **All FAIL** (oracle fixture; not in matrix) |

`MATRIX_MUST_PASS` is
`{scripted, policy, reflective, supervisor, handoff, planner, critic, federation, golden}`.
`MATRIX_EXPECTED_FAIL` is
`{noop, eager, leaky, hallucinator, biased, overreach, flaky_plan}`.
Expected-fail failures never fail `agentest matrix`’s exit status.

Details: [`SAMPLE-AGENTS.md`](SAMPLE-AGENTS.md), [`SCENARIOS-8-10.md`](SCENARIOS-8-10.md), [`SCENARIOS-EXPECTED-FAIL.md`](SCENARIOS-EXPECTED-FAIL.md), [`ORCHESTRATION.md`](ORCHESTRATION.md).

---

## 7. Writing or extending cases

### `CaseSpec` shape

```python
@dataclass(frozen=True)
class CaseSpec:
    checklist_id: str
    make_env: Callable[[], Env]
    golden: Callable[[Env], Trace]
    broken: Callable[[Env], Trace]
    oracle: Callable[[Env, Trace], Result]
```

Place new cases in the appropriate module under `src/agentest/cases/`
(`t1.py`, `privacy.py`, `orchestration.py`, …), return them from
`all_cases()`, and ensure `_build_registry()` in `registry.py` already
imports that module (it does for current packs). Add the catalogue ID to the
right `*_IDS` list and to `SUITE_IDS` via those constants.

**Broken-agent contract:** every ID must Pass on `golden` and Fail on
`broken` before merge (`CONTRIBUTING.md`).

### Sync rule for pack CSVs

1. Change pack CSVs in the catalogue first (catalogue source of truth).
2. Copy them into `catalog/` byte-identical.
3. Refresh hashes and pins:
   ```bash
   python scripts/check_catalog_pins.py --write-hashes
   # edit catalog/VERSION: hub_revision / hub_main_sha_at_sync / pack URLs
   python scripts/check_catalog_pins.py          # offline
   python scripts/check_catalog_pins.py --live   # optional network check
   ```
4. Keep catalogue `USER-GUIDE.md` / README / FAQ pointing at current agentest sample
   agents (green ladder 1–10 + expected-fail 11–15 / `agentest samples --failing`).

Do **not** invent conflicting catalogue IDs only in this repo. Security-labelled
work remains **parked** (see README non-goals).

### Keeping catalogue and GitHub in sync

| Surface | Authority | What must match |
|:--------|:----------|:----------------|
| published catalogue | **Design** (packs, USER-GUIDE, kit) | Pack CSV bytes for suites in scope |
| This GitHub repo | **Runner** (cases, oracles, samples, CI) | Vendored `catalog/*.csv` + `catalog/VERSION` |

**Offline guard (CI):** `python scripts/check_catalog_pins.py` compares each
in-scope CSV to `sha256_*` lines in `catalog/VERSION`. No catalogue token or network.

**Live guard (authors):** `python scripts/check_catalog_pins.py --live` downloads
`packs/<name>.csv` from catalogue `main` and byte-compares. Optional; never required
for contributor CI.

After editing catalogue docs only (no pack change), still bump runner docs that
mention sample-agent counts, and leave `hub_revision` / pack hashes unchanged.

### Where things live

| Concern | Path |
|:--------|:-----|
| Cases (recording) / expectations | `src/agentest/cases/`, `profiles/_lib/samples.yaml` |
| Sample agents | `src/agentest/samples/` |
| Policy rules (teaching) | `src/agentest/samples/policies/` |
| Vendored packs | `catalog/*.csv`, `catalog/VERSION` |
| catalogue sync check | `scripts/check_catalog_pins.py` |
| Pytest | `tests/functional`, `tests/privacy`, … |
| CI | `.github/workflows/ci.yml` (includes offline sync check) |

---

## 8. CI — what Actions runs, how to mirror locally

[`.github/workflows/ci.yml`](../.github/workflows/ci.yml) on `push`/`pull_request` to `main`:

1. Checkout + Python **3.11**
2. `pip install -e ".[dev]"`
3. `python scripts/check_catalog_pins.py` (offline catalog hash check)
4. `pytest -q`
5. Golden suites: functional, privacy, explainability, bias_fairness, orchestration
6. `agentest samples` + `agentest matrix`

Mirror locally:

```bash
python -m pip install -e ".[dev]"
python scripts/check_catalog_pins.py
pytest -q
agentest run --suite functional --agent golden
agentest run --suite privacy --agent golden
agentest run --suite explainability --agent golden
agentest run --suite bias_fairness --agent golden
agentest run --suite orchestration --agent golden
agentest samples
agentest matrix
```

---

## 9. FAQ / pitfalls

**Do I need network access to the catalogue?**  
No. Clone GitHub, `pip install -e ".[dev]"`, run. catalogue is for catalogue
authors syncing CSVs.

**Why do noop, eager, and the cx 11–15 agents fail some IDs?**  
By design. They teach that success flags and ungoverned tool use are not
enough. Matrix exit status ignores them.

**Can I use DeepEval / Ragas / Promptfoo here?**  
No. This harness is intentionally free of third-party eval frameworks.

**My agent passes T1-001 in a script but fails under `agentest run`.**  
Confirm registration in both `SAMPLE_AGENTS` and `samples/__init__.py`,
and that you return the same `Trace` the oracle sees (gateway-recorded
calls + honest `claims_success`).

**T1-002 / T1-003 behave oddly for my new agent name.**  
Extend `_PASSING_MULTI` / `_once_fn` in `cases/multi_run.py` so the
multi-run loop invokes your `handle` (see §5.6).

**Security pack?**  
Parked. Do not expect `--suite security` yet.

**Orchestration vs catalogue eval_group.**  
Orchestration is a runner theme selecting catalogue T3/T2 IDs. See
[`ORCHESTRATION.md`](ORCHESTRATION.md).

**Mutating `env` without tools.**  
Oracles that check traces will Fail; absence-tolerant oracles may still
Pass — that is a teaching signal, not a green light to skip the gateway.

---

## 10. Quick reference

### CLI

| Command | Purpose |
|:--------|:--------|
| `agentest run --suite S --agent A` | Run all IDs in suite `S` with agent `A` |
| `agentest run --suite S --ids ID1,ID2 --agent A` | Subset of IDs |
| `agentest run ... --json` | Machine-readable results |
| `agentest samples` | List teaching agents (cx 1–10) |
| `agentest matrix` | All suites × samples (+ golden) |
| `agentest matrix --no-golden` | Samples only |
| `pytest -q` | Full unit/integration suite |

Exit codes: `run` → 0 iff all results Pass; `matrix` → 0 iff every agent in
`MATRIX_MUST_PASS` that appears in the summary has `pass == total`.

### Suite aliases

`bias` → `bias_fairness` · `orch` → `orchestration`

### Agents

| Name | Role |
|:-----|:-----|
| `golden` / `broken` | Oracle Pass / Fail fixtures |
| `noop` … `federation` | Green teaching samples, complexity **1–10** |
| `leaky` … `flaky_plan` | Expected-fail scenarios, complexity **11–15** |

### Key modules

```
src/agentest/
  cli.py              # agentest entrypoint
  runner.py           # SUITE_IDS, run_ids, run_matrix
  env.py              # Env
  gateway.py          # ToolGateway, WRITE_TOOLS / READ_TOOLS
  types.py            # Trace, Result, Outcome
  policy.py           # permits / HIGH_PRIV (orchestration authz)
  cases/registry.py   # CaseSpec, SAMPLE_AGENTS, ALL_AGENTS, *_IDS
  cases/multi_run.py  # T1-002 / T1-003
  samples/base.py     # SampleAgent protocol
  samples/__init__.py # get_sample, MATRIX_MUST_PASS, MATRIX_EXPECTED_FAIL
catalog/              # vendored catalogue pack CSVs + VERSION
```

### Three commands to remember

```bash
pip install -e ".[dev]"
agentest run --suite functional --agent golden
agentest matrix
```

When your own agent is registered:

```bash
agentest run --suite functional --agent myagent
```

---

*Apache-2.0 runner · Checklist data CC BY 4.0 in the published catalogue · Author: Dr Srinivas Padmanabhuni*
