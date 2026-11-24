#!/usr/bin/env python3
"""Regenerate docs/packs/*.md from catalog/packs/*.jsonl (tables) plus the hand-written intros below.

Usage: python scripts/gen_pack_docs.py [--check]
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CAT = ROOT / "catalog" / "packs"
OUT = ROOT / "docs" / "packs"
REFS = json.loads((CAT / "references.json").read_text(encoding="utf-8"))

PACKS = {
    "ma": ("MULTI-AGENT.md", "Multi-agent pack (MA)", """\
Checks for systems of several agents: who may delegate to whom, who did what, whether handoffs keep their context, whether a loop,
a conflict or a failure is contained, and whether risky actions stay inside the supervisor's chain.

## What the traces must carry

Standard OpenTelemetry GenAI conventions (agent spans, pinned in `src/agentest/standards/semconv.yaml`):

| Observable | Where | Used for |
|---|---|---|
| `gen_ai.operation.name = invoke_agent` | one span per agent invocation | agent identity, delegation chain |
| `gen_ai.agent.name` (and `gen_ai.agent.id`) | on `invoke_agent` spans; optionally on `execute_tool` spans | attribution |
| span nesting | an `invoke_agent` span inside another one | the parent (delegating) agent |
| `gen_ai.operation.name = execute_tool`, `gen_ai.tool.name`, `gen_ai.tool.call.id`, `gen_ai.tool.call.arguments`, `gen_ai.tool.call.result` | tool spans | what each agent did |
| `gen_ai.input.messages` / `gen_ai.output.messages` on an `invoke_agent` span | what the agent was handed / returned | context fidelity, injection relay |
| `error.type` or span status ERROR | agent or tool span | failure containment |

The conventions define no attribute for a handoff, an agent role or an agent's decision. These three are **agentest extensions**
(outside the OpenTelemetry conventions, optional):

| Extension attribute | On | Meaning |
|---|---|---|
| `agentest.handoff.source` | `invoke_agent` span | the delegating agent's name, when span nesting cannot show it (flat traces). It overrides nesting. |
| `agentest.agent.role` | `invoke_agent` span | free-text role, for readers (no check depends on it) |
| `agentest.agent.decision` | `invoke_agent` span; also the root span for the run's final decision | the decision label an agent voted for (MA-008) |

Facts the standards do not carry go in the governance extension (`multiAgent`, see `docs/standards/EXTENSION.md`):
`supervisor`, `delegation` (delegator to allowed delegates, `*` for any), `maxDepth` (default 4), `maxHandoffs` (default 8),
`escalationTools`. The existing `roles.actors`, `approval.required` and `escalation.handoffTool` are reused.

**Cannot verify is not fail.** A trace with fewer than two distinct agents gives n/a for every MA check, and each check
returns n/a when its own observable (a delegation graph, an input message, a decision) is absent.

Related core checks (not changed): T3-002, T3-007, T3-009 (roles and handoff targets), T3-019 (handoff to a human).

Example agents with a clean control and one seeded defect per check: `examples/multi_agent/`.
"""),
    "pv": ("PRIVACY.md", "Privacy pack (PV)", """\
Privacy checks beyond the core set: health identifiers, data minimisation, conversational consent withdrawal, leakage across
sessions, erasure requests, credentials, re-identification and persistent memory.

Each check reads tool arguments, tool results, the user input and the final answer, plus governance facts where a check needs
to know which tool is which: `privacy.phiTools`, `privacy.memoryTools`, `privacy.erasureTools`, and the existing `dataClasses` /
`toolDataClasses`. Without the fact (or the pattern in the trace) the check returns n/a.

The detectors are deterministic patterns (labelled health identifiers, ICD-10-shaped codes, email, phone, SSN and card shapes,
credential shapes). They are conservative on purpose: a pattern that is not there is not a finding.

Related core and add-on checks (not changed): T3-018 (consent recorded before processing, opt-in via `--pack rai`), T5-004, T5-011,
X-019, X-020.
"""),
    "rt": ("RED-TEAMING.md", "Red-teaming pack (RT)", """\
Attack classes that the injection-focused core checks do not cover: direct jailbreaks, refusal bypass over several turns,
look-alike and poisoned tools, system-prompt extraction, and encoded payloads.

A check returns n/a when the traces contain no matching stimulus: the absence of an attack is not a pass. Tool-description checks
(RT-003, RT-004) read the MCP `tools/list` the agent publishes, so they work without a trace of an attack.

Related core checks (not changed): the T4 group (prompt injection) and T5 group (tool allowlist and arguments).
"""),
    "bf": ("BIAS-FAIRNESS.md", "Bias and fairness pack (BF)", """\
Counterfactual and group-level checks. The test harness records two root-span attributes (agentest extensions, outside the
GenAI conventions): `agentest.fairness.pair` (the runs that form one counterfactual pair) and `agentest.fairness.group` (the
demographic variant a run used). Without them the pair and group checks return n/a.

Thresholds are governance facts: `fairness.refusalGap` (default 0.2), `fairness.lengthRatio` (default 2.0),
`fairness.decisionRelevantAttributes` (attributes that may legitimately appear in a decision).

Related core and add-on checks (not changed): T7-004, T7-007, T7-011, T7-017 (persona swap on decisions and offers).
"""),
    "ex": ("EXPLAINABILITY.md", "Explainability pack (EX)", """\
These checks test that what the agent says about its own actions agrees with the trace: it names what it acted on, reports
tool use honestly, every executed call traces back to a model decision, failures are disclosed and nothing specific is asserted
after an empty retrieval. They do not judge the quality of the prose.

Related core checks (not changed): T1-018, X-003, X-008, X-015.
"""),
    "dl": ("DATA-LINEAGE.md", "Data-lineage pack (DL)", """\
Where a value came from and whether the record of the path is complete: written values have a source, restricted data does not
flow into public tools, tool records can be replayed and reads are stable between writes.

DL-002 reads two governance facts: `toolDataClasses` (tool to data classes) and `privacy.classLevels` (class to
`restricted`, `internal` or `public`).

Related core checks (not changed): X-011, X-012, X-013 (identifiers, amounts, contact details in the answer).
"""),
}


def rows(pack: str) -> list[dict]:
    return [json.loads(x) for x in (CAT / f"{pack}.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]


def esc(s: str) -> str:
    return s.replace("|", "\\|")


def render(pack: str) -> str:
    fname, title, intro = PACKS[pack]
    rs = rows(pack)
    out = [f"# {title}", "", f"{len(rs)} opt-in checks, IDs `{rs[0]['id']}` to `{rs[-1]['id']}`. They sit **outside** the 165 tests, "
           "which are unchanged. Select them with `--pack " + pack + "` or `--ids " + rs[0]["id"] + "`; see [Extension packs](README.md).", "", intro.rstrip(), "", "## Checks", "",
           "| ID | Title | Rule | Needs | n/a when | Sources |", "|---|---|---|---|---|---|"]
    for r in rs:
        refs = "; ".join(f"[{k}]" for k in r["references"])
        out.append(f"| {r['id']} | {esc(r['title'])} | {esc(r['rule'])} | {esc('; '.join(r['requires']))} | {esc(r['na_when'])} | {refs} |")
    used = sorted({k for r in rs for k in r["references"]})
    out += ["", "## Sources", ""] + [f"- **[{k}]** {REFS[k]['label']}: <{REFS[k]['url']}>" for k in used]
    out += ["", "Each check is a deterministic rule over recorded OTLP traces and the agent's published metadata; no model runs. "
            "A check whose observable is absent returns n/a, never a guessed verdict.", ""]
    return "\n".join(out)


def index() -> str:
    allrows = {p: rows(p) for p in PACKS}
    out = ["# Extension packs (opt-in, outside the 165 tests)", "",
           "The 165 tests are unchanged, and the default `agentest std run` output is unchanged. "
           "Extension packs add checks with their own ID prefixes for areas the core set covers thinly. They are never part of the default run; "
           "select them with `--pack` or `--ids`.", "",
           "| Pack | Prefix | Checks | Covers | Page |", "|---|---|---:|---|---|"]
    for p, (fname, title, _) in PACKS.items():
        out.append(f"| `{p}` | {allrows[p][0]['id'][:2]} | {len(allrows[p])} | {title.replace(' pack', '').split(' (')[0]} | [{fname}]({fname}) |")
    out += ["| `rai` | T1-, T3-, T7- | 5 | the five responsible-AI additions (T1-020, T1-021, T3-018, T3-019, T7-017) | [catalog/rai-additions-v1.4.0.jsonl](../../catalog/rai-additions-v1.4.0.jsonl) |", "",
            f"Total: {sum(len(v) for v in allrows.values())} pack checks plus the 5 `rai` additions.", "", "## Run them", "",
            "```bash", "agentest list --packs                      # every pack name and its size", "agentest list --pack ma                    # the checks in one pack",
            "agentest std run --agent a01 --pack ma,pv  # run packs on a bundled agent (comma-separated)",
            "agentest std run --agent a01 --ids MA-001,T3-018", "agentest std run --agents examples/multi_agent --agent triage_team_seeded --pack ma", "```", "",
            "`--pack` and `--ids` accept pack IDs, the five `rai` additions and the default test IDs in any mix. `--pack all` is the default run.", "",
            "## How the packs work", "",
            "- **Offline and deterministic.** Rules read recorded OTLP/JSON traces (OpenTelemetry GenAI conventions) and the agent's published metadata "
            "(A2A AgentCard, MCP tools, the governance extension). No model, no network, no per-agent adapter.",
            "- **Agent- and framework-agnostic.** No rule names an agent or a framework.",
            "- **Cannot verify is not fail.** When the attributes or the spec a check needs are absent the verdict is n/a, with the missing observable in the detail.",
            "- **Governance facts** for the packs are optional AgentCard extension fields (`multiAgent`, `privacy`, `fairness` thresholds), documented in "
            "[docs/standards/EXTENSION.md](../standards/EXTENSION.md) and validated by the bundled JSON Schema.",
            "- **Catalogue files.** `catalog/packs/<pack>.jsonl` has one row per check (id, title, rule, family, oracle, requires, na_when, severity, references); "
            "`catalog/packs/references.json` holds the cited sources. Sources are limited to resolvable references (arXiv, OWASP, specification pages, DOIs); none is invented.",
            "- **Examples.** `examples/multi_agent/` has clean control agents and seeded-defect agents; `agentest.standards.packs.synth` builds small sample traces for your own tests.",
            "", "## Why packs and not more core tests", "",
            "Opt-in packs keep the published 165 tests and their measured behaviour stable while new areas mature. A pack check can graduate into the core set later "
            "by an explicit catalogue change; until then it never changes a default verdict.", ""]
    return "\n".join(out)


def build() -> dict[Path, str]:
    files = {OUT / "README.md": index()}
    for p, (fname, _, _) in PACKS.items():
        files[OUT / fname] = render(p)
    return files


def main() -> int:
    files = build()
    if "--check" in sys.argv:
        stale = [str(p.relative_to(ROOT)) for p, t in files.items() if not p.exists() or p.read_text() != t]
        print("stale: " + ", ".join(stale) if stale else "pack docs are current")
        return 1 if stale else 0
    OUT.mkdir(parents=True, exist_ok=True)
    for p, t in files.items():
        p.write_text(t)
    print(f"wrote {len(files)} files under {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
