# Import Open Agent API approval outcomes

[Open Agent API v0.0.71](https://github.com/jiangxingfan1-coder/Open-Agent-API/tree/v0.0.71)
ran its offline ACP subprocess fixture. The log projects one pending snapshot
and three final outcomes: approval produced one fixture artifact; denial and
expiry produced none. It contains fixture labels and outcome facts, not raw
gateway events, credentials, or request text. The example does not need a
gateway or a model to run.

Follow [Start here](../../docs/START_HERE.md#the-path) to install agentest,
then run from the repository root:

```sh
ex=examples/open_agent_api_import
out=$(mktemp -d)
agentest std import "$ex/oaa-fixture.jsonl" --map "$ex/mapping.json" \
    --tools "$ex/tools.json" --service oaa-acp-fixture --out "$out/observed.otlp.jsonl"
agentest std run --otlp "$out/observed.otlp.jsonl" --tools "$ex/tools.json" \
    --ids T2-004,T3-004,X-016 --mode strict --format md --strict
```

The three checks pass: no unapproved effect (T2-004), one expired approval
treated as no (T3-004), and an action and target on the approval request (X-016).

For the negative control, remove the grant from a copy of the approved record
but keep its artifact. This control is bundled as `negative-control.jsonl`:

```sh
agentest std import "$ex/negative-control.jsonl" --map "$ex/mapping.json" \
    --tools "$ex/tools.json" --service oaa-acp-fixture --out "$out/control.otlp.jsonl"
agentest std run --otlp "$out/control.otlp.jsonl" --tools "$ex/tools.json" \
    --ids T2-004 --mode strict --format md --strict
```

The second command fails T2-004 and exits 1. This is a deliberate mutation,
not an observed failure of the gateway.

See the [pinned capture script and original fixture](https://gist.github.com/jiangxingfan1-coder/ee758b2ecc0a0ef09ea0c3cc432d8c8f/abc8207cb61c8cc2480d5167ba0cbad7f4c19238)
to regenerate the observations. The mapping records outcomes, not original
timestamps. To prove a specific grant preceded its effect, capture
timestamped approval and effect spans in the live run.
