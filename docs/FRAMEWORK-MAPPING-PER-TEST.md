# Framework mapping — per test

*Generated from `catalog/checklist-110.jsonl` by `scripts/gen_framework_mapping.py`. Do not edit by hand; re-run the script instead.*

This is the per-test counterpart to the class-level crosswalk in [FRAMEWORK-MAPPING.md](FRAMEWORK-MAPPING.md). Every row below is taken verbatim from the `control_refs` field carried by the catalogue entry for that ID, so the table and the machine-readable catalogue cannot disagree.

It remains an **indicative crosswalk**, not a compliance claim, an audit result or a certification statement. Passing a check does not make a system conformant with any framework. The mappings point at *themes*: they tell you which part of a framework is likely to care about a given failure mode, not which clause you have satisfied.

## Coverage

Of the 110 catalogue IDs:

| Framework | IDs with a reference | Share |
|:--|--:|--:|
| `NIST-AI-RMF` | 102 | 93% |
| `EU-AIA` | 53 | 48% |
| `OWASP-ASI` | 87 | 79% |

A blank cell is **not** an oversight and **not** a finding that the test is irrelevant to that framework. It means the catalogue author did not assert a mapping. Absence of a reference is the honest state for a test whose relationship to a framework is arguable; inventing a clause number to fill the cell would be worse than leaving it empty. See [Gaps and open questions](#gaps-and-open-questions).

## Token vocabulary

Tokens are copied from the catalogue. The expansions below say what each token refers to; they are orientation aids, not clause-level citations.

**`NIST-AI-RMF`**: NIST AI RMF 1.0 functions. The catalogue records the function, not a subcategory.

| Token | Meaning | IDs |
|:--|:--|--:|
| `GOVERN` | GOVERN function: roles, responsibilities and accountability structures | 3 |
| `MANAGE` | MANAGE function: risks prioritised, treated and monitored, incidents responded to | 20 |
| `MEASURE` | MEASURE function: system performance, security and fairness evaluated against stated claims | 79 |

**`EU-AIA`**: Regulation (EU) 2024/1689 articles.

| Token | Meaning | IDs |
|:--|:--|--:|
| `Art14` | Art. 14: human oversight | 15 |
| `Art9` | Art. 9: risk management system | 47 |

**`OWASP-ASI`**: OWASP Top 10 for Agentic Applications 2026 identifiers.

| Token | Meaning | IDs |
|:--|:--|--:|
| `ASI01` | ASI01: Agent Goal Hijack | 23 |
| `ASI02` | ASI02: Tool Misuse and Exploitation | 37 |
| `ASI03` | ASI03: Identity and Privilege Abuse | 19 |
| `ASI06` | ASI06: Memory and Context Poisoning | 14 |
| `ASI07` | ASI07: Insecure Inter-Agent Communication | 9 |
| `ASI09` | ASI09: Human-Agent Trust Exploitation | 2 |

## Per-test crosswalk

| ID | Class | Severity | NIST AI RMF | EU AI Act | OWASP agentic |
|:--|:--|:--|:--|:--|:--|
| **T1-001** | T1 | critical | `MEASURE` | `Art9` | — |
| **T1-002** | T1 | critical | `MEASURE` | `Art9` | `ASI01` |
| **T1-003** | T1 | high | `MEASURE` | `Art9` | — |
| **T1-004** | T1 | critical | `MEASURE` | — | `ASI02` |
| **T1-005** | T1 | high | `MEASURE` | `Art9` | — |
| **T1-006** | T1 | high | `MEASURE` | — | — |
| **T1-007** | T1 | medium | `MEASURE` | — | — |
| **T1-008** | T1 | critical | `MEASURE` | — | `ASI02` |
| **T1-009** | T1 | high | `MEASURE` | — | — |
| **T1-010** | T1 | medium | `MEASURE` | `Art14`, `Art9` | — |
| **T1-011** | T1 | medium | `MEASURE` | — | — |
| **T1-012** | T1 | high | `MEASURE` | — | — |
| **T1-013** | T1 | high | `MEASURE` | — | `ASI02` |
| **T1-014** | T1 | medium | `MEASURE` | — | — |
| **T1-015** | T1 | medium | `MEASURE` | — | — |
| **T1-016** | T1 | high | `MEASURE` | `Art9` | — |
| **T1-017** | T1 | high | `MEASURE` | — | — |
| **T1-018** | T1 | medium | `MEASURE` | — | — |
| **T2-001** | T2 | critical | `MEASURE` | — | `ASI02` |
| **T2-002** | T2 | critical | `MANAGE` | `Art9` | `ASI02` |
| **T2-003** | T2 | critical | `MEASURE` | — | `ASI02` |
| **T2-004** | T2 | critical | `GOVERN` | `Art14` | `ASI03` |
| **T2-005** | T2 | critical | `MEASURE` | `Art9` | `ASI03` |
| **T2-006** | T2 | high | `MEASURE` | — | `ASI02` |
| **T2-007** | T2 | high | `MEASURE` | `Art14`, `Art9` | `ASI02` |
| **T2-008** | T2 | medium | `MEASURE` | — | `ASI02` |
| **T2-009** | T2 | medium | `MEASURE` | — | `ASI02` |
| **T2-010** | T2 | high | `MEASURE` | `Art14`, `Art9` | `ASI02` |
| **T2-011** | T2 | critical | `MANAGE` | `Art9` | `ASI03` |
| **T2-012** | T2 | critical | `GOVERN` | `Art14` | `ASI09` |
| **T2-013** | T2 | medium | `MEASURE` | — | `ASI02` |
| **T2-014** | T2 | low | `MEASURE` | — | `ASI02` |
| **T3-001** | T3 | critical | `MANAGE` | `Art14` | `ASI07`, `ASI03` |
| **T3-002** | T3 | critical | `MANAGE` | `Art9` | `ASI03` |
| **T3-003** | T3 | critical | `MANAGE` | `Art14` | `ASI03` |
| **T3-004** | T3 | critical | `GOVERN` | `Art14` | `ASI09` |
| **T3-005** | T3 | high | — | `Art14`, `Art9` | `ASI03`, `ASI07` |
| **T3-006** | T3 | medium | — | — | `ASI03`, `ASI07` |
| **T3-007** | T3 | high | — | `Art9` | `ASI03`, `ASI07` |
| **T3-008** | T3 | critical | `MEASURE` | `Art9` | `ASI03` |
| **T3-009** | T3 | high | — | `Art9` | `ASI03`, `ASI07` |
| **T3-010** | T3 | high | — | `Art14`, `Art9` | `ASI03`, `ASI07` |
| **T3-011** | T3 | high | — | `Art9` | `ASI03`, `ASI07` |
| **T3-012** | T3 | medium | — | `Art14`, `Art9` | `ASI03`, `ASI07` |
| **T3-013** | T3 | critical | `MANAGE` | — | `ASI03` |
| **T3-014** | T3 | medium | — | `Art9` | `ASI03`, `ASI07` |
| **T4-001** | T4 | critical | `MEASURE` | `Art9` | `ASI01` |
| **T4-002** | T4 | critical | `MEASURE` | — | `ASI01`, `ASI02` |
| **T4-003** | T4 | critical | `MEASURE` | — | `ASI01`, `ASI02` |
| **T4-004** | T4 | critical | `MEASURE` | — | `ASI01`, `ASI03` |
| **T4-005** | T4 | critical | `MEASURE` | — | `ASI01` |
| **T4-006** | T4 | high | `MEASURE` | `Art9` | `ASI01` |
| **T4-007** | T4 | high | `MEASURE` | `Art9` | `ASI01` |
| **T4-008** | T4 | critical | `MEASURE` | — | `ASI01`, `ASI02` |
| **T4-009** | T4 | high | `MEASURE` | `Art9` | `ASI01` |
| **T4-010** | T4 | high | `MEASURE` | `Art9` | `ASI01` |
| **T4-011** | T4 | critical | `MEASURE` | — | `ASI01` |
| **T4-012** | T4 | medium | `MEASURE` | `Art9` | `ASI01` |
| **T4-013** | T4 | high | `MEASURE` | `Art9` | `ASI01` |
| **T4-014** | T4 | high | `MEASURE` | `Art9` | `ASI01` |
| **T4-015** | T4 | critical | `MEASURE` | — | `ASI01`, `ASI02` |
| **T4-016** | T4 | medium | `MEASURE` | `Art9` | `ASI01` |
| **T4-017** | T4 | high | `MEASURE` | `Art9` | `ASI01` |
| **T4-018** | T4 | critical | `MEASURE` | — | `ASI01`, `ASI02` |
| **T5-001** | T5 | critical | `MANAGE` | `Art9` | `ASI02` |
| **T5-002** | T5 | critical | `MEASURE` | — | `ASI02` |
| **T5-003** | T5 | critical | `MEASURE` | — | `ASI02` |
| **T5-004** | T5 | critical | `MEASURE` | `Art9` | `ASI02` |
| **T5-005** | T5 | critical | `MANAGE` | — | `ASI02` |
| **T5-006** | T5 | high | `MANAGE` | `Art9` | `ASI02` |
| **T5-007** | T5 | high | `MANAGE` | `Art9` | `ASI02` |
| **T5-008** | T5 | critical | `MEASURE` | — | `ASI02` |
| **T5-009** | T5 | high | `MANAGE` | `Art14`, `Art9` | `ASI02` |
| **T5-010** | T5 | high | `MANAGE` | `Art9` | `ASI02` |
| **T5-011** | T5 | critical | `MEASURE` | `Art9` | `ASI03` |
| **T5-012** | T5 | medium | `MANAGE` | — | `ASI02` |
| **T5-013** | T5 | high | `MANAGE` | `Art9` | `ASI02` |
| **T5-014** | T5 | high | `MANAGE` | `Art14`, `Art9` | `ASI02` |
| **T5-015** | T5 | medium | `MANAGE` | — | `ASI02` |
| **T5-016** | T5 | critical | `MANAGE` | `Art14` | `ASI03` |
| **T5-017** | T5 | high | `MANAGE` | `Art9` | `ASI02` |
| **T5-018** | T5 | critical | `MANAGE` | `Art9` | `ASI02` |
| **T6-001** | T6 | critical | `MEASURE` | — | `ASI06` |
| **T6-002** | T6 | critical | `MEASURE` | — | `ASI06` |
| **T6-003** | T6 | high | `MEASURE` | — | `ASI06` |
| **T6-004** | T6 | high | `MEASURE` | `Art9` | `ASI06` |
| **T6-005** | T6 | critical | `MANAGE` | — | `ASI06`, `ASI01` |
| **T6-006** | T6 | high | `MEASURE` | — | `ASI06` |
| **T6-007** | T6 | medium | `MEASURE` | — | `ASI06` |
| **T6-008** | T6 | high | `MEASURE` | — | `ASI06` |
| **T6-009** | T6 | high | `MEASURE` | — | `ASI06` |
| **T6-010** | T6 | medium | `MEASURE` | — | `ASI06` |
| **T6-011** | T6 | critical | `MEASURE` | — | `ASI06`, `ASI02` |
| **T6-012** | T6 | high | `MEASURE` | — | `ASI06` |
| **T6-013** | T6 | medium | `MEASURE` | `Art14`, `Art9` | `ASI06` |
| **T6-014** | T6 | high | `MEASURE` | — | `ASI06` |
| **T7-001** | T7 | high | `MEASURE` | — | `ASI01` |
| **T7-002** | T7 | critical | `MEASURE` | `Art9` | `ASI01` |
| **T7-003** | T7 | critical | `MEASURE` | `Art9` | `ASI01` |
| **T7-004** | T7 | high | `MEASURE` | — | — |
| **T7-005** | T7 | high | `MEASURE` | — | — |
| **T7-006** | T7 | high | `MEASURE` | — | `ASI02` |
| **T7-007** | T7 | high | `MEASURE` | — | — |
| **T7-008** | T7 | high | `MEASURE` | — | — |
| **T7-009** | T7 | medium | `MEASURE` | — | — |
| **T7-010** | T7 | high | `MEASURE` | `Art9` | — |
| **T7-011** | T7 | high | `MEASURE` | — | — |
| **T7-012** | T7 | medium | `MEASURE` | — | — |
| **T7-013** | T7 | high | `MEASURE` | — | — |
| **T7-014** | T7 | high | `MEASURE` | `Art9` | `ASI02` |

## Gaps and open questions

These are recorded so a reviewer can act on them, not hidden behind a filled-in cell. Every figure is computed from the catalogue when the page is generated.

### NIST AI RMF

8 IDs carry no `NIST-AI-RMF` token (T3 (8)): `T3-005`, `T3-006`, `T3-007`, `T3-009`, `T3-010`, `T3-011`, `T3-012`, `T3-014`. The tokens in use are `GOVERN`, `MANAGE`, `MEASURE`; the catalogue does not assert a MAP reference for any ID, and the catalogue records functions, not subcategories.

### EU AI Act

57 of 110 IDs carry no `EU-AIA` token, and the ones that do use only `Art14`, `Art9`. This is the expected shape rather than an error: the Act's high-risk requirements only apply to systems in scope, and most checklist IDs describe failure modes that exist regardless of regulatory classification.

### OWASP agentic identifiers

23 of 110 IDs carry no `OWASP-ASI` token (T1 (14), T7 (9)). The identifiers in use are `ASI01`, `ASI02`, `ASI03`, `ASI06`, `ASI07`, `ASI09`. Not asserted for any ID: `ASI04`, `ASI05`, `ASI08`, `ASI10`.

### Whole catalogue

IDs with no reference to any of the three frameworks: none.

A blank cell is a statement that no mapping is asserted. Where a test's relationship to a framework is arguable, an empty cell is more honest than an invented clause number.

## Sources

- NIST (2023). AI 100-1 *Artificial Intelligence Risk Management Framework (AI RMF 1.0).* [doi:10.6028/NIST.AI.100-1](https://doi.org/10.6028/NIST.AI.100-1)
- Regulation (EU) 2024/1689 (Artificial Intelligence Act). <https://eur-lex.europa.eu/eli/reg/2024/1689/oj/eng>
- OWASP GenAI Security Project. *OWASP Top 10 for Agentic Applications 2026.* <https://genai.owasp.org/2025/12/09/owasp-top-10-for-agentic-applications-the-benchmark-for-agentic-security-in-the-age-of-autonomous-ai/>
