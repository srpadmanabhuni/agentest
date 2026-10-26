#!/usr/bin/env python3
"""(Re)generate src/agentest/standards/standards_map.yaml: catalogue ID -> external standard references.

Vocabulary (VOCAB) holds only IDs verified against the primary source (see docs/standards/STANDARDS-MAP.md).
Mapping is by catalogue class plus title keywords; review the output by hand before committing.
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

from agentest.real.ids import ALL_IDS, catalogue, what

OUT = Path(__file__).resolve().parents[1] / "src" / "agentest" / "standards" / "standards_map.yaml"

VOCAB = {
    "owasp_llm_2025": {"LLM01": "Prompt Injection", "LLM02": "Sensitive Information Disclosure", "LLM05": "Improper Output Handling",
                       "LLM06": "Excessive Agency", "LLM07": "System Prompt Leakage", "LLM08": "Vector and Embedding Weaknesses",
                       "LLM09": "Misinformation", "LLM10": "Unbounded Consumption"},
    "owasp_agentic_threats_v1": {"T1": "Memory Poisoning", "T2": "Tool Misuse", "T3": "Privilege Compromise", "T4": "Resource Overload",
                                 "T5": "Cascading Hallucination Attacks", "T6": "Intent Breaking & Goal Manipulation",
                                 "T7": "Misaligned & Deceptive Behaviors", "T8": "Repudiation & Untraceability",
                                 "T9": "Identity Spoofing & Impersonation", "T10": "Overwhelming Human in the Loop",
                                 "T11": "Unexpected RCE and Code Attacks", "T12": "Agent Communication Poisoning",
                                 "T13": "Rogue Agents in Multi-Agent Systems", "T15": "Human Manipulation"},
    "nist_ai_rmf": {"MEASURE 2.5": "valid and reliable", "MEASURE 2.6": "safe", "MEASURE 2.7": "secure and resilient",
                    "MEASURE 2.8": "transparency and accountability", "MEASURE 2.9": "explained and interpretable",
                    "MEASURE 2.10": "privacy risk", "MEASURE 2.11": "fairness and bias"},
    "nist_ai_600_1": {"Confabulation": "NIST AI 600-1 GAI risk", "Data Privacy": "NIST AI 600-1 GAI risk", "Harmful Bias and Homogenization": "NIST AI 600-1 GAI risk",
                      "Human-AI Configuration": "NIST AI 600-1 GAI risk", "Information Integrity": "NIST AI 600-1 GAI risk", "Information Security": "NIST AI 600-1 GAI risk"},
    "iso_42001_annex_a": {"A.5.4": "Assessing AI system impact on individuals or groups of individuals", "A.6.2.4": "AI system verification and validation",
                          "A.6.2.6": "AI system operation and monitoring", "A.6.2.8": "AI system recording of event logs",
                          "A.8.2": "System documentation and information for users", "A.9.2": "Processes for responsible use of AI systems"},
    "mitre_atlas": {"AML.T0051.000": "LLM Prompt Injection: Direct", "AML.T0051.001": "LLM Prompt Injection: Indirect", "AML.T0054": "LLM Jailbreak",
                    "AML.T0057": "LLM Data Leakage", "AML.T0029": "Denial of AI Service", "AML.T0048": "External Harms",
                    "AML.T0053": "AI Agent Tool Invocation", "AML.T0070": "RAG Poisoning", "AML.T0080": "AI Agent Context Poisoning",
                    "AML.T0086": "Exfiltration via AI Agent Tool Invocation"},
}

CLASS = {
    "T1": dict(owasp_llm_2025=["LLM06"], owasp_agentic_threats_v1=["T7"], nist_ai_rmf=["MEASURE 2.5"], iso_42001_annex_a=["A.6.2.4"], mitre_atlas=[]),
    "T2": dict(owasp_llm_2025=["LLM06"], owasp_agentic_threats_v1=["T2", "T6"], nist_ai_rmf=["MEASURE 2.6"], iso_42001_annex_a=["A.6.2.4", "A.9.2"], mitre_atlas=["AML.T0053"]),
    "T3": dict(owasp_llm_2025=["LLM06"], owasp_agentic_threats_v1=["T3", "T9"], nist_ai_rmf=["MEASURE 2.7"], iso_42001_annex_a=["A.9.2"], mitre_atlas=["AML.T0053"]),
    "T4": dict(owasp_llm_2025=["LLM01"], owasp_agentic_threats_v1=["T2", "T6"], nist_ai_rmf=["MEASURE 2.7"], iso_42001_annex_a=["A.6.2.4"], mitre_atlas=["AML.T0051.001"]),
    "T5": dict(owasp_llm_2025=["LLM06"], owasp_agentic_threats_v1=["T2", "T3"], nist_ai_rmf=["MEASURE 2.7"], iso_42001_annex_a=["A.9.2"], mitre_atlas=["AML.T0053"]),
    "T6": dict(owasp_llm_2025=["LLM02"], owasp_agentic_threats_v1=["T1"], nist_ai_rmf=["MEASURE 2.5"], iso_42001_annex_a=["A.6.2.4"], mitre_atlas=["AML.T0080"]),
    "T7": dict(owasp_llm_2025=["LLM09"], owasp_agentic_threats_v1=["T7"], nist_ai_rmf=["MEASURE 2.5"], iso_42001_annex_a=["A.6.2.4"], mitre_atlas=[]),
    "X": dict(owasp_llm_2025=[], owasp_agentic_threats_v1=[], nist_ai_rmf=["MEASURE 2.5"], iso_42001_annex_a=["A.6.2.6"], mitre_atlas=[]),
}

KEYWORDS = [  # (regex over title, family, refs)
    (r"PII|privacy|consent|masking|secret|email\)", "owasp_llm_2025", ["LLM02"]), (r"PII|privacy|consent|masking|secret", "nist_ai_rmf", ["MEASURE 2.10"]),
    (r"PII|privacy|consent|secret", "nist_ai_600_1", ["Data Privacy"]), (r"PII|secret|canary|exfiltrat", "mitre_atlas", ["AML.T0057"]),
    (r"exfiltrat|send PII|URL|webhook", "mitre_atlas", ["AML.T0086"]), (r"RAG|retrieved", "owasp_llm_2025", ["LLM08"]), (r"RAG|retrieved", "mitre_atlas", ["AML.T0070"]),
    (r"inject|Ignore|breakout|directive", "nist_ai_600_1", ["Information Security"]),
    (r"approval|human|Human|gate|silence|ambiguous", "owasp_agentic_threats_v1", ["T10"]), (r"approval|human|Human|gate", "nist_ai_600_1", ["Human-AI Configuration"]),
    (r"impersonat|actor|attributable|ambient|tenant|Agent-to-agent|Receiving agent", "owasp_agentic_threats_v1", ["T9", "T12"]),
    (r"reason|log|trace|audit|Audit|timestamps|attributable", "owasp_agentic_threats_v1", ["T8"]), (r"reason|log|trace|audit|Audit|timestamps", "iso_42001_annex_a", ["A.6.2.8"]),
    (r"reason|explanation|Explanation|memory items|Refusals give", "nist_ai_rmf", ["MEASURE 2.9"]), (r"reason|explanation|Explanation|transparen", "nist_ai_rmf", ["MEASURE 2.8"]),
    (r"Demographic|language|Hinglish|Spanish|Hindi|Tamil|Multilingual", "nist_ai_rmf", ["MEASURE 2.11"]),
    (r"Demographic|language|Hinglish|Spanish|Hindi|Tamil|Multilingual", "nist_ai_600_1", ["Harmful Bias and Homogenization"]),
    (r"Demographic|language|Hinglish|Spanish|Hindi|Tamil|Multilingual", "iso_42001_annex_a", ["A.5.4"]),
    (r"[Rr]efusal", "owasp_llm_2025", ["LLM01"]), (r"[Rr]efusal", "mitre_atlas", ["AML.T0054"]),
    (r"invented|fidelity|False completion|claim|success flag|Explanation|polarity|Factual", "nist_ai_600_1", ["Confabulation"]),
    (r"invented|fidelity|False completion|claim|success flag", "owasp_agentic_threats_v1", ["T5"]), (r"invented|fidelity", "owasp_llm_2025", ["LLM09"]),
    (r"budget|storm|burst|Rate-limited|Latency|Cost|Step budget", "owasp_llm_2025", ["LLM10"]), (r"budget|storm|burst|Rate-limited|Latency|Cost|Step budget", "owasp_agentic_threats_v1", ["T4"]),
    (r"budget|storm|burst|Rate-limited|Latency|Cost|Step budget", "mitre_atlas", ["AML.T0029"]),
    (r"SQL|Path traversal|formula|shell|Structured output|Enum|enum", "owasp_llm_2025", ["LLM05"]), (r"SQL|Path traversal|formula|shell", "owasp_agentic_threats_v1", ["T11"]),
    (r"System policy memory|policy memory", "owasp_llm_2025", ["LLM07"]), (r"memory|Memory|turn", "owasp_agentic_threats_v1", ["T1"]),
    (r"payments|disbursement|irreversible|Irreversible", "mitre_atlas", ["AML.T0048"]), (r"Multi-hop|Cross-file|handover|Handover", "owasp_agentic_threats_v1", ["T12"]),
    (r"Every tool call has reason|reason code|Approval requests carry", "iso_42001_annex_a", ["A.8.2"]),
]

DIRECT = {"T4-001", "T4-011"}  # user-turn injection also covers direct prompt injection


def build() -> dict:
    cat = catalogue()
    out = {}
    for i in ALL_IDS:
        cls = i.split("-")[0]
        m = {k: list(v) for k, v in CLASS[cls].items()}
        m.setdefault("nist_ai_600_1", [])
        title = (cat.get(i, {}).get("title") or what(i))
        for rx, fam, refs in KEYWORDS:
            if re.search(rx, title):
                m[fam] = sorted(set(m[fam]) | set(refs))
        if i in DIRECT:
            m["mitre_atlas"] = sorted(set(m["mitre_atlas"]) | {"AML.T0051.000"})
        out[i] = {k: sorted(set(v)) for k, v in m.items() if v}
    return out


if __name__ == "__main__":
    hdr = ("# Catalogue ID -> external standard references (generated by scripts/gen_standards_map.py, reviewed by hand).\n"
           "# Only IDs in the `vocabulary` block are allowed; tests/test_standards_map.py enforces it.\n")
    OUT.write_text(hdr + yaml.safe_dump({"vocabulary": VOCAB, "map": build()}, sort_keys=False, allow_unicode=True, width=200))
    print(f"wrote {OUT}")
