# References and attribution

Bibliography for the oracles in `src/agentest/cases/` and the sample agents in
`src/agentest/samples/`. Every entry below was checked against arXiv, doi.org or
the publisher/standards body (October 2026). Each oracle docstring has an
**Attribution / References** section that says whether the check *applies* a
published method or is an **in-house heuristic** that only uses the reference as
background.

> agentest does not depend on any third-party evaluation framework. The papers are
> cited for ideas only. All checks are deterministic, trace-based Python.

Per-test source table with audit status: [TEST-SOURCES.md](TEST-SOURCES.md).

## A. Methods directly applied

| Used in | Reference |
|:--|:--|
| T7-004, T7-007, T7-011, T7-014 (metamorphic relations) | Chen, T. Y., Cheung, S. C., Yiu, S. M. (1998). *Metamorphic Testing: A New Approach for Generating Next Test Cases.* Tech. Rep. HKUST-CS98-01. Republished: [arXiv:2002.12543](https://arxiv.org/abs/2002.12543) |
| T7-007 (name swap; counterfactual token substitution) | Garg, S., Perot, V., Limtiaco, N., Taly, A., Chi, E. H., Beutel, A. (2019). *Counterfactual Fairness in Text Classification through Robustness.* AIES 2019. [doi:10.1145/3306618.3317950](https://doi.org/10.1145/3306618.3317950) |
| T1-009 (all-or-none batch) | Haerder, T., Reuter, A. (1983). *Principles of transaction-oriented database recovery.* ACM Computing Surveys 15(4). [doi:10.1145/289.291](https://doi.org/10.1145/289.291) (atomicity) |

## B. Conceptual background (checks are in-house heuristics)

| Topic / IDs | Reference |
|:--|:--|
| Terminal postconditions (T1-*, T1-018) | Hoare, C. A. R. (1969). *An axiomatic basis for computer programming.* CACM 12(10). [doi:10.1145/363235.363259](https://doi.org/10.1145/363235.363259) |
| Test oracles; golden/broken design | Barr, E. T., Harman, M., McMinn, P., Shahbaz, M., Yoo, S. (2015). *The Oracle Problem in Software Testing: A Survey.* IEEE TSE 41(5). [doi:10.1109/TSE.2014.2372785](https://doi.org/10.1109/TSE.2014.2372785) |
| DEPENDS_ON ordering (T2-001/009/013, T2-005) | Kahn, A. B. (1962). *Topological sorting of large networks.* CACM 5(11). [doi:10.1145/368996.369025](https://doi.org/10.1145/368996.369025) |
| Least privilege, complete mediation (T1-013, T5-012, T3-002/007/008, T5-011) | Saltzer, J. H., Schroeder, M. D. (1975). *The protection of information in computer systems.* Proc. IEEE 63(9). [doi:10.1109/PROC.1975.9939](https://doi.org/10.1109/PROC.1975.9939) |
| Ambient authority (T3-011) | Hardy, N. (1988). *The Confused Deputy.* ACM SIGOPS OSR 22(4). [doi:10.1145/54289.871709](https://doi.org/10.1145/54289.871709) |
| Single-use tokens (T3-010; analogy only) | RFC 6749 *The OAuth 2.0 Authorization Framework*, §4.1.2. [doi:10.17487/RFC6749](https://doi.org/10.17487/RFC6749) |
| Session TTL (T3-014), verify before disclose (T2-005) | NIST SP 800-63B, §7 Session management. <https://pages.nist.gov/800-63-3/sp800-63b.html> |
| PII regex detection (T5-004, T7-014) | McCallister, Grance, Scarfone (2010). NIST SP 800-122 *Guide to Protecting the Confidentiality of PII.* [doi:10.6028/NIST.SP.800-122](https://doi.org/10.6028/NIST.SP.800-122) |
| Consent withdrawal (T6-004), minimisation (T5-004), erasure context (T1-016) | Regulation (EU) 2016/679 (GDPR), Art. 5(1)(c), 7(3), 17. <https://eur-lex.europa.eu/eli/reg/2016/679/oj> |
| Indirect prompt injection (T4-009, T3-001) | Greshake, K. et al. (2023). *Not What You've Signed Up For: Compromising Real-World LLM-Integrated Applications with Indirect Prompt Injection.* AISec '23. [doi:10.1145/3605764.3623985](https://doi.org/10.1145/3605764.3623985) · [arXiv:2302.12173](https://arxiv.org/abs/2302.12173) |
| Repeated trials (T1-002, T1-003): background only; pass^k is all-k success, whereas we count false completions (T1-002) and mean TSR (T1-003) | Yao, S., Shinn, N., Razavi, P., Narasimhan, K. (2024). *τ-bench: A Benchmark for Tool-Agent-User Interaction in Real-World Domains.* [arXiv:2406.12045](https://arxiv.org/abs/2406.12045) (pass^k repeated-trial reliability) |
| Language-swap fairness (T7-004, T7-011) | Garg et al. (2019), above, is background only: it swaps identity tokens, not languages; the language-swap relation is in-house. |
| Excessive agency, sensitive info disclosure | OWASP Top 10 for LLM Applications 2025 (LLM01, LLM02, LLM06). <https://genai.owasp.org/llm-top-10/> |
| Human oversight (T2-004) | Regulation (EU) 2024/1689 (EU AI Act), Art. 14. <https://eur-lex.europa.eu/eli/reg/2024/1689/oj> |
| AI management system controls (T3-006, T3-002, T2-004) | ISO/IEC 42001:2023, Annex A. <https://www.iso.org/standard/81230.html> |
| Risk management (T1-003 tiers, T3-006) | NIST AI 100-1 (2023), *AI RMF 1.0.* [doi:10.6028/NIST.AI.100-1](https://doi.org/10.6028/NIST.AI.100-1) |
| Faithfulness of explanations (T1-018, T6-007, T7-009) | Jacovi, A., Goldberg, Y. (2020). *Towards Faithfully Interpretable NLP Systems: How Should We Define and Evaluate Faithfulness?* ACL 2020. [doi:10.18653/v1/2020.acl-main.386](https://doi.org/10.18653/v1/2020.acl-main.386) |
| Rationale evaluation (contrast for T7-009) | DeYoung, J. et al. (2020). *ERASER: A Benchmark to Evaluate Rationalized NLP Models.* ACL 2020. [doi:10.18653/v1/2020.acl-main.408](https://doi.org/10.18653/v1/2020.acl-main.408). We do **not** compute comprehensiveness/sufficiency. |
| Reason code per action (T5-015) | Yao, S. et al. (2023). *ReAct: Synergizing Reasoning and Acting in Language Models.* ICLR 2023. [arXiv:2210.03629](https://arxiv.org/abs/2210.03629) |
| Trajectory-level evaluation (explainability pack) | Kim, W., Park, S., In, Y., Kim, S., Lee, D., Park, C. (2025). *Beyond the Final Answer: Evaluating the Reasoning Trajectories of Tool-Augmented Agents.* [arXiv:2510.02837](https://arxiv.org/abs/2510.02837). The paper proposes **TRACE**, the label used in these docs. |
| Memory provenance (T6-007) | Lewis, P. et al. (2020). *Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks.* NeurIPS 2020. [arXiv:2005.11401](https://arxiv.org/abs/2005.11401) |
| Counterfactual fairness, the idea (T7-007) | Kusner, M. J., Loftus, J., Russell, C., Silva, R. (2017). *Counterfactual Fairness.* NeurIPS 2017. [arXiv:1703.06856](https://arxiv.org/abs/1703.06856). No causal model is fitted. |
| Catalogue (all IDs) | Padmanabhuni, S. (2026). *Agentic AI Assurance Test Taxonomy v1.* Zenodo. [doi:10.5281/zenodo.23587407](https://doi.org/10.5281/zenodo.23587407) · catalogue dataset |

## C. Agent patterns imitated by the sample agents

| Agent | Reference |
|:--|:--|
| `planner` | Wang, L. et al. (2023). *Plan-and-Solve Prompting.* ACL 2023. [arXiv:2305.04091](https://arxiv.org/abs/2305.04091) |
| `critic` | Madaan, A. et al. (2023). *Self-Refine: Iterative Refinement with Self-Feedback.* NeurIPS 2023. [arXiv:2303.17651](https://arxiv.org/abs/2303.17651) |
| `reflective`, `critic` | Shinn, N. et al. (2023). *Reflexion: Language Agents with Verbal Reinforcement Learning.* NeurIPS 2023. [arXiv:2303.11366](https://arxiv.org/abs/2303.11366) |
| `reflective`, `hallucinator` (reason before action) | ReAct (above) |

All sample agents are deterministic code. They do not call an LLM.

## D. Considered but NOT implemented (listed for clarity)

The following methods are often asked about. agentest does **not** implement them,
and no oracle claims to:

- LIME: Ribeiro, Singh, Guestrin (2016), KDD. [doi:10.1145/2939672.2939778](https://doi.org/10.1145/2939672.2939778)
- SHAP: Lundberg & Lee (2017), NeurIPS. [arXiv:1705.07874 https://arxiv.org/abs/1705.07874](https://arxiv.org/abs/1705.07874)
- Integrated Gradients: Sundararajan, Taly, Yan (2017), ICML. [arXiv:1703.01365 https://arxiv.org/abs/1703.01365](https://arxiv.org/abs/1703.01365)
- These attribute model inputs and need model internals or many forward passes. Our explainability oracles check trace faithfulness instead.
- Demographic parity / equalized odds: Hardt, Price, Srebro (2016), *Equality of Opportunity in Supervised Learning*, NeurIPS. [arXiv:1610.02413 https://arxiv.org/abs/1610.02413](https://arxiv.org/abs/1610.02413). The four-fifths rule: 29 CFR §1607.4(D) (EEOC Uniform Guidelines, 1978), <https://www.ecfr.gov/current/title-29/subtitle-B/chapter-XIV/part-1607/section-1607.4>. Both are group-rate metrics, and the bias pack uses single counterfactual pairs, so it computes no rates.
- Differential privacy: Dwork (2006), ICALP. [doi:10.1007/11787006_1](https://doi.org/10.1007/11787006_1)
- Training-data extraction: Carlini et al. (2021), USENIX Security. [arXiv:2012.07805 https://arxiv.org/abs/2012.07805](https://arxiv.org/abs/2012.07805)
- The privacy pack tests the agent's runtime behaviour, not the model's training data.
- Self-consistency: Wang, X. et al. (2023), ICLR. [arXiv:2203.11171 https://arxiv.org/abs/2203.11171](https://arxiv.org/abs/2203.11171). T1-002 and T1-003 repeat episodes but do not vote over sampled reasoning paths.
- LLM-as-a-judge: Zheng et al. (2023), NeurIPS Datasets & Benchmarks. [arXiv:2306.05685 https://arxiv.org/abs/2306.05685](https://arxiv.org/abs/2306.05685). Not used, because all oracles are deterministic.

## E. In-house heuristics (explicit list)

These checks are our own design. They are cited only to the catalogue and to background ideas:
T1-001, T1-002 (k-run false-completion count), T1-003 (mean TSR vs tier), T1-004, T1-005, T1-007, T1-011, T1-013, T1-015, T1-016, T1-018, T2-001,
T2-003, T2-004, T2-005, T2-009, T2-013, T3-001, T3-002, T3-006, T3-007, T3-008,
T3-010, T3-011, T3-014, T4-009, T5-004 (regex PII), T5-011, T5-012, T5-015, T6-003,
T6-006, T6-007, T6-010, T7-009 (keyword consistency + trace-cited steps), the
T7-014 regex detector, the language-swap relations of T7-004/T7-011, the bias-pack labelers, and the risk-tier thresholds in
`config/thresholds.py`.

## D. Master bibliography (`src/agentest/refs.py`)

Rendered from the single source used by `docs/tests/<ID>.md`. Verified against arXiv / Crossref / the publisher on 2026-10-26.
Zenodo appears only for the author's own taxonomy and catalogue (test-ID credit).

- `chen-mt` — Chen, T. Y., Cheung, S. C., Yiu, S. M. (1998/2020). *Metamorphic Testing: A New Approach for Generating Next Test Cases.* [arXiv:2002.12543](https://arxiv.org/abs/2002.12543)
- `segura-mt` — Segura, S., Fraser, G., Sanchez, A. B., Ruiz-Cortés, A. (2016). *A Survey on Metamorphic Testing.* IEEE TSE 42(9). [doi:10.1109/TSE.2016.2532875](https://doi.org/10.1109/TSE.2016.2532875)
- `barr-oracle` — Barr, E. T., Harman, M., McMinn, P., Shahbaz, M., Yoo, S. (2015). *The Oracle Problem in Software Testing: A Survey.* IEEE TSE 41(5). [doi:10.1109/TSE.2014.2372785](https://doi.org/10.1109/TSE.2014.2372785)
- `hoare` — Hoare, C. A. R. (1969). *An axiomatic basis for computer programming.* CACM 12(10). [doi:10.1145/363235.363259](https://doi.org/10.1145/363235.363259)
- `haerder` — Haerder, T., Reuter, A. (1983). *Principles of transaction-oriented database recovery.* ACM Computing Surveys 15(4). [doi:10.1145/289.291](https://doi.org/10.1145/289.291)
- `sagas` — Garcia-Molina, H., Salem, K. (1987). *Sagas.* SIGMOD '87. [doi:10.1145/38713.38742](https://doi.org/10.1145/38713.38742)
- `kahn` — Kahn, A. B. (1962). *Topological sorting of large networks.* CACM 5(11). [doi:10.1145/368996.369025](https://doi.org/10.1145/368996.369025)
- `lamport` — Lamport, L. (1978). *Time, clocks, and the ordering of events in a distributed system.* CACM 21(7). [doi:10.1145/359545.359563](https://doi.org/10.1145/359545.359563)
- `rfc9110` — Fielding, R., Nottingham, M., Reschke, J. (2022). RFC 9110 *HTTP Semantics* (§9.2.2 idempotent methods). [doi:10.17487/RFC9110](https://doi.org/10.17487/RFC9110)
- `rfc6585` — Nottingham, M., Fielding, R. (2012). RFC 6585 *Additional HTTP Status Codes* (429 Too Many Requests). [doi:10.17487/RFC6585](https://doi.org/10.17487/RFC6585)
- `rfc6749` — Hardt, D. (2012). RFC 6749 *The OAuth 2.0 Authorization Framework* (scopes, single-use codes). [doi:10.17487/RFC6749](https://doi.org/10.17487/RFC6749)
- `saltzer` — Saltzer, J. H., Schroeder, M. D. (1975). *The protection of information in computer systems.* Proc. IEEE 63(9). [doi:10.1109/PROC.1975.9939](https://doi.org/10.1109/PROC.1975.9939)
- `hardy` — Hardy, N. (1988). *The Confused Deputy.* ACM SIGOPS OSR 22(4). [doi:10.1145/54289.871709](https://doi.org/10.1145/54289.871709)
- `nist-800-122` — McCallister, E., Grance, T., Scarfone, K. (2010). NIST SP 800-122 *Guide to Protecting the Confidentiality of PII.* [doi:10.6028/NIST.SP.800-122](https://doi.org/10.6028/NIST.SP.800-122)
- `owasp-ssrf` — OWASP Cheat Sheet Series. *Server Side Request Forgery Prevention.* <https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html>
- `owasp-sqlparam` — OWASP Cheat Sheet Series. *Query Parameterization.* <https://cheatsheetseries.owasp.org/cheatsheets/Query_Parameterization_Cheat_Sheet.html>
- `owasp-path` — OWASP. *Path Traversal.* <https://owasp.org/www-community/attacks/Path_Traversal>
- `owasp-csv` — OWASP. *CSV Injection.* <https://owasp.org/www-community/attacks/CSV_Injection>
- `owasp-logging` — OWASP Cheat Sheet Series. *Logging* (data to exclude from logs). <https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html>
- `owasp-llm01` — OWASP Top 10 for LLM Applications 2025. *LLM01:2025 Prompt Injection.* <https://genai.owasp.org/llmrisk/llm01-prompt-injection/>
- `owasp-llm02` — OWASP Top 10 for LLM Applications 2025. *LLM02:2025 Sensitive Information Disclosure.* <https://genai.owasp.org/llmrisk/llm022025-sensitive-information-disclosure/>
- `owasp-llm05` — OWASP Top 10 for LLM Applications 2025. *LLM05:2025 Improper Output Handling.* <https://genai.owasp.org/llmrisk/llm052025-improper-output-handling/>
- `owasp-llm06` — OWASP Top 10 for LLM Applications 2025. *LLM06:2025 Excessive Agency.* <https://genai.owasp.org/llmrisk/llm062025-excessive-agency/>
- `owasp-llm07` — OWASP Top 10 for LLM Applications 2025. *LLM07:2025 System Prompt Leakage.* <https://genai.owasp.org/llmrisk/llm072025-system-prompt-leakage/>
- `owasp-llm09` — OWASP Top 10 for LLM Applications 2025. *LLM09:2025 Misinformation.* <https://genai.owasp.org/llmrisk/llm092025-misinformation/>
- `owasp-llm10` — OWASP Top 10 for LLM Applications 2025. *LLM10:2025 Unbounded Consumption.* <https://genai.owasp.org/llmrisk/llm102025-unbounded-consumption/>
- `owasp-agentic` — OWASP GenAI Security Project. *OWASP Top 10 for Agentic Applications for 2026.* <https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/>
- `owasp-agentic-threats` — OWASP GenAI Security Project. *Agentic AI – Threats and Mitigations.* <https://genai.owasp.org/resource/agentic-ai-threats-and-mitigations/>
- `iso42001` — ISO/IEC 42001:2023 *Information technology — Artificial intelligence — Management system.* <https://www.iso.org/standard/81230.html>
- `nist-rmf` — NIST (2023). AI 100-1 *Artificial Intelligence Risk Management Framework (AI RMF 1.0).* [doi:10.6028/NIST.AI.100-1](https://doi.org/10.6028/NIST.AI.100-1) · <https://www.nist.gov/itl/ai-risk-management-framework>
- `eu-ai-act` — Regulation (EU) 2024/1689 (Artificial Intelligence Act); Art. 14 human oversight. <https://eur-lex.europa.eu/eli/reg/2024/1689/oj/eng>
- `gdpr` — Regulation (EU) 2016/679 (GDPR), Art. 5(1)(c), 7(3), 17. <https://eur-lex.europa.eu/eli/reg/2016/679/oj>
- `greshake` — Greshake, K., Abdelnabi, S., Mishra, S., Endres, C., Holz, T., Fritz, M. (2023). *Not What You've Signed Up For: Compromising Real-World LLM-Integrated Applications with Indirect Prompt Injection.* AISec '23. [doi:10.1145/3605764.3623985](https://doi.org/10.1145/3605764.3623985) · [arXiv:2302.12173](https://arxiv.org/abs/2302.12173)
- `perez-ignore` — Perez, F., Ribeiro, I. (2022). *Ignore Previous Prompt: Attack Techniques For Language Models.* [arXiv:2211.09527](https://arxiv.org/abs/2211.09527)
- `liu-pi` — Liu, Y., Deng, G., Li, Y., et al. (2023). *Prompt Injection attack against LLM-integrated Applications.* [arXiv:2306.05499](https://arxiv.org/abs/2306.05499)
- `injecagent` — Zhan, Q., Liang, Z., Ying, Z., Kang, D. (2024). *InjecAgent: Benchmarking Indirect Prompt Injections in Tool-Integrated Large Language Model Agents.* [arXiv:2403.02691](https://arxiv.org/abs/2403.02691)
- `agentdojo` — Debenedetti, E., Zhang, J., Balunović, M., et al. (2024). *AgentDojo: A Dynamic Environment to Evaluate Prompt Injection Attacks and Defenses for LLM Agents.* [arXiv:2406.13352](https://arxiv.org/abs/2406.13352)
- `bipia` — Yi, J., Xie, Y., Zhu, B., et al. (2023). *Benchmarking and Defending Against Indirect Prompt Injection Attacks on Large Language Models.* [arXiv:2312.14197](https://arxiv.org/abs/2312.14197)
- `spotlighting` — Hines, K., Lopez, G., Hall, M., et al. (2024). *Defending Against Indirect Prompt Injection Attacks With Spotlighting.* [arXiv:2403.14720](https://arxiv.org/abs/2403.14720)
- `asb` — Zhang, H., Huang, J., Mei, K., et al. (2024). *Agent Security Bench (ASB): Formalizing and Benchmarking Attacks and Defenses in LLM-based Agents.* [arXiv:2410.02644](https://arxiv.org/abs/2410.02644)
- `agentpoison` — Chen, Z., Xiang, Z., Xiao, C., Song, D., Li, B. (2024). *AgentPoison: Red-teaming LLM Agents via Poisoning Memory or Knowledge Bases.* [arXiv:2407.12784](https://arxiv.org/abs/2407.12784)
- `taubench` — Yao, S., Shinn, N., Razavi, P., Narasimhan, K. (2024). *τ-bench: A Benchmark for Tool-Agent-User Interaction in Real-World Domains.* [arXiv:2406.12045](https://arxiv.org/abs/2406.12045)
- `trace` — Kim, W., Park, S., In, Y., et al. (2025). *Beyond the Final Answer: Evaluating the Reasoning Trajectories of Tool-Augmented Agents* (TRACE). [arXiv:2510.02837](https://arxiv.org/abs/2510.02837)
- `toolemu` — Ruan, Y., Dong, H., Wang, A., et al. (2023). *Identifying the Risks of LM Agents with an LM-Emulated Sandbox* (ToolEmu). [arXiv:2309.15817](https://arxiv.org/abs/2309.15817)
- `agentbench` — Liu, X., Yu, H., Zhang, H., et al. (2023). *AgentBench: Evaluating LLMs as Agents.* [arXiv:2308.03688](https://arxiv.org/abs/2308.03688)
- `agentboard` — Ma, C., Zhang, J., Zhu, Z., et al. (2024). *AgentBoard: An Analytical Evaluation Board of Multi-turn LLM Agents.* [arXiv:2401.13178](https://arxiv.org/abs/2401.13178)
- `apibank` — Li, M., Zhao, Y., Yu, B., et al. (2023). *API-Bank: A Comprehensive Benchmark for Tool-Augmented LLMs.* [arXiv:2304.08244](https://arxiv.org/abs/2304.08244)
- `helm` — Liang, P., Bommasani, R., Lee, T., et al. (2022). *Holistic Evaluation of Language Models.* [arXiv:2211.09110](https://arxiv.org/abs/2211.09110)
- `memory-survey` — Zhang, Z., Bo, X., Ma, C., et al. (2024). *A Survey on the Memory Mechanism of Large Language Model based Agents.* [arXiv:2404.13501](https://arxiv.org/abs/2404.13501)
- `lost-middle` — Liu, N. F., Lin, K., Hewitt, J., et al. (2023). *Lost in the Middle: How Language Models Use Long Contexts.* [arXiv:2307.03172](https://arxiv.org/abs/2307.03172)
- `halluc-survey` — Huang, L., Yu, W., Ma, W., et al. (2023). *A Survey on Hallucination in Large Language Models: Principles, Taxonomy, Challenges, and Open Questions.* [arXiv:2311.05232](https://arxiv.org/abs/2311.05232)
- `rag` — Lewis, P., Perez, E., Piktus, A., et al. (2020). *Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks.* [arXiv:2005.11401](https://arxiv.org/abs/2005.11401)
- `jacovi` — Jacovi, A., Goldberg, Y. (2020). *Towards Faithfully Interpretable NLP Systems: How Should We Define and Evaluate Faithfulness?* ACL 2020. [doi:10.18653/v1/2020.acl-main.386](https://doi.org/10.18653/v1/2020.acl-main.386)
- `react` — Yao, S., Zhao, J., Yu, D., et al. (2022). *ReAct: Synergizing Reasoning and Acting in Language Models.* [arXiv:2210.03629](https://arxiv.org/abs/2210.03629)
- `selfconsistency` — Wang, X., Wei, J., Schuurmans, D., et al. (2022). *Self-Consistency Improves Chain of Thought Reasoning in Language Models.* [arXiv:2203.11171](https://arxiv.org/abs/2203.11171)
- `sycophancy` — Sharma, M., Tong, M., Korbak, T., et al. (2023). *Towards Understanding Sycophancy in Language Models.* [arXiv:2310.13548](https://arxiv.org/abs/2310.13548)
- `anthropic-agents` — Anthropic (2024). *Building effective agents* (stopping conditions, workflows vs agents). <https://www.anthropic.com/engineering/building-effective-agents>
- `yong-lowres` — Yong, Z.-X., Menghini, C., Bach, S. H. (2023). *Low-Resource Languages Jailbreak GPT-4.* [arXiv:2310.02446](https://arxiv.org/abs/2310.02446)
- `deng-multi` — Deng, Y., Zhang, W., Pan, S. J., Bing, L. (2023). *Multilingual Jailbreak Challenges in Large Language Models.* [arXiv:2310.06474](https://arxiv.org/abs/2310.06474)
- `garg` — Garg, S., Perot, V., Limtiaco, N., et al. (2019). *Counterfactual Fairness in Text Classification through Robustness.* AIES 2019. [doi:10.1145/3306618.3317950](https://doi.org/10.1145/3306618.3317950)
- `bbq` — Parrish, A., Chen, A., Nangia, N., et al. (2021). *BBQ: A Hand-Built Bias Benchmark for Question Answering.* [arXiv:2110.08193](https://arxiv.org/abs/2110.08193)
- `decodingtrust` — Wang, B., Chen, W., Pei, H., et al. (2023). *DecodingTrust: A Comprehensive Assessment of Trustworthiness in GPT Models.* [arXiv:2306.11698](https://arxiv.org/abs/2306.11698)
- `mcp-tools` — Model Context Protocol specification 2025-06-18, *Tools.* <https://modelcontextprotocol.io/specification/2025-06-18/server/tools>
- `langgraph-interrupts` — LangGraph docs. *Interrupts* (human-in-the-loop). <https://docs.langchain.com/oss/python/langgraph/interrupts>
- `langgraph-persistence` — LangGraph docs. *Persistence* (checkpoints, durable resume). <https://docs.langchain.com/oss/python/langgraph/persistence>
- `openai-handoffs` — OpenAI Agents SDK docs. *Handoffs.* <https://openai.github.io/openai-agents-python/handoffs/>
- `openai-guardrails` — OpenAI Agents SDK docs. *Guardrails.* <https://openai.github.io/openai-agents-python/guardrails/>
- `python-sqlite` — Python docs. *sqlite3* (placeholders / parameter binding). <https://docs.python.org/3/library/sqlite3.html>
- `qwen25` — Qwen Team (2024). *Qwen2.5 Technical Report.* [arXiv:2412.15115](https://arxiv.org/abs/2412.15115)
- `llamacpp` — ggml-org. *llama.cpp* (GGUF inference, OpenAI-compatible server). <https://github.com/ggml-org/llama.cpp>
- `taxonomy` — Padmanabhuni, S. (2026). *Agentic AI Assurance Test Taxonomy v1.* Zenodo. [doi:10.5281/zenodo.23587407](https://doi.org/10.5281/zenodo.23587407) — source of the test IDs only
- `catalogue` — Padmanabhuni, S. (2026). *Agentic AI Assurance Test Catalogue — Consolidated Edition (All 110 Tests, T1–T7).* Zenodo. [doi:10.5281/zenodo.23614376](https://doi.org/10.5281/zenodo.23614376) — source of the test text only

<!-- gen_code_refs:begin -->
## D. Short keys used in code comments

Code comments cite these keys, for example `# Ref T4-009: [OWASP-LLM02-2025] [Greshake-2023]` above a rule in
`src/agentest/standards/rules.py`. A key in square brackets is defined in this table or in section E. The works are the
threat model, standard or method *behind* a check; the oracle itself is in-house deterministic code (see
[TEST-SOURCES.md](TEST-SOURCES.md)). Where an ID has no ID-specific source the comment says `Ref <ID>: internal design`
and names its catalogue row (`catalog/checklist-110.jsonl`, `catalog/rai-additions-v1.4.0.jsonl`, or `docs/tests/<ID>.md`
for the X-001..X-020 repo extensions). Entries here repeat the verified bibliography of `agentest.refs.BIB`.

| Short key | Reference | Bibliography key |
|:--|:--|:--|
| `[Chen-1998]` | Chen, T. Y., Cheung, S. C., Yiu, S. M. (1998/2020). *Metamorphic Testing: A New Approach for Generating Next Test Cases.* [arXiv:2002.12543](https://arxiv.org/abs/2002.12543) | `chen-mt` |
| `[Segura-2016]` | Segura, S., Fraser, G., Sanchez, A. B., Ruiz-Cortés, A. (2016). *A Survey on Metamorphic Testing.* IEEE TSE 42(9). [doi:10.1109/TSE.2016.2532875](https://doi.org/10.1109/TSE.2016.2532875) | `segura-mt` |
| `[Barr-2015]` | Barr, E. T., Harman, M., McMinn, P., Shahbaz, M., Yoo, S. (2015). *The Oracle Problem in Software Testing: A Survey.* IEEE TSE 41(5). [doi:10.1109/TSE.2014.2372785](https://doi.org/10.1109/TSE.2014.2372785) | `barr-oracle` |
| `[Hoare-1969]` | Hoare, C. A. R. (1969). *An axiomatic basis for computer programming.* CACM 12(10). [doi:10.1145/363235.363259](https://doi.org/10.1145/363235.363259) | `hoare` |
| `[Haerder-1983]` | Haerder, T., Reuter, A. (1983). *Principles of transaction-oriented database recovery.* ACM Computing Surveys 15(4). [doi:10.1145/289.291](https://doi.org/10.1145/289.291) | `haerder` |
| `[GarciaMolina-1987]` | Garcia-Molina, H., Salem, K. (1987). *Sagas.* SIGMOD '87. [doi:10.1145/38713.38742](https://doi.org/10.1145/38713.38742) | `sagas` |
| `[Kahn-1962]` | Kahn, A. B. (1962). *Topological sorting of large networks.* CACM 5(11). [doi:10.1145/368996.369025](https://doi.org/10.1145/368996.369025) | `kahn` |
| `[Lamport-1978]` | Lamport, L. (1978). *Time, clocks, and the ordering of events in a distributed system.* CACM 21(7). [doi:10.1145/359545.359563](https://doi.org/10.1145/359545.359563) | `lamport` |
| `[RFC9110]` | Fielding, R., Nottingham, M., Reschke, J. (2022). RFC 9110 *HTTP Semantics* (§9.2.2 idempotent methods). [doi:10.17487/RFC9110](https://doi.org/10.17487/RFC9110) | `rfc9110` |
| `[RFC6585]` | Nottingham, M., Fielding, R. (2012). RFC 6585 *Additional HTTP Status Codes* (429 Too Many Requests). [doi:10.17487/RFC6585](https://doi.org/10.17487/RFC6585) | `rfc6585` |
| `[RFC6749]` | Hardt, D. (2012). RFC 6749 *The OAuth 2.0 Authorization Framework* (scopes, single-use codes). [doi:10.17487/RFC6749](https://doi.org/10.17487/RFC6749) | `rfc6749` |
| `[Saltzer-1975]` | Saltzer, J. H., Schroeder, M. D. (1975). *The protection of information in computer systems.* Proc. IEEE 63(9). [doi:10.1109/PROC.1975.9939](https://doi.org/10.1109/PROC.1975.9939) | `saltzer` |
| `[Hardy-1988]` | Hardy, N. (1988). *The Confused Deputy.* ACM SIGOPS OSR 22(4). [doi:10.1145/54289.871709](https://doi.org/10.1145/54289.871709) | `hardy` |
| `[NIST-SP800-122]` | McCallister, E., Grance, T., Scarfone, K. (2010). NIST SP 800-122 *Guide to Protecting the Confidentiality of PII.* [doi:10.6028/NIST.SP.800-122](https://doi.org/10.6028/NIST.SP.800-122) | `nist-800-122` |
| `[OWASP-SSRF]` | OWASP Cheat Sheet Series. *Server Side Request Forgery Prevention.* <https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html> | `owasp-ssrf` |
| `[OWASP-SQLParam]` | OWASP Cheat Sheet Series. *Query Parameterization.* <https://cheatsheetseries.owasp.org/cheatsheets/Query_Parameterization_Cheat_Sheet.html> | `owasp-sqlparam` |
| `[OWASP-PathTraversal]` | OWASP. *Path Traversal.* <https://owasp.org/www-community/attacks/Path_Traversal> | `owasp-path` |
| `[OWASP-CSVInjection]` | OWASP. *CSV Injection.* <https://owasp.org/www-community/attacks/CSV_Injection> | `owasp-csv` |
| `[OWASP-Logging]` | OWASP Cheat Sheet Series. *Logging* (data to exclude from logs). <https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html> | `owasp-logging` |
| `[OWASP-LLM01-2025]` | OWASP Top 10 for LLM Applications 2025. *LLM01:2025 Prompt Injection.* <https://genai.owasp.org/llmrisk/llm01-prompt-injection/> | `owasp-llm01` |
| `[OWASP-LLM02-2025]` | OWASP Top 10 for LLM Applications 2025. *LLM02:2025 Sensitive Information Disclosure.* <https://genai.owasp.org/llmrisk/llm022025-sensitive-information-disclosure/> | `owasp-llm02` |
| `[OWASP-LLM05-2025]` | OWASP Top 10 for LLM Applications 2025. *LLM05:2025 Improper Output Handling.* <https://genai.owasp.org/llmrisk/llm052025-improper-output-handling/> | `owasp-llm05` |
| `[OWASP-LLM06-2025]` | OWASP Top 10 for LLM Applications 2025. *LLM06:2025 Excessive Agency.* <https://genai.owasp.org/llmrisk/llm062025-excessive-agency/> | `owasp-llm06` |
| `[OWASP-LLM07-2025]` | OWASP Top 10 for LLM Applications 2025. *LLM07:2025 System Prompt Leakage.* <https://genai.owasp.org/llmrisk/llm072025-system-prompt-leakage/> | `owasp-llm07` |
| `[OWASP-LLM09-2025]` | OWASP Top 10 for LLM Applications 2025. *LLM09:2025 Misinformation.* <https://genai.owasp.org/llmrisk/llm092025-misinformation/> | `owasp-llm09` |
| `[OWASP-LLM10-2025]` | OWASP Top 10 for LLM Applications 2025. *LLM10:2025 Unbounded Consumption.* <https://genai.owasp.org/llmrisk/llm102025-unbounded-consumption/> | `owasp-llm10` |
| `[OWASP-AgenticTop10-2026]` | OWASP GenAI Security Project. *OWASP Top 10 for Agentic Applications for 2026.* <https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/> | `owasp-agentic` |
| `[OWASP-AgenticThreats]` | OWASP GenAI Security Project. *Agentic AI – Threats and Mitigations.* <https://genai.owasp.org/resource/agentic-ai-threats-and-mitigations/> | `owasp-agentic-threats` |
| `[ISO-42001-2023]` | ISO/IEC 42001:2023 *Information technology — Artificial intelligence — Management system.* <https://www.iso.org/standard/81230.html> | `iso42001` |
| `[NIST-AIRMF-1.0]` | NIST (2023). AI 100-1 *Artificial Intelligence Risk Management Framework (AI RMF 1.0).* [doi:10.6028/NIST.AI.100-1](https://doi.org/10.6028/NIST.AI.100-1) · <https://www.nist.gov/itl/ai-risk-management-framework> | `nist-rmf` |
| `[EU-AIAct-2024]` | Regulation (EU) 2024/1689 (Artificial Intelligence Act); Art. 14 human oversight. <https://eur-lex.europa.eu/eli/reg/2024/1689/oj/eng> | `eu-ai-act` |
| `[GDPR-2016]` | Regulation (EU) 2016/679 (GDPR), Art. 5(1)(c), 7(3), 17. <https://eur-lex.europa.eu/eli/reg/2016/679/oj> | `gdpr` |
| `[Greshake-2023]` | Greshake, K., Abdelnabi, S., Mishra, S., Endres, C., Holz, T., Fritz, M. (2023). *Not What You've Signed Up For: Compromising Real-World LLM-Integrated Applications with Indirect Prompt Injection.* AISec '23. [doi:10.1145/3605764.3623985](https://doi.org/10.1145/3605764.3623985) · [arXiv:2302.12173](https://arxiv.org/abs/2302.12173) | `greshake` |
| `[Perez-2022]` | Perez, F., Ribeiro, I. (2022). *Ignore Previous Prompt: Attack Techniques For Language Models.* [arXiv:2211.09527](https://arxiv.org/abs/2211.09527) | `perez-ignore` |
| `[Liu-2023]` | Liu, Y., Deng, G., Li, Y., et al. (2023). *Prompt Injection attack against LLM-integrated Applications.* [arXiv:2306.05499](https://arxiv.org/abs/2306.05499) | `liu-pi` |
| `[InjecAgent-2024]` | Zhan, Q., Liang, Z., Ying, Z., Kang, D. (2024). *InjecAgent: Benchmarking Indirect Prompt Injections in Tool-Integrated Large Language Model Agents.* [arXiv:2403.02691](https://arxiv.org/abs/2403.02691) | `injecagent` |
| `[AgentDojo-2024]` | Debenedetti, E., Zhang, J., Balunović, M., et al. (2024). *AgentDojo: A Dynamic Environment to Evaluate Prompt Injection Attacks and Defenses for LLM Agents.* [arXiv:2406.13352](https://arxiv.org/abs/2406.13352) | `agentdojo` |
| `[BIPIA-2023]` | Yi, J., Xie, Y., Zhu, B., et al. (2023). *Benchmarking and Defending Against Indirect Prompt Injection Attacks on Large Language Models.* [arXiv:2312.14197](https://arxiv.org/abs/2312.14197) | `bipia` |
| `[Spotlighting-2024]` | Hines, K., Lopez, G., Hall, M., et al. (2024). *Defending Against Indirect Prompt Injection Attacks With Spotlighting.* [arXiv:2403.14720](https://arxiv.org/abs/2403.14720) | `spotlighting` |
| `[ASB-2024]` | Zhang, H., Huang, J., Mei, K., et al. (2024). *Agent Security Bench (ASB): Formalizing and Benchmarking Attacks and Defenses in LLM-based Agents.* [arXiv:2410.02644](https://arxiv.org/abs/2410.02644) | `asb` |
| `[AgentPoison-2024]` | Chen, Z., Xiang, Z., Xiao, C., Song, D., Li, B. (2024). *AgentPoison: Red-teaming LLM Agents via Poisoning Memory or Knowledge Bases.* [arXiv:2407.12784](https://arxiv.org/abs/2407.12784) | `agentpoison` |
| `[TauBench-2024]` | Yao, S., Shinn, N., Razavi, P., Narasimhan, K. (2024). *τ-bench: A Benchmark for Tool-Agent-User Interaction in Real-World Domains.* [arXiv:2406.12045](https://arxiv.org/abs/2406.12045) | `taubench` |
| `[TRACE-2025]` | Kim, W., Park, S., In, Y., et al. (2025). *Beyond the Final Answer: Evaluating the Reasoning Trajectories of Tool-Augmented Agents* (TRACE). [arXiv:2510.02837](https://arxiv.org/abs/2510.02837) | `trace` |
| `[ToolEmu-2023]` | Ruan, Y., Dong, H., Wang, A., et al. (2023). *Identifying the Risks of LM Agents with an LM-Emulated Sandbox* (ToolEmu). [arXiv:2309.15817](https://arxiv.org/abs/2309.15817) | `toolemu` |
| `[AgentBench-2023]` | Liu, X., Yu, H., Zhang, H., et al. (2023). *AgentBench: Evaluating LLMs as Agents.* [arXiv:2308.03688](https://arxiv.org/abs/2308.03688) | `agentbench` |
| `[AgentBoard-2024]` | Ma, C., Zhang, J., Zhu, Z., et al. (2024). *AgentBoard: An Analytical Evaluation Board of Multi-turn LLM Agents.* [arXiv:2401.13178](https://arxiv.org/abs/2401.13178) | `agentboard` |
| `[APIBank-2023]` | Li, M., Zhao, Y., Yu, B., et al. (2023). *API-Bank: A Comprehensive Benchmark for Tool-Augmented LLMs.* [arXiv:2304.08244](https://arxiv.org/abs/2304.08244) | `apibank` |
| `[HELM-2022]` | Liang, P., Bommasani, R., Lee, T., et al. (2022). *Holistic Evaluation of Language Models.* [arXiv:2211.09110](https://arxiv.org/abs/2211.09110) | `helm` |
| `[MemorySurvey-2024]` | Zhang, Z., Bo, X., Ma, C., et al. (2024). *A Survey on the Memory Mechanism of Large Language Model based Agents.* [arXiv:2404.13501](https://arxiv.org/abs/2404.13501) | `memory-survey` |
| `[LostInTheMiddle-2023]` | Liu, N. F., Lin, K., Hewitt, J., et al. (2023). *Lost in the Middle: How Language Models Use Long Contexts.* [arXiv:2307.03172](https://arxiv.org/abs/2307.03172) | `lost-middle` |
| `[HallucinationSurvey-2023]` | Huang, L., Yu, W., Ma, W., et al. (2023). *A Survey on Hallucination in Large Language Models: Principles, Taxonomy, Challenges, and Open Questions.* [arXiv:2311.05232](https://arxiv.org/abs/2311.05232) | `halluc-survey` |
| `[RAG-2020]` | Lewis, P., Perez, E., Piktus, A., et al. (2020). *Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks.* [arXiv:2005.11401](https://arxiv.org/abs/2005.11401) | `rag` |
| `[Jacovi-2020]` | Jacovi, A., Goldberg, Y. (2020). *Towards Faithfully Interpretable NLP Systems: How Should We Define and Evaluate Faithfulness?* ACL 2020. [doi:10.18653/v1/2020.acl-main.386](https://doi.org/10.18653/v1/2020.acl-main.386) | `jacovi` |
| `[ReAct-2022]` | Yao, S., Zhao, J., Yu, D., et al. (2022). *ReAct: Synergizing Reasoning and Acting in Language Models.* [arXiv:2210.03629](https://arxiv.org/abs/2210.03629) | `react` |
| `[SelfConsistency-2022]` | Wang, X., Wei, J., Schuurmans, D., et al. (2022). *Self-Consistency Improves Chain of Thought Reasoning in Language Models.* [arXiv:2203.11171](https://arxiv.org/abs/2203.11171) | `selfconsistency` |
| `[Sycophancy-2023]` | Sharma, M., Tong, M., Korbak, T., et al. (2023). *Towards Understanding Sycophancy in Language Models.* [arXiv:2310.13548](https://arxiv.org/abs/2310.13548) | `sycophancy` |
| `[Anthropic-Agents-2024]` | Anthropic (2024). *Building effective agents* (stopping conditions, workflows vs agents). <https://www.anthropic.com/engineering/building-effective-agents> | `anthropic-agents` |
| `[Yong-2023]` | Yong, Z.-X., Menghini, C., Bach, S. H. (2023). *Low-Resource Languages Jailbreak GPT-4.* [arXiv:2310.02446](https://arxiv.org/abs/2310.02446) | `yong-lowres` |
| `[Deng-2023]` | Deng, Y., Zhang, W., Pan, S. J., Bing, L. (2023). *Multilingual Jailbreak Challenges in Large Language Models.* [arXiv:2310.06474](https://arxiv.org/abs/2310.06474) | `deng-multi` |
| `[Garg-2019]` | Garg, S., Perot, V., Limtiaco, N., et al. (2019). *Counterfactual Fairness in Text Classification through Robustness.* AIES 2019. [doi:10.1145/3306618.3317950](https://doi.org/10.1145/3306618.3317950) | `garg` |
| `[BBQ-2021]` | Parrish, A., Chen, A., Nangia, N., et al. (2021). *BBQ: A Hand-Built Bias Benchmark for Question Answering.* [arXiv:2110.08193](https://arxiv.org/abs/2110.08193) | `bbq` |
| `[DecodingTrust-2023]` | Wang, B., Chen, W., Pei, H., et al. (2023). *DecodingTrust: A Comprehensive Assessment of Trustworthiness in GPT Models.* [arXiv:2306.11698](https://arxiv.org/abs/2306.11698) | `decodingtrust` |
| `[MCP-Tools-2025-06-18]` | Model Context Protocol specification 2025-06-18, *Tools.* <https://modelcontextprotocol.io/specification/2025-06-18/server/tools> | `mcp-tools` |
| `[LangGraph-Interrupts]` | LangGraph docs. *Interrupts* (human-in-the-loop). <https://docs.langchain.com/oss/python/langgraph/interrupts> | `langgraph-interrupts` |
| `[LangGraph-Persistence]` | LangGraph docs. *Persistence* (checkpoints, durable resume). <https://docs.langchain.com/oss/python/langgraph/persistence> | `langgraph-persistence` |
| `[OpenAIAgents-Handoffs]` | OpenAI Agents SDK docs. *Handoffs.* <https://openai.github.io/openai-agents-python/handoffs/> | `openai-handoffs` |
| `[OpenAIAgents-Guardrails]` | OpenAI Agents SDK docs. *Guardrails.* <https://openai.github.io/openai-agents-python/guardrails/> | `openai-guardrails` |
| `[Python-sqlite3]` | Python docs. *sqlite3* (placeholders / parameter binding). <https://docs.python.org/3/library/sqlite3.html> | `python-sqlite` |
| `[Qwen2.5-2024]` | Qwen Team (2024). *Qwen2.5 Technical Report.* [arXiv:2412.15115](https://arxiv.org/abs/2412.15115) | `qwen25` |
| `[llama.cpp]` | ggml-org. *llama.cpp* (GGUF inference, OpenAI-compatible server). <https://github.com/ggml-org/llama.cpp> | `llamacpp` |
| `[Padmanabhuni-2026-Taxonomy]` | Padmanabhuni, S. (2026). *Agentic AI Assurance Test Taxonomy v1.* Zenodo. [doi:10.5281/zenodo.23587407](https://doi.org/10.5281/zenodo.23587407) — source of the test IDs only | `taxonomy` |
| `[Padmanabhuni-2026-Catalogue]` | Padmanabhuni, S. (2026). *Agentic AI Assurance Test Catalogue — Consolidated Edition (All 110 Tests, T1–T7).* Zenodo. [doi:10.5281/zenodo.23614376](https://doi.org/10.5281/zenodo.23614376) — source of the test text only | `catalogue` |

## E. Specifications and framework documentation cited in module comments

Opened and checked on 2026-11-15. Framework documentation is cited only where a module reads that framework's log or
message shape or an example drives its public API; no framework code is bundled.

| Short key | Specification / documentation | URL |
|:--|:--|:--|
| `[Chen-2018]` | Chen, T. Y., Kuo, F.-C., Liu, H., Poon, P.-L., Towey, D., Tse, T. H., Zhou, Z. Q. (2018). *Metamorphic Testing: A Review of Challenges and Opportunities.* ACM Computing Surveys 51(1). | <https://doi.org/10.1145/3143561> |
| `[Utting-2012]` | Utting, M., Pretschner, A., Legeard, B. (2012). *A taxonomy of model-based testing approaches.* Software Testing, Verification and Reliability 22(5). | <https://doi.org/10.1002/stvr.456> |
| `[OTel-GenAI-semconv]` | OpenTelemetry. *Semantic conventions for generative AI systems* (status: Development). | <https://opentelemetry.io/docs/specs/semconv/gen-ai/> |
| `[OTel-GenAI-agent-spans]` | OpenTelemetry. *Semantic conventions for GenAI agent and framework spans.* | <https://opentelemetry.io/docs/specs/semconv/gen-ai/gen-ai-agent-spans/> |
| `[OTLP-spec]` | OpenTelemetry. *OTLP Specification* (JSON Protobuf encoding; OTLP/HTTP). | <https://opentelemetry.io/docs/specs/otlp/> |
| `[OTel-proto]` | OpenTelemetry. *opentelemetry-proto* (`trace/v1/trace.proto`, `common/v1/common.proto`). | <https://github.com/open-telemetry/opentelemetry-proto> |
| `[A2A-spec]` | A2A Protocol. *Agent2Agent protocol specification* (AgentCard, agent discovery). | <https://a2a-protocol.org/latest/specification/> |
| `[CEL]` | Common Expression Language (CEL). Inspiration for the safe expression subset in `expr.py`; no CEL code is used. | <https://cel.dev> |
| `[JSONLogic]` | JsonLogic. Inspiration for side-effect-free rule expressions; no JsonLogic code is used. | <https://jsonlogic.com/> |
| `[SARIF-2.1.0]` | OASIS. *Static Analysis Results Interchange Format (SARIF) Version 2.1.0.* | <https://docs.oasis-open.org/sarif/sarif/v2.1.0/sarif-v2.1.0.html> |
| `[PyPA-EntryPoints]` | Python Packaging Authority. *Entry points specification.* | <https://packaging.python.org/en/latest/specifications/entry-points/> |
| `[UAX24]` | Unicode Standard Annex #24, *Unicode Script Property* (script names used by the language-script check). | <https://www.unicode.org/reports/tr24/> |
| `[BCP47]` | IETF BCP 47 / RFC 5646, *Tags for Identifying Languages* (primary language subtags). | <https://www.rfc-editor.org/rfc/rfc5646> |
| `[Python-unicodedata]` | Python docs. *unicodedata* (character names). | <https://docs.python.org/3/library/unicodedata.html> |
| `[JSON-Schema-2020-12]` | JSON Schema, draft 2020-12 (MCP `inputSchema`). | <https://json-schema.org/draft/2020-12> |
| `[OpenAIAgents-SDK]` | OpenAI Agents SDK docs (RunItems, tracing). | <https://openai.github.io/openai-agents-python/> |
| `[LangGraph-docs]` | LangGraph docs. *Overview.* | <https://docs.langchain.com/oss/python/langgraph/overview> |
| `[AutoGen-AgentChat]` | Microsoft AutoGen docs. *AgentChat user guide.* | <https://microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/index.html> |
| `[smolagents-docs]` | Hugging Face. *smolagents* (library repository and documentation links). | <https://github.com/huggingface/smolagents> |
| `[n8n-docs]` | n8n documentation. | <https://docs.n8n.io/> |
| `[LlamaIndex-docs]` | LlamaIndex documentation. | <https://docs.llamaindex.ai/> |
| `[CrewAI-docs]` | CrewAI documentation. | <https://docs.crewai.com/> |
| `[InspectAI-docs]` | Inspect AI (UK AI Security Institute) documentation. | <https://inspect.aisi.org.uk/> |
| `[promptfoo-docs]` | promptfoo documentation. | <https://www.promptfoo.dev/docs/intro/> |
| `[DeepEval-docs]` | DeepEval documentation. | <https://deepeval.com/docs/getting-started> |
| `[OpenAI-FunctionCalling]` | OpenAI. *Function calling* guide (tool-call message shape used by the OpenAI-compatible reference agents). | <https://platform.openai.com/docs/guides/function-calling> |

Regenerate sections D and E and the code comments with `python scripts/gen_code_refs.py` (`--check` in CI-style use).
<!-- gen_code_refs:end -->
