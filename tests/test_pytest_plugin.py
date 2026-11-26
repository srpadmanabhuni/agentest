"""The pytest plugin judges a trace with the engine's checks and reports the failing check and its evidence."""

from __future__ import annotations

import importlib.metadata
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

import agentest
from agentest import CheckFailure, assert_checks

pytest_plugins = ["pytester"]

ROOT = Path(__file__).resolve().parents[1]
GOOD = (ROOT / "examples/agnostic_demo/agents/refill_bot").as_posix()
BUGGY = (ROOT / "examples/agnostic_demo/agents/refill_bot_buggy").as_posix()
FIRST = ROOT / "examples/first_trace"


@pytest.fixture
def pt(pytester: pytest.Pytester) -> pytest.Pytester:
    """A pytester that has the plugin: through the entry point when installed, by name otherwise (never both)."""
    if not any(e.name == "agentest" for e in importlib.metadata.entry_points(group="pytest11")):
        pytester.makeconftest("pytest_plugins = ['agentest.pytest_plugin']\n")
    return pytester


def _refund(rec: agentest.Recorder, answer: str) -> None:
    rec.tool("lookup_order", {"order_id": "A-1001"}, {"status": "delivered", "total": 40.0}, reason="check the order first")
    rec.tool("issue_refund", {"order_id": "A-1001", "amount": 40.0}, {"error": "payment service unavailable"}, error=True, reason="item arrived broken")
    rec.answer(answer)


def test_entry_point_is_declared_and_loads() -> None:
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert '[project.entry-points.pytest11]\nagentest = "agentest.pytest_plugin"' in text
    assert "[project.optional-dependencies]" in text and 'pytest = ["' not in text  # no extra: pytest is the user's own, and the plugin adds no dependency
    for entry in importlib.metadata.entry_points(group="pytest11"):  # present once the package is (re)installed
        if entry.name == "agentest":
            assert entry.value == "agentest.pytest_plugin"
            assert entry.load().__name__ == "agentest.pytest_plugin"


def test_plugin_does_not_make_pytest_a_runtime_dependency() -> None:
    code = "import sys, agentest; import agentest.cli; sys.exit(1 if 'pytest' in sys.modules else 0)"
    assert subprocess.run([sys.executable, "-c", code], cwd=ROOT).returncode == 0


def test_marker_checks_pass(pt: pytest.Pytester) -> None:
    pt.makepyfile(
        f"""
        import pytest

        @pytest.mark.agentest(trace={GOOD!r}, checks=["T1-018", "T2-001"])
        def test_ok():
            pass
        """
    )
    pt.runpytest().assert_outcomes(passed=1)


def test_failure_names_the_check_what_it_asserts_and_the_evidence(pt: pytest.Pytester) -> None:
    pt.makepyfile(
        f"""
        import pytest

        @pytest.mark.parametrize("agentest_trace", [{BUGGY!r}], indirect=True)
        def test_agent(agentest_trace):
            agentest_trace.assert_checks(["T1-018", "T4-003", "T2-001", "T1-003"])
        """
    )
    res = pt.runpytest()
    res.assert_outcomes(failed=1)
    res.stdout.fnmatch_lines(
        [
            "*agentest: 3 of 4 checks did not pass on*",
            "*FAIL  T1-018*",
            "*asserts:*",
            "*evidence: social#0: claims success*",
            "*FAIL  T4-003*",
            "*evidence: injected recipients:*audit@evil.example*",
            "*FAIL  T2-001*",
            "*passed: T1-003*",
        ]
    )


def test_marker_failure_is_the_message_alone(pt: pytest.Pytester) -> None:
    pt.makepyfile(
        f"""
        import pytest

        @pytest.mark.agentest(trace={BUGGY!r}, checks=["T1-018", "T4-003"])
        def test_agent():
            pass
        """
    )
    res = pt.runpytest()
    res.assert_outcomes(failed=1)
    out = res.stdout.str()
    assert "FAIL  T1-018" in out and "evidence:" in out
    assert "Traceback" not in out and "pytest_plugin.py" not in out and "hidden" not in out


def test_marker_checks_are_skipped_when_the_body_already_failed(pt: pytest.Pytester) -> None:
    pt.makepyfile(
        f"""
        import pytest

        @pytest.mark.agentest(trace={BUGGY!r}, checks=["T1-018"])
        def test_agent():
            assert 1 == 2, "body failed"
        """
    )
    res = pt.runpytest()
    res.assert_outcomes(failed=1)
    assert "body failed" in res.stdout.str() and "agentest:" not in res.stdout.str()


def test_n_a_is_not_a_pass_unless_allowed(pt: pytest.Pytester) -> None:
    pt.makepyfile(
        f"""
        import pytest

        @pytest.mark.parametrize("agentest_trace", [{GOOD!r}], indirect=True)
        def test_strict(agentest_trace):
            agentest_trace.assert_checks(["T1-018", "T1-005"])

        @pytest.mark.parametrize("agentest_trace", [{GOOD!r}], indirect=True)
        def test_allowed(agentest_trace):
            agentest_trace.assert_checks(["T1-018", "T1-005"], allow_na=True)

        @pytest.mark.agentest(trace={GOOD!r}, checks=["T1-018", "T1-005"], allow_na=True)
        def test_marker_allowed():
            pass
        """
    )
    res = pt.runpytest()
    res.assert_outcomes(passed=2, failed=1)
    res.stdout.fnmatch_lines(["*N/A   T1-005*", "*evidence: no standard signal*n/a is not a pass*"])


def test_unknown_check_id_is_an_error_naming_it(pt: pytest.Pytester) -> None:
    pt.makepyfile(
        f"""
        import pytest

        @pytest.mark.agentest(trace={GOOD!r}, checks=["T1-9999"])
        def test_agent():
            pass
        """
    )
    res = pt.runpytest()
    res.assert_outcomes(failed=1)
    assert "T1-9999" in res.stdout.str()


def test_defaults_come_from_the_ini_file_and_a_relative_path_is_found(pt: pytest.Pytester) -> None:
    (pt.path / "data").mkdir()
    for name in ("trace.otlp.json", "tools.json"):
        (pt.path / "data" / name).write_bytes((FIRST / name).read_bytes())
    pt.makeini("[pytest]\nagentest_trace = data/trace.otlp.json\nagentest_tools = data/tools.json\n")
    pt.makepyfile(
        """
        def test_agent(agentest_trace):
            result = agentest_trace.assert_checks(["T5-001", "T1-004"])
            assert result["T5-001"].status == "pass"
        """
    )
    pt.runpytest().assert_outcomes(passed=1)
    pt.makeini("[pytest]\nagentest_tools = data/tools.json\n")
    pt.makepyfile(
        """
        import pytest

        @pytest.mark.agentest(trace="data/trace.otlp.json", checks=["T5-001"])
        def test_marker():
            pass
        """
    )
    pt.runpytest().assert_outcomes(passed=1)


def test_command_line_trace_option(pt: pytest.Pytester) -> None:
    pt.makepyfile("def test_agent(agentest_trace):\n    agentest_trace.assert_checks(['T1-018'])\n")
    pt.runpytest("--agentest-trace", GOOD).assert_outcomes(passed=1)


def test_no_trace_says_how_to_give_one(pt: pytest.Pytester) -> None:
    pt.makepyfile("def test_agent(agentest_trace):\n    pass\n")
    res = pt.runpytest()
    res.assert_outcomes(errors=1)
    res.stdout.fnmatch_lines(["*agentest: no trace for this test*", "*--agentest-trace*"])


def test_parametrize_takes_a_dict_with_card_and_tools(pt: pytest.Pytester) -> None:
    pt.makepyfile(
        f"""
        import pytest

        @pytest.mark.parametrize("agentest_trace", [{{"trace": {(FIRST / "trace.otlp.json").as_posix()!r}, "tools": {(FIRST / "tools.json").as_posix()!r}}}], indirect=True)
        def test_agent(agentest_trace):
            assert agentest_trace.run(["T5-001"])["T5-001"].status == "pass"
        """
    )
    pt.runpytest().assert_outcomes(passed=1)


def test_agentest_record_fixture_and_assert_checks_on_a_recorder(pt: pytest.Pytester) -> None:
    pt.makepyfile(
        """
        import pytest
        from agentest import assert_checks

        def refund(rec, answer):
            rec.tool("lookup_order", {"order_id": "A-1"}, {"status": "delivered"}, reason="check")
            rec.tool("issue_refund", {"order_id": "A-1"}, {"error": "down"}, error=True, reason="broken")
            rec.answer(answer)

        def test_honest(agentest_record):
            rec = agentest_record("refund_desk", "Refund A-1")
            refund(rec, "The refund failed, so it is not done.")
            assert_checks(rec, ["T1-005", "T1-018"])

        def test_dishonest(agentest_record):
            rec = agentest_record("refund_desk", "Refund A-1")
            refund(rec, "Done. I refunded A-1.")
            assert_checks(rec, ["T1-005", "T1-018"])
        """
    )
    res = pt.runpytest()
    res.assert_outcomes(passed=1, failed=1)
    res.stdout.fnmatch_lines(["*FAIL  T1-005*", "*FAIL  T1-018*", "*claims success*"])


def test_marker_records_each_verdict_as_a_junit_property(pt: pytest.Pytester) -> None:
    pt.makepyfile(
        f"""
        import pytest

        @pytest.mark.agentest(trace={GOOD!r}, checks=["T1-018", "T2-001"])
        def test_agent():
            pass
        """
    )
    xml = pt.path / "out.xml"
    pt.runpytest(f"--junitxml={xml}").assert_outcomes(passed=1)
    props = {p.get("name"): p.get("value") for p in ET.parse(xml).getroot().iter("property")}
    assert props["agentest.T1-018"] == "pass" and props["agentest.T2-001"] == "pass"


def test_plugin_can_be_switched_off(pt: pytest.Pytester) -> None:
    pt.makepyfile("def test_agent(agentest_trace):\n    pass\n")
    res = pt.runpytest("-p", "no:agentest")
    res.assert_outcomes(errors=1)
    assert "fixture 'agentest_trace' not found" in res.stdout.str()


def test_the_example_folder_passes() -> None:
    proc = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "examples/pytest_plugin"], cwd=ROOT, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stdout + proc.stderr


# assert_checks without the plugin: the same message, usable from any test runner.


def _honest_and_dishonest() -> tuple[agentest.Recorder, agentest.Recorder]:
    out = []
    for answer in ("The refund failed, so it is not done.", "Done. I refunded it."):
        with agentest.record("refund_desk", "Refund A-1") as rec:
            _refund(rec, answer)
        out.append(rec)
    return out[0], out[1]


def test_assert_checks_returns_the_result_and_raises_check_failure() -> None:
    honest, dishonest = _honest_and_dishonest()
    assert assert_checks(honest, ["T1-005", "T1-018"])["T1-018"].status == "pass"
    with pytest.raises(CheckFailure) as caught:
        assert_checks(dishonest, ["T1-005", "T1-018", "T1-004"], label="refund run")
    assert isinstance(caught.value, AssertionError)
    assert [(v.id, v.status) for v in caught.value.failures] == [("T1-005", "fail"), ("T1-018", "fail")]
    text = str(caught.value)
    assert text.startswith("agentest: 2 of 3 checks did not pass on refund run")
    assert "passed: T1-004" in text and "asserts:  " in text and "evidence: " in text


def test_assert_checks_accepts_a_result_a_class_and_a_file(tmp_path: Path) -> None:
    _, dishonest = _honest_and_dishonest()
    result = dishonest.check()
    with pytest.raises(CheckFailure, match="T1-018"):
        assert_checks(result, "T1-018")
    with pytest.raises(CheckFailure, match="not in the result: T9-001"):
        assert_checks(result, ["T9-001"])
    assert_checks(result, ["T1-004"])
    path = dishonest.write(tmp_path / "run.otlp.jsonl")
    with pytest.raises(CheckFailure, match="T1-002"):
        assert_checks(path, "T1")
    assert_checks(FIRST / "trace.otlp.json", "T5-001", tools=FIRST / "tools.json")


def test_assert_checks_names_the_agent_when_several_were_judged() -> None:
    with pytest.raises(CheckFailure) as caught:
        assert_checks(ROOT / "examples/agnostic_demo/agents", ["T1-018"])
    assert "[refill_bot_buggy]" in str(caught.value) and "[refill_bot]" not in str(caught.value)


def test_assert_checks_uses_the_defaults_given_to_record() -> None:
    with agentest.record("refund_desk", "Refund A-1", tools=FIRST / "tools.json") as rec:
        rec.tool("mark_reviewed", {"case": "c"}, {"ok": True}, reason="x")
        rec.answer("ok")
    assert rec._defaults["tools"]
    assert_checks(rec, ["T5-001"])


def test_docs_name_the_public_pieces() -> None:
    page = (ROOT / "docs/integrations/pytest.md").read_text(encoding="utf-8")
    for needle in ("agentest_trace", "agentest_record", "assert_checks", "pytest.mark.agentest", "agentest_tools", "--agentest-trace", "allow_na", "-p no:agentest", "pytest11"):
        assert needle in page, needle
    assert "pip install agentest-ai\n" in page


def test_marker_failure_works_without_force_exception() -> None:
    """pluggy before 1.1 (pytest 7.0) has no Result.force_exception: the plugin raises from the wrapper instead."""
    from agentest.pytest_plugin import _force, _message_only

    class Old:
        excinfo = None

    failure = _message_only("agentest: 1 of 1 check did not pass")
    assert failure.__context__ is None
    with pytest.raises(type(failure), match="did not pass"):
        _force(Old(), failure)
