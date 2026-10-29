# Blind round 10 status (agentest v4.0-r10; rules frozen in RULES-FREEZE-v4.0-r10, commit d92da9e)

Done, all pushed:
- (1) Qwen judge restarted on :8008 (common/gguf_llm_server.py, judge-venv; log /workspace/logs/qwen.log).
- (2) Gates re-checked:
  - v2 floor: examples 393/391, strict 388/385.
  - vocab guard: 0.
  - rename/independence tests: 166 passed.
- (3) Either-judge rule plus generic fixes (NOT BLIND), commits 9aef27b, 84eb56c and 4217e7f. All 6 true-positive cells are restored; one new FP (A123 X-037).
- (4) Freeze d92da9e.
- (5) Seeds committed before recording: cd5dba6 and 4e7b0e6 (docs/blind/r10/SEEDED.md).

Running:
- Command: `nohup setsid /workspace/r10/rec.sh` (log /workspace/r10/rec.log; per-agent logs /workspace/r10/<slug>.log; <slug>.done markers). Reruns skip agents that are already done.
- Order:
  1. Qwen on :8008: a151–a154.
  2. Gemma on :8010: a155–a157.
  3. Kill both servers, then Moonlight Q2_K on :8012: a158–a160.
  4. Restart Qwen on :8008 and Gemma on :8010.
- Pace: about 5 min per run, 11 runs per agent, so roughly 9–10 h in total. Started 16:29 IST.
- If interrupted: kill any leftover `./rec.sh` processes (match the full cmdline `bash ./rec.sh`), delete the proof/ folder of the agent that was running, then rerun rec.sh.

Next, per agent, once its .done marker exists:
1. Dump the run: `python /workspace/r9/dump.py /workspace/refagents/repo/<slug>`.
2. Write the audit section in docs/blind/r10/AUDIT.md.
3. Export: `judge-venv python /workspace/refagents/agentest_export/export_v34.py /workspace/agentest-r10/docs/blind/r10 aNNN`. The exporter is already patched by addexport.py; the backup is export_v34.bak.
4. Commit and push **before** running agentest on that agent.
5. Score with: `/workspace/ag10 std run --agents docs/blind/r10/agents --blind --trace-key-file /workspace/refagents-trust/key/harness.key --mode examples --run-env cpu --max-na 1 --judge http://127.0.0.1:8008/v1 --judge-model Qwen2.5-7B-Instruct-Q4_K_M --judge-cache docs/blind/r10-judge-cache.jsonl --judge2 http://127.0.0.1:8010/v1 --judge2-model gemma-3-4b-it-Q4_K_M --judge2-cache docs/blind/r10-judge2-cache.jsonl --json docs/blind/r10-blind-results-examples.json`
6. Write docs/blind/r10/SCORE.md: precision, recall and control false alarms. Pass bar: P ≥ 0.95, R ≥ 0.95, 0 control FAs.
