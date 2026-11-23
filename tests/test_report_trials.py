"""Trials section on markdown, HTML and versioned JSON reports.

Metrics are report-only. A trial passes when its postconditions hold. Tasks are grouped by
``agentest.task.id``, otherwise by the input id, and a task is listed only when it has more than one run.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import jsonschema

from agentest.cli import main
from agentest.standards.metadata import Agent
from agentest.standards.otel import Run, from_otlp
from agentest.standards.reports import (
    SMALL_K,
    SMALL_K_NOTE,
    _fmt_metric,
    pass_all_k,
    pass_at_k,
    success_rate_se,
    to_html,
    to_markdown,
    to_versioned_json,
    trial_rows,
)

SCHEMA = json.loads((Path(__file__).resolve().parents[1] / "src/agentest/standards/schemas/verdicts.schema.json").read_text())
VERDICTS = {"desk": {"T1-001": {"status": "pass", "detail": "ok"}}}


def _run(task: str, label: str, rep: int = 0, *, task_attr: bool = True, input_id: str | None = None) -> Run:
    run = Run(input_id=input_id or task, rep=rep, input="go", answer="done",
              evaluations=[{"gen_ai.evaluation.score.label": label}])
    if task_attr:
        run.attrs["agentest.task.id"] = task
    return run


def _agent() -> Agent:
    return Agent("desk", Path("."), {"skills": []}, {}, {})


def test_metric_formulas_match_the_binomial_estimators():
    n, passes, k = 5, 3, 2
    assert pass_at_k(n, passes, k) == 1.0 - math.comb(n - passes, k) / math.comb(n, k)
    assert pass_all_k(n, passes, k) == math.comb(passes, k) / math.comb(n, k)
    # Draw size equal to the trial count collapses to "any success" and "every success".
    assert pass_at_k(4, 0, 4) == 0.0
    assert pass_at_k(4, 1, 4) == 1.0
    assert pass_all_k(4, 4, 4) == 1.0
    assert pass_all_k(4, 3, 4) == 0.0
    assert success_rate_se(4, 4) == 0.0
    assert success_rate_se(2, 1) == math.sqrt(0.5 * 0.5 / 2)


def test_trial_rows_shape_grouping_and_small_k_note():
    runs = [
        _run("book", "pass", 0),
        _run("book", "fail", 1),
        _run("book", "pass", 2),
        _run("once", "pass", 0),
        _run("ship", "pass", 0, task_attr=False, input_id="ship"),
        _run("ship", "pass", 1, task_attr=False, input_id="ship"),
    ]
    rows = trial_rows("desk", _agent(), runs, "examples")
    assert [r["task"] for r in rows] == ["book", "ship"]  # the single run is omitted
    book = rows[0]
    assert set(book) == {"agent", "task", "k", "passes", "pass@k", "pass^k", "success_rate_se", "note"}
    assert book["agent"] == "desk"
    assert book["k"] == 3 and book["passes"] == 2
    assert book["pass@k"] == pass_at_k(3, 2, 3) == 1.0
    assert book["pass^k"] == pass_all_k(3, 2, 3) == 0.0
    assert book["success_rate_se"] == success_rate_se(3, 2)
    assert book["note"] == SMALL_K_NOTE
    assert rows[1]["k"] == 2 and rows[1]["passes"] == 2
    assert rows[1]["pass@k"] == 1.0 and rows[1]["pass^k"] == 1.0

    many = [_run("bulk", "pass", i) for i in range(SMALL_K)]
    full = trial_rows("desk", _agent(), many, "examples")[0]
    assert full["k"] == SMALL_K and full["passes"] == SMALL_K
    assert full["pass@k"] == 1.0 and full["pass^k"] == 1.0 and full["success_rate_se"] == 0.0
    assert full["note"] == ""


def test_reports_pin_the_table_and_leave_verdicts_unchanged():
    rows = trial_rows("desk", _agent(), [_run("book", "pass", 0), _run("book", "fail", 1)], "strict")
    assert rows[0]["passes"] == 1  # strict mode still reads gen_ai.evaluation.result
    bare = to_versioned_json(VERDICTS, "examples")
    doc = to_versioned_json(VERDICTS, "examples", rows)
    assert doc["results"] == bare["results"]
    assert "trials" not in bare and doc["trials"] == rows
    jsonschema.Draft202012Validator(SCHEMA).validate(bare)
    jsonschema.Draft202012Validator(SCHEMA).validate(doc)

    md = to_markdown(VERDICTS, "examples", rows)
    assert md.startswith("# agentest ")
    assert "| ID | status | detail |" in md
    assert "## Trials" in md
    assert "| agent | task | k | passes | pass@k | pass^k | SE | note |" in md
    line = "| desk | book | 2 | 1 | 1 | 0 | " + _fmt_metric(rows[0]["success_rate_se"]) + " | " + SMALL_K_NOTE + " |"
    assert line in md
    assert "## Trials" not in to_markdown(VERDICTS, "examples")

    html = to_html(VERDICTS, "examples", rows)
    assert "<h2>Trials</h2>" in html
    assert "<th>pass@k</th><th>pass^k</th><th>SE</th>" in html
    assert f"<td>desk</td><td>book</td><td>2</td><td>1</td><td>1</td><td>0</td><td>{_fmt_metric(rows[0]['success_rate_se'])}</td>" in html
    assert "<h2>Trials</h2>" not in to_html(VERDICTS, "examples")


def _otlp(task: str, label: str, rep: int) -> dict:
    return {"resourceSpans": [{"scopeSpans": [{"spans": [{
        "traceId": f"{rep + 1:032x}", "spanId": f"{rep + 1:016x}", "name": "invoke_agent desk",
        "startTimeUnixNano": str(1_000_000_000 * (rep + 1)), "endTimeUnixNano": str(2_000_000_000 * (rep + 1)),
        "attributes": [
            {"key": "gen_ai.operation.name", "value": {"stringValue": "invoke_agent"}},
            {"key": "agentest.input.id", "value": {"stringValue": task}},
            {"key": "agentest.task.id", "value": {"stringValue": task}},
            {"key": "agentest.run.rep", "value": {"intValue": str(rep)}},
        ],
        "events": [{"name": "gen_ai.evaluation.result", "timeUnixNano": "1", "attributes": [
            {"key": "gen_ai.evaluation.score.label", "value": {"stringValue": label}},
        ]}],
        "status": {"code": 1},
    }]}]}]}


def test_std_run_json_and_markdown_include_the_trials_section(tmp_path, capsys):
    paths = []
    for rep, label in enumerate(("pass", "fail")):
        path = tmp_path / f"{label}.json"
        path.write_text(json.dumps(_otlp("book", label, rep)), encoding="utf-8")
        paths.append(str(path))
    assert from_otlp(json.loads(Path(paths[0]).read_text())).evaluations
    assert main(["std", "run", "--otlp", *paths, "--format", "json", "--ids", "T1-001"]) == 0
    doc = json.loads(capsys.readouterr().out)
    assert [r["id"] for r in doc["results"]] == ["T1-001"]
    assert doc["results"][0]["status"] in {"pass", "fail", "n/a"}
    assert doc["trials"] == [{
        "agent": "otlp_agent", "task": "book", "k": 2, "passes": 1,
        "pass@k": 1.0, "pass^k": 0.0, "success_rate_se": success_rate_se(2, 1), "note": SMALL_K_NOTE,
    }]
    jsonschema.Draft202012Validator(SCHEMA).validate(doc)
    assert main(["std", "run", "--otlp", *paths, "--format", "md", "--ids", "T1-001"]) == 0
    md = capsys.readouterr().out
    assert "| T1-001 |" in md
    assert "| otlp_agent | book | 2 | 1 | 1 | 0 |" in md
