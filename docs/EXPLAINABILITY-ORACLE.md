# Explainability oracle (freeze at M3)

> **Historical (pre-v3).** This page describes code that was removed in v3.1.0; it is kept for the record. The
> implementation is at the `v1.0.0` / `v2.0.0` tags. Current docs: [User Guide](USER-GUIDE.md), [Author Guide](AUTHOR-GUIDE.md).

**Pass:** every step cited in the explanation appears in the recorded tool/handover trace (matching IDs and order constraints).

**Fail:** explanation invents a tool, handover, or state transition that never ran.

**Unverified:** no trace available.

Fluency / prose quality is out of scope for v0.x.

## Related research

Algorithm and paper mapping for each explainability ID (TRACE [Kim et al. 2025], ReAct, TRAJECT-Bench, AgentDiagnose, RAG-style citation faithfulness, OWASP ASI / ISO 42001 / NIST AI RMF notes, and why SHAP/LIME alone are insufficient for multi-step tool agents):

→ **[`EXPLAINABILITY-RESEARCH.md`](EXPLAINABILITY-RESEARCH.md)**

catalogue taxonomy: [10.5281/zenodo.23587407](https://doi.org/10.5281/zenodo.23587407).
