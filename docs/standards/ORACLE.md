# Optional offline semantic oracle (v3.5)

The judge (`JUDGE.md`) answers open semantic questions with an LLM. The **oracle** is a smaller, stricter tool for
*closed* questions with a fixed label set, such as "is this tool call a break-glass access?". It runs on your own
machine, is deterministic, caches every answer, and is entirely optional: pyyaml stays the only required dependency.

## How it decides

An oracle task (`src/agentest/standards/oracle_tasks/*.json`, or your own file) has labels, a few prototype texts per
label, and a prompt for a small language model (SLM). Three methods:

| method | what decides |
|---|---|
| `embedding` | Nearest-prototype cosine per label. The margin between the best and second-best label decides; inside the `abstain` band nothing is decided (`not-assessed`). |
| `embedding+slm` (default) | The embedding is a **recall pre-filter**: a text at least `reject_margin` closer to the negatives is decided at once. Every other text goes to the SLM. |
| `slm` | The SLM alone. |

The SLM's answer must be one of the task's labels. Anything else is `not-assessed`. The oracle never falls back to
keywords or regular expressions.

## Determinism

- Temperature 0, greedy decoding, a fixed seed (`AGENTEST_ORACLE_SEED`, default 0). Grammar-constrained labels with
  the in-process llama.cpp backend.
- Vectors are L2-normalised and rounded to 6 decimals before use.
- Every vector and label is cached in JSON lines, keyed by `sha256(model id | kind | task@version | text)`. A new model
  or task version never reuses an old answer.
- `AGENTEST_ORACLE_OFFLINE=1` answers from the cache only. CI replays a committed cache this way, with no model and no
  network. A cache miss is `not-assessed`.

## Backends

| spec (`AGENTEST_ORACLE_EMBED`, `AGENTEST_ORACLE_SLM`) | needs |
|---|---|
| `hash` | Nothing. Character-trigram hashing: deterministic, **not semantic**. Use it for plumbing tests and as a lower bound. |
| `llamacpp:/path/model.gguf` | `pip install "agentest[oracle-llamacpp]"` (llama-cpp-python) |
| `onnx:/path/model_dir` (`model.onnx` + `tokenizer.json`) | `pip install "agentest[oracle-onnx]"` (onnxruntime, tokenizers, numpy). Single-threaded for bit-stable sums. |
| `http://127.0.0.1:8080/v1` | Nothing (standard library). A local OpenAI-compatible server such as llama.cpp `llama-server`. Loopback only unless `AGENTEST_ORACLE_ALLOW_REMOTE=1`. |
| `replay` | Nothing. Cache only. |

Other settings: `AGENTEST_ORACLE_CACHE` (default `~/.cache/agentest/oracle.jsonl`), and `AGENTEST_ORACLE_EMBED_MODEL` /
`AGENTEST_ORACLE_SLM_MODEL` (the model name sent to an HTTP server, also used as the cache id for `replay`).

Models used for the worked example (all local, zero cost):

- embeddings: `bge-m3` GGUF Q4_K_M (gpustack/bge-m3-GGUF)
- SLM: Qwen2.5-7B-Instruct GGUF Q4_K_M behind a local llama.cpp-compatible server

## From Python

```python
from agentest.standards import oracle as O

o = O.configure(embed="llamacpp:/models/bge-m3-Q4_K_M.gguf", slm="http://127.0.0.1:8080/v1")
d = o.classify(O.load_task("break-glass"), 'request_access {"mode": "emergency override"}')
d.label, d.via, d.margin   # ('break_glass', 'slm', 0.13)
```

In a rule, let `OracleUnavailable` propagate. It is a `NotAssessed`, so the verdict becomes `not-assessed`. For a
complete example that replaces a regex heuristic, see `examples/oracle_regex_replacement/`.

## What it is not

The oracle is not calibrated. Its prototypes and prompts are open and generic, not tuned on any agent. Measured
accuracy on the example's evaluation texts is reported in that example's README, misses included.
