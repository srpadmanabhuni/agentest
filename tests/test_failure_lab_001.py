"""Failure Lab 001: a refund retried after a tool timeout must create one refund, not two.

The recorded-trace tests need agentest only. The end-to-end tests run the OpenAI Agents SDK example's
refund workflow with a scripted model; they need ``pip install openai-agents==0.26.0`` and skip without it.
``--runxfail`` shows the original (unfixed) tool contract failing.
"""

from __future__ import annotations

import asyncio
import json
import sys
from importlib import metadata
from pathlib import Path

import pytest

import agentest

LAB = Path(__file__).resolve().parents[1] / "examples" / "failure-lab" / "001-refund-timeout-retry"
CHECKS = "T2-003,T1-006,T1-011"


def _verdicts(variant: str) -> dict[str, str]:
    doc = json.loads((LAB / "traces" / f"{variant}.otlp.json").read_text(encoding="utf-8"))
    return {c.id: c.status for c in agentest.run(doc, tools=str(LAB / "tools.json"), ids=CHECKS)}


def test_recorded_original_run_shows_two_refunds_and_is_caught():
    run = json.loads((LAB / "traces" / "original.run.json").read_text(encoding="utf-8"))
    assert [r["refund_ticket"] for r in run["refunds"]] == ["RF-1001", "RF-1002"]
    assert _verdicts("original") == {"T2-003": "fail", "T1-006": "fail", "T1-011": "fail"}


def test_recorded_fixed_run_shows_one_refund_and_passes():
    run = json.loads((LAB / "traces" / "fixed.run.json").read_text(encoding="utf-8"))
    assert [r["refund_ticket"] for r in run["refunds"]] == ["RF-1001"]
    assert _verdicts("fixed") == {"T2-003": "pass", "T1-006": "pass", "T1-011": "pass"}


def test_reproduce_script_readme_and_registry_name_the_same_checks():
    """The script, the README sample output and AFR-0001 must judge the checks that actually catch this failure."""
    script = (LAB / "reproduce.py").read_text(encoding="utf-8")
    assert f'CHECKS = "{CHECKS}"' in script
    readme = (LAB / "README.md").read_text(encoding="utf-8")
    assert f"--ids {CHECKS}" in readme
    for cid in CHECKS.split(","):
        assert f"{cid} fail " in readme and f"{cid} pass " in readme
    root = Path(__file__).resolve().parents[1]
    entry = json.loads((root / "registry" / "entries" / "AFR-0001.json").read_text(encoding="utf-8"))
    ids = set(CHECKS.split(","))
    assert set(entry["failing_checks"]) == ids
    assert set(entry["variants"]["original"]["expected_verdicts"]) == ids
    assert set(entry["variants"]["fixed"]["expected_verdicts"]) == ids
    assert f"--ids {CHECKS}" in entry["reproduce"]["judge"]


def _ledger_module():
    """The refund service needs no SDK, so these tests run everywhere."""
    sys.path.insert(0, str(LAB))
    try:
        import refund_ledger
    finally:
        sys.path.remove(str(LAB))
    return refund_ledger


def _create(ledger, key, order="ORD-1001", amount=49.99, reason="Item arrived damaged"):
    ledger.slow_replies = 0  # no late reply needed here
    return asyncio.run(ledger.create(order, amount, reason, idempotency_key=key))


def test_retry_with_the_same_request_key_returns_the_same_refund():
    ledger = _ledger_module().RefundLedger()
    first = _create(ledger, "req-1")
    retry = _create(ledger, "req-1")
    assert [r["refund_ticket"] for r in ledger.rows] == ["RF-1001"]
    assert retry["refund_ticket"] == first["refund_ticket"] == "RF-1001"
    assert retry["replayed"] is True and "replayed" not in first


def test_two_separate_requests_with_identical_arguments_both_create_a_refund():
    ledger = _ledger_module().RefundLedger()
    first = _create(ledger, "req-1")  # one request key minted per intended refund
    second = _create(ledger, "req-2")  # a new request, every argument the same
    assert [r["refund_ticket"] for r in ledger.rows] == ["RF-1001", "RF-1002"]
    assert first["refund_ticket"] == "RF-1001" and second["refund_ticket"] == "RF-1002"
    assert "replayed" not in second


def test_argument_derived_key_cannot_tell_a_repeat_from_a_retry():
    module = _ledger_module()
    ledger = module.RefundLedger()
    key = module.refund_key("ORD-1001", 49.99)
    _create(ledger, key)
    repeat = _create(ledger, key)  # a genuinely separate request, same arguments
    assert [r["refund_ticket"] for r in ledger.rows] == ["RF-1001"], "the limit the README describes: no second refund"
    assert repeat["replayed"] is True


def _sdk():
    try:
        version = metadata.version("openai-agents")
    except metadata.PackageNotFoundError:
        pytest.skip("pip install openai-agents==0.26.0 to run the workflow end to end")
    if version != "0.26.0":
        pytest.skip(f"Failure Lab 001 is pinned to openai-agents 0.26.0, found {version}")
    sys.path.insert(0, str(LAB))
    import refund_agent
    from to_trace import TOOLS, build_trace

    return refund_agent, TOOLS, build_trace


@pytest.mark.parametrize("variant", [
    "fixed",
    pytest.param("original", marks=pytest.mark.xfail(strict=True, reason="Failure Lab 001: the retried refund is created twice")),
])
def test_timeout_retry_creates_one_refund(variant, monkeypatch):
    monkeypatch.setenv("OPENAI_AGENTS_DISABLE_TRACING", "1")
    refund_agent, tools, build_trace = _sdk()
    run = refund_agent.run_scenario(variant)
    calls = [i for i in run["items"] if i.get("type") == "function_call" and i["name"] == "submit_refund"]
    assert len(calls) == 2, "the scenario must time out once and retry once"
    assert len(run["refunds"]) == 1, f"refunds created: {[r['refund_ticket'] for r in run['refunds']]}"
    agentest.assert_passes(agentest.run(build_trace(run), tools=str(tools), ids=CHECKS), ids=CHECKS)
