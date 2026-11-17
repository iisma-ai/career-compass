# 0026 — The 1.6(a) answer-conditional gap is estimated by regression adjustment (REG)
Date: 2026-11-17        Status: Accepted. Completes ADR 0025; implements the owner's choice in ADR 0023.

## Context
E12 (`research/findings/e12_conditional_estimator.md`) compared two estimators of the answer-conditional gap, each with
an estimand that doesn't change with sample size. Both were calibrated at 1,000 per group (coverage .89–.92) with power
≥ .98. The pre-registered rule picks the estimator that explains more of the raw gender gap: REG, 81% vs 65% for FIX.

## Decision
For the 1.6 study, the 1.6(a) gap is estimated by **REG**:
- **Model:** OLS of the agreement metric on 1, group, the shape-centred 24-item profile (5 terms), its squares
  (6 terms), elevation, differentiation and differentiation².
- **Gap and test:** gap = the group coefficient; HC1 robust SE; parity if the 90% CI lies inside ±.05 (TOST).
- **Population:** people shown families. Run separately for top-3 family agreement and top-10 overlap, and for the
  gender and age contrasts.
- **Also reported:**
  - the raw gap with a 95% CI (ADR 0023);
  - FIX (18 fixed strata) as a sensitivity analysis;
  - the share of the raw gap explained.
- **Sample size:** 1,000 per group is confirmed adequate for this test (E12). Expected power is ≥ .93 if the pilot
  resembles this data.

## Consequences
- The 1.6 pre-registration can now be written once the study exists. The protocol draft §8 and ROADMAP 1.6 name REG.
- Profile shape is a covariate in the audit only, never in the product (ADR 0015 is unaffected).

## Evidence
`research/findings/e12_conditional_estimator.md`, `e12_conditional_estimator.json`; ADRs 0023–0025.
