# Failure registry

A list of agent failures that anyone can re-run. **AiEnsured agentest, an Agentic AI Testing platform** gives each one a stable ID (`AFR-0001`, `AFR-0002`, ...), a category from the [failure taxonomy](../docs/taxonomy/TAXONOMY.md), the [OWASP Agentic Top 10](../docs/taxonomy/ASI-MAPPING.md) entries its failing checks map to, a recorded trace, and the verdicts agentest must give on it. CI re-runs every entry on every pull request, so an entry that stops reproducing turns a check red.

The list of entries is in the [index](../docs/registry/INDEX.md). Each entry is one file in [`entries/`](entries/), checked against the [schema](schema/afr-entry.schema.json).

## What an entry is, and is not

- It is one **recorded run** and the checks that fail on it, scoped to the example and version it names. It is not a verdict on a framework, a model or a product, and the entry says what it does not show.
- It is **reproducible**: the trace is in the repository, and `python scripts/run_registry.py` judges it with agentest alone. No model, key or network is needed to check the verdicts.
- It is not an incident database. Public incident catalogues exist (for example AVID and the Agent Incident Registry). An entry can link to a record there when it describes the same kind of failure (`links.external_registries`), and never needs to.

## Fields

| Field | Meaning |
|---|---|
| `id` | `AFR-NNNN`, issued in order, never reused. The file is `entries/<id>.json`. |
| `title`, `summary` | What the agent did wrong, in plain words. |
| `status` | `reproducible`, `fixed-upstream`, `needs-review` or `withdrawn` (the ID stays). |
| `category` | A taxonomy category, `AFC-NN`. Must be the category of at least one failing check. |
| `asi` | OWASP Agentic Top 10 entries (`ASI01` to `ASI10`) covered by the mapping of the failing checks. May be empty. |
| `failing_checks` | Check IDs that fail on the original run. Must equal the checks expected to fail in `variants.original`. |
| `target` | What was run, its version, and what the finding does not say. |
| `reproduce` | The command that regenerates the traces, whether it is offline, and the agentest command that prints the verdicts. |
| `variants.original` / `variants.fixed` | A recorded trace (plus AgentCard and tools list if needed) and the expected verdict for each check. `fixed` is optional. |
| `credit` | Who found, reproduced, wrote the check or fixed it. |
| `links` | The Failure Lab write-up, an issue or pull request, and optional external registry records. |

## Run it

```bash
python scripts/run_registry.py                 # validate and re-run every entry
python scripts/run_registry.py --entry AFR-0002
python scripts/run_registry.py --write-index   # after adding an entry, rewrite docs/registry/INDEX.md
```

## Add an entry

See [submit a reproducible agent failure](../CONTRIBUTING.md#submit-a-reproducible-agent-failure). In short: open the [reproducible agent failure](../.github/ISSUE_TEMPLATE/reproducible-failure.yml) issue, or copy [`entries/AFR-0002.json`](entries/AFR-0002.json), point it at your recorded trace, and open a pull request.

Failure Lab cases become registry entries as they land: each new case adds the next `AFR` ID in the same pull request.
