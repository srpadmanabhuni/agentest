# Head-to-head protocol: agentest vs DeepEval vs Inspect AI
Pre-registration draft, 29 Oct 2026. It becomes binding when `scripts/freeze.sh` writes FROZEN.sha256 and the hashes are committed (private). Nothing gets scored before then.

## 1. Datasets
| Dataset | Licence / terms | Labels | Role |
|---|---|---|---|
| TRAIL, [PatronusAI/TRAIL](https://huggingface.co/datasets/PatronusAI/TRAIL), [arXiv 2505.08638](https://arxiv.org/abs/2505.08638) | MIT plus HF gate terms: **do not reshare the submissions set**. TRAIL data stays private on the box (`data/`, `converted/trail*` and `results/*trail*` are git-ignored), and only aggregate scores are published | 148 traces (117 GAIA, 31 SWE-bench), span-located errors in 20 categories with impact; only 4 traces have no error | **Primary** for per-category defect scoring |
| τ-bench historical trajectories, [sierra-research/tau-bench](https://github.com/sierra-research/tau-bench), [arXiv 2406.12045](https://arxiv.org/abs/2406.12045) | MIT | task reward 0/1 for each trajectory | **Clean control and binary detection.** 40 failed + 40 passed, seed 42 |
| AgentRewardBench, [arXiv 2504.08942](https://arxiv.org/abs/2504.08942) | no licence declared | expert success/side-effect/looping labels | **Not used** until the authors confirm a licence. We adopt its protocol ideas only (see §6) |

## 2. Conversion (no agent-specific code)
- `scripts/convert_chat_to_otlp.py` reads OpenAI-style chat messages. It keeps every user turn, and puts any model text sent alongside a tool call into `agentest.tool.reason`.
- `scripts/convert_openinference_to_otlp.py` reads OpenInference span trees (TRAIL). It keeps the original span IDs, so findings can be scored by location. TOOL spans become `execute_tool` and LLM spans become `chat` with token usage. The top span becomes `invoke_agent`. Each tool call's reason is the model's text immediately before it.
- Both converters use only standard field names; no dataset, agent or tool names appear in code. Labels go to `labels.jsonl`, which no runner reads. Each trace is run as its own agentest invocation.

## 3. Mapping tool output to defect labels (frozen in `config/mapping.json`)
- **agentest:** a trace is flagged on any `fail`. Each check ID maps to one TRAIL category, and the mapping is set **on the dev split only**.
  - T5-015 and X-003 (the per-call-reason requirement) are **not excluded**. τ-bench GPT-4o traces really carry no reasons, and these checks report that truthfully.
  - Because neither dataset labels "missing reason" as a defect, their effect is reported twice: with and without them in detection (pre-registered as two rows, not chosen afterwards).
- **DeepEval** (default metrics and thresholds): TaskCompletionMetric, plus GEval "Correctness" (one fixed criterion sentence). A trace is flagged when success is False.
- **Inspect AI:** the built-in `model_graded_qa()` with its default template, replaying the transcript. Grade I means flagged.
- **TRAIL per-category:**
  - agentest emits categories through the mapping.
  - The competitors have no category output. They are scored at trace level only, and this is stated rather than inventing a mapping for them.
  - Location and joint accuracy use the TRAIL official scorer (`scripts/trail_calculate_scores.py`, fetched from [patronus-ai/trail-benchmark](https://github.com/patronus-ai/trail-benchmark)). agentest currently reports no span location in its verdicts, so it will score near 0 there. That is reported as a known gap.

## 4. Judge, cost and environment
- All three tools use the same judge: Qwen2.5-7B-Instruct-Q4_K_M at http://127.0.0.1:8008/v1 (llama.cpp, OpenAI-compatible), temperature 0, on CPU.
- No cloud keys are set, so API spend is zero. DeepEval telemetry is turned off.
- The judge sees the same transcript truncation (the last 6,000 chars) in every LLM-based tool.
- Tools run one after another, never at the same time, so their runtimes are comparable.

## 5. Freeze and hygiene
- `freeze.sh` hashes the protocol, scripts, mapping, splits, converted sample and data, and records the versions (`pip freeze`, the agentest version and commit, the judge GGUF sha256). `sha256sum -c` must pass before scoring.
- **Dev/test split:** TRAIL is split 30% dev / 70% test with seed 42, stratified by source (GAIA 35/82, SWE 9/22), in `splits/`. All mapping and configuration choices are made on dev. Test is scored **once**, after the freeze. τ-bench is used as test only, with no tuning.

## 6. Best practices adopted (with sources)
| # | Practice | How it is built in | Source |
|---|---|---|---|
| 1 | TRAIL official metrics: per-category F1, location accuracy, joint location+category accuracy | `trail_calculate_scores.py` (official) plus per-category F1 in `score.py` | [TRAIL arXiv 2505.08638](https://arxiv.org/abs/2505.08638), [scorer](https://github.com/patronus-ai/trail-benchmark/blob/main/benchmarking/calculate_scores.py) |
| 2 | pass^k reliability | X-049 (v4.1) already does repeats. Here k=1 traces are fixed, so pass^k applies only where τ-bench has several trials per task (`trial` field), reported as agreement across trials | [τ-bench arXiv 2406.12045](https://arxiv.org/abs/2406.12045) |
| 3 | Score the judges against expert labels, with precision as the headline (false positives are costly) | precision first, recall, false-alarm rate | [AgentRewardBench arXiv 2504.08942](https://arxiv.org/abs/2504.08942) |
| 4 | Agentic Benchmark Checklist: task and outcome validity, report limitations, prevent shortcuts | §8 limitations; no labels reach runners; checklist walk-through in the report appendix | [ABC / "Establishing Best Practices for Building Rigorous Agentic Benchmarks" arXiv 2507.02825](https://arxiv.org/abs/2507.02825) |
| 5 | Confidence intervals; paired comparison; plan sample size | bootstrap 95% CI over traces (B=2000, seed 42) for F1; paired McNemar | [Miller, "Adding Error Bars to Evals" arXiv 2411.00640](https://arxiv.org/abs/2411.00640) |
| 6 | No CLT intervals at small n | Wilson intervals for precision, recall and false-alarm rate | [Bowyer et al., ICML 2025](https://proceedings.mlr.press/v267/bowyer25a.html) |
| 7 | Exact McNemar test between tools on the same traces | `mcnemar_exact` | [Dietterich 1998, Neural Computation](https://doi.org/10.1162/089976698300017197); [Dror et al. ACL 2018](https://aclanthology.org/P18-1128/) |
| 8 | Statistical power and sample size | minimal detectable recall difference printed with the results; underpowered contrasts are labelled "inconclusive" | [Card et al. EMNLP 2020 arXiv 2010.06595](https://arxiv.org/abs/2010.06595) |
| 9 | Macro **and** micro averages; class balance reported | `macro_micro`; positives and clean counts per split and the support for each category | [TRAIL](https://arxiv.org/abs/2505.08638) (weighted F1); [Opitz & Burst arXiv 1911.03347](https://arxiv.org/abs/1911.03347) |
| 10 | Cohen's kappa against human labels | `kappa` per tool | [Cohen 1960](https://doi.org/10.1177/001316446002000104); used for judge agreement in [Zheng et al. arXiv 2306.05685](https://arxiv.org/abs/2306.05685) |
| 11 | Judge position and verbosity bias controls | single-answer grading only (no pairwise comparison, so position bias does not arise); fixed truncation for every tool; length of flagged vs clean transcripts is reported (verbosity check) | [Zheng et al. MT-Bench/Judge arXiv 2306.05685](https://arxiv.org/abs/2306.05685) |
| 12 | Report abstentions; never count them silently | not-assessed, judge errors and missing outputs are counted per tool. Primary rule: an abstention = not flagged; a sensitivity row excludes them | [Trust or Escalate arXiv 2407.18370](https://arxiv.org/abs/2407.18370) |
| 13 | Report cost and latency next to accuracy | wall-clock per trace (median, total), judge tokens, $0 API | [Kapoor et al. "AI Agents That Matter" arXiv 2407.01502](https://arxiv.org/abs/2407.01502) |
| 14 | Error analysis by category | per-category table with support; 10 sampled FPs/FNs per tool, described in aggregate (no TRAIL text quoted) | [TRAIL](https://arxiv.org/abs/2505.08638); [ABC](https://arxiv.org/abs/2507.02825) |
| 15 | Contamination check | the competitors and agentest use the same judge, so contamination affects them equally. Recorded: the judge's training cutoff (Qwen2.5, Sept 2024) vs. dataset release (TRAIL May 2025: after the cutoff; τ-bench Jun 2024: possible exposure, flagged). agentest's rules were not written from TRAIL test traces (dev only) | [Xu et al. survey arXiv 2406.04244](https://arxiv.org/abs/2406.04244) |
| 16 | Transparency and reproducibility: seeds, versions, hashes, full configs, all scenarios published including losses | FROZEN.sha256, FROZEN.versions, seeds 42; full per-tool tables | [HELM arXiv 2211.09110](https://arxiv.org/abs/2211.09110) |
| 17 | Pre-registration and no tuning on test | §5 | [ABC](https://arxiv.org/abs/2507.02825); [Bowman & Dahl arXiv 2104.02145](https://arxiv.org/abs/2104.02145) |
| 18 | Fair competitor configuration | default metrics and templates, only the model swapped; versions cited (deepeval 4.3.2, inspect-ai 0.3.286) | [HELM](https://arxiv.org/abs/2211.09110) (standardised conditions) |

**Rejected or deferred:**
- **TRAIL's Pearson correlation on reliability, security and similar scores:** rejected. No tool here outputs those 1–5 scores, and inventing them would be unfair.
- **Pairwise / position-swap judging:** not applicable, because every tool grades one trace at a time.
- **Several judges / a jury** ([arXiv 2404.18796](https://arxiv.org/abs/2404.18796)): deferred. The primary run uses one shared judge for fairness. A Gemma 3 4B second-judge run is an optional sensitivity row.
- **Repeated sampling of the judge (k>1) to estimate judge variance** ([Miller](https://arxiv.org/abs/2411.00640)): deferred because of runtime. Temperature is 0, and 10 traces are re-run once to report the flip rate.
- **Canary strings / n-gram overlap contamination tests:** rejected. We test evaluators, not the generating model, so the overlap of the judge's training data with these traces cannot be measured with the tools on the box.
- **AgentRewardBench data:** deferred until its licence is confirmed.

## 7. Metrics reported
- For each tool, on each dataset and split:
  - n, positives and clean counts;
  - TP, FP and FN, precision, recall and F1, with Wilson and bootstrap CIs;
  - false-alarm rate on clean traces;
  - Cohen's kappa;
  - abstentions;
  - median and total runtime.
- Pairwise McNemar tests.
- TRAIL only: agentest's per-category, macro and micro F1, and the official location and joint accuracy.

## 8. Known limitations (stated in the report)
- **τ-bench labels:** they cover task outcome, not defect type. Clean (reward=1) traces may still contain defects, and reward=0 traces may be user-simulator faults.
- **TRAIL has almost no clean traces (4).** Its trace-level precision is therefore uninformative, and false alarms come from τ-bench.
- **agentest location output:** agentest gives no span locations yet.
- **Competitor categories:** the competitors have no category output.
- **Weak judge:** a 7B local judge is weaker than the GPT-4-class judges the competitors' defaults assume. This is applied equally to all tools and stated.
