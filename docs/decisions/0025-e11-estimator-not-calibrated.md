# 0025 — E11: the stratified conditional-gap estimator isn't calibrated at pilot size; compare fixed estimands (E12)
Date: 2026-11-17        Status: Accepted. Supersedes the estimator details (strata and pooling) of ADR 0023; the
                        owner's choice of an answer-conditional bar stands.

## Context
E11 (`research/findings/e11_conditional_gap_power.md`) found:
- **Power is fine.** At 1,000 per group, a true gap of 0 is cleared at least 97% of the time.
- **The ADR 0023 estimator isn't calibrated for the gender contrast.** Coverage of its 90% CI is .81 for top-10
  overlap and .86 for top-3 families, with bias from adaptive stratum pooling the likely cause.
- The full-data conditional gender gap is .009–.011 (77% and 74% of the raw gap explained).

## Options
1. Keep the estimator and use a wider CI (e.g. a bootstrap). Bootstrapping doesn't remove the bias from pooling
   coarsely.
2. Raise n. Coverage only reaches .88 at 2,000 per group, and ADR 0024 fixed the study at 1,000.
3. **Compare estimators with a fixed estimand, in a pre-registered E12 (chosen):**
   - regression adjustment (OLS of agreement on group + continuous profile-shape covariates, robust SE);
   - fixed coarse strata defined in advance, with the target defined on the same strata.

## Decision
Option 3. The 1.6 pre-registration waits for E12. The owner's choices stand: an answer-conditional bar
(ADR 0023) and 1,000 per group (ADR 0024).

## Consequences
- ADR 0023's strata and pooling are no longer the planned estimator. E12 picks the replacement.

## Evidence
`research/findings/e11_conditional_gap_power.md`, `e11_conditional_gap_power.json`; ADRs 0023, 0024.
