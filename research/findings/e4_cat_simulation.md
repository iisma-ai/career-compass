# E4 — Adaptive questionnaire (CAT) simulation: how few questions do we need?

Pre-registered 2026-11-15, before running `research/feasibility/e4_cat_simulation.py`. Before this was written, only
column names, missing-value coding, the gender codes and one smoke fit of girth `grm_mml` on a random 56k sample of the
R items had been run, to check the tool's speed and parameterisation. No CAT, no split and no E4 metric had been computed.
Script: `research/feasibility/e4_cat_simulation.py` (`--seed 42`, `--quick` for a smoke run, `--table incl_shared` for
the robustness run). Outputs: `research/findings/e4_cat_simulation.json`, `research/findings/e4_*.png`.

## Pre-registration

```
Question:      How many adaptively chosen items reproduce (a) the full 48-item RIASEC scale scores and (b) the
               full-test top-10 O*NET occupation list, and is the adaptivity worth it compared with the best
               fixed short form of the same length?
Hypothesis:    With six per-scale GRMs, EAP scoring and a correlated prior, about 3-4 items per scale (18-24 in
               total) give r >= .90 with the full-bank theta. Basis: interest CATs reached usable precision at
               about 4 items per area with SE < .50 (Simsek & Tavsancil 2022, level C), and with 8 items per scale
               (alpha .83-.90, research/findings/e1_data_audit.md) a scale is close to saturated after 4-5 good
               items. Top-10 occupation overlap is expected to be the harder bar, because the 923 O*NET profiles
               are dense and small profile changes reorder the top 10 (E5 measures that ceiling in parallel).
               With only 8 items per scale the adaptive advantage over a fixed best-k form should be small:
               adaptive gains shrink at short test lengths and small banks (note 02, `[UNVERIFIED]` summary),
               and the bank leaves little to choose from (with 3 items per scale already used, the CAT picks
               from only 5 left per scale). Expect the CAT to beat random-k clearly, and best-fixed-k only marginally.
Data:          data/processed/riasec_people.parquet (n = 80,085; 0.15% item cells missing, kept as missing).
               Split 70/30 stratified by gender (male / female / other+missing) x age band (13-17, 18-24, 25+),
               seed 42. Calibration (about 56,060) is used only for item parameters and the prior. Simulation
               (about 24,025) is used only for replay.
               O*NET: data/processed/onet_occupations.parquet (923 occupations, OI profiles R..C on 1-7).
               Robustness: data/processed/riasec_people_incl_shared_network.parquet (115,974), headline numbers
               only, with its own 70/30 split and recalibration.
Method:        Calibration: one unidimensional logistic GRM per scale, P(X >= k) = 1 / (1 + exp(-a(theta - b_k))),
               by MML with girth 0.8.0 grm_mml (N(0,1) latent, quadrature), with convergence checked against our
               own marginal log-likelihood. Low discrimination flag: a < 0.65. Compared with E2 flags
               (weak R1, A7, S4; gender DIF E4, R3, I8, R4, E1). Local dependence: Yen's Q3 on EAP residuals,
               flagged if Q3 - mean(Q3) > .20 (the I medical/lab vs nature/animal split is the prior suspect).
               Latent 6x6 correlation matrix: pairwise ML on the calibration set given the fixed GRM item
               parameters (bivariate-normal latent, product quadrature). It is compared with E2's CFA phi and
               used as the prior covariance.
               theta estimation: EAP on a 1-D quadrature grid per scale (-5..5, 81 points).
                 Independent prior: N(0,1) per scale.
                 Correlated prior: Gaussian (expectation-propagation-style) approximation. Each scale's
                 likelihood becomes a Gaussian site (moment-matched from its N(0,1) posterior) and is combined
                 with the 6-D N(0, Phi) prior. The final per-scale estimate is the exact grid posterior of that
                 scale under its Gaussian cavity prior from the other five scales.
               Engines (all replay each simulation person's REAL recorded answers; a missing answer removes the
               item from that person's pool without counting as administered):
                 A  max Fisher information at the current independent-prior EAP, round-robin across scales
                    (R, I, A, S, E, C). Starter = the most informative item at theta = 0 for each scale.
                 B  correlated 6-D prior. Selection = maximum expected reduction in the trace of the posterior
                    covariance (exact 1-D preposterior variance on the grid for the item's scale, propagated to
                    the other scales through the Gaussian posterior regression). Same 6 starter items as A.
                 C  B plus ranking-aware stopping: stop when the top-10 occupation SET is identical at the
                    current item and at each of the previous 3 items, with a minimum of 12 items and caps 20/30/40.
                    C-lit (literature design, note 02): stop when the posterior SD < .40 on the person's current top-3
                    scales AND the top-10 has been stable for 3 items, minimum 12, cap 40.
                 Baselines: (i) random fixed k, balanced round-robin across scales, random item order within a
                 scale drawn per person; (ii) best fixed k by discrimination (round-robin; within a scale in
                 descending a); (iii) O*NET Mini-IP-like = the 5 highest-a items per scale (30 items), scored
                 both by EAP and by plain raw item means, since we do not have the Mini-IP items; (iv) the full
                 48 items (reference). Fixed forms are scored with the correlated-prior EAP (primary) and the
                 independent EAP. The comparison uses whichever scoring is better for the fixed form.
                 Variants: the full bank (48) vs the bank without the 8 flagged items (40: R1, A7, S4, E4, R3, I8,
                 R4, E1), with the same calibration. The reference stays the full 48-item test. Agreement with a
                 40-item reference is also reported.
               Fixed-length curves: k = 6..48 (engines A and B run to exhaustion; the state is recorded after every
               item). Variable length: posterior SE thresholds .30 / .40 / .50 (stop when every scale's SE is
               below the threshold; engine A skips scales already below it), each with caps 20 / 30 / 40 and no
               cap, plus the C rules above.
               Synthetic check: 10,000 simulees with theta ~ N(0, Phi), with responses generated from the
               calibrated GRMs (complete data). Run A, B and the fixed forms; report agreement with the true theta and
               with the simulee's own full-test score.
Profile used for matching:
               Reference = the person's observed full-test raw scale means (1-5), as the full product test would
               score them. CAT profile = the predicted full-test raw scale mean: mean over the scale's 8 items of
               the observed answer if administered, else its posterior expected score E[X_j | answers]. This
               keeps both profiles on the raw metric, so the comparison is not distorted by the theta
               standardisation. Secondary: theta-metric ranking vs the theta_full ranking.
               Matching = Pearson correlation between the 6-scale person profile and each occupation's OI
               profile (O*NET-style baseline). Top-k by descending r. matching.py (built in parallel by the
               ml-experimenter) is used for cosine_centered if it exists; otherwise an equivalent minimal Pearson
               function is in the script.
Baselines:     random-k (trivial), best-fixed-k by a, Mini-IP-like 30 (raw and EAP), full test (reference).
Metrics:       Per scale and averaged over the 6 scales: r(theta_CAT, theta_full) where theta_full is the
               independent-prior EAP on all answered items, and r(predicted raw, observed full raw).
               Top-10 overlap |T10_CAT intersect T10_full| / 10, top-3 overlap, Holland agreement (first letter,
               counting full-test ties as agreement; same top-3 set; same ordered top-3 code), and Kendall tau-b /
               NDCG@10 is NOT computed (dropped to save time; top-3/top-10 overlap carry the ranking signal).
               Items used: mean, median, P10/P90, distribution.
               Breakdowns: gender x age band (male/female x 13-17/18-24/25+); flat (full-test differentiation
               < 1.0, E1 threshold) vs differentiated (>= 1.0).
               Bootstrap: 1,000 person resamples (seed 42) for headline numbers and for the paired CAT minus
               best-fixed differences.
```

### Success bars (fixed now; not to be changed after seeing results)

**Primary (skill bar).** Judged on the simulation set, main table, full bank or reduced bank (whichever is better,
named in the verdict):
- **Proven**: some engine configuration that never uses more than 20 items (fixed k <= 20, or a variable-length rule
  with cap <= 20) reaches **mean r(theta_CAT, theta_full) >= .90** (mean over the 6 scales) **AND mean top-10
  overlap >= 70%** with the full-test ranking. The same configuration must meet both.
- **Promising**: the r bar is met within <= 20 items but top-10 overlap is 60-70%, OR both bars are met only at
  21-30 items.
- **Not viable**: neither of the above.
- Reported against this bar (not gating): r(predicted raw, observed raw); whether the bar is met in every
  gender x age cell; the gap to the E5 noise ceiling.

**Literature-based design (reported, not gating).** The note-02 design: median 24-30 items, cap 40, SE/SD .35-.45
on the top 3 dimensions plus 3-item top-10 stability. We report the median items used and the accuracy of the rules
that land in that range (C-lit, SE .30 / .40 with cap 40).

**Secondary (complexity justification).** The best adaptive engine (A, B or C) at equal length k = 20 (and at k = 12
and 30 for context) must beat the **best fixed short form** (best-k by discrimination, with its better scoring) by
**>= .03 in mean r(theta, theta_full) OR >= 5 percentage points in mean top-10 overlap**, with the paired bootstrap
95% CI of that difference excluding 0. For variable-length rules, the comparison is against the best fixed form whose
length equals the rule's mean items used (rounded). If this fails, the v1 recommendation defaults to a fixed short form
(possibly with an adaptive "lost user" extension), because the CAT's complexity is not justified by accuracy alone.

### Additions made after the pre-registration (declared, not gating)
1. **Calibration estimator.** girth `grm_mml` fits thresholds by matching marginal counts and stops when the change in a
   is below 1e-3, so a "more iterations" check means nothing. A smoke test showed girth's a are about 3-5% too low. The
   final item parameters therefore come from my own Bock-Aitkin EM (exact MML on the 81-point grid), started from girth's
   solution. Both sets are in the JSON.
2. **Family-level metrics** (added after the quick run, at the coordinator's request, once E5 had shown that the full
   test itself is unstable at occupation level): symmetric family hit rate for the top-10 and **top-3 family** overlap
   (each family scored by its best member, as in E5). E3 families come from `research/findings/e3_families.csv`
   (r >= .80: 101 families; r >= .90: 172).
3. **Post-hoc stopping-rule check** (`research/feasibility/e4_posthoc_stopping.py`, see Results 6). It was added because
   agreement with the full test jumps to 1.0 at 48 items (part-whole), which biases the pre-registered secondary comparison
   for variable-length rules.

---

## Results

Run: `.venv/Scripts/python -I research/feasibility/e4_cat_simulation.py --seed 42` (36 min). Robustness:
`--table incl_shared` (26 min). Post hoc: `research/feasibility/e4_posthoc_stopping.py` (12 min). Raw output:
`e4_cat_simulation.json`, `e4_cat_simulation_incl_shared.json`, `e4_posthoc_stopping.json`. Split: calibration
56,060 and simulation **24,025** (1,743 missing item cells). Sample caveats are as in E1: self-selected, 67% female,
median age 23, about 50% US. All numbers are evidence level E. Every CI below is a 95% percentile bootstrap over
simulation people (B = 1,000; 500 for the variable-length rules) and is about +/- .003 at this n, unless stated otherwise.
I use "top-10" for mean top-10 occupation overlap with the full-test list (Pearson, `matching.py`) and "top-3 fam" for
top-3 family overlap (r >= .80 families).

### 1. Calibration (six logistic GRMs)
- Convergence: EM raised the marginal log-likelihood over girth by 96-182 per scale. Max |delta a| was .06-.11 and
  max |delta b| .05-.11. Thresholds are ordered for all 48 items.
- **No item has a < 0.65.** The lowest discriminations are **A7 .93, S4 .96, R1 1.15, S1 1.21, E4 1.30, S2 1.33, I8 1.39**.
  The highest are I5 3.77, I7 3.24, C8 3.02, C3 2.94, I3 2.69 and R5 2.66.
- E2's three weak items (R1, A7, S4) are the three lowest-a items in their own scales. Among the gender-DIF items, E4 and
  I8 are the lowest-a in their scales and E1 is mid-range. R3 (1.70) and R4 (2.04) discriminate well, so their problem is
  DIF, not weak measurement.
- Information is not evenly spread. R information is 0.7 at theta = -2 and 10.5 at 0. This is the floor effect: the
  model cannot separate people who dislike all R activities. I and S are most informative at or below the mean, and R
  and C above it (`scale_info_at` in the JSON).
- Empirical reliability of the full-test EAP: R .86, I .91, A .87, S .87, E .85, C .90. The full-test posterior SE
  averages .30 (I) to .38 (E). **No simulee reaches SE < .30 on all six scales, even with all 48 items, and 54% never
  reach SE < .40.**
- **Local dependence** (Yen's Q3; mean Q3 is about -.12 per scale; flag = Q3 more than .20 above the mean). The pairs well
  above the cut are in I: I2-I3 .33, I2-I6 .29, I6-I8 .23. These are the nature/animal facet E2 found, plus A3-A8 .25,
  R2-R8 .20 and C5-C6 .20. The I scale's information is therefore somewhat overstated, which E2 predicted.
- **Latent correlations** (pairwise ML): E-C .60, R-C .54, S-E .42, R-E .38, R-I .35, I-A .34, A-S .34, A-E .33, then
  <= .24. They agree with E2's CFA phi (r = .996 across the 15 pairs; max |diff| .05). In the incl-shared table they are
  slightly higher (max |diff| from E2 .11).

### 2. Fixed-length curves (`e4_items_vs_r.png`, `e4_items_vs_top10.png`, `e4_items_vs_top3families.png`)

| k | Engine | r(theta, theta_full) | r(raw) | top-10 | top-3 fam (r>=.80) | fam hit (r>=.90) | 1st letter | exact 3-letter |
|---|---|---|---|---|---|---|---|---|
| 12 | A max-info | .907 | .878 | .441 | .500 | .582 | .724 | .267 |
| 12 | **B corr. prior** | **.915** | .886 | .441 | .505 | .583 | .730 | .277 |
| 12 | best fixed (corr.) | .909 | .885 | .439 | .500 | .581 | .725 | .273 |
| 12 | random fixed | .854 | .861 | .395 | .457 | .534 | .691 | .232 |
| 20 | A | .954 | .930 | .542 | .596 | .683 | .797 | .362 |
| 20 | **B** | **.957** [.956, .957] | .932 | **.537** [.533, .540] | **.595** [.591, .598] | .678 | .797 | .361 |
| 20 | best fixed (corr.) | .952 | .934 | .543 | .599 | .685 | .800 | .368 |
| 20 | random fixed | .916 | .922 | .508 | .561 | .650 | .770 | .334 |
| 24 | B | .968 | .948 | .583 | .634 | .720 | .825 | .409 |
| 24 | best fixed (corr.) | .965 | .948 | .586 | .637 | .724 | .828 | .412 |
| 30 | A | .982 | .964 | .645 | .688 | .774 | .860 | .473 |
| 30 | B | .980 | .964 | .639 | .681 | .769 | .859 | .467 |
| 30 | best fixed (corr.) | .977 | .963 | .639 | .682 | .770 | .859 | .468 |
| 30 | Mini-IP-like (5 best-a per scale, raw means, no IRT) | (.960)* | .960 | .622 | .664 | .753 | .834 | .447 |
| 48 | full test (reference) | 1 | 1 | 1 | 1 | 1 | 1 | 1 |

\* The raw mean correlated with theta_full.

- **r >= .90 needs about 12 items**: B .915 at 12 and .897 at 10; best fixed .909 at 12; random needs about 18.
  Per scale at k = 20 (B): R .96, I .96, A .96, S .96, **E .94** (lowest, as expected from E's lower alpha) and C .96.
- **Top-10 overlap rises almost linearly with k and never reaches .70 before about 36 items** (A .70 at 36; B .70 at 36).
  At 44 items it is still only .82, and it jumps to 1.0 at 48 because the reference *is* those 48 answers.
- Scoring with the correlated prior adds +.003 to +.016 in r at k <= 12 and nothing at k >= 24. It never improves top-10
  overlap meaningfully.
- cosine_centered gives lower agreement throughout (B k = 20: .434 vs .537 for Pearson). This mirrors E5, where it was the
  least stable method.
- Reduced bank (without the 8 flagged items) vs the full bank, B at k = 20: r .956 vs .957, top-10 .534 vs .537. The
  flagged items cost nothing because the CAT almost never picks them (section 5). Dropping all 8 also changes the
  "full test" itself: the 40-item full test vs the 48-item full test gives r .992 and top-10 only .73. Even the reference
  list depends heavily on which items are in it.

### 3. Variable-length rules (`e4_items_used_hist.png`; engine B unless stated otherwise)

| Rule | Items mean / median [P10-P90] | r | top-10 | top-3 fam | 1st letter |
|---|---|---|---|---|---|
| SE < .50, no cap | 21.0 / 15 [10-48] | .953 | .554 | .602 | .788 |
| SE < .50, cap 20 | 15.6 / 15 [10-20] | .941 | .481 | .541 | .756 |
| SE < .40, cap 30 | 27.0 / 30 [20-30] | .976 | .607 | .653 | .838 |
| SE < .40, cap 40 | 31.8 / 33 [20-40] | .983 | .658 | .697 | .862 |
| SE < .40, no cap | 35.2 / 33 [20-48] | .985 | .753 | .780 | .895 |
| SE < .30, any cap | = cap (never reached) | | | | |
| A, per-scale SE < .40, no cap | 28.6 / 27 [20-39] | .981 | .600 | .647 | .828 |
| C top-10 stable 3 items, min 12, cap 20 | 18.9 / 20 [15-20] | .952 | .528 | .586 | .790 |
| C stable, cap 30 | 24.9 / 29 [15-30] | .966 | .598 | .644 | .832 |
| C stable, no cap | 30.5 / 29 [15-48] | .971 | .733 | .760 | .885 |
| **C-lit** (SD < .40 on the top-3 scales + stable, min 12, cap 40) | **35.1 / 40** [24-40] | .985 | **.710** | .740 | .891 |
| C-lit with SD < .45 | 31.8 / 34 [19-40] | .979 | .681 | .716 | .876 |

- SE rules behave badly with an 8-item-per-scale bank. SE .30 is never reached, so the rule becomes "ask everything".
  SE .40 is a two-humped mixture (about 20-30 items, or the full bank) because 54% of people cannot reach .40 on every
  scale. SE .50 stops early (median 15), but 14% still run to 48.
- The literature-based design (median 24-30, cap 40) is matched by "SE .40, cap 30" (median 30, mean 27: top-10 .61,
  top-3 fam .65) and "C stable, cap 30" (median 29). C-lit has median 40, so it runs to the cap for over half of users.

### 4. Synthetic check: known true theta (n = 10,000 drawn from N(0, Phi), responses generated by the calibrated GRMs; `e4_synthetic_vs_real.png`)

| | vs own full test: r / top-10 | vs **TRUE** theta: r / top-10 / top-3 fam / 1st letter |
|---|---|---|
| B k = 12 | .921 / .443 | .879 / .431 / .491 / .694 |
| B k = 20 | .959 / .533 | .912 / **.481** / .545 / .731 |
| best fixed k = 20 | .953 / .531 | .906 / .480 / .540 / .720 |
| B k = 30 | .981 / .632 | .930 / .518 / .572 / .748 |
| **full 48 items** | 1 / 1 | **.938-.943 / .532 / .584 / .755** |

- On synthetic data the engines agree with their own full test almost exactly as they do on real data (B k = 20: .959 / .533
  vs .957 / .537 real). The GRM fits these data well enough that real answers do not degrade the CAT relative to model
  data. Model misfit is not the bottleneck.
- **The key ceiling:** even the full 48-item test recovers only **53% of the true top-10** (and 58% of the true top-3
  families). This matches E5's independent ceiling (.553 top-10 under SEM noise). **A 20-item test recovers 90% of what the
  full test itself recovers** (top-10 .481 / .532), as do 93% at top-3 family level (.545 / .584) and 97% at 30 items.
- The live-vs-simulation gap: Alkan & Deniz (2023, level C) found a simulated r of .91-.97 with the paper form but only .73-.91
  live. A live gap comes from context, order effects, fatigue, new respondents and item-parameter drift, and none of
  these exist in replay. Expect live agreement with a full-length administration to be lower than everything here. A drop
  of about .05-.15 in r would be in line with that study. Projection, our interpretation: if r falls from .96 to about .88,
  the E5 conversion puts top-10 overlap with a full test at about .40 and top-3 family at about .45-.50.

### 5. Who gets which items (`e4_item_usage.png`)
- Engine B first gives one starter per scale: **R5, I5, A4, S5, E6, C8** (the most informative at theta = 0). Next it
  asks A2 (23% of people), R6 (18%), S3 (15%), C3 (13%) or R5 (11%).
- In the first 20 items, B allocates per scale **R 3.7, I 2.7, A 3.8, S 3.6, E 3.0, C 3.2**. I gets the fewest because its
  items are the most discriminating. The allocation is nearly identical across gender x age cells (R 3.60-3.74, A
  3.81-3.95), so the CAT does not route men and women to different content.
- **Items almost never used in the first 20:** A7, S4, E4 (0.0%), R3 (0.02%), S1 (0.1%), C5, I4, I8 (< 0.5%). The engine
  avoids the E2-flagged items by itself. **C8, E6, S3, S5, I5, A4 and R8 are given to > 99.8%** of simulees, and the CAT
  is in practice the fixed best-a order. **With 8 items per scale, there is almost nothing left to adapt.**

### 6. Post hoc (not pre-registered): is the variable-length "gain" real? (`e4_posthoc_stopping.json`)
Against the pre-registered comparator (best fixed at the rule's *mean* length), "C stable, no cap" beats best fixed 30 by
**+.094 top-10** and "SE .40, no cap" beats best fixed 35 by +.063. Both clear the pre-registered 5-point bar with CIs
excluding 0. Two checks show these gains are a part-whole artefact of the reference, not better measurement:

| Rule (mean items) | Rule top-10 | Best fixed, same mean k | Best fixed, **each person's own k** | Best fixed, lengths shuffled | **Synthetic vs TRUE: rule / fixed same mean k** |
|---|---|---|---|---|---|
| C stable, no cap (30) | .733 | .639 | **.735** | .684 | .510 / .519 |
| SE .40, no cap (35) | .753 | .690 | **.756** | .771 | .518 / .530 |
| C-lit SD .40, cap 40 (35) | .710 | .690 | **.709** | .696 | .526 / .529 |
| C stable, cap 30 (25) | .598 | .589 | .601 | .587 | .503 / .504 |

- Give the fixed form each person's *own* stopping length and it matches every rule, so item selection adds nothing.
- Against the true theta, every adaptive rule is **equal to or slightly worse than** a fixed form of the same mean length.
- What the rules "gain" is that they give some people (40-48 items) almost the whole reference test. Because overlap is
  convex in k near 48, that raises the average without measuring anyone better.

### 7. Subgroups (`e4_group_curves.png`; B at k = 20)

| Group (n) | r | top-10 | top-3 fam | 1st letter | E5 full-test top-10 under SEM noise |
|---|---|---|---|---|---|
| Female 13-17 (2,890) | .955 | .554 | .599 | .788 | .57 |
| Female 18-24 (6,299) | .955 | .550 | .612 | .798 | .54 |
| Female 25+ (6,972) | .954 | .560 | .622 | .808 | .56 |
| Male 13-17 (1,199) | .957 | **.456** | **.522** | .778 | **.46** |
| Male 18-24 (2,825) | .958 | .481 | .534 | .793 | .49 |
| Male 25+ (3,626) | .958 | .522 | .579 | .789 | .52 |
| Flat, differentiation < 1.0 (988) | .974 | **.212** | .272 | .626 | .17 |
| Differentiated (23,037) | .956 | .551 | .609 | .805 | .553 |

- Scale-level accuracy (r) is equal across groups, so the measurement itself is not worse for anyone.
- Occupation-list agreement is lower for males, especially teenage boys (.456 vs .554 for teenage girls), and very low
  for flat profiles. **In every group, the CAT-at-20 gap tracks the full test's own instability (E5, last column) almost
  one-for-one.** The cause is less differentiated profiles (E1: flat in 8.6% of males 13-17), not an item or engine bias.
  It is still a fairness issue: the product is less certain for these users and must say so.
- The incl-shared table gives the same pattern (male 13-17 .437, flat .234).

### 8. Lost-user signal
- **Posterior SE barely predicts whether a person's list is trustworthy**: the person-level correlation of max-SE with
  top-10 agreement is .11 at k = 12 and 20.
- **Predicted differentiation** (max - min of the predicted raw profile) predicts it much better (r = .41 at k = 20).
  - Top-10 agreement by quintile of predicted differentiation: .36, .49, .56, .61, .66.
  - Flagging predicted differentiation < 1.0 after 20 items marks 5.7% of users. It catches 64% of truly flat profiles
    (PPV .47), and their lists agree only .26 with the full test (vs .55 for the rest).
- Running flat users to 40 items (C-lit) raises their agreement to .46. But E5 shows their full-test list is itself
  unstable (.17), so longer testing does not give them a reliable answer. They need a different flow, not more of the
  same items.

### 9. Robustness: incl-shared-network table (calibration 81,183, simulation 34,791)

| | Main | Incl. shared |
|---|---|---|
| B k = 12: r / top-10 | .915 / .441 | .914 / .432 |
| B k = 20: r / top-10 / top-3 fam | .957 / .537 / .595 | .956 / .531 / .585 |
| best fixed k = 20: r / top-10 | .952 / .543 | .951 / .533 |
| B minus best fixed (indep.) at 20: r / top-10 | +.004 / -.004 | +.004 / .000 [-.002, .002] |
| B k = 30: r / top-10 | .980 / .639 | .979 / .635 |
| C-lit (mean items): top-10 | .710 (35.1) | .702 (34.7) |
| Male 13-17 / flat top-10 at k = 20 | .456 / .212 | .437 / .234 |

No conclusion changes.

### 10. Relative to the E5 ceiling (secondary analysis requested after E5; not part of the pre-registered bars)
E5 (`research/findings/e5_stability.md`): the full test's own top-10 stability under one SEM of noise is **.553**
(differentiated profiles). The family hit rate (r >= .90) is .697 and top-3 families (r >= .80) .60. Retest-like
(replicate vs replicate) values are .42 top-10 and .57 family.
- **CAT B at 20 items vs the full test: top-10 .537 (differentiated .551), family hit (r >= .90) .678, top-3 fam .595.**
  A 20-item CAT disagrees with the full test about as much as the full test disagrees with itself after one SEM of noise.
- At 30 items: .639 / .769 / .681, which is above the E5 one-SEM ceiling on every measure.
- On truth (synthetic): 20 items recover 90% (occupations) to 93% (top-3 families) of what the full test recovers, and 30
  items 97-98%.
- **E5 r-to-overlap conversion.** By E5's noise curve, B's r = .957 at k = 20 "should" give top-10 of about .62, but we
  observe .54. At k = 30, r .980 should give about .73, but we observe .64. So CAT error hurts rankings more than isotropic
  noise at the same per-scale r. One likely reason (not tested) is that EAP shrinkage flattens the profile shape, and Pearson
  matching is shape-only. The E5 conversion therefore overstates what a given r buys. Use the direct E4 numbers.

## Verdict

### Primary bar (pre-registered; r >= .90 AND top-10 >= 70% within <= 20 items)
| Criterion | Best configuration within 20 items | Result |
|---|---|---|
| mean r(theta, theta_full) >= .90 | B, k = 12: .915; k = 20: .957 [.956, .957] | **met** (from 12 items) |
| top-10 overlap >= 70% | best at <= 20 items: A/best fixed k = 20 .54 | **not met** (.70 needs about 36 items) |
| Promising clause 1 (top-10 60-70% within 20) | .54 | not met |
| Promising clause 2 (both bars at 21-30 items) | top-10 at 30 = .645 | not met |

**Verdict: NOT VIABLE against the bar as written.** I keep the bar, but it was mis-specified, so this verdict does not mean
"a short test is not viable". The bar asked a 20-item test to agree with the full test's top-10 at 70%. The full test
agrees with its own true-score list only 53-55% of the time (E5; section 4 here). E5's conversion puts 70% at a per-scale
r of about .975, and our data put it at about .99. The scale-level part of the bar is met comfortably from about 12 items.

### Secondary bar (CAT must beat best fixed by >= .03 r or >= 5 points top-10, CI excluding 0)
- **Fixed-length engines: FAILED at every length.** The largest CAT advantage is B over best fixed at k = 12: +.005 r
  [.004, .006] and +.003 top-10 [.001, .005]. At k = 20 it is +.004 r and -.004 top-10 [-.006, -.001]. At k = 30 it is
  -.000 r and +.001 top-10. Engine A gives the same picture.
- **Variable-length rules: nominally MET** by "C stable, no cap" (+.094 top-10) and "SE .40, no cap" (+.063). The post-hoc
  checks in section 6 show both gains are part-whole artefacts: no gain at equal per-person length, and none against true
  theta. All capped rules fail (C-lit +.020, C stable cap 30 +.008).
- **Interpretation: the CAT's complexity is not justified with this 48-item bank.** That is what the pre-registered
  fallback anticipated.

### Literature design (median 24-30, cap 40; reported only)
"SE .40, cap 30" (median 30, mean 27) gives r .976, top-10 .61, top-3 fam .65 and first letter .84. The fixed 24- and
30-item forms do as well at the same length.

## Caveats
- **Part-whole inflation.** The reference is the same answers the short form draws from, so all "vs full test" numbers
  (especially at k >= 36) are inflated relative to a separate administration. The synthetic true-theta numbers and E5
  are the honest anchors.
- **Replay is not live.** Answers were given in a fixed 48-item order, without the adaptive context. Expect lower live
  agreement (Alkan & Deniz 2023: .73-.91 live vs .91-.97 simulated; level C).
- **Small bank.** With 8 items per scale, the result "CAT does not beat a fixed form" is specific to this bank. With a
  60-180-item bank (O*NET IP Short Form/parent; note 02), adaptivity has room to work, and this needs re-testing.
- **Model.** These are unidimensional GRMs per scale. Local dependence inside I (Q3 up to .33) overstates I information.
  Measurement invariance was not tested with IRT here; E2 found scalar non-invariance by gender and age. Using one set of
  item parameters for all groups is therefore an approximation, although subgroup scale-level r is equal (.954-.958).
- **The Gaussian (EP-style) correlated prior is an approximation** to a full 6-D posterior. It was not validated against
  exact 6-D integration. On synthetic data engine B (correlated prior) tracks the true theta slightly better than engine A
  (independent prior): r .912 vs .898 at k = 20. Selection also differs between the two, so this is not a pure scoring
  comparison.
- Sample: self-selected, young, female-majority online sample, English items, about 50% US. The calibration is not
  transferable to Spanish users without re-calibration.
- Interests predict direction and engagement more than satisfaction (note 01). "Agreement with the full test" is a
  measurement criterion, not a validity criterion for career outcomes.

## Implications and recommended v1 engine configuration
The product question "how few questions?" now has a clear answer for this bank: **about 12 items give scale scores at
r >= .90, 20-24 items give a profile and Holland letter about as dependable as the full test under its own noise, and no
item count makes a ranked top-10 occupation list stable.** Below is a concrete v1 recommendation (proposal for the
research-editor and MODELS.md):

| Component | v1 setting | Evidence |
|---|---|---|
| Model | Six unidimensional logistic GRMs, parameters from this calibration (EM-polished; `calibration.items` in the JSON). Keep MIRT out. | Section 1; Phi from section 1 |
| Prior / scoring | EAP on an 81-point grid with the correlated 6-D prior (Phi, Gaussian-site approximation). Report the *predicted full-scale raw profile* for matching, and theta + SE internally. | +.005-.016 r at k <= 12; equal later |
| Item selection | **Fixed content-balanced order by discrimination** (round-robin R-I-A-S-E-C) over the retained 40 items: R5 I5 A4 S5 E6 C8 / R8 I7 A2 S3 E3 C3 / R6 I3 A5 S7 C1 R7 I6 A8 S8 E2 C4 ... (full order in `best_fixed_order`, with flagged items removed). Implement it behind the same interface as a CAT selector so that max-info/variance-reduction can be switched on when the bank grows. | Sections 2, 5, 6: CAT = best-fixed |
| Starter items | R5, I5, A4, S5, E6, C8 (one per scale) | Section 5 |
| Length / stopping | **24 items (4 per scale) by default.** r .965-.968, first letter .83, top-3 fam .63-.64 (about the E5 one-SEM ceiling of .60). Optional "refine" step to 30 (r .98, top-3 fam .68). Do **not** use SE stopping: SE .30 is unreachable and SE .40 is unreachable for 54% of people with this bank. | Sections 2, 3 |
| Cap | 40 (all retained items), only via the refine option | |
| Item exclusions | Drop all 8 E2-flagged items: **R1, A7, S4** (weak, lowest a) and **E4, R3, I8, R4, E1** (gender DIF). Cost: nothing measurable (r -.001, top-10 -.003 at k = 20). Replace them in v2 with new, DIF-screened items (I: computing/physics; E: non-sales leading). | Section 2; E2 |
| Output granularity | Show the **top-3 occupation families** (E3 r >= .80) with 2-3 example occupations each, and the Holland code with ties shown. **Do not show a ranked top-10 of occupations as a precise result.** | Sections 2, 4, 10; E3/E5 |
| Lost-user trigger | After the 24 items: **predicted differentiation < 1.0** (raw 1-5 metric; 5.7% of users, top-10 agreement .26) **or predicted elevation < 2.0** (E1/E5 threshold; not tested in E4). Then switch to the lost-user flow: broader/scenario items, a wider and more diverse set of families, and explicit uncertainty wording. **Do not trigger on posterior SE** (correlation with list stability only .11). | Section 8 |
| Fairness monitoring | Report family-level agreement by gender x age. Teenage boys and flat profiles get the least stable lists (top-10 .46 / .21 at k = 20, mirroring E5), so the UI must widen the result set for low-differentiation profiles rather than sounding certain. | Section 7 |

**When to revisit adaptivity:** once the bank has >= 15-20 calibrated items per scale (for example after adding O*NET IP
items, CC BY), re-run E4. Selection then has room to help, and the posterior-variance engine (B) and code are ready.

## Suggested updates to other docs (for the research-editor; not edited here)
- `irt-cat-simulation` skill: girth 0.8 `grm_mml` underestimates a by about 3-5% here (marginal-count threshold
  approximation), so use an EM polish. With 8-item scales, SE .30 is unreachable and SE .40 is unreachable for half of
  users. Overlap with the full test has a part-whole jump at k -> 48, so compare variable-length rules with per-person
  matched or true-theta references.
- `riasec-scoring` skill / MODELS.md: v1 is a fixed 24-item best-a form with GRM-EAP scoring, family-level output, and a
  differentiation-based lost-user trigger.
- RESEARCH.md: E4 verdict "not viable vs the pre-registered bar; the bar was unreachable for any instrument (E5)". The
  practical answer is 12 items for scale scores at r >= .90 and 24 items for family-level results at the full test's own
  noise level. "CAT not justified with this bank."
- CLAUDE.md "Current phase": E4 done.

## Sources
- Alkan, V., & Deniz, K. Z. (2023). Developing a CAT form of the Occupational Field Interest Inventory (level C). https://dergipark.org.tr/en/pub/epod/issue/76343/1153713
- Simsek, A. S., & Tavsancil, E. (2022). Polytomous IRT-based CAT for measuring psychological traits (level C). https://dx.doi.org/10.21031/epod.1148313
- O*NET Interest Profiler forms (Mini-IP 30 items, Short Form 60) (level A). https://www.onetcenter.org/IP.html
- PROMIS-style SE stopping rules (level A/B). https://www.ncbi.nlm.nih.gov/pmc/articles/PMC12681468/
- Mulder, J., & van der Linden, W. J. (2009), multidimensional CAT selection (methods). https://link.springer.com/doi/10.1007/s11336-008-9097-5
- Yen's Q3 and the relative cut-off of .20 above the mean Q3 (Christensen, Makransky & Horton 2017): `[UNVERIFIED: not yet in notes]`.
- Bock & Aitkin (1981) EM for MML item calibration: `[UNVERIFIED: method reference, not in notes]`.
- Own experiments: `research/findings/e1_data_audit.md`, `e2_structure.md`, `e3_occupation_space.md`, `e5_stability.md`, and this file.

