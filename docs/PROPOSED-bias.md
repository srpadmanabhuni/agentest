# PROPOSED bias expansion (catalogue v1.2 — draft only)

> **Historical (pre-v3).** This page describes code that was removed in v3.1.0; it is kept for the record. The
> implementation is at the `v1.0.0` / `v2.0.0` tags. Current docs: [User Guide](USER-GUIDE.md), [Author Guide](AUTHOR-GUIDE.md).

**Do not** add these IDs to `catalog/bias_fairness.csv` until the catalogue dataset is bumped.
This file tracks solo/v1.2 ideas so M4 stays faithful to the three published rows.

Possible future metamorphic probes (examples):

1. Gendered pronoun swap on identical support-ticket facts → same escalate/resolve label  
2. Regional English variety (en-IN vs en-US) policy question → same allow/refuse  
3. Name-only swap on hiring *screening rubric* facts (still illustrative) → same shortlist label  
4. k-run rate bound across cohorts (requires larger fixtures; still non-certifying)

When promoting: assign new catalogue IDs in the catalogue first, pin revision in `catalog/VERSION`, then implement CaseSpecs.
