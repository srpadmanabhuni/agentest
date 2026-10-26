# Framework mapping — per test

*Generated from `catalog/checklist-110.jsonl` by `scripts/gen_framework_mapping.py`. Do not edit by hand; re-run the script instead.*

This is the per-test counterpart to the class-level crosswalk in [FRAMEWORK-MAPPING.md](FRAMEWORK-MAPPING.md). Every row below is taken verbatim from the `control_refs` field carried by the catalogue entry for that ID, so the table and the machine-readable catalogue cannot disagree.

It remains an **indicative crosswalk**, not a compliance claim, an audit result or a certification statement. Passing a check does not make a system conformant with any framework. The mappings point at *themes*: they tell you which part of a framework is likely to care about a given failure mode, not which clause you have satisfied.

## Coverage

Of the 110 catalogue IDs:

| Framework | IDs with a reference | Share |
|:--|--:|--:|
| `NIST-AI-RMF` | 102 | 93% |
| `ISO42001` | 62 | 56% |
| `EU-AIA` | 53 | 48% |
| `OWASP-ASI` | 87 | 79% |

A blank cell is **not** an oversight and **not** a finding that the test is irrelevant to that framework. It means the catalogue author did not assert a mapping. Absence of a reference is the honest state for a test whose relationship to a framework is arguable; inventing a clause number to fill the cell would be worse than leaving it empty. See [Gaps and open questions](#gaps-and-open-questions).

## Token vocabulary

The tokens are the repo's own shorthand, not identifiers published by the framework owners. Expansions below are the mapping the catalogue intends.

**`NIST-AI-RMF`** — NIST AI RMF 1.0 subcategories (MEASURE / MANAGE / GOVERN).

| Token | Meaning | IDs |
|:--|:--|--:|
| `MEASURE-2.3` | MEASURE 2.3 — system performance/security evaluated against stated claims | 79 |
| `MANAGE-2.4` | MANAGE 2.4 — mechanisms to sustain deployed AI value and respond to incidents | 20 |
| `GOVERN-1.2` | GOVERN 1.2 — roles, responsibilities and accountability structures | 3 |

**`ISO42001`** — ISO/IEC 42001:2023 Annex A control groups.

| Token | Meaning | IDs |
|:--|:--|--:|
| `A.8` | Annex A.8 — AI system performance evaluation and operational controls | 59 |
| `A.6` | Annex A.6 — AI system impact assessment (data, privacy, harms) | 3 |

**`EU-AIA`** — Regulation (EU) 2024/1689 articles.

| Token | Meaning | IDs |
|:--|:--|--:|
| `Art9` | Art. 9 — risk management system | 47 |
| `Art14` | Art. 14 — human oversight | 15 |

**`OWASP-ASI`** — Descriptive threat names from the OWASP Agentic Security Initiative threat themes. These are **not** OWASP `ASIxx` identifiers — see the note on that below.

| Token | Meaning | IDs |
|:--|:--|--:|
| `ToolMisuse` | tool / capability misuse by the agent | 37 |
| `PromptInjection` | instruction injection through untrusted content | 21 |
| `PrivilegeCompromise` | privilege escalation or privilege confusion across agents | 19 |
| `MemoryPoisoning` | poisoning of persisted memory or state | 14 |
| `AgenticHandoff` | unsafe handover between agents of differing privilege | 9 |
| `GoalHijacking` | goal or objective hijacking | 2 |
| `HumanManipulation` | manipulation of the human approver | 2 |

## Per-test crosswalk

| ID | Class | Severity | NIST AI RMF | ISO/IEC 42001 | EU AI Act | OWASP agentic |
|:--|:--|:--|:--|:--|:--|:--|
| **T1-001** | T1 | critical | `MEASURE-2.3` | `A.8` | `Art9` | — |
| **T1-002** | T1 | critical | `MEASURE-2.3` | `A.8` | `Art9` | `GoalHijacking` |
| **T1-003** | T1 | high | `MEASURE-2.3` | `A.8` | `Art9` | — |
| **T1-004** | T1 | critical | `MEASURE-2.3` | `A.8` | — | `ToolMisuse` |
| **T1-005** | T1 | high | `MEASURE-2.3` | `A.8` | `Art9` | — |
| **T1-006** | T1 | high | `MEASURE-2.3` | `A.8` | — | — |
| **T1-007** | T1 | medium | `MEASURE-2.3` | `A.8` | — | — |
| **T1-008** | T1 | critical | `MEASURE-2.3` | `A.8` | — | `ToolMisuse` |
| **T1-009** | T1 | high | `MEASURE-2.3` | `A.8` | — | — |
| **T1-010** | T1 | medium | `MEASURE-2.3` | `A.8` | `Art14`, `Art9` | — |
| **T1-011** | T1 | medium | `MEASURE-2.3` | `A.8` | — | — |
| **T1-012** | T1 | high | `MEASURE-2.3` | `A.8` | — | — |
| **T1-013** | T1 | high | `MEASURE-2.3` | `A.8` | — | `ToolMisuse` |
| **T1-014** | T1 | medium | `MEASURE-2.3` | `A.8` | — | — |
| **T1-015** | T1 | medium | `MEASURE-2.3` | `A.8` | — | — |
| **T1-016** | T1 | high | `MEASURE-2.3` | `A.8` | `Art9` | — |
| **T1-017** | T1 | high | `MEASURE-2.3` | `A.8` | — | — |
| **T1-018** | T1 | medium | `MEASURE-2.3` | `A.8` | — | — |
| **T2-001** | T2 | critical | `MEASURE-2.3` | `A.8` | — | `ToolMisuse` |
| **T2-002** | T2 | critical | `MANAGE-2.4` | `A.8` | `Art9` | `ToolMisuse` |
| **T2-003** | T2 | critical | `MEASURE-2.3` | `A.8` | — | `ToolMisuse` |
| **T2-004** | T2 | critical | `GOVERN-1.2` | `A.6` | `Art14` | `PrivilegeCompromise` |
| **T2-005** | T2 | critical | `MEASURE-2.3` | `A.8` | `Art9` | `PrivilegeCompromise` |
| **T2-006** | T2 | high | `MEASURE-2.3` | — | — | `ToolMisuse` |
| **T2-007** | T2 | high | `MEASURE-2.3` | — | `Art14`, `Art9` | `ToolMisuse` |
| **T2-008** | T2 | medium | `MEASURE-2.3` | — | — | `ToolMisuse` |
| **T2-009** | T2 | medium | `MEASURE-2.3` | — | — | `ToolMisuse` |
| **T2-010** | T2 | high | `MEASURE-2.3` | — | `Art14`, `Art9` | `ToolMisuse` |
| **T2-011** | T2 | critical | `MANAGE-2.4` | `A.8` | `Art9` | `PrivilegeCompromise` |
| **T2-012** | T2 | critical | `GOVERN-1.2` | `A.6` | `Art14` | `HumanManipulation` |
| **T2-013** | T2 | medium | `MEASURE-2.3` | — | — | `ToolMisuse` |
| **T2-014** | T2 | low | `MEASURE-2.3` | — | — | `ToolMisuse` |
| **T3-001** | T3 | critical | `MANAGE-2.4` | — | `Art14` | `AgenticHandoff`, `PrivilegeCompromise` |
| **T3-002** | T3 | critical | `MANAGE-2.4` | `A.8` | `Art9` | `PrivilegeCompromise` |
| **T3-003** | T3 | critical | `MANAGE-2.4` | `A.8` | `Art14` | `PrivilegeCompromise` |
| **T3-004** | T3 | critical | `GOVERN-1.2` | `A.6` | `Art14` | `HumanManipulation` |
| **T3-005** | T3 | high | — | — | `Art14`, `Art9` | `PrivilegeCompromise`, `AgenticHandoff` |
| **T3-006** | T3 | medium | — | — | — | `PrivilegeCompromise`, `AgenticHandoff` |
| **T3-007** | T3 | high | — | — | `Art9` | `PrivilegeCompromise`, `AgenticHandoff` |
| **T3-008** | T3 | critical | `MEASURE-2.3` | `A.8` | `Art9` | `PrivilegeCompromise` |
| **T3-009** | T3 | high | — | — | `Art9` | `PrivilegeCompromise`, `AgenticHandoff` |
| **T3-010** | T3 | high | — | — | `Art14`, `Art9` | `PrivilegeCompromise`, `AgenticHandoff` |
| **T3-011** | T3 | high | — | — | `Art9` | `PrivilegeCompromise`, `AgenticHandoff` |
| **T3-012** | T3 | medium | — | — | `Art14`, `Art9` | `PrivilegeCompromise`, `AgenticHandoff` |
| **T3-013** | T3 | critical | `MANAGE-2.4` | `A.8` | — | `PrivilegeCompromise` |
| **T3-014** | T3 | medium | — | — | `Art9` | `PrivilegeCompromise`, `AgenticHandoff` |
| **T4-001** | T4 | critical | `MEASURE-2.3` | `A.8` | `Art9` | `PromptInjection` |
| **T4-002** | T4 | critical | `MEASURE-2.3` | — | — | `PromptInjection`, `ToolMisuse` |
| **T4-003** | T4 | critical | `MEASURE-2.3` | — | — | `PromptInjection`, `ToolMisuse` |
| **T4-004** | T4 | critical | `MEASURE-2.3` | `A.8` | — | `PromptInjection`, `PrivilegeCompromise` |
| **T4-005** | T4 | critical | `MEASURE-2.3` | `A.8` | — | `PromptInjection` |
| **T4-006** | T4 | high | `MEASURE-2.3` | — | `Art9` | `PromptInjection` |
| **T4-007** | T4 | high | `MEASURE-2.3` | — | `Art9` | `PromptInjection` |
| **T4-008** | T4 | critical | `MEASURE-2.3` | — | — | `PromptInjection`, `ToolMisuse` |
| **T4-009** | T4 | high | `MEASURE-2.3` | — | `Art9` | `PromptInjection` |
| **T4-010** | T4 | high | `MEASURE-2.3` | — | `Art9` | `PromptInjection` |
| **T4-011** | T4 | critical | `MEASURE-2.3` | `A.8` | — | `PromptInjection` |
| **T4-012** | T4 | medium | `MEASURE-2.3` | — | `Art9` | `PromptInjection` |
| **T4-013** | T4 | high | `MEASURE-2.3` | — | `Art9` | `PromptInjection` |
| **T4-014** | T4 | high | `MEASURE-2.3` | — | `Art9` | `PromptInjection` |
| **T4-015** | T4 | critical | `MEASURE-2.3` | — | — | `PromptInjection`, `ToolMisuse` |
| **T4-016** | T4 | medium | `MEASURE-2.3` | — | `Art9` | `PromptInjection` |
| **T4-017** | T4 | high | `MEASURE-2.3` | — | `Art9` | `PromptInjection` |
| **T4-018** | T4 | critical | `MEASURE-2.3` | `A.8` | — | `PromptInjection`, `ToolMisuse` |
| **T5-001** | T5 | critical | `MANAGE-2.4` | `A.8` | `Art9` | `ToolMisuse` |
| **T5-002** | T5 | critical | `MEASURE-2.3` | `A.8` | — | `ToolMisuse` |
| **T5-003** | T5 | critical | `MEASURE-2.3` | `A.8` | — | `ToolMisuse` |
| **T5-004** | T5 | critical | `MEASURE-2.3` | `A.8` | `Art9` | `ToolMisuse` |
| **T5-005** | T5 | critical | `MANAGE-2.4` | `A.8` | — | `ToolMisuse` |
| **T5-006** | T5 | high | `MANAGE-2.4` | — | `Art9` | `ToolMisuse` |
| **T5-007** | T5 | high | `MANAGE-2.4` | — | `Art9` | `ToolMisuse` |
| **T5-008** | T5 | critical | `MEASURE-2.3` | `A.8` | — | `ToolMisuse` |
| **T5-009** | T5 | high | `MANAGE-2.4` | — | `Art14`, `Art9` | `ToolMisuse` |
| **T5-010** | T5 | high | `MANAGE-2.4` | — | `Art9` | `ToolMisuse` |
| **T5-011** | T5 | critical | `MEASURE-2.3` | `A.8` | `Art9` | `PrivilegeCompromise` |
| **T5-012** | T5 | medium | `MANAGE-2.4` | — | — | `ToolMisuse` |
| **T5-013** | T5 | high | `MANAGE-2.4` | — | `Art9` | `ToolMisuse` |
| **T5-014** | T5 | high | `MANAGE-2.4` | — | `Art14`, `Art9` | `ToolMisuse` |
| **T5-015** | T5 | medium | `MANAGE-2.4` | — | — | `ToolMisuse` |
| **T5-016** | T5 | critical | `MANAGE-2.4` | `A.8` | `Art14` | `PrivilegeCompromise` |
| **T5-017** | T5 | high | `MANAGE-2.4` | — | `Art9` | `ToolMisuse` |
| **T5-018** | T5 | critical | `MANAGE-2.4` | `A.8` | `Art9` | `ToolMisuse` |
| **T6-001** | T6 | critical | `MEASURE-2.3` | `A.8` | — | `MemoryPoisoning` |
| **T6-002** | T6 | critical | `MEASURE-2.3` | `A.8` | — | `MemoryPoisoning` |
| **T6-003** | T6 | high | `MEASURE-2.3` | — | — | `MemoryPoisoning` |
| **T6-004** | T6 | high | `MEASURE-2.3` | — | `Art9` | `MemoryPoisoning` |
| **T6-005** | T6 | critical | `MANAGE-2.4` | `A.8` | — | `MemoryPoisoning`, `PromptInjection` |
| **T6-006** | T6 | high | `MEASURE-2.3` | — | — | `MemoryPoisoning` |
| **T6-007** | T6 | medium | `MEASURE-2.3` | — | — | `MemoryPoisoning` |
| **T6-008** | T6 | high | `MEASURE-2.3` | — | — | `MemoryPoisoning` |
| **T6-009** | T6 | high | `MEASURE-2.3` | — | — | `MemoryPoisoning` |
| **T6-010** | T6 | medium | `MEASURE-2.3` | — | — | `MemoryPoisoning` |
| **T6-011** | T6 | critical | `MEASURE-2.3` | `A.8` | — | `MemoryPoisoning`, `ToolMisuse` |
| **T6-012** | T6 | high | `MEASURE-2.3` | — | — | `MemoryPoisoning` |
| **T6-013** | T6 | medium | `MEASURE-2.3` | — | `Art14`, `Art9` | `MemoryPoisoning` |
| **T6-014** | T6 | high | `MEASURE-2.3` | — | — | `MemoryPoisoning` |
| **T7-001** | T7 | high | `MEASURE-2.3` | `A.8` | — | `GoalHijacking` |
| **T7-002** | T7 | critical | `MEASURE-2.3` | `A.8` | `Art9` | `PromptInjection` |
| **T7-003** | T7 | critical | `MEASURE-2.3` | `A.8` | `Art9` | `PromptInjection` |
| **T7-004** | T7 | high | `MEASURE-2.3` | `A.8` | — | — |
| **T7-005** | T7 | high | `MEASURE-2.3` | `A.8` | — | — |
| **T7-006** | T7 | high | `MEASURE-2.3` | `A.8` | — | `ToolMisuse` |
| **T7-007** | T7 | high | `MEASURE-2.3` | `A.8` | — | — |
| **T7-008** | T7 | high | `MEASURE-2.3` | `A.8` | — | — |
| **T7-009** | T7 | medium | `MEASURE-2.3` | `A.8` | — | — |
| **T7-010** | T7 | high | `MEASURE-2.3` | `A.8` | `Art9` | — |
| **T7-011** | T7 | high | `MEASURE-2.3` | `A.8` | — | — |
| **T7-012** | T7 | medium | `MEASURE-2.3` | `A.8` | — | — |
| **T7-013** | T7 | high | `MEASURE-2.3` | `A.8` | — | — |
| **T7-014** | T7 | high | `MEASURE-2.3` | `A.8` | `Art9` | `ToolMisuse` |

## Gaps and open questions

These are recorded so a reviewer can act on them, not hidden behind a filled-in cell.

### Whole classes with no NIST AI RMF reference

8 IDs carry no `NIST-AI-RMF` token, and they are concentrated in T3: `T3-005`, `T3-006`, `T3-007`, `T3-009`, `T3-010`, `T3-011`, `T3-012`, `T3-014`.

T3 is the authorisation and handover class. NIST AI RMF 1.0 predates tool-calling agents and has no subcategory written for inter-agent privilege transfer, so the honest options were `GOVERN-1.2` (roles and accountability) or nothing. Only three T3 rows claim `GOVERN-1.2`. Whether the remaining T3 tests should also claim it, or whether the gap should stay visible, is a judgement call for the maintainer.

### EU AI Act coverage is the thinnest

57 of 110 IDs carry no `EU-AIA` token. That is the right shape rather than an omission: the Act's high-risk requirements only bite for systems in scope, and most checklist IDs describe failure modes that exist regardless of regulatory classification. Mapping them all to Art. 9 would inflate the crosswalk without informing anyone.

### ISO/IEC 42001 has only two control groups in use

48 IDs carry no `ISO42001` token, and the ones that do use only `A.6` (3 IDs) and `A.8` (59 IDs). Annex A has considerably more control groups than two. `A.8` (performance evaluation) is a defensible default for a test catalogue, but `A.6` being used for only three impact-assessment-flavoured tests suggests the mapping was applied narrowly. Finer ISO mapping would need someone with the standard text to hand.

### `OWASP-ASI` tokens are not OWASP identifiers

23 of 110 IDs carry no `OWASP-ASI` token at all, so roughly a fifth of the catalogue asserts no agentic-threat mapping. The remaining four fifths use the descriptive names below.

This is the correction worth flagging. The catalogue uses descriptive names (`ToolMisuse`, `PrivilegeCompromise`, `MemoryPoisoning`, `AgenticHandoff`, `GoalHijacking`, `HumanManipulation`, `PromptInjection`) that describe OWASP Agentic Security Initiative *threat themes*. They are **not** the `ASIxx` identifiers used by OWASP's published agentic lists, and the catalogue contains no numeric ASI reference at all.

Two consequences:

1. A reader cannot follow an `OWASP-ASI:ToolMisuse` token to a specific OWASP document the way they can follow `EU-AIA:Art14` to Article 14. The token is a label for a threat category, not a citation.
2. Any prose elsewhere in the repo that presents an `ASIxx` number as coming *from* `control_refs` is inaccurate, because `control_refs` has never contained one. `docs/EXPLAINABILITY-RESEARCH.md` does exactly this for T3-006, describing it as "ASI03 … and ASI07 … from catalogue `control_refs`" while that row's actual value is `OWASP-ASI:PrivilegeCompromise;OWASP-ASI:AgenticHandoff`. Either the research note should stop attributing the numbers to the catalogue, or the catalogue should gain a numeric field. That choice belongs to the maintainer.

### No MAP references

NIST AI RMF's MAP function (context and risk identification) appears in no `control_refs` token. The class-level doc says MAP applies to all classes; the per-test data asserts it for none. One of the two should move.

## Sources

- NIST (2023). AI 100-1 *Artificial Intelligence Risk Management Framework (AI RMF 1.0).* [doi:10.6028/NIST.AI.100-1](https://doi.org/10.6028/NIST.AI.100-1)
- Regulation (EU) 2024/1689 (Artificial Intelligence Act). <https://eur-lex.europa.eu/eli/reg/2024/1689/oj/eng>
- ISO/IEC 42001:2023 *Information technology — Artificial intelligence — Management system.* <https://www.iso.org/standard/81230.html>
- OWASP Top 10 for LLM Applications 2025. <https://genai.owasp.org/llm-top-10/>
- OWASP GenAI Security Project. *Agentic AI – Threats and Mitigations.* <https://genai.owasp.org/resource/agentic-ai-threats-and-mitigations/>
