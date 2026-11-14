# Framework mapping (T1–T7)

This table maps each test class in the Agentic AI Test Checklist 110 to the themes of common frameworks. It is an informal, indicative crosswalk for orientation only. It is **not** a compliance claim, an audit result or a certification statement, and passing these checks does not make a system conformant with any framework.

This page works at the **class** level: one row per class. For the **per-test** crosswalk (all 110 IDs, generated from the `control_refs` field in `catalog/checklist-110.jsonl`) see [FRAMEWORK-MAPPING-PER-TEST.md](FRAMEWORK-MAPPING-PER-TEST.md). This page is a readable orientation table; the generated page is the auditable mapping and cannot drift from the catalogue.

| Class | Name | NIST AI RMF (functions) | EU AI Act (themes) | OWASP Top 10 for LLM apps 2025 / agentic threats | ISO/IEC 42001 (general themes) |
|---|---|---|---|---|---|
| T1 | Task success / terminal state | MEASURE (validity, reliability), MANAGE | Accuracy and robustness | LLM09 Misinformation (false "done" claims) | Performance evaluation, operational controls |
| T2 | Dependency ordering | MEASURE, MANAGE | Robustness, record-keeping | LLM06 Excessive Agency | Operational planning and control |
| T3 | Control handover / authorisation | GOVERN (roles, accountability), MANAGE | Human oversight | LLM06 Excessive Agency; agentic: privilege compromise, human-in-the-loop bypass | Roles and responsibilities, human oversight |
| T4 | Prompt injection from untrusted documents | MEASURE (security, resilience), MANAGE | Cybersecurity, robustness | LLM01 Prompt Injection; LLM02 Sensitive Information Disclosure | Risk treatment, information security interfaces |
| T5 | Tool-call allowlists | GOVERN, MANAGE | Human oversight, cybersecurity | LLM06 Excessive Agency; agentic: tool misuse | Operational controls, third-party/tool controls |
| T6 | State drift across turns | MEASURE, MANAGE (monitoring) | Accuracy, post-market monitoring | LLM04 Data and Model Poisoning (memory); agentic: memory poisoning | Monitoring, measurement, continual improvement |
| T7 | Metamorphic / consistency | MEASURE (validity, fairness) | Accuracy, non-discrimination | LLM09 Misinformation | Performance evaluation, impact assessment themes |

Notes
- NIST AI RMF 1.0 functions: GOVERN, MAP, MEASURE, MANAGE. MAP applies to all classes (context and risk identification). The per-test `control_refs` data contains no MAP token, so treat that as guidance rather than something this catalogue encodes.
- EU AI Act themes refer to the high-risk system requirements (risk management, data, record-keeping, transparency, human oversight, accuracy/robustness/cybersecurity). Whether they apply depends on your use case.
- OWASP IDs refer to the OWASP Top 10 for LLM Applications 2025; "agentic" refers to the OWASP Agentic Security Initiative threat themes.
- Corrections welcome via pull request.

## Sources

- NIST (2023). AI 100-1 *Artificial Intelligence Risk Management Framework (AI RMF 1.0).* [doi:10.6028/NIST.AI.100-1](https://doi.org/10.6028/NIST.AI.100-1) · <https://www.nist.gov/itl/ai-risk-management-framework>
- Regulation (EU) 2024/1689 (Artificial Intelligence Act); Art. 14 human oversight. <https://eur-lex.europa.eu/eli/reg/2024/1689/oj/eng>
- OWASP Top 10 for LLM Applications 2025: <https://genai.owasp.org/llm-top-10/> (LLM01 <https://genai.owasp.org/llmrisk/llm01-prompt-injection/>, LLM02 <https://genai.owasp.org/llmrisk/llm022025-sensitive-information-disclosure/>, LLM04 <https://genai.owasp.org/llmrisk/llm042025-data-and-model-poisoning/>, LLM06 <https://genai.owasp.org/llmrisk/llm062025-excessive-agency/>, LLM09 <https://genai.owasp.org/llmrisk/llm092025-misinformation/>)
- OWASP GenAI Security Project. *Agentic AI – Threats and Mitigations.* <https://genai.owasp.org/resource/agentic-ai-threats-and-mitigations/>
- OWASP GenAI Security Project. *OWASP Top 10 for Agentic Applications for 2026.* <https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/>
- ISO/IEC 42001:2023 *Information technology — Artificial intelligence — Management system.* <https://www.iso.org/standard/81230.html>
