# packs-labelled-v1

Labelled scenarios for the 41 opt-in pack checks (MA, PV, RT, BF, EX, DL) and the 5 responsible-AI opt-ins (T1-020, T1-021, T3-018, T3-019, T7-017).

- `author/`: the scenario authoring code. It only builds traces (`Synth`); it never calls a check. Each pattern carries its label, the spec clause it comes from and its provenance.
- `data/*.jsonl.gz`, `labels.jsonl`, `tools_std.json`: the generated, locked set. `MANIFEST.json` holds the sha256 of every file, the lock hash and the lock time.
- `build.py` regenerates the set (byte-identical except the lock timestamp). `run_eval.py OUT.jsonl` verifies the manifest and writes one prediction per scenario and check.
- Do not tune a check against this set. A fix needs a fresh held-out set to re-measure.

Limits: labels are self-authored by the author of the checks, the traces are synthetic, and the example-trace labels come from the README tables written with the checks. It is a regression and self-consistency set, not an independent held-out benchmark.
