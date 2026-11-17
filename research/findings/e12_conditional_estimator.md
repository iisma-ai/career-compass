# E12 — A calibrated estimator for the answer-conditional gap at 1,000 per group

Pre-registered 2026-11-17, before `research/feasibility/e12_conditional_estimator.py` has been run (ADR 0003, ADR 0025).

## Pre-registration

```
Question:      Which answer-conditional gap estimator, with an estimand that doesn't change with sample size, gives
               calibrated 90% CIs and adequate power at 1,000 adults per group?
Data, metrics, contrasts, population: as E11 (adults, complete items, engine, v1 24-item form vs 48-item reference,
               people shown families; A3 and O10; gender and age).
Covariates (all from the 24-item profile p, 1-5 scale): shape c = p - mean(p) (6 values, one dropped as redundant),
               elevation, differentiation.
Estimators:
  REG  OLS: y ~ 1 + group + c_R..c_E (5) + c_R^2..c_C^2 (6) + elevation + differentiation + differentiation^2.
       Gap = group coefficient; HC1 robust SE.
       Target = the same coefficient fitted on the full shown population.
  FIX  Fixed coarse strata: top-1 letter (6) x differentiation band [< 1.5, 1.5-2.5, >= 2.5] = 18 strata, no
       adaptive pooling. Pooled-mix standardisation and SE as in E11. If a stratum has no member of one group in a
       sample, it is dropped from both groups' weighting in that sample (frequency reported).
       Target = the same estimator on the full shown population.
Simulation:    n = 1000 per group (ADR 0024); also 500 and 2000 for context. R = 1000, seed 42. Scenario A (target
               shifted to 0 by subtracting the full-data target from the focal group), scenario B (as observed).
Metrics:       coverage of the 90% CI for the estimator's own target (B); P(cleared, TOST +-.05) under A and B;
               mean bias (B: mean estimate - target); full-data share of the raw gender gap explained.
Selection rule: an estimator QUALIFIES if, at n = 1000, coverage is in [.85, .95] and P(cleared | A) >= .80 for
               all four tests (2 metrics x 2 contrasts). Among qualifiers, choose the one that explains the larger
               share of the raw gender gap on the full data (averaged over A3 and O10): the more complete adjustment.
               If none qualifies: "none calibrated", and the 1.6 plan goes back to the owner.
```

## Known limits, stated before running
- **REG's "conditional gap" is a model-defined quantity:** a linear projection. Quadratic terms limit misspecification
  but don't remove it.
- **FIX's coarse strata adjust less completely than E11's 134 strata.** That trade-off is the reason for the
  selection rule.
- **Replay data, self-selected sample** (as E8–E11).
