"""smolagents CodeAgent: the ``python_interpreter`` wrapper is not a tool call; the tools its code calls are.

The code is parsed with ``ast`` and never run. Rules stay agent-agnostic: T5-001 / T5-018 still judge declared tools
only, so a tool the code calls that is not declared still fails, and the wrapper alone never does.
"""
import json
import os
from pathlib import Path

from agentest.cli import main
from agentest.standards.importers import _code_calls, adapt, is_write_from_tools

ROOT = Path(__file__).resolve().parents[1]
FX = ROOT / "tests" / "fixtures" / "smolagents_code"
CARD = ROOT / "examples" / "langgraph_import" / "agents" / "expense_bot" / "agent-card.json"
DECLARED = frozenset({"suggest_menu", "book_table"})


def _verdicts(tmp_path: Path) -> dict:
    otlp = tmp_path / "menu.otlp.jsonl"
    assert main(["std", "import", str(FX / "native.jsonl"), "--map", str(FX / "map.json"), "--tools", str(FX / "tools.json"),
                 "--service", "menu_bot", "--out", str(otlp)]) == 0
    out = {}
    for line in otlp.read_text().splitlines():  # one trace per recorded run, judged one by one
        one = tmp_path / "one.otlp.jsonl"
        one.write_text(line + "\n")
        res = tmp_path / "one.json"
        assert main(["std", "run", "--otlp", str(one), "--card", str(CARD), "--tools", str(FX / "tools.json"),
                     "--ids", "T5-001,T5-018", "--format", "json", "--out", str(res)]) in (0, 1)
        out[len(out)] = {r["id"]: (r["status"], r["detail"]) for r in json.loads(res.read_text())["results"]}
    return out


def _calls(raw_steps, tools=None):
    is_write = None
    if tools:
        is_write = is_write_from_tools(tools)
    ep = adapt({"agent": "a", "input": "q", "trace": raw_steps}, {"dialect": "smolagents"}, is_write)
    return [(c.name, c.arguments) for c in ep.tool_calls]


def _wrap(code, cid="c1", **step):
    return {"step_number": 1, "tool_calls": [{"id": cid, "type": "function", "function": {"name": "python_interpreter", "arguments": code}}],
            "observations": "ok", **step}


def test_fixture_runs_end_to_end(tmp_path):
    v = _verdicts(tmp_path)
    # 0 declared tool called in code: the real tool shows up and the wrapper does not fail T5-001 / T5-018
    assert v[0]["T5-001"][0] == "pass" and v[0]["T5-018"][0] == "pass"
    # 1 code that calls no tool at all: no tool call, nothing undeclared
    assert v[1]["T5-001"][0] in ("pass", "n/a") and v[1]["T5-018"][0] in ("pass", "n/a")
    # 2 the code also calls a tool that is not declared: still a failure, naming the tool and not the wrapper
    assert v[2]["T5-001"] == ("fail", "undeclared tools: ['wipe_guest_list']")
    assert v[2]["T5-018"] == ("fail", "undeclared tools: ['wipe_guest_list']")
    # 3 unparseable code: imports without error, and no tool is invented
    assert v[3]["T5-001"][0] in ("pass", "n/a")


def test_imported_trace_has_the_real_tool_span_and_no_wrapper(tmp_path):
    otlp = tmp_path / "m.otlp.jsonl"
    assert main(["std", "import", str(FX / "native.jsonl"), "--map", str(FX / "map.json"), "--tools", str(FX / "tools.json"),
                 "--out", str(otlp)]) == 0
    names = [[a["value"].get("stringValue") for sp in ss["spans"] for a in sp["attributes"] if a["key"] == "gen_ai.tool.name"]
             for d in map(json.loads, otlp.read_text().splitlines()) for rs in d["resourceSpans"] for ss in rs["scopeSpans"]]
    assert [n for n in names if n] == [["suggest_menu"], ["suggest_menu", "wipe_guest_list"]]


def test_arguments_literals_resolved_names_and_source_text():
    code = "city = 'Pune'\nr = suggest_menu('veg', people=4, city=city, notes=build_notes(x))\n"
    assert _code_calls(code, DECLARED) == [("build_notes", {"arg0": "x"}), ("suggest_menu", {"arg0": "veg", "people": 4, "city": "Pune", "notes": "build_notes(x)"})]


def test_order_nested_and_repeated_names_resolve_only_when_assigned_once():
    code = "n = 1\nn = 2\nbook_table(people=n)\nprint(suggest_menu(diet='veg'))\n"
    assert _code_calls(code, DECLARED) == [("book_table", {"people": "n"}), ("suggest_menu", {"diet": "veg"})]


def test_builtins_locals_imports_methods_and_final_answer_are_not_tools():
    code = (
        "import json, re\nfrom math import sqrt\n"
        "def helper(a):\n    return len(a)\n"
        "fmt = lambda s: s.strip()\n"
        "class Box:\n    pass\n"
        "data = json.loads('{}')\nm = re.findall('a', 'a')\nprint(helper([1]), sqrt(4), fmt(' x '), Box(), sorted([2, 1]), isinstance(1, int))\n"
        "for item in range(3):\n    str(item)\n"
        "final_answer('done')\n"
    )
    assert _code_calls(code, frozenset()) == []


def test_declared_tool_shadowing_a_builtin_name_is_a_tool():
    assert _code_calls("input(prompt='x')", frozenset({"input"})) == [("input", {"prompt": "x"})]
    assert _code_calls("input('x')", frozenset()) == []


def test_unparseable_or_odd_code_gives_no_calls_and_no_error():
    for code in ("suggest_menu(", "x = = 1", "\x00", "def f(:\n pass", "", "   ", "```python\nsuggest_menu(\n```", "(" * 5000):
        assert _code_calls(code, DECLARED) == []
    assert _calls([_wrap("suggest_menu(")]) == []
    assert _calls([_wrap(None)]) == []
    assert _calls([_wrap({"unexpected": 1})]) == []


def test_code_is_never_executed(tmp_path):
    marker = tmp_path / "ran"
    code = f"open({str(marker)!r}, 'w').write('x')\n__import__('os').system('touch {marker}')\nexec('print(1)')\nlookup_secret()\n"
    got = _calls([_wrap(code)])
    assert got == [("lookup_secret", {})] and not marker.exists() and not os.path.exists(marker)


def test_fenced_code_dict_arguments_and_code_action_fallback():
    fenced = "```python\nsuggest_menu(diet='veg')\n```<end_code>"
    assert _calls([_wrap(fenced)]) == [("suggest_menu", {"diet": "veg"})]
    assert _calls([_wrap({"code": "suggest_menu(diet='veg')"})]) == [("suggest_menu", {"diet": "veg"})]
    step = {"step_number": 1, "code_action": "book_table(people=2)", "tool_calls": [
        {"id": "c", "function": {"name": "python_interpreter", "arguments": ""}}], "observations": "ok"}
    assert _calls([step]) == [("book_table", {"people": 2})]


def test_result_error_and_call_ids_follow_the_step():
    ep = adapt({"agent": "a", "input": "q", "trace": [_wrap("suggest_menu(1)\nbook_table(2)", error={"type": "E", "message": "boom"})]},
               {"dialect": "smolagents"})
    assert [(c.name, c.call_id, c.result, c.error) for c in ep.tool_calls] == [
        ("suggest_menu", "c1#0", None, False), ("book_table", "c1#1", "ok", True)]


def test_declared_python_interpreter_is_a_real_tool_and_is_kept(tmp_path):
    tools = tmp_path / "tools.json"
    tools.write_text(json.dumps({"tools": [{"name": "python_interpreter", "annotations": {"readOnlyHint": False}},
                                           {"name": "suggest_menu", "annotations": {"readOnlyHint": True}}]}))
    assert _calls([_wrap("suggest_menu(diet='v')")], tools) == [("python_interpreter", {"raw": "suggest_menu(diet='v')"})]


def test_tool_calling_agent_steps_are_unchanged():
    steps = [{"step_number": 1, "tool_calls": [{"id": "c1", "function": {"name": "suggest_menu", "arguments": {"diet": "veg"}}}], "observations": "ok"}]
    assert _calls(steps) == [("suggest_menu", {"diet": "veg"})]
