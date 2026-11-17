# E11 — Is 1,000 per group enough for the answer-conditional parity test?

Pre-registered 2026-11-17, before `research/feasibility/e11_conditional_gap_power.py` has been run (ADR 0003).
ADR 0023 defines the 1.6(a) bar on the answer-conditional gap. ADR 0024 fixes the study at 1,000 adults per group
and asks for this check.

## Pre-registration

```
Question:      At 1,000 adults per group, does the TOST on the answer-conditional gap (90% CI inside +-.05) clear
               with power >= .80 when the true conditional gap is 0, for both agreement metrics and both contrasts?
               Secondary: the pooled-mix conditional gap on the full data (the recomputation ADR 0023 requires).
Data:          data/processed/riasec_people.parquet, age >= 18, complete 48 items. Engine (ADR 0020), v1 24-item form,
               48-item reference. Population: people shown families (24-item gate not triggered).
Metrics:       A3 = top-3 family agreement; O10 = top-10 occupation overlap (24 vs 48 items).
Contrasts:     gender (female vs male); age (18-24 vs 25+).
Estimator (ADR 0023): strata = top-2 Holland code (24-item profile) x differentiation band
               [<1.5, 1.5-2, 2-2.5, 2.5-3, >=3]. Pooling inside each sample: within a top-2 code, merge a band into
               its higher neighbour (the highest band into its lower neighbour) until each cell has >= 10 per group;
               if the whole code still has < 10 in a group, it joins one "other" stratum (its bands merged).
               w_s = pooled share of stratum s (both groups together). mean_g = sum_s w_s * mean_gs.
               gap = mean_1 - mean_0. SE^2 = sum_s w_s^2 (var_1s/n_1s + var_0s/n_0s). 90% CI = gap +- 1.645 SE.
Simulation:    n per group in {500, 750, 1000, 1500, 2000}; R = 1000 replications; seed 42; sampling without
               replacement from the shown population of each group.
               Scenario A (design): the focal group's values are shifted by minus the full-data conditional gap,
                 so the true conditional gap is ~0 while the profile mixes keep their real differences.
               Scenario B (realistic): data as they are (true gap = full-data conditional gap).
               Coverage: share of replications whose 90% CI contains the full-data conditional gap (scenario B).
Decision rule: 1,000 per group is ADEQUATE if, in scenario A, P(cleared) >= .80 for A3 and O10 in both contrasts,
               and coverage is between .85 and .95 for all four. Otherwise report the smallest grid n that meets it
               (or "> 2000"), and the owner decides (ADR 0024).
Verdict:       "adequate" / "not adequate (n needed = X)" / "SE not calibrated; not usable".
```

## Known limits, stated before running
- **Replay data from a self-selected online sample;** the pilot's profile mix may differ.
- **The SE ignores the randomness of the stratum weights and of the pooling.** Coverage checks how much that matters.
- **The shift in scenario A is constant.** The real conditional gap may vary by stratum.
- **Scenario B uses the full-data gap as the truth,** so its power depends on that point estimate.

## Run notes
- Smoke run then full run: 62,530 adults, 54,230 shown families, R = 1000, seed 42, 81 s. No changes after the
  pre-registration commit.

## Results
**Full-data answer-conditional gaps (pooled-mix standardisation, ADR 0023; recomputation that ADR 0023 required):**

| Contrast | Metric | Raw gap | Conditional gap (SE) | Share explained by profile shape | Strata |
|---|---|---|---|---|---|
| Gender (F − M) | top-3 families (A3) | .042 | **.009** (.003) | 77% | 134 |
| Gender | top-10 overlap (O10) | .043 | **.011** (.002) | 74% | 134 |
| Age (18–24 − 25+) | A3 | −.012 | −.012 (.002) | 3% | 140 |
| Age | O10 | −.014 | −.010 (.002) | 27% | 140 |

**Simulation (P(cleared) under A: true gap 0; under B: true gap as observed; coverage of the 90% CI under B):**

| Contrast, metric | n = 500 A / B / cov | 750 | **1,000** | 1,500 | 2,000 |
|---|---|---|---|---|---|
| Gender A3 | .687 / .503 / .826 | .881 / .723 / .838 | **.972 / .871 / .863** | .998 / .982 / .905 | 1.000 / .997 / .906 |
| Gender O10 | .754 / .492 / .702 | .946 / .751 / .752 | **.989 / .917 / .806** | 1.000 / .989 / .830 | 1.000 / .999 / .880 |
| Age A3 | .820 / .684 / .910 | .947 / .870 / .893 | **.992 / .941 / .906** | .999 / .990 / .902 | 1.000 / .999 / .907 |
| Age O10 | .937 / .885 / .901 | .993 / .962 / .875 | **1.000 / .993 / .916** | 1.000 / 1.000 / .903 | 1.000 / 1.000 / .895 |

## Verdict
**"SE not calibrated; not usable"** (pre-registered rule). At 1,000 per group, power in scenario A is ≥ .97 for all
four tests, but coverage for gender O10 (.806) is below .85, and below .85 at every n up to 1,500.

## Interpretation (ours)
- **The low coverage is bias, not only a small SE.** It is confined to the gender contrast, where profile mixes differ
  most, and it shrinks as n grows (.70 → .88). That pattern fits the adaptive pooling: at pilot size, sparse strata
  are merged, so the sample estimate controls for profile shape more coarsely than the full-data estimate and is
  pulled towards the raw gap. The age contrast, with similar mixes, is calibrated.
- **So 1,000 per group is not shown to be inadequate; the ADR 0023 estimator is.** A fixed estimand that does not
  change with sample size (e.g. regression adjustment on continuous profile-shape covariates, or fixed coarse strata
  defined in advance with the full-data target on the same strata) should be compared in a new pre-registered
  experiment (E12) before the 1.6 pre-registration.
- The pooled-mix conditional gaps confirm E10's exploratory result: about three-quarters of the gender gap is profile
  composition. The remaining conditional gaps, .009–.011, are well inside ±.05.

## Caveats
- As listed before the run. In addition, the "truth" for coverage is the full-data estimate with 134–140 strata. It is
  itself only one definition of the conditional gap.
