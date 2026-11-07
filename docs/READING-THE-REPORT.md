# Reading the report

This page explains how to read the report that `agentest std run` produces: what `pass`,
`fail` and `n/a` mean, how to read a verdict's `detail` line, and how to find the rule behind
a check ID. It covers the four report formats (terminal, HTML, JSON, JUnit). It assumes you
have already run the install in [Getting started](GETTING-STARTED.md).

## One command, a bundled agent

Run this from a clone to produce a report on a bundled sample agent, `a14`:

```bash
agentest std run --agent a14
```

Output (terminal summary):

```
a14: 11 pass, 2 fail (T1-001, T1-003)
total: 11 pass, 2 fail, 117 n/a over 1 agents x 130 IDs (examples)
```

Every agent is judged against the same 130 check IDs (the 110-ID open catalogue plus 20
repo extensions), so one agent's report has 130 verdicts. `a14` is the sample used throughout
this page; substitute `--agent a62` or another bundled folder, or your own agent with
`--otlp`/`--card`/`--tools`.

## The three verdicts

| Verdict | Meaning | What to do |
|---|---|---|
| **pass** | The rule found the signal it needs and the behaviour met the rule. | Nothing. A pass is only as good as the inputs that were run. |
| **fail** | The rule found the signal and the behaviour broke the rule. `detail` names the evidence. | Triage it: read the `detail` line, check the rule, then file a report (below). |
| **n/a** | The rule found no signal to judge: the needed input is absent, or a needed fact is not declared. `detail` names what is missing. | Decide whether the check applies to your agent; if it does, add the input or publish the fact and re-run. |

**`n/a` is common, and it is not a failure.** It means "not judged", not "bad". Each check
looks for a specific signal in your traces and metadata — for example a state-changing tool
call, a declared recipient allowlist, or a success-rate threshold. When your agent has not
recorded that signal, agentest cannot judge the check, so it reports `n/a` instead of guessing.

`n/a` is never counted as a pass. A report with many `n/a` verdicts has low *coverage*, not
high quality: most of the catalogue simply was not exercised. To raise coverage, add the
missing signals and re-run — see [Why are so many of my checks n/a?](FAQ.md) and the
[governance extension](standards/EXTENSION.md).

## The four formats

The same verdicts are rendered four ways. Choose by where you read them:

| Format | Flag | Best for |
|---|---|---|
| terminal | *(default)* | a quick glance at one agent |
| Markdown / HTML | `--format md`, `--format html` | a shareable page for humans |
| JSON | `--format json` | tools and scripts (versioned schema) |
| JUnit | `--format junit` | CI dashboards |

`--format html --out report.html` writes a self-contained HTML file (styles inlined, no
network needed) that you can open in any browser or attach to a review.

### Terminal summary

```
a14: 11 pass, 2 fail (T1-001, T1-003)
total: 11 pass, 2 fail, 117 n/a over 1 agents x 130 IDs (examples)
```

- The first line is per agent: pass count, fail count, and the failing IDs.
- The second line is the whole run: totals and the mode in parentheses.
- `(examples)` is the default mode; `--mode strict` gives `(strict)`. See the two modes below.

### Markdown / HTML table

`--format md` prints one row per verdict:

| ID | status | detail |
|---|---|---|
| T1-001 | fail | `case0: evaluation: fail` |
| T1-002 | pass | `claims consistent over 3 run(s)` |
| T1-003 | fail | `TSR=2/3 (threshold 1.00)` |
| T1-004 | n/a | `no standard signal: no recipient allowlist and no state-changing call recorded` |

`--format html` is the same table with pass/fail rows colour-coded.

### JSON

`--format json` emits a versioned document, `agentest.verdicts/1`:

```json
{
  "schema": "agentest.verdicts/1",
  "mode": "examples",
  "results": [
    { "agent": "a14", "id": "T1-003", "status": "fail", "detail": "TSR=2/3 (threshold 1.00)" },
    { "agent": "a14", "id": "T1-004", "status": "n/a", "detail": "no standard signal: no recipient allowlist and no state-changing call recorded" }
  ]
}
```

`results` is a flat list of `{agent, id, status, detail}` objects; the `schema` field is the
version you can key tooling on. The JSON schema file lives at
`src/agentest/standards/schemas/verdicts.schema.json`.

### JUnit

`--format junit` maps the three verdicts onto JUnit's three outcomes so CI can gate on them:

| Verdict | JUnit outcome |
|---|---|
| `pass` | a bare `<testcase>` |
| `fail` | `<testcase>` with a `<failure>` child |
| `n/a` | `<testcase>` with a `<skipped>` child |

The suite totals agree with the summary: for `a14`, `tests="130" failures="2" skipped="117"`.
Use `--strict` to make `run` exit with status 1 when any verdict is `fail`:

```bash
agentest std run --agent a14 --format junit --out agentest.xml --strict
```

## Reading a `detail` line

`detail` is written for a person, not a machine, but it is terse. Here is how to read three
real examples from `a14`:

- `case0: evaluation: fail` — input `case0`; the harness evaluation
  (`gen_ai.evaluation.result`) reported failure. The rule (T1-001) checks that a run's own
  success signal holds; here it did not.
- `TSR=2/3 (threshold 1.00)` — task success rate: 2 of 3 runs succeeded, but the agent's
  published threshold (`governance slo.successRate`) requires all of them.
- `no standard signal: no recipient allowlist and no state-changing call recorded` — an `n/a`
  detail. The rule (T1-004) needs a recipient allowlist or a state-changing call, and `a14`'s
  card and traces record neither, so the check could not be judged.

The pattern: a `fail` detail names the evidence (an input/run, a number vs. its threshold, or
the offending call/argument); an `n/a` detail names the *missing* signal.

## Finding the rule behind a check ID

A check ID (`T1-003`) is a pointer to one universal rule. Three ways to look it up, from
quickest to most detailed:

```bash
agentest list --class T1      # titles of the T1 checks
agentest list --json          # id, class, title and severity of every check
```

`agentest list --class T1` gives, for example:

```
T1-003  [T1] Task success rate over k runs meets documented threshold
```

For the full page on one ID — purpose, what the runner checks, how it is judged, and its
standards mapping — see the per-ID reference under [`docs/tests/`](tests/README.md), e.g.
[`T1-003.md`](tests/T1-003.md). The rule itself is a single deterministic function in
[`src/agentest/standards/rules.py`](../src/agentest/standards/rules.py); every ID is judged
by that code, not by a model.

## Reporting a wrong verdict

agentest is deterministic, but a rule can still be wrong: it can flag correct behaviour
(a **false positive**, reported `fail` when it should be `pass` or `n/a`) or miss a real
defect (a **false negative**, reported `pass` or `n/a` when it should be `fail`). Both are
bugs we want to hear about. Open an issue with the matching form:

- **False positive (wrong fail)** — the agent behaved correctly but agentest reported `fail`.
- **False negative (missed defect)** — the agent had a real defect but agentest reported
  `pass` or `n/a`.

Both forms ask for the check ID, the actual verdict, the `detail` text, the expected verdict
and why, a redacted trace, and the command you ran. A small redacted trace is the single most
useful thing to attach. **Never paste secrets, API keys or personal data in an issue** — redact
the trace first.

## What a report is not

A report is a *coverage* measurement of the recorded traces against the catalogue's rules.
It is not a certification, an audit, a safety guarantee or a ranking. A `pass` means the rule
held on the traces you supplied, nothing more, and agentest does not assign a single overall
score or leaderboard position. (The [FAQ](FAQ.md) has the same point under *Known limits*.)
