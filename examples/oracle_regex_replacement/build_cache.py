"""Rebuild oracle-cache.jsonl with local models and print the accuracy table (run once; tests replay the cache).

    /path/to/venv-with-llama-cpp/bin/python examples/oracle_regex_replacement/build_cache.py \\
        --gguf bge-m3-Q4_K_M.gguf --slm http://127.0.0.1:8008/v1 --slm-model Qwen/Qwen2.5-7B-Instruct-GGUF:Q4_K_M

Needs ``llama-cpp-python`` (extra ``oracle-llamacpp``) for the embedding and a loopback OpenAI-compatible server for
the SLM. Every SLM answer is cached for every case (not only the ones the hybrid sends to it), so the table can
compare regex, embedding only, SLM only and the hybrid from the cache alone.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1] / "src"))

import report  # noqa: E402

from agentest.standards import oracle  # noqa: E402

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--gguf", required=True)
    ap.add_argument("--slm", required=True)
    ap.add_argument("--slm-model", default="")
    ap.add_argument("--out", default=str(HERE / "oracle-cache.jsonl"))
    a = ap.parse_args()
    out = Path(a.out)
    if out.exists():
        out.unlink()
    o = oracle.Oracle(oracle.LlamaCppBackend(a.gguf), oracle.HttpBackend(a.slm, a.slm_model), out)
    rows = report.evaluate(o, warm=True)
    print(report.table(rows))
    print(json.dumps(report.summary(rows), indent=1))
