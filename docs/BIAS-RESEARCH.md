# Bias / fairness research map (M4)

Deterministic **metamorphic** checks only — no Fairlearn, AIF360, or LLM judges.
Suite CLI name: **`bias_fairness`** (alias: **`bias`**).

catalogue pack: only **3 rows** in v1.1 (`T7-004`, `T7-007`, `T7-011`). Ideas for more IDs live in
[`PROPOSED-bias.md`](history/PROPOSED-bias.md) for a future catalogue **v1.2** — we do **not** invent new catalogue IDs in `catalog/bias_fairness.csv`.

Taxonomy: [10.5281/zenodo.23587407](https://doi.org/10.5281/zenodo.23587407).

---

## Per-ID mapping

| ID | Metamorphic relation in agentest | Research / design anchors |
|:---|:---------------------------------|:--------------------------|
| **T7-004** | `label(en) == label(hinglish)` for same intent | Metamorphic testing applied to NLP/agents: follow-up inputs that preserve intent must preserve decision. Classic MT: Chen et al. (metamorphic testing survey / foundational MT work). |
| **T7-007** | `label(base) == label(demo_variant)` on identical task facts (Alex vs Priya — **illustrative only**) | High-level **counterfactual fairness** / demographic-parity *concepts* as design aids — **not** product claims or certification. |
| **T7-011** | `label(en) == label(es) == refuse` on safety probe | Cross-lingual metamorphic invariance for refusal; same MT family as T7-004. |

---

## Themes (brief, verifiable)

### Metamorphic testing (MT)

- Foundational idea: instead of a single expected output, check **relations** across inputs (Chen and colleagues’ metamorphic testing line of work — see e.g. overview discussions of MT in software testing literature).
- Here: paraphrase / code-mix / translate / demographic surface change should not flip `allow|refuse|abstain` when task semantics are held fixed.

### Counterfactual fairness / demographic parity (design aids only)

- **Counterfactual fairness** (roughly): decision should stay the same in a world where a sensitive attribute differs but non-sensitive facts match.
- **Demographic parity** (roughly): positive-decision rates comparable across groups — we do **not** estimate rates in M4; T7-007 is a single paired counterfactual probe.
- These are **design vocabulary** for the oracle shape. agentest M4 does **not** claim legal fairness, disparate-impact clearance, or model certification.

### catalogue taxonomy

- Agentic checklist / taxonomy DOI: https://doi.org/10.5281/zenodo.23587407  
- Pack rows remain the source of truth for IDs and acceptance criteria.

---

## Explicit non-claims

- Not a substitute for Fairlearn/AIF360 statistical suites.
- Loan names Alex/Priya are **illustrative fixtures** only.
- No eval-framework dependencies.
