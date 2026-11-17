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
