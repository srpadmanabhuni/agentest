#!/usr/bin/env python3
"""Offline first run: judge the bundled good and buggy agents and print the failing checks.

CPU only. No account, API key, GPU or model. agentest's only package dependency is PyYAML.
The OpenTelemetry trace shape and the JUnit CI workflow already live in this repo
(examples/otel_plain/emit_trace.py, docs/developers/CI.md); this script does not add a second copy.

Optional catalogue load (off unless you ask, or you are in Colab): one Hugging Face config,
``all``, split ``train``. That uses the third-party ``datasets`` package, which is not an
agentest dependency. The library cache is left as-is (no forced re-download).

  python examples/colab_quickstart.py
  python examples/colab_quickstart.py --load-dataset
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AGENTS = "examples/agnostic_demo/agents"
DATASET_ID = "srinivaspadmanabhuni/agentic-ai-test-checklist-110"
CATALOGUE_CONFIG = "all"  # live default config on the dataset card
CATALOGUE_SPLIT = "train"
HIGHLIGHT = "T2-001"
EXPECTED_CLEAN = "refill_bot: 55 pass, 0 fail"
EXPECTED_BUGGY = "refill_bot_buggy: 41 pass, 16 fail"

# Walkthroughs already in docs/walkthroughs/. Ids not listed there are still printed below.
WALKTHROUGH_FOR = {
    "T2-001": "docs/walkthroughs/01-verify-before-acting.md",
    "T2-005": "docs/walkthroughs/01-verify-before-acting.md",
    "T4-001": "docs/walkthroughs/02-instructions-hidden-in-tool-output.md",
    "T4-002": "docs/walkthroughs/02-instructions-hidden-in-tool-output.md",
    "T4-003": "docs/walkthroughs/02-instructions-hidden-in-tool-output.md",
    "T4-012": "docs/walkthroughs/02-instructions-hidden-in-tool-output.md",
    "T1-002": "docs/walkthroughs/03-claims-success-it-did-not-earn.md",
    "T1-018": "docs/walkthroughs/03-claims-success-it-did-not-earn.md",
    "T3-006": "docs/walkthroughs/03-claims-success-it-did-not-earn.md",
    "T7-014": "docs/walkthroughs/04-personal-data-left-unmasked.md",
}
ALREADY_IN_REPO = (
    "docs/walkthroughs/README.md",
    "docs/walkthroughs/05-bring-your-own-log.md",
    "examples/otel_plain/emit_trace.py",
    "docs/developers/CI.md",
    "docs/GETTING-STARTED.md",
    "docs/testers/QUICKSTART.md",
)


def _cli_env() -> dict[str, str]:
    env = os.environ.copy()
    src = str(ROOT / "src")
    prev = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = src if not prev else src + os.pathsep + prev
    env.pop("AGENTEST_HUB_CATALOGUE", None)  # this demo stays on the vendored catalogue
    return env


def _invoked_as_script() -> bool:
    return Path(sys.argv[0]).name == "colab_quickstart.py"


def want_dataset_load() -> bool:
    """One catalogue load: explicit flag or env, else only when running in Colab."""
    if _invoked_as_script():
        if "--no-dataset" in sys.argv:
            return False
        if "--load-dataset" in sys.argv:
            return True
    env = os.environ.get("AGENTEST_COLAB_LOAD_DATASET")
    if env is not None and env.strip() != "":
        return env.strip().lower() in {"1", "true", "yes", "on"}
    return bool(os.environ.get("COLAB_RELEASE_TAG", "").strip())


def _fail(msg: str, code: int = 1) -> None:
    print(msg, file=sys.stderr)
    raise SystemExit(code)


def _run_agents() -> tuple[str, dict]:
    with tempfile.TemporaryDirectory() as td:
        dest = Path(td) / "report.json"
        proc = subprocess.run(
            [sys.executable, "-m", "agentest", "std", "run", "--agents", AGENTS, "--json", str(dest)],
            cwd=ROOT,
            env=_cli_env(),
            text=True,
            capture_output=True,
        )
        if proc.returncode != 0:
            _fail(proc.stderr or proc.stdout or f"agentest exited {proc.returncode}")
        if not dest.is_file():
            _fail("agentest did not write the JSON report")
        return proc.stdout, json.loads(dest.read_text(encoding="utf-8"))


def _catalogue_row(test_id: str) -> dict | None:
    path = ROOT / "catalog" / "checklist-110.jsonl"
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("id") == test_id:
            return row
    return None


def _cell(text: str, n: int = 160) -> str:
    return " ".join(text.split())[:n].replace("|", "/")


def _print_report(stdout: str, res: dict) -> list[str]:
    print(stdout.rstrip())
    print()
    if EXPECTED_CLEAN not in stdout or EXPECTED_BUGGY not in stdout:
        _fail(f"demo summary drifted from the documented counts:\n{stdout}")
    clean, buggy = res.get("refill_bot"), res.get("refill_bot_buggy")
    if not clean or not buggy:
        _fail(f"expected refill_bot and refill_bot_buggy, got {sorted(res)}")
    fails = sorted(i for i, c in buggy.items() if c["status"] == "fail")
    if HIGHLIGHT not in fails:
        _fail(f"{HIGHLIGHT} did not fail on refill_bot_buggy")
    if clean[HIGHLIGHT]["status"] != "pass":
        _fail(f"{HIGHLIGHT} did not pass on refill_bot ({clean[HIGHLIGHT]['status']})")
    print("Failing checks on the buggy agent, next to the same check on the clean agent.")
    print("n/a is not a pass: the trace had no signal for that check.")
    print()
    print("| ID | refill_bot | refill_bot_buggy | evidence on the buggy agent | walkthrough |")
    print("|---|---|---|---|---|")
    linked: list[str] = []
    for i in fails:
        guide = WALKTHROUGH_FOR.get(i, "")
        if guide and guide not in linked:
            linked.append(guide)
        print(f"| {i} | {clean[i]['status']} | {buggy[i]['status']} | {_cell(buggy[i]['detail'])} | {guide} |")
    print()
    if any(i.startswith("X-") for i in fails):
        print("Rows starting with X- are repo extensions. They are not in the 110-row catalogue.")
        print()
    return linked


def _print_catalogue(test_id: str) -> None:
    row = _catalogue_row(test_id)
    if not row:
        _fail(f"{test_id} is not in catalog/checklist-110.jsonl")
    print(f"Catalogue row for {test_id} (vendored file, offline): {row['title']}")
    print(f"Objective: {_cell(row.get('objective', ''), 400)}")
    print(f"Acceptance criteria: {_cell(row.get('acceptance_criteria', ''), 400)}")
    print()


def _load_hub_row(test_id: str) -> None:
    if not want_dataset_load():
        print(
            "Hub catalogue was not loaded. "
            f"One load of {DATASET_ID} config {CATALOGUE_CONFIG!r} split {CATALOGUE_SPLIT!r} "
            "runs in Colab, or locally with --load-dataset or AGENTEST_COLAB_LOAD_DATASET=1. "
            "The datasets package is optional and is not an agentest dependency. Its cache is used as-is."
        )
        print()
        return
    try:
        from datasets import load_dataset
    except ImportError:
        _fail(
            "optional catalogue load needs the datasets package (not an agentest dependency): pip install datasets",
            code=2,
        )
    ds = load_dataset(DATASET_ID, CATALOGUE_CONFIG, split=CATALOGUE_SPLIT)
    rows = [r for r in ds if r.get("id") == test_id]
    if len(rows) != 1:
        _fail(
            f"config {CATALOGUE_CONFIG!r} split {CATALOGUE_SPLIT!r} has {len(rows)} rows for {test_id} (features: {list(ds.features)})",
            code=2,
        )
    print(f"Hub config {CATALOGUE_CONFIG} split {CATALOGUE_SPLIT}: {rows[0]['id']} — {rows[0]['title']}")
    print()


def _print_next(linked: list[str]) -> None:
    print("Already in this repository (not repeated here):")
    seen: list[str] = []
    for rel in sorted(linked) + [p for p in ALREADY_IN_REPO if p not in linked]:
        if rel not in seen:
            seen.append(rel)
            print(f"- {rel}")
    print()
    print("Own trace: python examples/otel_plain/emit_trace.py writes one OTLP/JSON trace with the standard library.")
    print("CI: docs/developers/CI.md runs agentest std run --format junit --out agentest.xml --strict")
    print("Contact: srinivas AT testAIng.com")


def main() -> int:
    stdout, res = _run_agents()
    linked = _print_report(stdout, res)
    _print_catalogue(HIGHLIGHT)
    _load_hub_row(HIGHLIGHT)
    _print_next(linked)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
