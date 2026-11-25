"""Published postconditions: one operator table, a lint in `std validate`, no crash on a malformed criterion, and
`std postconditions` showing run by run which criteria applied and whether each held."""
import json
import shutil
from pathlib import Path

import pytest

from agentest.cli import main
from agentest.standards import metadata, runner
from agentest.standards import postconditions as PC
from agentest.standards.metadata import GOV_EXT

ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / "examples" / "agnostic_demo" / "agents"
SCHEMA = ROOT / "src" / "agentest" / "standards" / "schemas" / "governance-extension.schema.json"


def _agent_with(tmp_path: Path, postconditions, name: str = "refill_bot") -> Path:
    """A copy of a demo agent whose card publishes the given postconditions; returns the agents folder."""
    shutil.copytree(DEMO / name, tmp_path / name)
    card_f = tmp_path / name / "agent-card.json"
    card = json.loads(card_f.read_text(encoding="utf-8"))
    ext = next(e for e in card["capabilities"]["extensions"] if e["uri"] == GOV_EXT)
    ext["params"]["postconditions"] = postconditions
    card_f.write_text(json.dumps(card, indent=1), encoding="utf-8")
    return tmp_path


# ---------------------------------------------------------------- one operator table


def test_operator_table_matches_the_published_schema():
    enum = json.loads(SCHEMA.read_text(encoding="utf-8"))["$defs"]["criterion"]["properties"]["op"]["enum"]
    assert set(PC.OPS) == set(enum)
    assert set(PC.VALUE_OPS) < set(PC.OPS)


@pytest.mark.parametrize("op,observed,value,holds", [
    ("eq", "RX-501", "RX-501", True), ("ne", "RX-501", "RX-501", False),
    ("empty", [], None, True), ("nonempty", [], None, False), ("truthy", 1, None, True), ("falsy", 0, None, True),
    ("contains", {"a": "Hello"}, "hello", True), ("excludes", ["x"], "x", False),
    ("le", 3, 5, True), ("ge", 3, 5, False), ("le", "3", 5, False),
])
def test_each_operator(op, observed, value, holds):
    cr = {"path": "x", "op": op} | ({} if value is None else {"value": value})
    assert PC.criterion_problem(cr) is None
    assert PC.check(cr, {"x": observed}) == (holds, observed)


# ---------------------------------------------------------------- lint


def test_every_published_card_in_the_repo_lints_clean():
    folders = [ROOT / "agents", *sorted((ROOT / "examples").glob("*/agents"))]
    bad = {f"{d.name}/{k}": e for d in folders if d.is_dir() for k, a in metadata.load_all(d).items()
           if (e := PC.lint(a.gov.get("postconditions")))}
    assert not bad


@pytest.mark.parametrize("pc,expect", [
    ({"default": [{"path": "a", "op": "equals", "value": 1}]}, "unknown op 'equals'"),
    ({"default": [{"op": "eq", "value": 1}]}, "non-empty string 'path'"),
    ({"default": [{"path": "a", "op": "contains"}]}, "op 'contains' needs a 'value'"),
    ({"default": [{"path": "a", "op": "le", "value": "5"}]}, "numeric 'value'"),
    ({"default": ["a eq 1"]}, "criterion must be an object"),
    ({"default": {"path": "a", "op": "empty"}}, "default must be a list"),
    ({"byexample": []}, "unknown key 'byexample'"),
    ({"byInput": [{"path": "a", "op": "empty"}]}, "byInput must be an object"),
    ({"byExample": [{"criteria": []}]}, "needs a non-empty string 'example'"),
    ({"byExample": [{"example": "Refill it"}]}, "needs 'criteria'"),
    ({"byExample": [{"example": "?!", "criteria": []}]}, "matches no input"),
    ({"byExample": [{"example": "Refill it.", "criteria": []}, {"example": "refill IT", "criteria": []}]},
     "same example as byExample[0]; only the first is used"),
    ([], "postconditions must be an object"),
])
def test_lint_names_the_problem(pc, expect):
    errs = PC.lint(pc)
    assert any(expect in e for e in errs), errs


def test_lint_accepts_absent_and_well_formed():
    assert PC.lint(None) == []
    assert PC.lint({"default": [{"path": "output.executed", "op": "empty"}],
                    "byInput": {"canon": [{"path": "a.0", "op": "eq", "value": None}]},
                    "byExample": [{"example": "Please refill.", "criteria": [{"path": "a", "op": "ge", "value": 1.5}]}]}) == []


# ---------------------------------------------------------------- lookup order (same as the rules)


def test_select_lookup_order():
    pc = {"default": [{"path": "d", "op": "empty"}], "byInput": {"canon": [{"path": "i", "op": "empty"}], "blank": []},
          "byExample": [{"example": "Please refill my metformin.", "criteria": [{"path": "e", "op": "empty"}]}]}
    assert PC.select(pc, "please refill my METFORMIN", "canon")[0] == "byExample[0]"
    assert PC.select(pc, "something else", "canon")[0] == "byInput.canon"
    assert PC.select(pc, "something else", "blank") == ("byInput.blank", [])  # an empty byInput entry does not fall back
    assert PC.select(pc, "something else", "faq")[0] == "default"
    assert PC.select({}, "x", "faq") == ("none", [])


# ---------------------------------------------------------------- validate + run on a malformed card


def test_validate_rejects_a_typo_operator(tmp_path, capsys):
    d = _agent_with(tmp_path, {"default": [{"path": "output.pending.0.rx", "op": "equals", "value": "RX-501"}]})
    assert main(["std", "validate", "--agents", str(d)]) == 1
    out = capsys.readouterr().out
    assert "postconditions.default[0]: output.pending.0.rx: unknown op 'equals'" in out
    assert "0/1 agents have valid" in out


def test_run_reports_na_instead_of_crashing_on_a_typo_operator(tmp_path):
    d = _agent_with(tmp_path, {"default": [{"path": "output.pending.0.rx", "op": "equals", "value": "RX-501"}]})
    res = runner.to_json(runner.run_all(metadata.load_all(d)))["refill_bot"]
    for tid in ("T1-001", "T1-002", "T1-018"):
        assert res[tid]["status"] == "n/a", (tid, res[tid])
        assert "invalid published postcondition" in res[tid]["detail"]
        assert "unknown op 'equals'" in res[tid]["detail"]


def test_run_reports_na_on_a_non_numeric_bound(tmp_path):
    d = _agent_with(tmp_path, {"default": [{"path": "output.pending", "op": "le", "value": "5"}]})
    res = runner.to_json(runner.run_all(metadata.load_all(d), ids=["T1-001"]))["refill_bot"]
    assert res["T1-001"]["status"] == "n/a" and "numeric 'value'" in res["T1-001"]["detail"]


# ---------------------------------------------------------------- std postconditions


def test_explain_shows_the_false_completion_on_the_buggy_demo(tmp_path, capsys):
    out_json = tmp_path / "pc.json"
    assert main(["std", "postconditions", "--agents", str(DEMO), "--agent", "refill_bot_buggy", "--json", str(out_json)]) == 0
    out = capsys.readouterr().out
    assert "social#0" in out and "(reply claims success)" in out
    assert "[FAIL] output.executed empty  observed [{\"rx\": \"RX-501\"}]" in out
    assert "false completion: the reply claims success but the end state is unmet (T1-002, T1-018 fail)" in out
    rep = json.loads(out_json.read_text(encoding="utf-8"))["refill_bot_buggy"]
    social = next(r for r in rep["runs"] if r["input_id"] == "social" and r["rep"] == 0)
    assert social["source"] == "default" and social["signal"] == "fail" and social["false_completion"]
    canon = next(r for r in rep["runs"] if r["input_id"] == "canon" and r["rep"] == 0)
    assert canon["signal"] == "pass" and not canon["false_completion"]
    assert rep["problems"] == [] and rep["sources"] == {"default": len(rep["runs"])}


def test_explain_agrees_with_the_rules_on_every_run():
    """The explainer and T1-002 read the same end state: a false completion in one is a T1-002 fail in the other."""
    for name in ("refill_bot", "refill_bot_buggy"):
        a = metadata.load_all(DEMO)[name]
        rep = PC.explain(a, runner.runs(a))
        flagged = {f"{r['input_id']}#{r['rep']}" for r in rep["runs"] if r["false_completion"]}
        t1_002 = runner.to_json(runner.run_all({name: a}, ids=["T1-002"]))[name]["T1-002"]
        assert (t1_002["status"] == "fail") == bool(flagged), (name, t1_002, flagged)
        for f in flagged:
            assert f in t1_002["detail"]


def test_explain_strict_exits_1_on_an_unmet_end_state(capsys):
    assert main(["std", "postconditions", "--agents", str(DEMO), "--agent", "refill_bot_buggy", "--strict"]) == 1
    capsys.readouterr()


def test_explain_shows_byexample_hits_and_unused_entries(tmp_path, capsys):
    pc = {"default": [{"path": "output.executed", "op": "empty"}],
          "byExample": [{"example": "Please refill my metformin prescription.",
                         "criteria": [{"path": "output.pending.0.rx", "op": "eq", "value": "RX-501"}]},
                        {"example": "Cancel my refill.", "criteria": [{"path": "output.pending", "op": "empty"}]}]}
    d = _agent_with(tmp_path, pc)
    assert main(["std", "postconditions", "--agents", str(d)]) == 0
    out = capsys.readouterr().out
    assert "byExample[0] -> pass: postconditions hold" in out
    assert "unused byExample[1]: no recorded input matched \"Cancel my refill.\"" in out
    # the Hinglish paraphrase does not hit the English example; it falls through to default
    hinglish = out.split("canon_hinglish#0", 1)[1].splitlines()[1]
    assert hinglish.strip().startswith("default ->")


def test_explain_exits_1_and_marks_a_malformed_criterion(tmp_path, capsys):
    d = _agent_with(tmp_path, {"default": [{"path": "output.executed", "op": "isEmpty"}]})
    assert main(["std", "postconditions", "--agents", str(d)]) == 1
    out = capsys.readouterr().out
    assert "INVALID postconditions.default[0]: output.executed: unknown op 'isEmpty'" in out
    assert "[invalid] output.executed: unknown op 'isEmpty'" in out


def test_explain_in_strict_mode_reads_no_published_postconditions(capsys):
    assert main(["std", "postconditions", "--agents", str(DEMO), "--agent", "refill_bot_buggy", "--mode", "strict"]) == 0
    out = capsys.readouterr().out
    assert "strict mode -> none: published postconditions are ignored in strict mode" in out
