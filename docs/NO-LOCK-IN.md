# No lock-in

agentest v3 is designed so that you can adopt it, replace it, or run it alongside anything else without rewriting
your agent. Every guarantee below is enforced by a test in [`tests/test_no_lock_in.py`](../tests/test_no_lock_in.py)
or a CI step in [`.github/workflows/ci.yml`](../.github/workflows/ci.yml).

| Guarantee | How it is enforced |
|---|---|
| **No vendor SDKs.** Runtime imports are the Python stdlib, PyYAML and agentest only. There are no model, cloud or eval-framework SDKs, no API keys and no network calls. | `test_runtime_imports_are_stdlib_pyyaml_or_agentest_only` (AST scan of `src/`) |
| **Minimal, permissive dependencies.** The only runtime dependency is `pyyaml>=6`, with no `==` pins. The licence is Apache-2.0. | `test_dependencies_minimal_unpinned_permissive` |
| **Your agent never imports agentest.** Reference and demo agents emit plain traces. | `test_reference_and_demo_agents_need_no_agentest_import` |
| **Standard inputs.** OTel GenAI spans (OTLP/JSON from any collector), the A2A AgentCard, MCP tool annotations and JSON Schema. | `test_cli_otlp_file_from_any_collector`; the CI step "Traces-only onboarding" |
| **Standard, versioned outputs.** Verdicts JSON (validated against [`verdicts.schema.json`](../src/agentest/standards/schemas/verdicts.schema.json)), SARIF 2.1.0 (validated against the OASIS schema), JUnit XML, Markdown and HTML. | `test_versioned_json_validates`, `test_sarif_validates_against_oasis_schema`, `test_junit_structure`, `test_markdown_and_html` |
| **Open catalogue.** All 136 checks export as CSV or JSON (catalogue text is CC BY 4.0). | `test_catalogue_exports_csv_and_json`; `agentest std catalog --format csv` |
| **Optional, schema-checked extension.** The governance extension is validated by [`governance-extension.schema.json`](../src/agentest/standards/schemas/governance-extension.schema.json). Without it, rules fall back to standard fields or return `n/a`. | `test_governance_extension_schema_validates_every_published_card`, `test_extension_is_optional_absent_means_na` |
| **Override anything locally.** `rules_dir` adds your own rules, config can disable any ID, and thresholds are configurable. | `test_local_rules_dir_config_disable_and_thresholds` |
| **Plugins without forking.** Rules can be added through Python entry points (`agentest.rules`), and log adapters through `agentest std import --dialect file:my_dialect.py`. | `test_entry_point_plugin`; the [ONBOARDING](developers/ONBOARDING.md) guide |
| **Traces-only onboarding.** Traces with no card still produce results. | `test_traces_only_agent_degrades_gracefully`; [`examples/otel_plain/`](../examples/otel_plain/) |

## Leaving agentest

Your instrumentation is plain OpenTelemetry, your AgentCard is plain A2A, and your tools are plain MCP. None of these
belongs to agentest. The SARIF and JUnit output works in any code-scanning or CI dashboard. To leave, delete the
dependency. The only agentest-specific artifacts are the `agentest.*` span attributes and the extension block in
your card, and both are ignored by every other tool.

## Residual risks (honest list)

1. **Language-dependent heuristics.** Many oracles classify replies with English regular expressions, with partial
   Spanish and Hindi coverage. Replies in other languages may show up as `n/a` or as false results. See
   [FALSE-POSITIVES](testers/FALSE-POSITIVES.md).
2. **Extension fields have no standard yet.** These are approval decisions (`agentest.approval`), data classes,
   limits and allow-lists. If an A2A or OTel convention appears, the fields will need a migration. The plan is to
   map the fields onto it and keep reading the old names for one major version.
3. **OTel GenAI semantic conventions are still in *Development* status.** Attribute names may change upstream.
   The version agentest reads is pinned in `standards/semconv.yaml`, and older versions and other instrumentation
   styles are mapped there as data; parsing is in a single place (`standards/otel.py`).
4. **The bundled agents ship as data** (`agents/`: AgentCard, MCP tools and OTLP traces only) in the wheel's
   `share/agentest/`. They are systems under test, not engine code, but they add to the package size.
5. **The legacy v2 engine was removed in v3.1.0.** Its regression record (v3.0.0 vs v2.0.0) stays in
   [REGRESSION.md](standards/REGRESSION.md) and the code stays at the `v2.0.0` tag; the CI guard
   `tests/test_standards_guard.py` fails if v2 code (modules, folders or imports) or per-agent YAML returns anywhere in the repo.
6. **The vendored SARIF schema** in `tests/schemas/` is used only in tests and is not shipped in the wheel. Keep its
   OASIS licence notice if you redistribute the tests.
7. **Framework instrumentation naming.** Some frameworks emit non-GenAI span names. These need rows in
   `semconv.yaml` (attribute and event names only) or a dialect for `agentest std import`.
