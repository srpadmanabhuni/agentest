"""Verified bibliography and per-test reference mapping.

Every entry was opened and checked (title and first authors) against arXiv, doi.org/Crossref
or the publishing body on 2026-10-26. Zenodo is used only to credit the author's own test
taxonomy/catalogue (``TAXONOMY``, ``CATALOGUE``); every method is cited to its original source.
"""

from __future__ import annotations

A = "https://arxiv.org/abs/"
D = "https://doi.org/"

BIB: dict[str, str] = {
    # --- software testing foundations
    "chen-mt": f"Chen, T. Y., Cheung, S. C., Yiu, S. M. (1998/2020). *Metamorphic Testing: A New Approach for Generating Next Test Cases.* [arXiv:2002.12543]({A}2002.12543)",
    "segura-mt": f"Segura, S., Fraser, G., Sanchez, A. B., Ruiz-Cortés, A. (2016). *A Survey on Metamorphic Testing.* IEEE TSE 42(9). [doi:10.1109/TSE.2016.2532875]({D}10.1109/TSE.2016.2532875)",
    "barr-oracle": f"Barr, E. T., Harman, M., McMinn, P., Shahbaz, M., Yoo, S. (2015). *The Oracle Problem in Software Testing: A Survey.* IEEE TSE 41(5). [doi:10.1109/TSE.2014.2372785]({D}10.1109/TSE.2014.2372785)",
    "hoare": f"Hoare, C. A. R. (1969). *An axiomatic basis for computer programming.* CACM 12(10). [doi:10.1145/363235.363259]({D}10.1145/363235.363259)",
    "haerder": f"Haerder, T., Reuter, A. (1983). *Principles of transaction-oriented database recovery.* ACM Computing Surveys 15(4). [doi:10.1145/289.291]({D}10.1145/289.291)",
    "sagas": f"Garcia-Molina, H., Salem, K. (1987). *Sagas.* SIGMOD '87. [doi:10.1145/38713.38742]({D}10.1145/38713.38742)",
    "kahn": f"Kahn, A. B. (1962). *Topological sorting of large networks.* CACM 5(11). [doi:10.1145/368996.369025]({D}10.1145/368996.369025)",
    "lamport": f"Lamport, L. (1978). *Time, clocks, and the ordering of events in a distributed system.* CACM 21(7). [doi:10.1145/359545.359563]({D}10.1145/359545.359563)",
    "rfc9110": f"Fielding, R., Nottingham, M., Reschke, J. (2022). RFC 9110 *HTTP Semantics* (§9.2.2 idempotent methods). [doi:10.17487/RFC9110]({D}10.17487/RFC9110)",
    "rfc6585": f"Nottingham, M., Fielding, R. (2012). RFC 6585 *Additional HTTP Status Codes* (429 Too Many Requests). [doi:10.17487/RFC6585]({D}10.17487/RFC6585)",
    "rfc6749": f"Hardt, D. (2012). RFC 6749 *The OAuth 2.0 Authorization Framework* (scopes, single-use codes). [doi:10.17487/RFC6749]({D}10.17487/RFC6749)",
    # --- security principles
    "saltzer": f"Saltzer, J. H., Schroeder, M. D. (1975). *The protection of information in computer systems.* Proc. IEEE 63(9). [doi:10.1109/PROC.1975.9939]({D}10.1109/PROC.1975.9939)",
    "hardy": f"Hardy, N. (1988). *The Confused Deputy.* ACM SIGOPS OSR 22(4). [doi:10.1145/54289.871709]({D}10.1145/54289.871709)",
    "nist-800-122": f"McCallister, E., Grance, T., Scarfone, K. (2010). NIST SP 800-122 *Guide to Protecting the Confidentiality of PII.* [doi:10.6028/NIST.SP.800-122]({D}10.6028/NIST.SP.800-122)",
    "owasp-ssrf": "OWASP Cheat Sheet Series. *Server Side Request Forgery Prevention.* <https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html>",
    "owasp-sqlparam": "OWASP Cheat Sheet Series. *Query Parameterization.* <https://cheatsheetseries.owasp.org/cheatsheets/Query_Parameterization_Cheat_Sheet.html>",
    "owasp-path": "OWASP. *Path Traversal.* <https://owasp.org/www-community/attacks/Path_Traversal>",
    "owasp-csv": "OWASP. *CSV Injection.* <https://owasp.org/www-community/attacks/CSV_Injection>",
    "owasp-logging": "OWASP Cheat Sheet Series. *Logging* (data to exclude from logs). <https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html>",
    # --- standards / regulation
    "owasp-llm01": "OWASP Top 10 for LLM Applications 2025. *LLM01:2025 Prompt Injection.* <https://genai.owasp.org/llmrisk/llm01-prompt-injection/>",
    "owasp-llm02": "OWASP Top 10 for LLM Applications 2025. *LLM02:2025 Sensitive Information Disclosure.* <https://genai.owasp.org/llmrisk/llm022025-sensitive-information-disclosure/>",
    "owasp-llm05": "OWASP Top 10 for LLM Applications 2025. *LLM05:2025 Improper Output Handling.* <https://genai.owasp.org/llmrisk/llm052025-improper-output-handling/>",
    "owasp-llm06": "OWASP Top 10 for LLM Applications 2025. *LLM06:2025 Excessive Agency.* <https://genai.owasp.org/llmrisk/llm062025-excessive-agency/>",
    "owasp-llm07": "OWASP Top 10 for LLM Applications 2025. *LLM07:2025 System Prompt Leakage.* <https://genai.owasp.org/llmrisk/llm072025-system-prompt-leakage/>",
    "owasp-llm09": "OWASP Top 10 for LLM Applications 2025. *LLM09:2025 Misinformation.* <https://genai.owasp.org/llmrisk/llm092025-misinformation/>",
    "owasp-llm10": "OWASP Top 10 for LLM Applications 2025. *LLM10:2025 Unbounded Consumption.* <https://genai.owasp.org/llmrisk/llm102025-unbounded-consumption/>",
    "owasp-agentic": "OWASP GenAI Security Project. *OWASP Top 10 for Agentic Applications for 2026.* <https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/>",
    "owasp-agentic-threats": "OWASP GenAI Security Project. *Agentic AI – Threats and Mitigations.* <https://genai.owasp.org/resource/agentic-ai-threats-and-mitigations/>",
    "iso42001": "ISO/IEC 42001:2023 *Information technology — Artificial intelligence — Management system.* <https://www.iso.org/standard/81230.html>",
    "nist-rmf": f"NIST (2023). AI 100-1 *Artificial Intelligence Risk Management Framework (AI RMF 1.0).* [doi:10.6028/NIST.AI.100-1]({D}10.6028/NIST.AI.100-1) · <https://www.nist.gov/itl/ai-risk-management-framework>",
    "eu-ai-act": "Regulation (EU) 2024/1689 (Artificial Intelligence Act); Art. 14 human oversight. <https://eur-lex.europa.eu/eli/reg/2024/1689/oj/eng>",
    "gdpr": "Regulation (EU) 2016/679 (GDPR), Art. 5(1)(c), 7(3), 17. <https://eur-lex.europa.eu/eli/reg/2016/679/oj>",
    # --- prompt injection
    "greshake": f"Greshake, K., Abdelnabi, S., Mishra, S., Endres, C., Holz, T., Fritz, M. (2023). *Not What You've Signed Up For: Compromising Real-World LLM-Integrated Applications with Indirect Prompt Injection.* AISec '23. [doi:10.1145/3605764.3623985]({D}10.1145/3605764.3623985) · [arXiv:2302.12173]({A}2302.12173)",
    "perez-ignore": f"Perez, F., Ribeiro, I. (2022). *Ignore Previous Prompt: Attack Techniques For Language Models.* [arXiv:2211.09527]({A}2211.09527)",
    "liu-pi": f"Liu, Y., Deng, G., Li, Y., et al. (2023). *Prompt Injection attack against LLM-integrated Applications.* [arXiv:2306.05499]({A}2306.05499)",
    "injecagent": f"Zhan, Q., Liang, Z., Ying, Z., Kang, D. (2024). *InjecAgent: Benchmarking Indirect Prompt Injections in Tool-Integrated Large Language Model Agents.* [arXiv:2403.02691]({A}2403.02691)",
    "agentdojo": f"Debenedetti, E., Zhang, J., Balunović, M., et al. (2024). *AgentDojo: A Dynamic Environment to Evaluate Prompt Injection Attacks and Defenses for LLM Agents.* [arXiv:2406.13352]({A}2406.13352)",
    "bipia": f"Yi, J., Xie, Y., Zhu, B., et al. (2023). *Benchmarking and Defending Against Indirect Prompt Injection Attacks on Large Language Models.* [arXiv:2312.14197]({A}2312.14197)",
    "spotlighting": f"Hines, K., Lopez, G., Hall, M., et al. (2024). *Defending Against Indirect Prompt Injection Attacks With Spotlighting.* [arXiv:2403.14720]({A}2403.14720)",
    "asb": f"Zhang, H., Huang, J., Mei, K., et al. (2024). *Agent Security Bench (ASB): Formalizing and Benchmarking Attacks and Defenses in LLM-based Agents.* [arXiv:2410.02644]({A}2410.02644)",
    "agentpoison": f"Chen, Z., Xiang, Z., Xiao, C., Song, D., Li, B. (2024). *AgentPoison: Red-teaming LLM Agents via Poisoning Memory or Knowledge Bases.* [arXiv:2407.12784]({A}2407.12784)",
    # --- agent evaluation
    "taubench": f"Yao, S., Shinn, N., Razavi, P., Narasimhan, K. (2024). *τ-bench: A Benchmark for Tool-Agent-User Interaction in Real-World Domains.* [arXiv:2406.12045]({A}2406.12045)",
    "trace": f"Kim, W., Park, S., In, Y., et al. (2025). *Beyond the Final Answer: Evaluating the Reasoning Trajectories of Tool-Augmented Agents* (TRACE). [arXiv:2510.02837]({A}2510.02837)",
    "toolemu": f"Ruan, Y., Dong, H., Wang, A., et al. (2023). *Identifying the Risks of LM Agents with an LM-Emulated Sandbox* (ToolEmu). [arXiv:2309.15817]({A}2309.15817)",
    "agentbench": f"Liu, X., Yu, H., Zhang, H., et al. (2023). *AgentBench: Evaluating LLMs as Agents.* [arXiv:2308.03688]({A}2308.03688)",
    "agentboard": f"Ma, C., Zhang, J., Zhu, Z., et al. (2024). *AgentBoard: An Analytical Evaluation Board of Multi-turn LLM Agents.* [arXiv:2401.13178]({A}2401.13178)",
    "apibank": f"Li, M., Zhao, Y., Yu, B., et al. (2023). *API-Bank: A Comprehensive Benchmark for Tool-Augmented LLMs.* [arXiv:2304.08244]({A}2304.08244)",
    "helm": f"Liang, P., Bommasani, R., Lee, T., et al. (2022). *Holistic Evaluation of Language Models.* [arXiv:2211.09110]({A}2211.09110)",
    "memory-survey": f"Zhang, Z., Bo, X., Ma, C., et al. (2024). *A Survey on the Memory Mechanism of Large Language Model based Agents.* [arXiv:2404.13501]({A}2404.13501)",
    "lost-middle": f"Liu, N. F., Lin, K., Hewitt, J., et al. (2023). *Lost in the Middle: How Language Models Use Long Contexts.* [arXiv:2307.03172]({A}2307.03172)",
    "halluc-survey": f"Huang, L., Yu, W., Ma, W., et al. (2023). *A Survey on Hallucination in Large Language Models: Principles, Taxonomy, Challenges, and Open Questions.* [arXiv:2311.05232]({A}2311.05232)",
    "rag": f"Lewis, P., Perez, E., Piktus, A., et al. (2020). *Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks.* [arXiv:2005.11401]({A}2005.11401)",
    "jacovi": f"Jacovi, A., Goldberg, Y. (2020). *Towards Faithfully Interpretable NLP Systems: How Should We Define and Evaluate Faithfulness?* ACL 2020. [doi:10.18653/v1/2020.acl-main.386]({D}10.18653/v1/2020.acl-main.386)",
    "react": f"Yao, S., Zhao, J., Yu, D., et al. (2022). *ReAct: Synergizing Reasoning and Acting in Language Models.* [arXiv:2210.03629]({A}2210.03629)",
    "selfconsistency": f"Wang, X., Wei, J., Schuurmans, D., et al. (2022). *Self-Consistency Improves Chain of Thought Reasoning in Language Models.* [arXiv:2203.11171]({A}2203.11171)",
    "sycophancy": f"Sharma, M., Tong, M., Korbak, T., et al. (2023). *Towards Understanding Sycophancy in Language Models.* [arXiv:2310.13548]({A}2310.13548)",
    "anthropic-agents": "Anthropic (2024). *Building effective agents* (stopping conditions, workflows vs agents). <https://www.anthropic.com/engineering/building-effective-agents>",
    # --- multilingual / fairness
    "yong-lowres": f"Yong, Z.-X., Menghini, C., Bach, S. H. (2023). *Low-Resource Languages Jailbreak GPT-4.* [arXiv:2310.02446]({A}2310.02446)",
    "deng-multi": f"Deng, Y., Zhang, W., Pan, S. J., Bing, L. (2023). *Multilingual Jailbreak Challenges in Large Language Models.* [arXiv:2310.06474]({A}2310.06474)",
    "garg": f"Garg, S., Perot, V., Limtiaco, N., et al. (2019). *Counterfactual Fairness in Text Classification through Robustness.* AIES 2019. [doi:10.1145/3306618.3317950]({D}10.1145/3306618.3317950)",
    "bbq": f"Parrish, A., Chen, A., Nangia, N., et al. (2021). *BBQ: A Hand-Built Bias Benchmark for Question Answering.* [arXiv:2110.08193]({A}2110.08193)",
    "decodingtrust": f"Wang, B., Chen, W., Pei, H., et al. (2023). *DecodingTrust: A Comprehensive Assessment of Trustworthiness in GPT Models.* [arXiv:2306.11698]({A}2306.11698)",
    # --- frameworks used by the reference agents (official docs)
    "mcp-tools": "Model Context Protocol specification 2025-06-18, *Tools.* <https://modelcontextprotocol.io/specification/2025-06-18/server/tools>",
    "langgraph-interrupts": "LangGraph docs. *Interrupts* (human-in-the-loop). <https://docs.langchain.com/oss/python/langgraph/interrupts>",
    "langgraph-persistence": "LangGraph docs. *Persistence* (checkpoints, durable resume). <https://docs.langchain.com/oss/python/langgraph/persistence>",
    "openai-handoffs": "OpenAI Agents SDK docs. *Handoffs.* <https://openai.github.io/openai-agents-python/handoffs/>",
    "openai-guardrails": "OpenAI Agents SDK docs. *Guardrails.* <https://openai.github.io/openai-agents-python/guardrails/>",
    "python-sqlite": "Python docs. *sqlite3* (placeholders / parameter binding). <https://docs.python.org/3/library/sqlite3.html>",
    "qwen25": f"Qwen Team (2024). *Qwen2.5 Technical Report.* [arXiv:2412.15115]({A}2412.15115)",
    "llamacpp": "ggml-org. *llama.cpp* (GGUF inference, OpenAI-compatible server). <https://github.com/ggml-org/llama.cpp>",
    # --- author's own (Zenodo allowed only here)
    "taxonomy": f"Padmanabhuni, S. (2026). *Agentic AI Assurance Test Taxonomy v1.* Zenodo. [doi:10.5281/zenodo.23587407]({D}10.5281/zenodo.23587407) — source of the test IDs only",
    "catalogue": f"Padmanabhuni, S. (2026). *Agentic AI Assurance Test Catalogue — Consolidated Edition (All 110 Tests, T1–T7).* Zenodo. [doi:10.5281/zenodo.23614376]({D}10.5281/zenodo.23614376) — source of the test text only",
}

CLASS_REFS: dict[str, list[str]] = {
    "T1": ["hoare", "barr-oracle", "taubench"],
    "T2": ["kahn", "taubench", "eu-ai-act"],
    "T3": ["saltzer", "hardy", "owasp-llm06", "owasp-agentic", "iso42001"],
    "T4": ["greshake", "injecagent", "agentdojo", "owasp-llm01"],
    "T5": ["saltzer", "toolemu", "owasp-llm06", "mcp-tools"],
    "T6": ["memory-survey", "agentboard"],
    "T7": ["chen-mt", "segura-mt"],
    "X": ["barr-oracle"],
}

ID_REFS: dict[str, list[str]] = {
    "T1-002": ["nist-rmf"], "T1-003": ["nist-rmf"], "T1-006": ["rfc9110"], "T1-008": ["haerder", "sagas"], "T1-009": ["haerder"],
    "T1-012": ["haerder"], "T1-016": ["gdpr"], "T1-017": ["haerder", "langgraph-persistence"], "T1-018": ["jacovi", "trace"],
    "T2-003": ["rfc9110"], "T2-004": ["langgraph-interrupts"], "T2-005": ["nist-800-122"], "T2-008": ["sagas"], "T2-012": ["langgraph-interrupts"],
    "T2-014": ["lamport"],
    "T3-001": ["greshake"], "T3-003": ["rfc6749"], "T3-004": ["eu-ai-act"], "T3-005": ["eu-ai-act"], "T3-006": ["nist-rmf"], "T3-009": ["rfc6749"],
    "T3-010": ["rfc6749"], "T3-013": ["owasp-agentic-threats"], "T3-014": ["owasp-agentic-threats"],
    "T4-001": ["perez-ignore"], "T4-002": ["owasp-ssrf"], "T4-004": ["toolemu"], "T4-005": ["spotlighting", "bipia"], "T4-006": ["greshake"],
    "T4-008": ["owasp-csv"], "T4-009": ["owasp-llm02"], "T4-010": ["rag", "agentpoison"], "T4-011": ["liu-pi"], "T4-012": ["spotlighting"],
    "T4-014": ["deng-multi"], "T4-018": ["asb", "bipia"],
    "T5-004": ["nist-800-122", "owasp-llm02"], "T5-005": ["owasp-ssrf"], "T5-006": ["owasp-llm10"], "T5-008": ["owasp-path"], "T5-009": ["rfc6585"],
    "T5-010": ["owasp-sqlparam", "python-sqlite"], "T5-011": ["owasp-llm02"], "T5-015": ["react", "trace"], "T5-017": ["owasp-ssrf"], "T5-018": ["openai-guardrails"],
    "T6-004": ["gdpr"], "T6-005": ["owasp-llm07"], "T6-007": ["rag", "jacovi"], "T6-008": ["lost-middle"], "T6-009": ["rag"], "T6-011": ["owasp-llm02"],
    "T7-001": ["helm"], "T7-002": ["yong-lowres", "deng-multi"], "T7-003": ["yong-lowres", "deng-multi"], "T7-004": ["garg", "deng-multi"],
    "T7-005": ["helm"], "T7-007": ["garg", "bbq", "decodingtrust"], "T7-008": ["selfconsistency", "taubench"], "T7-009": ["jacovi", "trace"],
    "T7-011": ["garg", "deng-multi"], "T7-013": ["deng-multi"], "T7-014": ["nist-800-122", "owasp-llm02"],
    "X-001": ["halluc-survey", "owasp-llm09"], "X-002": ["halluc-survey", "owasp-llm09"], "X-003": ["react", "trace"], "X-004": ["rfc6585", "owasp-llm10"],
    "X-005": ["anthropic-agents", "owasp-llm10"], "X-006": ["owasp-llm10"], "X-007": ["owasp-llm10"], "X-008": ["halluc-survey"], "X-009": ["sycophancy"],
    "X-010": ["owasp-llm05"], "X-011": ["halluc-survey"], "X-012": ["halluc-survey"], "X-013": ["halluc-survey", "owasp-llm09"], "X-014": ["deng-multi"],
    "X-015": ["eu-ai-act"], "X-016": ["eu-ai-act", "langgraph-interrupts"], "X-017": ["langgraph-interrupts"], "X-018": ["selfconsistency", "chen-mt"],
    "X-019": ["owasp-logging", "owasp-llm02"], "X-020": ["owasp-logging", "nist-800-122"],
    "X-021": ["anthropic-agents", "owasp-llm10"], "X-022": ["anthropic-agents", "owasp-llm06"], "X-023": ["anthropic-agents", "owasp-llm10"],
    "X-024": ["taubench", "trace"],
    "X-025": ["halluc-survey", "taubench"],
    "X-026": ["owasp-llm05", "owasp-logging"],
    "X-027": ["halluc-survey", "taubench"],
    "X-028": ["gdpr", "owasp-llm02"],
    "X-029": ["garg", "taubench"],
    "X-030": ["halluc-survey", "taubench"],
    "X-031": ["halluc-survey", "taubench"],
    "X-032": ["owasp-llm01", "taubench"],
    "X-033": ["halluc-survey", "taubench"],
    "X-034": ["gdpr", "taubench"],
    "X-035": ["taubench", "trace"],
    "X-036": ["halluc-survey", "taubench"],
    "X-101": ["nist-800-122", "owasp-llm02"],
    "X-102": ["owasp-llm02", "memory-survey"],
    "X-103": ["gdpr", "owasp-llm02"],
    "X-104": ["gdpr", "nist-800-122"],
    "X-105": ["greshake", "injecagent", "agentdojo"],
    "X-106": ["owasp-llm06", "saltzer"],
    "X-107": ["owasp-llm02", "owasp-llm07"],
    "X-108": ["owasp-ssrf", "owasp-sqlparam", "owasp-llm05"],
    "X-109": ["owasp-llm10", "helm"],
    "X-110": ["rfc9110", "anthropic-agents"],
    "X-111": ["jacovi", "halluc-survey"],
    "X-112": ["jacovi", "eu-ai-act"],
    "X-113": ["garg", "decodingtrust"],
    "X-114": ["yong-lowres", "deng-multi"],
}


def refs_for(test_id: str) -> list[str]:
    """Ordered, de-duplicated bibliography keys for a test ID (class background + ID-specific + taxonomy credit)."""
    cls = "X" if test_id.startswith("X-") else test_id[:2]
    keys = ID_REFS.get(test_id, []) + CLASS_REFS.get(cls, [])
    if cls != "X":
        keys += ["taxonomy", "catalogue"]
    out: list[str] = []
    for k in keys:
        if k not in out:
            out.append(k)
    return out
