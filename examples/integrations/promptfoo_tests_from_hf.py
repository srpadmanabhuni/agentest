"""Convert the agentest checklist examples CSV on HF into a promptfoo tests file (stdlib only).
Usage: python promptfoo_tests_from_hf.py [limit]  -> writes tests.yaml-compatible tests.json
"""
import csv
import io
import json
import sys
import urllib.request

URL = ("https://huggingface.co/datasets/srinivaspadmanabhuni/agentic-ai-test-checklist-110"
       "/resolve/main/examples/examples-v1.3.0.csv")
limit = int(sys.argv[1]) if len(sys.argv) > 1 else None
text = urllib.request.urlopen(URL, timeout=60).read().decode("utf-8")
tests = []
for r in list(csv.DictReader(io.StringIO(text)))[:limit]:
    tests.append({
        "description": f'{r["example_id"]} {r["title"]}',
        "vars": {"scenario": r["scenario"], "input": r["input"]},
        "assert": [{"type": "llm-rubric", "value": r["expected_behavior"]}],
        "metadata": {"test_id": r["test_id"], "severity": r["severity"]},
    })
json.dump(tests, open("tests.json", "w"), indent=1)
print(f"wrote {len(tests)} tests to tests.json")
