# Catalogue and Hugging Face

Moved from the README. How the GitHub runner and the Hugging Face checklist fit together.

## Catalogue

The test IDs come from the open catalogue on Hugging Face. The reference agents are the systems under test.
- Dataset: [Agentic AI Test Checklist 110](https://huggingface.co/datasets/srinivaspadmanabhuni/agentic-ai-test-checklist-110) (test definitions, manual procedures, standards crosswalk). Hub configs include `golden` and `golden_v2` (pass/fail oracle cases for assessable core tests).
- Reference agents: [agentic-ai-reference-agents](https://huggingface.co/srinivaspadmanabhuni/agentic-ai-reference-agents) (runnable agents, code only, with recorded runs).
- Viewer Space: [agentic-ai-reference-agents-viewer](https://huggingface.co/spaces/srinivaspadmanabhuni/agentic-ai-reference-agents-viewer) (browse the recorded runs).

### From GitHub to Hugging Face and back

- **Read the tests** in the [dataset](https://huggingface.co/datasets/srinivaspadmanabhuni/agentic-ai-test-checklist-110): each ID's objective, acceptance criteria, manual procedure and standards
  crosswalk. Every verdict this repository prints uses the same IDs.
- **Try the checks in your browser** with the [Assurance Report Card Space](https://huggingface.co/spaces/srinivaspadmanabhuni/agentest-assurance-report-card): paste an agent prompt or agent
  logic (rule-based design review mapped to checklist IDs) or a trace (judged by these rules, run offline in the page).
  See its [sample output](https://huggingface.co/spaces/srinivaspadmanabhuni/agentest-assurance-report-card/blob/main/samples/SAMPLE_OUTPUT.md).
- **Run them in CI** from here: [Install](#install), [Quickstart](#quickstart), JUnit / SARIF output.
- The dataset card and the Space link back to this repository.

**Load the checklist in three lines:**

```python
from datasets import load_dataset
ds = load_dataset("srinivaspadmanabhuni/agentic-ai-test-checklist-110", "p0_smoke", split="train")
print(ds[0]["id"], ds[0]["title"])  # T1-001  Terminal postconditions hold after a single agent task
```

`p0_smoke` is the 47 highest-priority tests and loads in a few seconds. Config `all` has all 110 tests; `traces` has 440 labelled synthetic traces (`label` is `pass` or `fail`; the labels come from class templates, so treat them as examples of a failure shape, not recordings of real agents). Then run the checks on a bundled sample agent with the [60-second first win](../README.md#60-second-first-win), or open the [Colab](https://colab.research.google.com/github/srpadmanabhuni/agentest/blob/main/examples/colab_quickstart.ipynb) (free CPU, no login, no model).

**Caveats:** some checks are uncalibrated regex heuristics. Reference-agent results come from a small local model (Qwen2.5-7B-Instruct, CPU) with a limited number of runs (k = 1-3). Some governance metadata uses a documented non-standard A2A extension ([`urn:agentest:a2a-ext:governance:v1`](standards/EXTENSION.md)).
