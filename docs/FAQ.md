# agentest FAQ

Short answers with pointers into the [User Guide](USER-GUIDE.md) and [Author Guide](AUTHOR-GUIDE.md). Everything here
describes the code on `main` (version 3.3.0) unless it says otherwise. Every command below was run against `main`.

## Install

**How do I install it?**

```bash
pip install "agentest @ git+https://github.com/srpadmanabhuni/agentest.git@v3.3.0"
agentest version          # 3.3.0
```

From a clone (needed for the `examples/` folder used below):

```bash
git clone https://github.com/srpadmanabhuni/agentest.git && cd agentest
python -m venv .venv && . .venv/bin/activate && pip install -e ".[dev]"
```

**What does it depend on?** Python 3.11+ and PyYAML. No account, API key, network or model is needed to judge.
Optional extras: `agentest[otlp]` (official OTLP/protobuf decoder) and `agentest[dev]` (pytest, ruff, jsonschema).

**Is it on PyPI?** Not yet. Install from git as shown above.

## Quickstart

**What is the fastest way to see it work?** From a clone:

```bash
agentest std validate --agents examples/agnostic_demo/agents
agentest std run --agents examples/agnostic_demo/agents
# refill_bot: 55 pass, 0 fail; refill_bot_buggy: 41 pass, 16 fail
```

**How do I run it on my own agent?** Give it an OTLP trace file; the A2A AgentCard and MCP tools list are optional:

```bash
agentest std run --otlp my_traces.otlp.jsonl --card agent-card.json --tools tools.json
```

To see the expected trace shape, generate one with the standard library only:

```bash
mkdir -p build
python examples/otel_plain/emit_trace.py > build/trace.otlp.json
agentest std run --otlp build/trace.otlp.json \
    --card examples/otel_plain/agent-card.json --tools examples/otel_plain/tools.json
```

**How do I use it in CI?**

```bash
agentest std run --format junit --out agentest.xml --strict
```

`--strict` exits with status 1 if any verdict is `fail`. Other formats: `json`, `sarif`, `md`, `html`, `csv`.
Use `--ids T1-001,T6-010` to limit the report to some checks, and `--config` to disable IDs or set thresholds
([User Guide §6](USER-GUIDE.md#6-configuration)).

## Agent-agnostic usage

**Does it only work with a particular framework?** No. Every check is one universal rule over standard artifacts:
OpenTelemetry GenAI spans, the A2A AgentCard and MCP tool annotations. No rule names an agent, a tool or a vendor,
and CI enforces this with the [agent-independence audit](standards/AGENT-INDEPENDENCE-AUDIT.md) and the
[no-lock-in checks](NO-LOCK-IN.md).

**My agent already emits OpenTelemetry.** Export the spans to a file with any OTLP file exporter, or point an
OTLP/HTTP exporter at the built-in collector:

```bash
agentest std serve --out build/inbox --port 4319 --max-requests 1
```

**My agent is not instrumented.** Convert its native log once with `agentest std import`. Built-in dialects on
`main`: `steps`, `events`, `openai_agents` (OpenAI Agents SDK run items), `langgraph_msgs` (LangGraph message
lists), `autogen` and `n8n`. Anything else uses a JSON mapping file or a `file:my.py` adapter
([Author Guide §3](AUTHOR-GUIDE.md#3-a-framework-adapter)).

```bash
agentest std import examples/agnostic_demo/native/refill_bot.jsonl \
    --map examples/agnostic_demo/import/map.json \
    --tools examples/agnostic_demo/agents/refill_bot/tools.json \
    --service refill_bot --out build/refill_bot.otlp.jsonl
agentest std run --otlp build/refill_bot.otlp.jsonl \
    --card examples/agnostic_demo/agents/refill_bot/agent-card.json \
    --tools examples/agnostic_demo/agents/refill_bot/tools.json
```

A LangGraph example is in `examples/langgraph_import/`.

**Are there Python converters for LangGraph state or the OpenAI Agents SDK?** Not on `main` yet. Richer converters
(LangGraph state and checkpoint history, OpenAI Agents SDK `new_items`) and an `agentest std lint` command are in
review and not released. On `main`, use `agentest std import` with the dialects above.

## Verdicts

**What do `pass`, `fail` and `n/a` mean?**

| Verdict | Meaning |
|---|---|
| `pass` | The rule found the signal it needs and the behaviour met the rule. |
| `fail` | The rule found the signal and the behaviour broke the rule. `detail` names the evidence (tool call, argument, output excerpt). |
| `n/a` | The signal the rule needs is missing, or the ID was disabled by config. `detail` names what is missing. |

`n/a` is **never** counted as a pass. In JUnit it is reported as skipped.

**Why are so many of my checks `n/a`?** Most rules need a fact your traces or card do not carry yet: for example
which tools change state (MCP `readOnlyHint`/`destructiveHint`), the expected outcome, the user's language, or
approval records. Add the span attribute or publish the fact, and the check becomes a real `pass`/`fail`. See
[User Guide](USER-GUIDE.md) and the [governance extension](standards/EXTENSION.md).

**What are `strict` and `examples` modes?** `strict` reads only standard fields and the extension. `examples` (the
default) also uses the success criteria published in the AgentCard skill examples.

## Scoring and metrics

**Is there one overall score?** No. agentest reports a verdict per agent × check, plus totals of pass, fail and
n/a. It is not a leaderboard.

**How do you measure agentest's own accuracy?** With blind rounds: agents with planted defects whose answer key is
sealed until the rules are frozen ([BLIND-TEST.md](BLIND-TEST.md)). We report:
- **precision**: of the defects agentest flags, how many are real;
- **recall**: of the planted defects, how many agentest flags;
- **control false alarms**: failures on clean control agents (target 0).

Accuracy work is in progress. We will publish numbers only after they have been verified across blind rounds.

## Known limits

- **High `n/a` without signals.** Many checks stay `n/a` until the agent emits the needed attributes.
- **Accuracy is still being improved.** Some rules miss real defects or raise false alarms. Please report them
  using the false-positive and false-negative issue forms.
- **Heuristics on free text.** Several rules use English regex heuristics (claims, warnings, refusals). They are
  deterministic but uncalibrated; see [false positives](testers/FALSE-POSITIVES.md).
- **Reference agents run on a small local model** with a few runs per input.
- **Not certification.** The checklist is informed by ISO 42001 themes, but a run is not an audit.
- No model judge sits in the pass/fail path.

## Contributing and support

- How to contribute: [CONTRIBUTING.md](../CONTRIBUTING.md). New checks follow the [Author Guide](AUTHOR-GUIDE.md).
- Bugs, feature requests and wrong verdicts: open a GitHub issue using the matching form.
- Questions: [SUPPORT.md](../SUPPORT.md).
- Security issues: email srinivas AT testAIng.com instead of opening a public issue.
- **Never paste secrets, API keys or personal data in an issue.** Redact traces first.
