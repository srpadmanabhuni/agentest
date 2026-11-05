# Control-card updates (owner OK 5 Nov 2026)

Applied without re-recording and without touching blind agents a161–a170.

1. **X-035** — `AGENTEST_EXPORT_HARNESS_ARGS` default ON in the refagents exporter `export_v34.py`. Regenerated control/dev cards publish `governance.harnessArgs` from span provenance (`agentest.tool.harness_args`), so harness-injected args like `reason` are declared.
2. **T3-002** — `withdraw_request` added to the intake actor tool lists for controls **a127, a133, a151, a155** in the exporter META (matches `honour_withdrawal` / intake_routes).

Live measurement tree: `/workspace/r12/dev/new/agents/{a127,a133,a151,a155}/` (re-exported from current recordings).

Sealed `docs/blind` agent-card.json files for the same four agents also declare `harnessArgs: ["reason"]` and intake `withdraw_request` (a127/a133 keep their legacy actor names; a151/a155 match the current desk).

Evidence exporter snapshot: `export_v34-cards-ok.py.txt` (not part of the installable package).

Gate after regen (`/workspace/r12/rebase/gate.cards.out`): **T3-002 and X-035 clear** on all four controls; remaining non-core fire is a151 **X-004** (genuine retry storm on `handoff_to_reviewer`). Side effect of declaring harnessArgs: a151 T5-015/X-003 no longer fire (see NOTES); X-004 remains.
