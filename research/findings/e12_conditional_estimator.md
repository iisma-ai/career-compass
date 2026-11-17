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

## Run notes
- Smoke run then full run: 54,230 adults shown families, R = 1000, seed 42, 31 s. No changes after the
  pre-registration commit.

## Results
**Full-data targets** (raw gap → conditional gap; share of raw gap explained):

| Contrast, metric | Raw | REG | FIX |
|---|---|---|---|
| Gender A3 | .042 | **.009** (78%) | .014 (67%) |
| Gender O10 | .043 | **.007** (83%) | .016 (62%) |
| Age A3 | −.012 | −.007 (42%) | −.010 (13%) |
| Age O10 | −.014 | −.009 (32%) | −.010 (24%) |

**At 1,000 per group:** coverage of the 90% CI / P(cleared | target 0) / P(cleared | as observed) / mean bias.

| Contrast, metric | REG | FIX |
|---|---|---|
| Gender A3 | .896 / .980 / .927 / +.001 | .891 / .982 / .904 / −.000 |
| Gender O10 | .910 / .999 / .991 / +.002 | .906 / .999 / .966 / −.000 |
| Age A3 | .910 / .997 / .977 / −.000 | .910 / .995 / .959 / −.001 |
| Age O10 | .919 / 1.000 / .998 / +.000 | .913 / .998 / .997 / +.000 |

FIX dropped a stratum (empty for one group) in 18% of gender samples at n = 1,000 (about 50% at n = 500). REG coverage
is .89–.92 at every n in {500, 1000, 2000}. Full table in `e12_conditional_estimator.json`.

## Verdict
**Both estimators qualify. Chosen: REG** by the pre-registered rule, because it explains more of the raw gender gap
(81% vs 65%, mean of A3 and O10).

## Interpretation (ours)
- Unlike E11's adaptive pooling, a fixed estimand gives calibrated CIs at 1,000 per group. So the owner's plan
  (answer-conditional bar, 1,000 per group) is feasible with REG.
- On this data the conditional gender gap is about .007–.009. If the pilot resembles it, 1.6(a) is expected to pass
  (P ≥ .93 at 1,000 per group).
- REG's quantity is a model-based adjustment: the gap among people with the same profile shape, elevation and
  differentiation, under a quadratic linear model. The 1.6 report should also show the raw gap (already required by
  ADR 0023) and FIX as a sensitivity check.

## Caveats
- Replay data, self-selected sample, model-defined estimand.
- The 24-item profile used as covariate is the same profile whose agreement is measured, so the adjustment is for
  "answers as scored", not for latent interests.
