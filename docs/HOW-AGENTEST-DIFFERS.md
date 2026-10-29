# How agentest differs

This page compares agentest with six widely used LLM/agent evaluation and observability tools on how they
gather and trust evidence about agent behaviour. It is meant to be factual and fair. Each competitor claim
links to that project's own docs or repository. All sources were **accessed on 29 Oct 2026**. Where we could
not find a claim confirmed in official material, the table says **not documented**. That means we did not
find it documented, not that the feature is absent. Corrections are welcome as issues or PRs.

## Summary

These tools are mature and widely adopted. Most of them offer things agentest does not: hosted or self-hosted
UIs and dashboards, production-scale tracing, prompt management, human annotation, deep RAG metrics, dataset
generation, red-teaming scanners and broad framework integrations. agentest is narrower. It is a
trace-based test runner for agent behaviour, and in v4.0 it focuses on whether the trace being scored can be
trusted.

| | Where evidence comes from | Traces verified / signed | Forged-trace resistance | Tool calls checked against real tool traffic | Agent-agnostic tests |
|---|---|---|---|---|---|
| **agentest** | Harness-recorded traces (OpenTelemetry-compatible) plus structural checks and an optional local LLM judge | In v4.0 (in progress): harness-signed, hash-chained traces | In v4.0 (in progress): blind mode refuses unsigned traces; CI forgery test | In v4.0 (in progress): spans cross-checked against intercepted tool traffic | Yes; CI guard fails if test code names an agent |
| **Giskard** (v3) | Checks and scans on agent inputs/outputs; LLM judges via provider SDKs [G1] | Not documented | Not documented | Not documented | Library checks are generic; per-agent setup is user-written [G1] |
| **LangSmith / openevals / agentevals** | Traces, datasets, LLM-as-judge and trajectory evaluators [L1][L2][L3] | Not documented | Not documented | Not documented; trajectory evaluators compare the recorded message/tool-call trajectory to a reference [L2][L3] | Evaluators are generic; reference trajectories are per task [L2] |
| **Langfuse** | Traces (SDKs, OpenTelemetry), datasets, LLM-as-judge, code evaluators, user feedback, human annotation [F1][F2] | Not documented as shipped; a community proposal to add signing was closed [F3] | Not documented | Not documented | Framework- and model-agnostic platform [F2] |
| **DeepEval** | Test cases (`LLMTestCase`), traces from `@observe`, LLM-as-judge metrics, deterministic metrics [D1][D2] | Not documented | Not documented | `ToolCorrectnessMetric` compares `tools_called` you supply (or traced) against `expected_tools` [D2] | Metrics are generic; expected tools are per test case [D2] |
| **Ragas** | Datasets/samples of messages and tool calls, LLM-based and non-LLM metrics [R1][R2] | Not documented | Not documented | `ToolCallAccuracy` / `ToolCallF1` compare tool calls in the supplied conversation with `reference_tool_calls` [R2] | Metrics are generic; references are per sample [R2] |
| **Arize Phoenix** | OpenTelemetry/OpenInference traces, datasets and experiments, LLM evals [P1] | Not documented | Not documented | Not documented | Framework-agnostic via OpenTelemetry [P1] |

## The five questions in more detail

### 1. Where the evidence comes from
- **agentest** scores traces recorded by its own test harness: the tool calls, tool results, approvals and the
  final reply. Most checks are structural (deterministic code over the trace, with no model call). Checks about
  meaning use an optional local judge model. No check reads agent stdout, stderr or log files.
- **Giskard v3** describes itself as evals, red teaming and test generation for agentic systems, with LLM judges
  through optional provider extras [G1].
- **LangSmith** offers tracing and evaluation on hosted or self-hosted deployments [L1]. **openevals** and **agentevals**
  provide ready-made evaluators, including LLM-as-judge and trajectory match evaluators [L2][L3].
- **Langfuse** supports LLM-as-a-judge, code evaluators, user feedback and manual labelling on traces and datasets [F1][F2].
- **DeepEval** offers LLM-as-a-judge metrics and tracing that captures model decisions and tool calls for
  trajectory-based evals [D1]. Its tool-correctness score itself is deterministic [D2].
- **Ragas** evaluates conversation samples and offers test-data generation [R1]. Its agent metrics include
  `ToolCallAccuracy`, `ToolCallF1`, `TopicAdherence` and `AgentGoalAccuracy` [R2].
- **Phoenix** offers tracing over OpenTelemetry/OpenInference, datasets and experiments, and LLM-based evals [P1].

### 2. Whether traces are verified or signed
- **agentest, in v4.0 (in progress):** the harness signs each trace and hash-chains its events with a key the
  agent under test cannot access, so editing, removing or reordering events is detectable.
- **Others:** we found no documented cryptographic signing or hash-chaining of traces in the official docs of
  Giskard, LangSmith, openevals/agentevals, DeepEval, Ragas or Phoenix. For Langfuse, a community proposal to add
  trace signing through a third-party exporter was opened and later closed. We did not find it documented as a
  shipped feature [F3]. LangSmith's docs say its ingestion queue checks data integrity on insert [L1]. That refers to
  reliable storage, not to cryptographic verification of trace content.

### 3. Resistance to forged traces
- **agentest, in v4.0 (in progress):** blind mode refuses unsigned traces. When agentest has to rebuild tool calls
  from the model's own messages, the result is marked low-trust and fails in blind mode. A CI test runs a fake
  agent that forges log lines, success flags and approvals, and the build fails if any check passes it.
- **Others:** not documented. These tools generally score the trace or test case they are given, which suits
  their main use, debugging and evaluating your own applications.

### 4. Tool calls verified against real tool traffic, or only from recorded spans and outputs
- **agentest, in v4.0 (in progress):** each tool call in the trace is cross-checked against tool traffic the
  harness intercepted. A claimed call that was never seen fails as forged.
- **DeepEval** compares the `tools_called` on a test case (which can come from tracing) with `expected_tools` [D2].
  **Ragas** compares tool calls in the supplied messages with `reference_tool_calls` [R2]. **openevals/agentevals**
  compare an agent's trajectory with a reference trajectory [L2][L3]. In each case the docs describe matching the
  recorded or supplied calls. Cross-checking against independently intercepted tool traffic is not documented.
  For Giskard, Langfuse and Phoenix it is likewise not documented.

### 5. Agent-agnostic tests
- **agentest:** test code uses only the generic agent interface and traces. A blocking CI check fails if test
  code mentions any agent's ID, name or tool names.
- **Others:** all of these provide generic evaluators or metrics. Per-task references (expected tools, reference
  trajectories, datasets) are supplied by the user, which is normal and expected. We found no documented
  equivalent of a CI guard against agent-specific coupling in test code.

### Trust labels (agentest, in v4.0 (in progress))
Every result carries an evidence/trust label naming where its evidence came from: harness-recorded and
signed, cross-checked with traffic, judged by the local model, or self-reported by the agent. Uncorroborated
self-reports earn no credit in blind scores.

## Licence, pricing and self-hosting (brief)

| | Licence | Pricing | Self-hosting |
|---|---|---|---|
| **agentest** | Apache-2.0; only required runtime dependency is `pyyaml` | Free | Runs locally; no service needed |
| **Giskard** | Apache-2.0 [G1] | Open-source library [G1]; other offerings not reviewed here | Library runs locally [G1] |
| **LangSmith** | Proprietary platform; openevals and agentevals are MIT [L2][L3] | Developer $0 (1 seat, 5k base traces/mo), Plus $39/seat/mo, Enterprise custom [L4] | Self-hosted on Kubernetes as an Enterprise add-on [L1][L4] |
| **Langfuse** | MIT, except `ee` folders [F1] | Cloud: Hobby free, Core $29/mo, Pro $199/mo, Enterprise $2,499/mo [F2] | Free self-hosting (Docker Compose, Kubernetes) [F2] |
| **DeepEval** | Apache-2.0 [D1] | Open-source library; the vendor also offers the Confident AI platform [D1] | Library runs locally [D1] |
| **Ragas** | Apache-2.0 [R1] | Open-source library [R1] | Library runs locally [R1] |
| **Arize Phoenix** | Elastic License 2.0 [P2] | Open source; Arize also offers a commercial platform [P1] | Docker, Kubernetes/Helm and other options [P1] |

Prices change often. Check the linked pages for current figures.

## Where the others are stronger
- **Scale and production use:** LangSmith, Langfuse and Phoenix are built for production tracing at volume, with
  retention, alerts, RBAC/SSO and dashboards [L4][F2][P1].
- **UI and workflow:** playgrounds, prompt management, annotation queues and experiment comparison [F2][L4].
- **RAG and metric breadth:** Ragas and DeepEval have deep RAG and general LLM metric libraries, and Ragas does
  test-data generation [R1][D1].
- **Red teaming and scanning:** Giskard offers vulnerability scanning and test generation [G1].
- **Ecosystem:** broad framework integrations and large communities [D1][F1][P1].

agentest is meant to complement these tools, not replace them. It can read OpenTelemetry traces, so the same
instrumentation can feed both.

## Sources (all accessed 29 Oct 2026)
- [G1] Giskard README: https://github.com/Giskard-AI/giskard (docs: https://docs.giskard.ai/oss)
- [L1] Self-hosted LangSmith: https://docs.langchain.com/langsmith/self-hosted
- [L2] openevals: https://github.com/langchain-ai/openevals
- [L3] agentevals: https://github.com/langchain-ai/agentevals
- [L4] LangSmith pricing: https://www.langchain.com/pricing
- [F1] Langfuse README and licence: https://github.com/langfuse/langfuse
- [F2] Langfuse pricing and self-hosting FAQ: https://langfuse.com/pricing
- [F3] Langfuse issue #12774, trace-signing proposal (closed): https://github.com/langfuse/langfuse/issues/12774
- [D1] DeepEval README: https://github.com/confident-ai/deepeval
- [D2] DeepEval Tool Correctness: https://deepeval.com/docs/metrics-tool-correctness
- [R1] Ragas README: https://github.com/explodinggradients/ragas
- [R2] Ragas agent metrics: https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/agents/
- [P1] Arize Phoenix README: https://github.com/Arize-ai/phoenix
- [P2] Phoenix licence: https://github.com/Arize-ai/phoenix/blob/main/LICENSE
