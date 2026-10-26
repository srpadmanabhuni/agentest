# Framework mapping (T1–T7)

This table maps each test class in the Agentic AI Test Checklist 110 to the themes of common frameworks. It is an informal, indicative crosswalk for orientation only. It is **not** a compliance claim, an audit result or a certification statement, and passing these checks does not make a system conformant with any framework.

This page works at the **class** level: one row per class. For the **per-test** crosswalk — all 110 IDs, generated directly from the `control_refs` field in `catalog/checklist-110.jsonl` — see [FRAMEWORK-MAPPING-PER-TEST.md](FRAMEWORK-MAPPING-PER-TEST.md). The two pages answer different questions: this one is a readable orientation table; the generated one is the auditable mapping, and it is the place to look when you need to know what a specific ID claims.

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
- NIST AI RMF 1.0 functions: GOVERN, MAP, MEASURE, MANAGE. The table above asserts MAP for no class, while the per-test `control_refs` data contains no `MAP-*` token at all. Treat "MAP applies to all classes" as guidance rather than as something this catalogue encodes.
- EU AI Act themes refer to the high-risk system requirements (risk management, data, record-keeping, transparency, human oversight, accuracy/robustness/cybersecurity). Whether they apply depends on your use case.
- OWASP IDs refer to the OWASP Top 10 for LLM Applications 2025. The "agentic" column refers to OWASP Agentic Security Initiative threat *themes*; the tokens in `control_refs` (`ToolMisuse`, `PrivilegeCompromise`, …) are descriptive labels for those themes and are **not** published OWASP `ASIxx` identifiers. See the note in the per-test document.
- Corrections welcome via pull request.

