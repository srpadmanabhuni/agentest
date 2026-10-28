# pack_defects - demo agents for the v4.0 packs (X-031 to X-044)

Two data-only agents with synthetic KYC and grant traces. No model, no network, no cost.

| Agent | What it shows |
|---|---|
| `kyc_bot_buggy` | Each run carries one privacy, security, performance, explainability or bias defect. It fails all 14 pack checks. |
| `kyc_bot` | The same triggers, handled correctly. It passes all 14 pack checks. |

    python examples/pack_defects/make_traces.py      # rebuild the traces (stdlib only, deterministic)
    agentest std run --max-na 1 --agents examples/pack_defects/agents

`kyc_bot` still fails a few older checks on purpose. They are T5-004 and X-020 (the consented PAN is sent raw), T5-015 and X-003 (no per-call reasons), and X-028 (the leak run reads the full KYC record). The traces are built to exercise the packs, not to be a clean reference agent. The run-by-run defect list is in the docstring of `make_traces.py`. All Aadhaar, PAN and key values are synthetic.
