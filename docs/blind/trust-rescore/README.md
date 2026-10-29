# Rounds 6-8 re-scored on v4.0-trust - NOT BLIND

These rules were written after rounds 6-8 were scored, and the traces are unsigned, so this is not a blind result.
Command per round (non-blind mode, since unsigned traces are refused by `--blind`):
`agentest std run --agents docs/blind/rN/agents --mode {examples,strict} --run-env cpu --max-na 1 --judge-cache docs/blind/rN-judge-cache.jsonl --judge-offline --judge-model default`
(this reproduces `docs/blind/rN-rescore-r9-*.json` exactly on the r9 freeze 5510856). Examples and strict match.

| Round | decided cells | low trust | medium | high | frozen-r9 TP / FP | branch fails | new fails (T5-015 / X-003, harness default reason) | TP cells low trust |
|---|---|---|---|---|---|---|---|---|
| 6 | 304 | 74 | 230 | 0 | 20 / 0 | 28 | 8 | 3 (T7-009 x3) |
| 7 | 340 | 81 | 259 | 0 | 21 / 0 | 33 | 12 | 3 (T1-001, X-033, T7-009) |
| 8 | 545 | 122 | 423 | 0 | 27 / 0 (14 FN) | 43 | 16 | 4 (X-038 x2, T7-009 x2) |

No trace is attested (unsigned, no intercepted traffic), so no cell is high trust and none would earn blind credit.
