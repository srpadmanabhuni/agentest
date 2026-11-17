#!/usr/bin/env python3
"""Keep the source-reference comments in the code and the short-key tables in docs/REFERENCES.md in sync.

Sources of truth (nothing is invented here):

* ``agentest.refs`` (``BIB``, ``CLASS_REFS``, ``ID_REFS``): the bibliography verified against arXiv / doi.org / the
  publisher or standards body, and its per-ID mapping (the same mapping that renders ``docs/tests/<ID>.md``);
* ``catalog/checklist-110.jsonl`` and ``catalog/rai-additions-v1.4.0.jsonl``: the ``control_refs`` crosswalk of each ID;
* the SPECS table below: specifications and framework documentation that modules implement or read, each opened and
  checked on 2026-11-15.

It only writes comment lines that start with ``# Ref `` (above every ``@rule`` in ``rules.py``, after the module docstring of
the modules in MODULE_REFS, and above a few regex constants) and the generated tables of ``docs/REFERENCES.md``.
It never changes code, so behaviour is identical with and without the comments.

Usage:  python scripts/gen_code_refs.py           # rewrite comments and tables
        python scripts/gen_code_refs.py --check   # exit 1 if anything is stale
"""
# Ref: this script is the source of the short keys in docs/REFERENCES.md section D/E.

from __future__ import annotations

import ast
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from agentest.refs import BIB, CLASS_REFS, ID_REFS  # noqa: E402

# bibliography key (agentest.refs.BIB) -> short key used in code comments and docs/REFERENCES.md
SHORT = {
    "chen-mt": "Chen-1998", "segura-mt": "Segura-2016", "barr-oracle": "Barr-2015", "hoare": "Hoare-1969", "haerder": "Haerder-1983",
    "sagas": "GarciaMolina-1987", "kahn": "Kahn-1962", "lamport": "Lamport-1978", "rfc9110": "RFC9110", "rfc6585": "RFC6585",
    "rfc6749": "RFC6749", "saltzer": "Saltzer-1975", "hardy": "Hardy-1988", "nist-800-122": "NIST-SP800-122", "owasp-ssrf": "OWASP-SSRF",
    "owasp-sqlparam": "OWASP-SQLParam", "owasp-path": "OWASP-PathTraversal", "owasp-csv": "OWASP-CSVInjection", "owasp-logging": "OWASP-Logging",
    "owasp-llm01": "OWASP-LLM01-2025", "owasp-llm02": "OWASP-LLM02-2025", "owasp-llm05": "OWASP-LLM05-2025", "owasp-llm06": "OWASP-LLM06-2025",
    "owasp-llm07": "OWASP-LLM07-2025", "owasp-llm09": "OWASP-LLM09-2025", "owasp-llm10": "OWASP-LLM10-2025",
    "owasp-agentic": "OWASP-AgenticTop10-2026", "owasp-agentic-threats": "OWASP-AgenticThreats", "iso42001": "ISO-42001-2023",
    "nist-rmf": "NIST-AIRMF-1.0", "eu-ai-act": "EU-AIAct-2024", "gdpr": "GDPR-2016", "greshake": "Greshake-2023", "perez-ignore": "Perez-2022",
    "liu-pi": "Liu-2023", "injecagent": "InjecAgent-2024", "agentdojo": "AgentDojo-2024", "bipia": "BIPIA-2023", "spotlighting": "Spotlighting-2024",
    "asb": "ASB-2024", "agentpoison": "AgentPoison-2024", "taubench": "TauBench-2024", "trace": "TRACE-2025", "toolemu": "ToolEmu-2023",
    "agentbench": "AgentBench-2023", "agentboard": "AgentBoard-2024", "apibank": "APIBank-2023", "helm": "HELM-2022",
    "memory-survey": "MemorySurvey-2024", "lost-middle": "LostInTheMiddle-2023", "halluc-survey": "HallucinationSurvey-2023", "rag": "RAG-2020",
    "jacovi": "Jacovi-2020", "react": "ReAct-2022", "selfconsistency": "SelfConsistency-2022", "sycophancy": "Sycophancy-2023",
    "anthropic-agents": "Anthropic-Agents-2024", "yong-lowres": "Yong-2023", "deng-multi": "Deng-2023", "garg": "Garg-2019", "bbq": "BBQ-2021",
    "decodingtrust": "DecodingTrust-2023", "mcp-tools": "MCP-Tools-2025-06-18", "langgraph-interrupts": "LangGraph-Interrupts",
    "langgraph-persistence": "LangGraph-Persistence", "openai-handoffs": "OpenAIAgents-Handoffs", "openai-guardrails": "OpenAIAgents-Guardrails",
    "python-sqlite": "Python-sqlite3", "qwen25": "Qwen2.5-2024", "llamacpp": "llama.cpp", "taxonomy": "Padmanabhuni-2026-Taxonomy",
    "catalogue": "Padmanabhuni-2026-Catalogue",
}

# Specifications / documentation that modules implement or read: short key -> (citation, url). Each URL (or DOI) was opened on 2026-11-15
# (ISO and EUR-Lex answer scripted clients with 403 / a bot challenge; ISO 42001 was read via a browser-style fetch).
SPECS = {
    "Chen-2018": ("Chen, T. Y., Kuo, F.-C., Liu, H., Poon, P.-L., Towey, D., Tse, T. H., Zhou, Z. Q. (2018). *Metamorphic Testing: A Review of Challenges and Opportunities.* ACM Computing Surveys 51(1).", "https://doi.org/10.1145/3143561"),
    "Utting-2012": ("Utting, M., Pretschner, A., Legeard, B. (2012). *A taxonomy of model-based testing approaches.* Software Testing, Verification and Reliability 22(5).", "https://doi.org/10.1002/stvr.456"),
    "OTel-GenAI-semconv": ("OpenTelemetry. *Semantic conventions for generative AI systems* (status: Development).", "https://opentelemetry.io/docs/specs/semconv/gen-ai/"),
    "OTel-GenAI-agent-spans": ("OpenTelemetry. *Semantic conventions for GenAI agent and framework spans.*", "https://opentelemetry.io/docs/specs/semconv/gen-ai/gen-ai-agent-spans/"),
    "OTLP-spec": ("OpenTelemetry. *OTLP Specification* (JSON Protobuf encoding; OTLP/HTTP).", "https://opentelemetry.io/docs/specs/otlp/"),
    "OTel-proto": ("OpenTelemetry. *opentelemetry-proto* (`trace/v1/trace.proto`, `common/v1/common.proto`).", "https://github.com/open-telemetry/opentelemetry-proto"),
    "A2A-spec": ("A2A Protocol. *Agent2Agent protocol specification* (AgentCard, agent discovery).", "https://a2a-protocol.org/latest/specification/"),
    "CEL": ("Common Expression Language (CEL). Inspiration for the safe expression subset in `expr.py`; no CEL code is used.", "https://cel.dev"),
    "JSONLogic": ("JsonLogic. Inspiration for side-effect-free rule expressions; no JsonLogic code is used.", "https://jsonlogic.com/"),
    "SARIF-2.1.0": ("OASIS. *Static Analysis Results Interchange Format (SARIF) Version 2.1.0.*", "https://docs.oasis-open.org/sarif/sarif/v2.1.0/sarif-v2.1.0.html"),
    "PyPA-EntryPoints": ("Python Packaging Authority. *Entry points specification.*", "https://packaging.python.org/en/latest/specifications/entry-points/"),
    "UAX24": ("Unicode Standard Annex #24, *Unicode Script Property* (script names used by the language-script check).", "https://www.unicode.org/reports/tr24/"),
    "BCP47": ("IETF BCP 47 / RFC 5646, *Tags for Identifying Languages* (primary language subtags).", "https://www.rfc-editor.org/rfc/rfc5646"),
    "Python-unicodedata": ("Python docs. *unicodedata* (character names).", "https://docs.python.org/3/library/unicodedata.html"),
    "JSON-Schema-2020-12": ("JSON Schema, draft 2020-12 (MCP `inputSchema`).", "https://json-schema.org/draft/2020-12"),
    "OpenAIAgents-SDK": ("OpenAI Agents SDK docs (RunItems, tracing).", "https://openai.github.io/openai-agents-python/"),
    "LangGraph-docs": ("LangGraph docs. *Overview.*", "https://docs.langchain.com/oss/python/langgraph/overview"),
    "AutoGen-AgentChat": ("Microsoft AutoGen docs. *AgentChat user guide.*", "https://microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/index.html"),
    "smolagents-docs": ("Hugging Face. *smolagents* (library repository and documentation links).", "https://github.com/huggingface/smolagents"),
    "n8n-docs": ("n8n documentation.", "https://docs.n8n.io/"),
    "LlamaIndex-docs": ("LlamaIndex documentation.", "https://docs.llamaindex.ai/"),
    "CrewAI-docs": ("CrewAI documentation.", "https://docs.crewai.com/"),
    "InspectAI-docs": ("Inspect AI (UK AI Security Institute) documentation.", "https://inspect.aisi.org.uk/"),
    "promptfoo-docs": ("promptfoo documentation.", "https://www.promptfoo.dev/docs/intro/"),
    "DeepEval-docs": ("DeepEval documentation.", "https://deepeval.com/docs/getting-started"),
    "OpenAI-FunctionCalling": ("OpenAI. *Function calling* guide (tool-call message shape used by the OpenAI-compatible reference agents).", "https://platform.openai.com/docs/guides/function-calling"),
}
KEY_NAME = {v: k for k, v in SHORT.items()}
CLASS_OF = lambda i: "X" if i.startswith("X-") else i[:2]  # noqa: E731
HIDDEN = ("a161", "a162", "a163", "a164", "a165", "a166", "a167", "a168", "a169", "a170")  # never opened (standing rule); asserted below

from agentest.standards.catalog import ALL_IDS, RAI_ADDITION_IDS  # noqa: E402

KNOWN_IDS = set(ALL_IDS) | set(RAI_ADDITION_IDS)
CATALOGUE_FILES = ("catalog/checklist-110.jsonl", "catalog/rai-additions-v1.4.0.jsonl")


def _controls() -> tuple[dict[str, str], dict[str, str]]:
    ctl, src = {}, {}
    for f in CATALOGUE_FILES:
        for line in (ROOT / f).read_text(encoding="utf-8").splitlines():
            if line.strip():
                r = json.loads(line)
                ctl[r["id"]] = r.get("control_refs") or ""
                src[r["id"]] = f
    return ctl, src


CTL, CAT_SRC = _controls()


def internal_src(i: str) -> str:
    if i in CAT_SRC:
        return f"{CAT_SRC[i]} {i}"
    return f"docs/tests/{i}.md, src/agentest/standards/catalog.py"


def keys(ks: list[str]) -> str:
    return " ".join(f"[{SHORT[k]}]" for k in ks)


def rule_lines(i: str) -> list[str]:
    spec = [k for k in ID_REFS.get(i, [])]
    bg = [k for k in CLASS_REFS[CLASS_OF(i)] if k not in spec]
    if spec:
        out = [f"# Ref {i}: {keys(spec)}" + (f"; class background: {keys(bg)}" if bg else "")]
    else:
        out = [f"# Ref {i}: internal design ({internal_src(i)})" + (f"; class background: {keys(bg)}" if bg else "")]
    if CTL.get(i):
        out.append(f"# Ref {i} controls (catalogue control_refs, indicative): {CTL[i]}")
    return out


def classify(i: str) -> str:
    return "external" if ID_REFS.get(i) else "internal"


RULES_HEADER = [
    "# Ref policy: every rule below is an in-house deterministic oracle over OTel traces and published metadata. The works cited in the",
    "# Ref policy (cont.): the `# Ref <ID>` comments are the threat model, standard or method behind the check, not validation of this implementation; where an ID has",
    "# Ref policy (cont.): no ID-specific source the comment says `internal design` and gives the catalogue row. See docs/TEST-SOURCES.md (method and audit per ID).",
    "# Ref keys: defined in docs/REFERENCES.md. Oracle families: [Barr-2015] state-based, [Chen-2018] metamorphic, [Utting-2012] model-derived,",
    "# Ref keys (cont.): [TauBench-2024] k-run reliability. Trace shape: [OTel-GenAI-semconv]; agent metadata: [A2A-spec], [MCP-Tools-2025-06-18].",
    "# Ref catalogue credit: [Padmanabhuni-2026-Taxonomy] (IDs), [Padmanabhuni-2026-Catalogue] (test text). Control crosswalk: docs/standards/STANDARDS-MAP.md.",
]

INLINE_RULES = {  # exact line prefix in rules.py -> comment lines placed above it
    "BUDGET = {": ["# Ref: default budgets: resource-limit concern per [OWASP-LLM10-2025] (X-005, X-006, X-007, T5-006); the numeric defaults are in-house."],
    "SSN_RX = ": ["# Ref: PII examples per [NIST-SP800-122] (T5-004, T7-014, X-020); the regex patterns are in-house heuristics, not a PII standard."],
    "SQL_RX = ": ["# Ref: parameterised vs inline-literal SQL per [OWASP-SQLParam] and [Python-sqlite3] (T5-010); the regexes are in-house."],
    "TRAVERSAL_RX = ": ["# Ref: path-traversal patterns per [OWASP-PathTraversal] (T5-008); the regex is in-house."],
    "DIRECTIVE_RX = ": ["# Ref: injected directives in untrusted content per [Greshake-2023], [Perez-2022], [Spotlighting-2024] (T4-*); the span patterns are in-house."],
    "LANG_SCRIPTS": ["# Ref: primary language subtags per [BCP47]; script names per [UAX24] (X-014); the language-to-script table is in-house."],
    "SOFT_RX = ": ["# Ref: soft delete vs erasure context per [GDPR-2016] Art. 17 (T1-016); the field-name vocabulary is in-house."],
    "REVOKE_RX = ": ["# Ref: consent withdrawal per [GDPR-2016] Art. 7(3) (T6-004); the phrasing patterns are in-house."],
}

MODULE_REFS = {
    "src/agentest/standards/rules.py": RULES_HEADER,
    "src/agentest/standards/otel.py": [
        "# Ref: [OTel-GenAI-semconv], [OTel-GenAI-agent-spans] (span and attribute names); [OTLP-spec] (JSON encoding). `agentest.*` attributes are the in-house extension",
        "# Ref: internal design (docs/standards/EXTENSION.md).",
    ],
    "src/agentest/standards/otlp_proto.py": ["# Ref: [OTLP-spec] (protobuf encoding), [OTel-proto] (field numbers); the stdlib decoder is in-house."],
    "src/agentest/standards/serve.py": ["# Ref: [OTLP-spec] (OTLP/HTTP receiver behaviour); the sink layout under <out>/ is in-house design."],
    "src/agentest/standards/metadata.py": [
        "# Ref: [A2A-spec] (AgentCard), [MCP-Tools-2025-06-18] (tools/list, annotations), [JSON-Schema-2020-12] (inputSchema).",
        "# Ref: internal design (docs/standards/EXTENSION.md) for the governance extension urn:agentest:a2a-ext:governance:v1.",
    ],
    "src/agentest/standards/inputs.py": [
        "# Ref: metamorphic relations [Chen-1998] (idea), [Chen-2018] (survey), [Segura-2016] (survey); generator from published metadata [Utting-2012].",
        "# Ref: internal design for the concrete input families and relation set (docs/tests/T7-*.md, docs/TEST-SOURCES.md).",
    ],
    "src/agentest/standards/importers.py": [
        "# Ref: dialect mappings read these public log formats: [OpenAIAgents-SDK], [LangGraph-docs], [AutoGen-AgentChat], [smolagents-docs], [n8n-docs],",
        "# Ref: [LlamaIndex-docs], [CrewAI-docs]. Target format: [OTel-GenAI-semconv]. The mapping engine itself is in-house (no framework code is used).",
    ],
    "src/agentest/standards/expr.py": ["# Ref: [CEL] and [JSONLogic] (inspiration only); the allow-listed Python-ast evaluator is in-house design."],
    "src/agentest/standards/scenario.py": ["# Ref: test-oracle concept per [Barr-2015]; scenario format is internal design (docs/standards/DESIGN.md)."],
    "src/agentest/standards/reports.py": ["# Ref: [SARIF-2.1.0] (SARIF output); JSON verdict schema is internal design (src/agentest/standards/schemas/verdicts.schema.json)."],
    "src/agentest/standards/ext.py": ["# Ref: [PyPA-EntryPoints] (plugin entry points); config/rule-extension design is internal (docs/standards/EXTENSION.md)."],
    "src/agentest/standards/hub.py": ["# Ref: internal design (catalog/VERSION, docs/CATALOGUE-AND-HF.md): pinned-revision, sha256-verified, cached catalogue fetch."],
    "src/agentest/standards/catalog.py": ["# Ref: [Padmanabhuni-2026-Taxonomy] (IDs), [Padmanabhuni-2026-Catalogue] (text); the X-001..X-020 extensions are internal design (docs/tests/X-*.md)."],
    "src/agentest/standards/runner.py": ["# Ref: internal design (docs/standards/REGRESSION.md); verdict baseline comparison is regression testing of the rules themselves."],
    "src/agentest/standards/episode.py": ["# Ref: internal design (docs/standards/DESIGN.md); mirrors the OTel GenAI message/tool-call shapes of [OTel-GenAI-semconv]."],
    "src/agentest/mock_agent.py": ["# Ref: endpoint contract is internal design (docs/GETTING-STARTED.md); it replays [OTel-GenAI-semconv] traces and serves [A2A-spec] / [MCP-Tools-2025-06-18] metadata."],
    "src/agentest/cli.py": ["# Ref: internal design (docs/USER-GUIDE.md, docs/HOW-IT-WORKS.md); the std subcommands are in src/agentest/standards/cli.py."],
    "src/agentest/standards/cli.py": ["# Ref: internal design (docs/standards/DEVELOPER-GUIDE.md); output formats cite their specs in reports.py, trace input in otel.py."],
    "src/agentest/local.py": ["# Ref: internal design (docs/GETTING-STARTED.md); probe results are scored by the rules in standards/rules.py."],
    "src/agentest/paths.py": ["# Ref: internal design (docs/standards/DEVELOPER-GUIDE.md); no external source."],
    "src/agentest/refs.py": ["# Ref: this module IS the bibliography (agentest.refs.BIB); short keys for code comments are in docs/REFERENCES.md (section D, scripts/gen_code_refs.py)."],
    "scripts/gen_test_docs.py": ["# Ref: renders per-test References from agentest.refs; sources are listed in docs/REFERENCES.md."],
    "scripts/gen_framework_mapping.py": ["# Ref: control_refs vocabulary: [NIST-AIRMF-1.0], [OWASP-AgenticTop10-2026], [EU-AIAct-2024]; indicative crosswalk only (docs/FRAMEWORK-MAPPING.md)."],
    "scripts/gen_standards_map.py": ["# Ref: VOCAB ids come from [OWASP-LLM01-2025] .. [OWASP-LLM10-2025], [OWASP-AgenticThreats], [NIST-AIRMF-1.0] (docs/standards/STANDARDS-MAP.md)."],
    "scripts/gen_code_refs.py": ["# Ref: this script is the source of the short keys in docs/REFERENCES.md section D/E."],
    "examples/integrations/deepeval_goldens.py": ["# Ref: [DeepEval-docs] (Golden / EvaluationDataset API used here)."],
    "examples/integrations/inspect_ai_task.py": ["# Ref: [InspectAI-docs] (Task, Sample, scorers used here)."],
    "examples/integrations/promptfoo_tests_from_hf.py": ["# Ref: [promptfoo-docs] (tests file format produced here)."],
    "examples/otel_plain/emit_trace.py": ["# Ref: [OTel-GenAI-semconv], [OTLP-spec] (the trace shape written here)."],
    "examples/langgraph_import/test_langgraph.py": ["# Ref: [LangGraph-docs] (message-list shape imported); importer is src/agentest/standards/importers.py."],
    "templates/test_langgraph.py": ["# Ref: [LangGraph-docs] (message-list shape imported); importer is src/agentest/standards/importers.py."],
}
SKIP_NOTE = "module docstring ends the statement list"


def strip_refs_above(lines: list[str], idx: int) -> int:
    """Remove contiguous '# Ref ' lines immediately above lines[idx]; return new index of the target line."""
    j = idx
    while j > 0 and lines[j - 1].startswith("# Ref"):
        j -= 1
    del lines[j:idx]
    return j


def strip_refs_below(lines: list[str], idx: int) -> None:
    j = idx
    while j < len(lines) and lines[j].startswith("# Ref"):
        j += 1
    del lines[idx:j]


def annotate(rel: str) -> tuple[str, int, int]:
    p = ROOT / rel
    text = p.read_text(encoding="utf-8")
    tree = ast.parse(text)
    lines = text.split("\n")
    n_rules = 0
    inserts: list[tuple[int, list[str], str]] = []  # (line index of target, comment lines, kind)
    # 1. rule decorators (rules.py only)
    if rel.endswith("standards/rules.py"):
        import agentest.standards.rules as R

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                for d in node.decorator_list:
                    if isinstance(d, ast.Call) and getattr(d.func, "id", "") == "rule":
                        ids: list[str] = []
                        for a in d.args:
                            if isinstance(a, ast.Constant):
                                ids.append(a.value)
                            elif isinstance(a, ast.Starred) and isinstance(a.value, ast.Name):
                                ids.extend(getattr(R, a.value.id))
                        block: list[str] = []
                        ids = [i for i in ids if i in KNOWN_IDS]  # e.g. the transient 'T3-006b' is popped from RULES and is not a catalogue ID
                        for i in ids:
                            block += rule_lines(i)
                        n_rules += len(ids)
                        inserts.append((d.lineno - 1, block, "rule"))
        for prefix, cm in INLINE_RULES.items():
            hit = [k for k, ln in enumerate(lines) if ln.startswith(prefix)]
            assert len(hit) == 1, (prefix, hit)
            inserts.append((hit[0], list(cm), "inline"))
    # 2. module header after the docstring
    if rel in MODULE_REFS:
        first = tree.body[0]
        assert isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant) and isinstance(first.value.value, str), rel
        inserts.append((first.end_lineno, list(MODULE_REFS[rel]), "module"))
    # apply bottom-up so earlier indices stay valid
    for idx, block, kind in sorted(inserts, key=lambda t: -t[0]):
        if kind == "module":
            strip_refs_below(lines, idx)
            lines[idx:idx] = block
        else:
            idx = strip_refs_above(lines, idx)
            lines[idx:idx] = block
    new = "\n".join(lines)
    return new, n_rules, len(inserts)


def tables() -> str:
    used = set()
    out = ["| Short key | Reference | Bibliography key |", "|:--|:--|:--|"]
    for k, short in SHORT.items():
        out.append(f"| `[{short}]` | {BIB[k]} | `{k}` |")
        used.add(short)
    d = "\n".join(out)
    e = ["| Short key | Specification / documentation | URL |", "|:--|:--|:--|"]
    for short, (cite, url) in SPECS.items():
        e.append(f"| `[{short}]` | {cite} | <{url}> |")
    return d, "\n".join(e)


BEGIN, END = "<!-- gen_code_refs:begin -->", "<!-- gen_code_refs:end -->"


def refs_doc() -> str:
    p = ROOT / "docs" / "REFERENCES.md"
    text = p.read_text(encoding="utf-8")
    text = text.split(BEGIN)[0].rstrip("\n") + "\n"
    d, e = tables()
    block = f"""
{BEGIN}
## D. Short keys used in code comments

Code comments cite these keys, for example `# Ref T4-009: [OWASP-LLM02-2025] [Greshake-2023]` above a rule in
`src/agentest/standards/rules.py`. A key in square brackets is defined in this table or in section E. The works are the
threat model, standard or method *behind* a check; the oracle itself is in-house deterministic code (see
[TEST-SOURCES.md](TEST-SOURCES.md)). Where an ID has no ID-specific source the comment says `Ref <ID>: internal design`
and names its catalogue row (`catalog/checklist-110.jsonl`, `catalog/rai-additions-v1.4.0.jsonl`, or `docs/tests/<ID>.md`
for the X-001..X-020 repo extensions). Entries here repeat the verified bibliography of `agentest.refs.BIB`.

{d}

## E. Specifications and framework documentation cited in module comments

Opened and checked on 2026-11-15. Framework documentation is cited only where a module reads that framework's log or
message shape or an example drives its public API; no framework code is bundled.

{e}

Regenerate sections D and E and the code comments with `python scripts/gen_code_refs.py` (`--check` in CI-style use).
{END}
"""
    return text + block


def main() -> int:
    check = "--check" in sys.argv
    stale = []
    total_rules = 0
    for rel in MODULE_REFS:
        new, n, _ = annotate(rel)
        total_rules += n
        old = (ROOT / rel).read_text(encoding="utf-8")
        if new != old:
            stale.append(rel)
            if not check:
                (ROOT / rel).write_text(new, encoding="utf-8")
    newdoc = refs_doc()
    if newdoc != (ROOT / "docs" / "REFERENCES.md").read_text(encoding="utf-8"):
        stale.append("docs/REFERENCES.md")
        if not check:
            (ROOT / "docs" / "REFERENCES.md").write_text(newdoc, encoding="utf-8")
    if check and stale:
        print("stale:", ", ".join(stale))
        return 1
    print(("up to date" if check else "updated") + f": {len(stale)} file(s) changed, {total_rules} rule ids annotated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
