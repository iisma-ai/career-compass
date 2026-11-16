# E9 — Sample sizes for the fairness audit (1.6), lost-user trial (1.5) and usability pilot (1.7)

Pre-registered 2026-11-16, before `research/feasibility/e9_study_power.py` has been run (ADR 0003). E8 covered the
item pilot's DIF screen; this covers the other v1 research-mode studies (ROADMAP milestones 1.5–1.7). All studies are
adults only (ADR 0014). Gender is self-reported, optional and used only in the offline audit (ADR 0015).

## Pre-registration

```
Question:      How many participants per group / arm do milestones 1.5, 1.6 and 1.7 need?
Data:          data/processed/riasec_people.parquet, age >= 18, complete 48 items (as E8). O*NET 31.0 occupations
               (923) and the r >= .80 families (research/findings/e3_families.csv, family_r80; 101 families).
Product proxy: The 24-item v1 form = first 24 items of best_fixed_order (e4_cat_simulation.json), scored as raw
               scale means (4 items per scale). This is a PROXY for GRM-EAP scoring (L2); it is used only to get
               per-person variances and rates, not to report quality. Full test = mean of all 8 items per scale.
               Matching = matching.score_matrix(method="pearson"); top-3 families = families ranked by their best
               member's score (E5 family_top_lists).
Groups:        gender: female vs male; age: 18-24 vs 25+ (the only age contrast an 18+ study can make).

1.6(a) agreement parity.
  Per-person metrics: A3 = |top-3 families (24-item) n top-3 families (full)| / 3;
                      O10 = top-10 occupation overlap (24-item vs full).
  Bar to show (ROADMAP 1.6a): group difference "within .05" = 90% CI of the difference inside +-.05 (TOST).
  n per group = ceil(2 * (z_.95 + z_.90)^2 * sd^2 / .05^2), sd = pooled per-person SD, true gap assumed 0.
  Simulation check at that n: B = 1000 resamples per group (without replacement), focal group shifted so the group
  means are equal; P(CI inside +-.05) must be >= .78 (.80 minus Monte Carlo error). If not, add 10% to n and repeat.
  The observed gaps in this data are reported descriptively; if an observed gap exceeds .05 the audit is expected to
  FAIL at any n, which is reported as a finding, not as a sample-size problem.
1.6(b) exposure: share of people whose 24-item top-3 families include an R-top family (family's mean OI profile
  peaks on R); same for S-top. n per group so the 95% CI half-width of the gender difference is <= .03, using the
  observed group shares (normal approximation, Wald).
1.6(c) lost-user gate rate: gate = differentiation < 1.0 OR elevation < 2.0 on the 24-item proxy (MODELS L3);
  n per group for a 95% CI half-width of the difference <= .03 (as b).
1.6 recommended n per group = max over (a) A3 and O10, (b), (c), across both gender and age contrasts.

1.5 lost-user trial: gated users only; two arms (usual broad-families flow vs new flow); outcome career decision
  self-efficacy. Smallest effect of interest d = 0.30 (OUR CHOICE; no data on this flow exists); two-sided alpha .05,
  power .80: n per arm = ceil(2 * (z_.975 + z_.80)^2 / d^2) + 1. Sensitivity: d = .20 and .50.
  Screening: total adults to screen = 2 * n_arm / gate rate (adults, 24-item proxy).
1.7 usability: within-person comparison of real families vs a shuffled-families control (random families for the same
  person, order randomised and blinded). Smallest effect of interest d_z = 0.30 (OUR CHOICE); paired, two-sided alpha
  .05, power .80: n = ceil(((z_.975 + z_.80) / d_z)^2 + z_.975^2 / 2). Sensitivity: d_z = .20 and .50.
  Completion time (median <= 6 min) has no data to plan from; it is reported descriptively with a CI.
Verdict:       Planning result: a table of n. No success bar.
```

## Known limits, stated before running
- The 24-item proxy uses raw means, not GRM-EAP; per-person agreement variance may differ slightly.
- OpenPsychometrics is a self-selected online sample (E1). Group shares and the gate rate in a real pilot can differ.
- d = .30 and d_z = .30 are our choices for the smallest effect worth detecting, not evidence about the effects.
- Teen groups can't be audited in an 18+ study; the boys 13–17 gap (E5) stays an offline-only finding until
  research with minors is approved.
