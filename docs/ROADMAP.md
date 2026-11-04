# agentest roadmap

This is a forward-looking plan, not a commitment. Items may move or change as we learn from real traces. Every item follows three rules: it stays zero cost (open-weights models and free tooling only), standards output is test coverage mapping and never a compliance percentage, and only verified control codes from `src/agentest/standards/standards_map.yaml` are used.

Install: `pip install agentest-ai` (until the PyPI release is live, install from the GitHub tag as shown in the README).

## Already scheduled (November 2026)

These are tracked separately and are not repeated below: the LangGraph adapter and instrumentation guide, golden cases for the 38 assessable core tests, and published per-check false-alarm and miss rates.

## After the current blind round (mid-November to December 2026)

- **smolagents adapter**, the same pattern as the LangGraph one (an importer dialect plus an optional wrapper, no new runtime dependencies). Size S to M.
- **MCP shadow-tool scenario**: a mock MCP server offers a look-alike, malicious tool next to the real one, and an assertion checks that the agent calls the legitimate tool. Size M.
- **Token and env-var exfiltration scenario**, extending T4-002: secrets or environment variables must never reach unauthenticated hosts. Size S to M.
- **PII injection scenarios**: synthetic PII seeded into memory and tool outputs, with an assertion that it does not leak to the model, logs or external calls. Size M.
- **Coverage-mapping JSON**: `agentest std run --format coverage-json` reports the number of mapped tests and the pass/fail count for each control, drawn from `src/agentest/standards/standards_map.yaml` (OWASP LLM and Agentic, NIST AI RMF and AI 600-1, ISO/IEC 42001 Annex A, MITRE ATLAS). Every report carries the disclaimer "test coverage, not a compliance determination". Size S to M.
- **Standards landing pages** under `docs/standards/` (OWASP Agentic, NIST AI RMF, ISO/IEC 42001, and an EU AI Act page only once its mappings are verified), linking to the Hugging Face catalogue files. Size S.
- **PyPI project description** for `agentest-ai`. Size S.

## Q1 2027

- **Golden traces beyond the core set**: pass and fail trace pairs for every remaining assessable rule, built with free, open-weights models only (for example Qwen or Llama, run locally or via free inference). Size L.
- **Agent playground Space**: drop in a trace and get a scorecard, extending the existing demo and viewer Spaces. Size M.
- **P0 smoke results across agent frameworks**, with a reproducible harness and open-weights models only. Each framework's maintainers get a heads-up before results are published. Size L.
- **Integration docs for the LangChain and CrewAI ecosystems** (documentation and community integrations). Size M.
- **Regional positioning pages** (EU, US, APAC). Size S.

Suggestions are welcome through GitHub issues and discussions.
