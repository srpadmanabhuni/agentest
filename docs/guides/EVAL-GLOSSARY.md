# AI Evaluation Glossary and agentest Mappings

A practical glossary of foundational AI evaluation concepts defined in plain language, with direct mappings to agentest commands, flags, schema fields, and report sections.

agentest runs offline, deterministic evaluations over recorded OpenTelemetry GenAI traces without relying on an LLM-as-a-judge. Use this glossary to translate common evaluation terminology into concrete agentest testing artifacts.

---

## 1. Task

### Definition
A **task** represents a distinct objective, prompt, scenario, or operational workload assigned to an AI agent. It encapsulates the problem description, required inputs, preconditions, and expected success criteria against which the agent's actions are evaluated.

### agentest Mapping
* **Trace Schema / Field**: `agentest.task.id` (or the top-level scenario identifier in imported traces) groups multiple runs under one common task definition.
* **CLI & Configuration**: Loaded via `--agent <name>` or through `--config <file>` (under the `scenarios` key) with expected outcomes for evaluation.
* **Reporting**: In Markdown, HTML, and JSON reports, results are aggregated and structured per task.

---

## 2. Trial

### Definition
A **trial** is a single, recorded execution attempt or episode of a given task by an agent. Because generative models and autonomous agents can exhibit stochastic reasoning trajectories, evaluating an agent on a task often involves executing multiple independent trials ($k$ trials) to measure consistency and variance.

### agentest Mapping
* **Trace Schema / Field**: Each trial corresponds to a unique session or run within an OpenTelemetry OTLP trace file (differentiated by run ID, session attributes, or repeated task entries).
* **CLI Flags**: Evaluated by passing multi-trial trace logs to `agentest std run --otlp <path>`.
* **Reporting**: Grouped under the **Trials** section in markdown, HTML, and JSON reports, reporting `k`, `passes`, `pass@k`, `pass^k`, and `SE` (standard error), grouped by `agentest.task.id`.
* **Guardrail Checks**: Check `NT-041` validates that repeated trials of a task maintain identical initial state declarations without cross-trial contamination.

---

## 3. Grader

### Definition
A **grader** (or evaluator) is the decision mechanism that inspects the agent's outputs, actions, intermediate tool calls, or final state changes to assign a verdict (such as pass, fail, or non-applicable). Unlike probabilistic LLM judges, agentest employs deterministic, rule-based graders that execute entirely offline.

### agentest Mapping
* **Rules & Checks**: The 165 tests (spanning `T1-001` through `T7-014`, plus opt-in NT checks) serve as deterministic graders.
* **CLI Command**: `agentest std run` acts as the execution runner invoking the check suite.
* **Custom Graders**: Extra rule modules can be imported using the `--config` file's `rules_dir` parameter.

---

## 4. Transcript

### Definition
A **transcript** is the complete temporal record of an agent's execution. It captures all user inputs, model prompts, generated messages, tool invocations, argument payloads, environment observation responses, error codes, and intermediate internal reasoning steps.

### agentest Mapping
* **Trace Format**: Standardized OpenTelemetry GenAI spans (`gen_ai.system`, `gen_ai.prompt`, `gen_ai.completion`, and tool execution spans) stored in OTLP/JSONL format.
* **CLI Commands**:
  * `agentest std import <log>` converts heterogeneous agent event logs into standardized OTLP transcripts.
  * `agentest record` (in Python API) logs in-process tool calls and steps directly into an evaluation transcript.
* **Trace Readers**: Spans in the transcript provide the exact evidence lines surfaced in fail reports.

---

## 5. Outcome

### Definition
The **outcome** is the final state of the environment, external systems, and session results after the agent concludes its execution. While an agent's transcript reveals *how* it proceeded, the outcome verifies whether the intended state transitions actually occurred (e.g., record created in a database, balance updated, or empty cart avoided).

### agentest Mapping
* **Trace Schema / Fields**: Postconditions and environment assertions declared in scenarios or trace attributes (such as end-state object ledgers).
* **Core Checks**:
  * `T1-001`: Verifies that claimed outcomes match verified state changes.
  * `T1-018`: Prevents unearned success claims (e.g., claiming a purchase completed when no state write occurred).
* **Reporting**: Detailed in the report's verdict summary under postcondition satisfaction.

---

## 6. Pass@k

### Definition
$\text{pass}@k$ is an evaluation metric measuring the probability that an agent succeeds at least once across $k$ independent trials of a task. It quantifies whether an agent possesses the capacity or capability to solve a task when given multiple attempts.

$$\text{pass}@k = \mathbb{E}\left[1 - \frac{\binom{n - c}{k}}{\binom{n}{k}}\right]$$

*(where $n$ is total trials sampled and $c$ is the number of successful trials)*

### agentest Mapping
* **Reporting Section**: Computed and displayed in the **Trials** summary (`k`, `passes`, `pass@k`, `pass^k`, `SE`) of versioned JSON, Markdown, and HTML reports when $k > 1$ trials are present for a task.
* **CLI Comparison**: Analyzed across runs using `agentest std diff OLD.json NEW.json` to observe whether capability thresholds improve across versions.

---

## 7. Pass^k

### Definition
$\text{pass}^k$ (or strict consistency pass rate) measures the probability that an agent succeeds on *all* $k$ consecutive trials of a task without failing any attempt ($P(\text{all } k \text{ trials pass}) = (\text{pass rate})^k$). This metric assesses reliability and deterministic repeatability for mission-critical production workflows.

### agentest Mapping
* **Reporting Section**: Displayed alongside $\text{pass}@k$ in the **Trials** summary (`k`, `passes`, `pass@k`, `pass^k`, `SE`) of evaluation reports to highlight variance and brittleness.
* **Core Checks**: Check `NT-042` verifies consistency requirements for tasks marked with `consistency_required`, ensuring every trial satisfies declared postconditions.

---

## 8. Capability Suite vs. Regression Suite

### Definition
* **Capability Suite**: A diagnostic, exploratory collection of evaluation checks applied broadly across an agent's tasks to identify behavioral blindspots, security weaknesses, and uncaught failure modes. Low pass rates are expected and informative.
* **Regression Suite**: A curated, graduated subset of checks that previously caught real defects and have since been resolved. Run in continuous integration (CI) pipelines to guarantee that fixed issues never reoccur.

### agentest Mapping
* **Configuration Files**:
  * `templates/capability.yaml`: Configured with an extensive selection of `--ids` to survey system capabilities without blocking builds.
  * `templates/regression.yaml`: Configured with graduated check IDs that must consistently pass.
* **CLI Execution Modes**:
  * Capability runs omit `--strict` so full reports can be inspected:
    ```bash
    agentest std run --otlp traces.otlp.jsonl --config templates/capability.yaml --ids T1-018,T4-001,T5-009,T6-007,T7-014 --format md --out capability.md
    ```
  * Regression runs include `--strict` to exit with status 1 if any check fails, gating pull requests and builds:
    ```bash
    agentest std run --otlp traces.otlp.jsonl --config templates/regression.yaml --ids T1-018,T2-001 --format junit --out agentest.xml --strict
    ```
* **CLI Comparison Tool**: `agentest std diff --fail-on-new-fail` tracks check transitions between baseline and candidate runs to flag regressions automatically.
