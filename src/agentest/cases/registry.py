"""Case registry and CaseSpec."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from agentest.env import Env
from agentest.types import Outcome, Result, Trace

AgentFn = Callable[[Env], Trace]
EnvFactory = Callable[[], Env]

ORACLE_AGENTS = ("golden", "broken")
SAMPLE_AGENTS = ("noop", "eager", "scripted", "policy", "reflective", "supervisor", "handoff", "planner", "critic", "federation", "leaky", "hallucinator", "biased", "overreach", "flaky_plan")
ALL_AGENTS = ORACLE_AGENTS + SAMPLE_AGENTS


@dataclass(frozen=True)
class CaseSpec:
    """One scenario: env factory plus golden/broken reference trajectories.

    There is no per-scenario oracle: :meth:`run` records the episode(s) as plain data
    and judges them with the model-driven expectations in ``profiles/_lib/samples.yaml``.
    """
    checklist_id: str
    make_env: EnvFactory
    golden: AgentFn
    broken: AgentFn

    def _act(self, agent_name: str) -> AgentFn:
        if agent_name == "golden":
            return self.golden
        if agent_name == "broken":
            return self.broken
        from agentest.samples import get_sample

        sample = get_sample(agent_name)
        return lambda env: sample.handle(self.checklist_id, env)

    def record(self, agent_name: str) -> list[dict]:
        """Run the scenario for ``agent_name`` and return native episode dicts (plain data)."""
        from agentest.cases import multi_run
        from agentest.samples.record import snap

        if agent_name not in ALL_AGENTS:
            raise ValueError(f"unknown agent {agent_name!r}; choose one of: {', '.join(ALL_AGENTS)}")
        if self.checklist_id in multi_run.MULTI_RUN_IDS:
            return multi_run.record_multi(self.checklist_id, agent_name)
        env = self.make_env()
        tr = self._act(agent_name)(env)
        return [episode(agent_name, self.checklist_id, 0, env, tr, snap)]

    def run(self, agent_name: str) -> Result:
        """Record the scenario and judge it with the shared expectation library."""
        return judge(self.checklist_id, self.record(agent_name))


def episode(agent: str, cid: str, rep: int, env: Env, tr: Trace, snap: Callable) -> dict:
    """Native sample episode: tool trace plus plain-data env/trace snapshots for the expectations."""
    return {"agent": agent, "probe": cid, "rep": rep, "input": cid,
            "trace": [{"name": c.name, "args": c.args, "result": c.result, "allowed": c.allowed, "ok": c.succeeded,
                       "actor": (c.meta or {}).get("actor", "")} for c in tr.calls],
            "output": {"message": tr.message, "claims_success": tr.claims_success,
                       "emails": list(env.emails), "outputs": (env.extras or {}).get("outputs"),
                       "env": snap(env), "tr": snap(tr)},
            "extra": {}}


def library_profile():
    """The shared sample-scenario expectation library as a :class:`Profile`."""
    from agentest.model.profile import Profile, _read
    from agentest.standards import DATA

    path = DATA / "scenarios.yaml"
    return Profile(agent="scenario", adapter="sample", **_read(path), source=str(path))


def judge(cid: str, episodes: list[dict]) -> Result:
    """Model-driven verdict for one scenario ID over recorded episodes."""
    from agentest.model.adapters import adapt
    from agentest.model.expect import evaluate_expectations

    prof = library_profile()
    r = evaluate_expectations(prof, [adapt(e, prof) for e in episodes], [cid])[cid]
    oc = {"pass": Outcome.PASS, "fail": Outcome.FAIL}.get(r.status, Outcome.UNVERIFIED)
    return Result(cid, oc, r.detail)



def _build_registry() -> dict[str, CaseSpec]:
    from agentest.cases import (
        bias,
        explainability,
        orchestration,
        privacy,
        t1,
        t2,
        t5,
        t6,
    )

    specs: list[CaseSpec] = []
    specs.extend(t1.all_cases())
    specs.extend(t2.all_cases())
    specs.extend(t5.all_cases())
    specs.extend(t6.all_cases())
    specs.extend(privacy.all_cases())
    specs.extend(explainability.all_cases())
    specs.extend(bias.all_cases())
    specs.extend(orchestration.all_cases())
    return {s.checklist_id: s for s in specs}


CASE_REGISTRY: dict[str, CaseSpec] = _build_registry()

FUNCTIONAL_IDS: list[str] = [
    "T1-001",
    "T1-002",
    "T1-003",
    "T1-004",
    "T1-005",
    "T1-007",
    "T1-009",
    "T1-011",
    "T1-013",
    "T1-015",
    "T2-001",
    "T2-003",
    "T2-009",
    "T2-013",
    "T5-012",
    "T6-003",
    "T6-006",
    "T6-010",
]

PRIVACY_IDS: list[str] = [
    "T1-016",
    "T2-005",
    "T3-008",
    "T4-009",
    "T5-004",
    "T5-011",
    "T6-004",
    "T7-014",
]

EXPLAINABILITY_IDS: list[str] = [
    "T1-018",
    "T3-006",
    "T5-015",
    "T6-007",
    "T7-009",
]

BIAS_FAIRNESS_IDS: list[str] = [
    "T7-004",
    "T7-007",
    "T7-011",
]

ORCHESTRATION_IDS: list[str] = [
    # catalogue packs/orchestration.csv — runner theme pack (not a catalogue eval_group).
    # T3-006 CaseSpec lives in explainability; listed here for thematic suite runs only.
    "T3-001",
    "T3-002",
    "T3-006",
    "T3-007",
    "T3-010",
    "T3-011",
    "T3-014",
    "T2-004",
]



def get_case(checklist_id: str) -> CaseSpec:
    """Return the CaseSpec for a checklist ID."""
    try:
        # Look up the case spec to replay its reference trajectory.
        return CASE_REGISTRY[checklist_id]
    except KeyError as exc:
        raise ValueError(f"checklist ID not implemented: {checklist_id}") from exc
