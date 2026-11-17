# 0023 — The 1.6(a) fairness bar uses the answer-conditional gap; the raw gap is still reported
Date: 2026-11-17        Status: Accepted (owner's decision). Resolves the open question in ADR 0022.

## Context
ADR 0022 left one choice to the owner: whether the fairness bar should use the raw gender gap in agreement between
the short form and the full test, or the gap among people with similar answers. In E10's exploratory analysis the raw
gap was .042. After adjusting for profile shape (top-2 code × differentiation) it was .011. A gender-blind engine can
only control the second, because it treats identical answers identically (ADR 0015).

## Decision (owner, 2026-11-17)
- **Bar for milestone 1.6(a):**
  - Compare groups on the **answer-conditional gap:** each group's mean agreement is standardised to the **pooled**
    sample's distribution of profile-shape strata, then the difference is taken.
  - Strata are the top-2 Holland code × differentiation band: < 1.5, 1.5–2, 2–2.5, 2.5–3, ≥ 3.
  - The population is people who are shown families.
  - Parity is shown when the 90% CI of the conditional gap lies inside ±.05 (TOST), separately for top-3 family
    agreement and for top-10 overlap.
- **Always reported, not part of the bar:**
  - the raw gap with a 95% CI;
  - the share of the gap explained by profile shape;
  - stratum sizes. Strata with fewer than 10 people per group are pooled into a neighbouring differentiation band and
    the pooling is listed.
- Both groups are standardised to the pooled mix. This is symmetric and doesn't treat either gender as the reference.
  E10's post-hoc analysis instead reweighted men to women's mix, so the 1.6 pre-registration must recompute the
  exploratory numbers with the pooled method.
- The sample size for 1.6(a) has to be recomputed for the conditional estimator when 1.6 is pre-registered. E9's
  580-per-group figure applies to the raw gap only.
- Unchanged: 1.6(b) exposure, (c) gate rate and (d) the gender-blind code check. The S-top precision question (2,052
  vs about 1,000 per group, ADR 0019) is still open.

## Consequences
- ROADMAP 1.6, the protocol draft (§8), STATUS and CLAUDE.md are updated.
- Risk: conditioning on profile shape could hide a real disadvantage if the profile shape itself were produced unfairly
  by the items. Item-level DIF screening (ADR 0018) and reporting the raw gap are the safeguards.

## Evidence
ADR 0022; `research/findings/e10_gap_mitigation.md` (post-hoc 2), `e10_posthoc.json`; ADRs 0015, 0019.
