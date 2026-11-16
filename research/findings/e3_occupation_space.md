# E3 — Occupation space: distribution, effective resolution and per-person coverage

Pre-registered 2026-11-15, before running `research/feasibility/e3_occupation_space.py`.
Disclosure: while building and testing `src/career_compass/matching.py`, I saw (i) the pure-type
self-check top-5 lists per method and (ii) the number of complete-linkage families (101 / 123 / 172 / 286 at
r >= .80 / .85 / .90 / .95). I have looked at no person-level matching outcome (coverage, top-1 r, reach) yet.

## Pre-registration

```
Question:      How are the 923 rated O*NET 31.0 occupations spread in RIASEC space, how many
               distinguishable profiles exist, and does each matching method give every kind of
               person (especially A- and S-leaning people, given E1's r = -.68 person-vs-catalogue
               mismatch) good matches from a broad pool?
Hypothesis:    (1) The catalogue is concentrated in the R/C region (E1: 42% R-top, 3% A-top), so
               the Prediger plane shows a dense Things/Data cluster and a sparse Ideas/People side.
               (2) Many occupations are near-duplicates in shape, so the effective resolution is
               well below 923 (family count at r >= .90 is 172, seen during module tests).
               (3) Under Pearson matching, A-top people get high top-1 r but from a tiny pool
               (the same ~28 A-top occupations), so exposure is very unequal (Gini > .6) and many
               R/C occupations are "dead" (never in anyone's top 10). Population-normed matching
               (cosine_centered) spreads exposure at a modest cost in Pearson r.
               (4) Job zone relates to shape (higher zones are more I/E, lower zones more R),
               while the domain source (ML vs ML/Expert) does not.
Data:          data/processed/onet_occupations.parquet (923 occupations, OI 1-7, job zone 2-5,
               oi_domain_source); data/processed/riasec_people.parquet (80,085 people, raw 1-5
               scale means); robustness: data/processed/riasec_people_incl_shared_network.parquet
               (115,974); data/raw/onet_31_0/db_31_0_csv/related_occupations.csv (read only).
Method:        Matching uses src/career_compass/matching.py (methods pearson, cosine_centered,
               euclid_z, hexagon; definitions in the module docstring).
               Q1 Distribution: top-letter and top-2-letter Holland code counts (argmax of OI;
                  ties reported). Prediger angle projection on the self-centred profile
                  (x = sum c_k cos(k*60deg), y = sum c_k sin(k*60deg), R = 0deg), scatter coloured
                  by job zone, and the people density in the same plane. Angular histograms of
                  people vs occupations (angle is scale-free). PCA of centred occupation profiles
                  (variance by component, participation ratio).
               Q2 Resolution: all 425,503 occupation pairs, Pearson r of profiles. Count pairs with
                  r > .95 and > .98, the number of occupations with at least one such twin, and
                  single-linkage connected components at those thresholds ("distinct profiles").
                  Complete-linkage clustering on 1 - r: number of families at r_min = .80, .85,
                  .90, .95 (every within-family pair >= r_min). r_min = .90 is the primary family
                  definition, used again in E5. Family size distribution. Check against O*NET
                  related_occupations: mean profile r of related pairs vs all pairs, and the share
                  of related pairs inside the same family.
               Q3 Coverage: for every person and every method, the top 10 (ties broken by catalogue
                  order). Per person: the Pearson r of the method's top-1 and 10th occupation (the
                  common quality currency across methods), the mean Pearson r of its top 10, and
                  the pool size (number of occupations with Pearson r >= .70 and >= .80; method-free).
                  Grouped by the person's unique top type (R..C; people with a tied top type form a
                  "tied" group), and by gender and age band (13-17, 18-24, 25+).
                  Exposure: number of people whose top 10 contains each occupation. Reach = share of
                  the 923 occupations with exposure >= 1 (primary) and >= 0.1% of people (secondary).
                  Gini of exposure over all 923 occupations, including the zeros. Exposure share by
                  occupation top letter vs people's top-type share. Reach within each top-type group.
                  Bootstrap 95% CIs (people resampled, B = 1000 for medians, B = 200 for reach/Gini).
                  Exploratory (not gating): Pearson re-ranked with a family cap (at most 2 per
                  r >= .90 family) and with MMR (lambda = .7, candidates = top 50, similarity =
                  occupation-occupation Pearson r). Report the reach/Gini gain and the cost in mean
                  top-10 r.
               Q4 Correlates: Kruskal-Wallis by job zone for each centred RIASEC score and for
                  differentiation (max - min OI), with epsilon-squared; chi-square of top letter
                  x job zone with Cramer's V. The same for domain source (ML vs ML/Expert, 52 vs 871),
                  using Mann-Whitney. Share of OI values clipped at exactly 1.0 or 7.0.
Baselines:     (i) Random top 10 (10 uniformly random occupations per person).
               (ii) Holland first-letter baseline: 10 random occupations whose top letter equals
                    the person's top type (does full 6-D matching beat one-letter matching?).
               (iii) Pearson (O*NET-style) is the reference method that the others are compared to.
Metrics:       median (and IQR) of the Pearson r of top-1 and 10th; pool sizes; reach (>= 1 and
               >= 0.1%); exposure Gini; per-group medians; families per r_min; twin-pair counts;
               epsilon-squared, Cramer's V.
Success bar:   Applied per method, on the main table:
               (a) median (over people) Pearson r of the method's top-1 occupation >= .80;
               (b) reach (exposure >= 1) >= 60% of the 923 occupations;
               (c) every unique-top-type group (R, I, A, S, E, C) has median top-1 Pearson r >= .60.
               PROVEN if at least one method meets (a), (b) and (c).
               PROMISING if no method is proven, but one method meets two of the three and is within
                 the margin on the third ((a) >= .70, (b) >= 40%, (c) >= .50).
               NOT VIABLE otherwise.
               Effective resolution (Q2) and correlates (Q4) are descriptive and not gated.
               Note: Pearson maximises (a) by construction, so (a) mostly tests the other methods,
               and (b) mostly tests Pearson.
```

---

## Results

Run: `.venv/Scripts/python -I research/feasibility/e3_occupation_space.py --seed 42` (about 45 s; a second run
reproduced every number). Smoke run first with `--quick` (8,000 people). Raw results:
`research/findings/e3_occupation_space.json`. Families: `research/findings/e3_families.csv` (code, title, family id at
r_min = .80/.85/.90/.95, label = most central member). n = 923 occupations and 80,085 people (main table). The person
sample is self-selected (E1: median age 23, 67% female, 49% US), so all person-level numbers are evidence level E for
this sample only. Matching code: `src/career_compass/matching.py`.

### Q1: Distribution of the 923 occupations (`e3_holland_distribution.png`, `e3_prediger_scatter.png`, `e3_angle_hist.png`)

| Top letter | R | I | A | S | E | C |
|---|---|---|---|---|---|---|
| Occupations | 388 (42.0%) | 112 (12.1%) | **28 (3.0%)** | 129 (14.0%) | 100 (10.8%) | 166 (18.0%) |
| People (first argmax) | 4.0% | 28.2% | 19.8% | 33.1% | 6.4% | 8.5% |

- Two occupations have a tied top letter. All 30 ordered two-letter codes occur, but **RC alone covers 312 occupations
  (34%)**. Next are EC 86, CE 67, SI 64, RI 51, CR 46 and IR 46. The `holland_code` column has 98 distinct three-letter
  codes.
- 11.9% of all OI values sit exactly at the clip points 1.0 or 7.0, and 50.3% of occupations have at least one clipped
  value. The median occupation differentiation is 4.95 OI points.
- Shape space: PCA of the centred profiles explains 47 / 23 / 15 / 9 / 5% (participation ratio 3.2 effective dimensions).
  The Prediger plane (first circular harmonic) holds 66% of the centred variance.
- In the Prediger plane, occupations form a dense block at Things + Data (R/C, mostly job zone 2). The People + Ideas
  quadrant (S/A), where most people sit, is thinly populated and mostly job zone 4-5 (`e3_prediger_scatter.png`).
  The angular histograms barely overlap: people point A/S/I, occupations point R/C (`e3_angle_hist.png`).

### Q2: Effective resolution (`e3_families_curve.png`)

| Measure | Value |
|---|---|
| Pairwise profile r (425,503 pairs) | median .28; 5th pct -.56; 95th pct .95; 99th pct .99 |
| Pairs with r > .95 / > .98 | 23,185 / 9,550 |
| Occupations with at least one twin at r > .95 / > .98 | **872 (94%)** / 731 (79%) |
| Connected components (single linkage) at r > .95 / > .98 | 62 / 243 (chaining makes these coarse) |
| **Families, complete linkage, all within-family pairs r >= r_min** | r_min .50: 36 · .70: 68 · .80: **101** · .85: 123 · **.90: 172** · .95: 286 · .98: 455 |
| r >= .90 families | 27 singletons; median size 3; largest 97 (R machine operators, e.g. "Extruding and Forming Machine Setters ... Synthetic and Glass Fibers"); 70% of occupations are in families of 5 or more |
| r >= .90 families by top letter of the family mean | R 44, C 40, S 32, I 27, E 18, **A 11** |
| O*NET related_occupations (18,460 pairs, both rated) | mean profile r .84 (Primary-Short .89, Primary-Long .86, Supplemental .81) vs .26 for all pairs; 16.8% of related pairs are in the same r >= .90 family (chance 1.9%); 7.3% of related pairs have r < .50 |

So interests alone can tell apart **about 100-170 occupation profiles**, not 923. At r >= .90 there are 172 groups,
and the 97-member R block is effectively a single profile. A-type space is thin: 28 occupations in 11 families.
O*NET's own "related occupations" mostly share an interest profile (r .84), but most are not r >= .90 twins, so related
occupations are a reasonable source of "similar careers" that are not exact duplicates.

### Q3: Coverage per person (`e3_coverage_by_type.png`, `e3_exposure_lorenz.png`, `e3_pool_size.png`)

Quality is the Pearson r between the person and the occupation the method ranks first (or tenth), which is a common
currency across methods. 95% CIs are percentile bootstraps over people (B = 1000). 15 people have an exactly flat
profile (all six scores equal) and get an arbitrary ranking.

| Method | Median top-1 r [95% CI] | Median 10th r | Median mean top-10 r | Reach (>= 1 person) | Reach (>= 0.1% of people) | Exposure Gini [CI] | Top 10% of occ. get | Min top-type median top-1 r |
|---|---|---|---|---|---|---|---|---|
| **pearson** | **.928** [.927, .929] | .808 | .852 | **97.2%** (26 dead) | 71.1% | .766 [.764, .768] | 64.8% of slots | **.887 (A)** |
| hexagon | .919 [.918, .919] | .793 | .830 | 97.5% (23 dead) | 70.4% | .780 [.779, .782] | 68.4% | .875 (A) |
| cosine_centered | .537 [.534, .539] | .517 | .525 | 100% | 88.3% | .484 | 30.4% | .432 (A) |
| euclid_z | .380 [.376, .383] | .308 | .327 | 98.3% | 84.7% | .563 | 37.6% | **.030 (A)** |
| Baseline: random 10 | -.21 (best of 10: .59) | | -.17 | 100% | 100% | .02 | 10.7% | |
| Baseline: random 10 with person's top letter | best of 10: .81 | | .48 | 100% | 83.1% | .61 | 36.8% | |

Full 6-D Pearson matching clearly beats one-letter matching (mean top-10 r .85 vs .48; best-of-10 .93 vs .81).

Reach depends on how many people are pooled. With Pearson it is 33-37% for 100 people, 71-74% for 1,000, 86% for 5,000,
92-95% for 20,000 and 97.2% for 80,085 (min-max of 5 subsamples). This is why the secondary ">= 0.1% of people" reach
(71%) is the more meaningful number. With Pearson, 1.6% of people have no occupation at r >= .70, and 8.7% have none
at r >= .80.

**By the person's top type (Pearson; unique top type, tied people separate):**

| Top type | n | Median top-1 r [CI] | p10-p90 top-1 | Median 10th r (p10) | Pool r >= .80: median (share with 0) | Pool r >= .70: median | Distinct occupations reached by the group | Share of top-10 with the same top letter |
|---|---|---|---|---|---|---|---|---|
| R | 2,426 | .952 | .80-.99 | .879 (.66) | 44 (10%) | 143 | 524 | 79% |
| I | 19,460 | .915 | .80-.98 | .797 (.61) | 9 (10%) | 30 | 315 | 64% |
| **A** | 13,988 | **.887** [.886, .888] | .78-.96 | **.689 (.59)** | **3 (14%)** | **8** | **166** | 58% |
| S | 25,260 | .949 | .85-.99 | .858 (.73) | 22 (3%) | 50 | 274 | 92% |
| E | 4,782 | .937 | .78-.99 | .823 (.63) | 12 (12%) | 29 | 273 | 71% |
| C | 6,826 | .961 | .87-.99 | .887 (.73) | 40 (2%) | 89 | 498 | 73% |
| tied | 7,343 | .902 | .77-.98 | .767 (.60) | 5 (16%) | 21 | 641 | n/a |

**A-top people do not get poor top-1 matches (median .89). They get a tiny pool.** The median A-top person has 3
occupations at r >= .80 and 8 at r >= .70. Their 10th match is at r .69, and 13,988 people share 166 occupations.
S-top people do well on quality (.95) and pool (22), but 274 occupations serve 25,260 people.

**Exposure is driven by people, not by the catalogue (Pearson).** S-top occupations (14% of the catalogue) fill 47.4% of
all top-10 slots, I-top 19.0% and A-top 13.1% (3% of the catalogue). R-top occupations (42% of the catalogue) get 4.0%.
All 26 dead occupations are R-top (24 in job zone 2), and 93% of R-top occupations are reached at least once. The most
exposed occupations are Music Therapists (in 24% of all top-10s), Art Therapists (18%), Art/Drama/Music Teachers,
Postsecondary (18%), Marriage and Family Therapists (18%), Political Science Teachers (17%), Sociologists (16%) and
Actors (15%).

**Subgroups (Pearson):**

| Group | n | Median top-1 r | Share of top-10 that is R-top / S-top / A-top | Mean job zone of top-10 |
|---|---|---|---|---|
| Male | 25,499 | .924 | 8.9% / 35.4% / 14.5% | 4.05 |
| Female | 53,870 | .930 | **1.7%** / **53.1%** / 12.4% | 4.25 |
| Other (small n) | 622 | .906 | 4.4% / 40.7% / 21.6% | 4.31 |
| 13-17 | 13,882 | .921 | 4.4% / 38.2% / 17.7% | 4.20 |
| 18-24 | 30,689 | .933 | 3.8% / 48.3% / 13.0% | 4.17 |
| 25+ | 35,514 | .927 | 4.1% / 50.2% / 11.5% | 4.20 |
| Flat (diff < 1.0) | 3,175 | .929 | 10.1% / 33.3% / 14.6% | 3.89 |
| Low elevation (< 2.0) | 9,029 | .952 | 4.2% / 46.6% / 14.7% | 4.09 |

- Match quality is equal across gender and age (all .92-.93). The *content* differs, though: women's top-10s contain 5x
  fewer R-top occupations and 1.5x more S-top occupations than men's. This mirrors the gender gap on Things-People
  (E2 d = .67), so it is steering that comes from the answers, not from the matcher. The ethics review should see it.
- For flat profiles, Pearson still reports a high top-1 r (.93). Correlating two nearly flat noise vectors produces
  confident-looking matches, so **Pearson r is not a confidence measure** (see E5).
- The normed methods change the content a lot:
  - cosine_centered puts 47.6% R-top occupations into men's top-10 (22.0% for women).
  - euclid_z gives **flat and low-elevation people 80-83% R-top occupations with mean job zone 2.2-2.7**. People who
    dislike everything get funnelled to low-preparation manual jobs, which is an unacceptable failure mode.
  - euclid_z gives A-top people a median top-1 r of .03: only 2.7% of their top-10 are A-top occupations.

**Agreement with Pearson** (mean top-10 overlap): hexagon .69, cosine_centered .09, euclid_z .03.

**Exploratory re-ranking of Pearson (not gated).** Both re-rankings keep the same top 1.

| Variant | Median mean top-10 r | Distinct r >= .90 families in top-10 | Reach >= 1 / >= 0.1% | Gini | Overlap with plain Pearson |
|---|---|---|---|---|---|
| Plain Pearson | .852 | 5.3 | 97.2% / 71.1% | .766 | 1 |
| Family cap (max 2 per family) | .841 | 6.6 | 95.6% / 70.2% | .772 | .79 |
| MMR (lambda .7, top-50 candidates) | .847 | 6.2 | 96.0% / 68.5% | .779 | .87 |

Within-list diversity rises at a cost of about .01 in mean r, but catalogue-level exposure does **not** improve. That is
expected: the concentration comes from the person population leaning S/A/I, not from redundant lists.

### Q4: Job zone and domain source

| Variable (centred OI) | Median by job zone 2 / 3 / 4 / 5 | Kruskal-Wallis epsilon-squared |
|---|---|---|
| R | 3.46 / 1.81 / -0.40 / -0.69 | **.39** |
| I | -0.97 / -0.14 / 0.49 / 1.70 | **.41** |
| A | -1.75 / -1.99 / -1.66 / -1.17 | .04 |
| S | -1.25 / -1.00 / -1.01 / 1.56 | .14 |
| E | -1.20 / -1.28 / -0.17 / -1.50 | .08 |
| C | 1.33 / 1.36 / 1.23 / -0.16 | .20 |
| Differentiation (raw OI) | 5.55 / 4.99 / 4.51 / 4.54 | .20 |
| Prediger y (Ideas +) | -2.20 / -1.45 / -0.99 / +1.57 | .25 |

All p < 1e-10. Top letter x job zone: chi2 = 569, **Cramer's V = .45**. 72% of job zone 2 occupations are R-top
(243/337), while job zone 5 is I (68) and S (65) out of 152. **Job zone strongly relates to shape**: preparation level
and interest type are confounded in the catalogue. So an S/I-leaning person is in practice matched to graduate-level
jobs (mean job zone of the top-10 is 4.2 for Pearson).

Domain source: only 52 occupations are "Machine Learning" only (mostly new green-economy and management titles, e.g.
Chief Sustainability Officers, Wind Energy Development Managers). Their shapes differ modestly. They are more E (rank
biserial .32, p = .0001) and less S (-.28, p = .0006). None are A-top or S-top (top letter chi2 p = .016, V = .12). Their
differentiation is the same (p = .23). This looks like a difference in content (which titles were left without expert
review), not a scoring artefact. The sample is small.

### Robustness: incl-shared-network table (n = 115,974)

| Method | Median top-1 r | Reach >= 1 / >= 0.1% | Gini | Min top-type median (A) | Minors 13-17 median top-1 |
|---|---|---|---|---|---|
| pearson | .929 (main .928) | 97.9% / 73.4% | .752 | .890 | .925 |
| hexagon | .920 (.919) | 97.9% / 72.9% | .766 | .879 | .915 |
| cosine_centered | .534 (.537) | 100% / 88.5% | .482 | .427 | .510 |
| euclid_z | .383 (.380) | 98.3% / 85.4% | .561 | .022 | .326 |

No headline changes, and every verdict is the same.

## Verdict (against the pre-registered bar)

| Method | (a) median top-1 r >= .80 | (b) reach >= 60% | (c) every top-type median >= .60 | Verdict |
|---|---|---|---|---|
| **pearson** | .928 yes | 97.2% yes | .887 (A) yes | **PROVEN** |
| hexagon | .919 yes | 97.5% yes | .875 (A) yes | **PROVEN** |
| cosine_centered | .537 no | 100% yes | .432 no | not viable |
| euclid_z | .380 no | 98.3% yes | .030 no | not viable |

**Overall: PROVEN.** Shape-based matching gives almost everyone a close top-1 match and touches almost every occupation.
In hindsight the bar was too lenient on coverage. Reach ">= 1 of 80,085 people" is nearly automatic (97%), while the
meaningful concentration problem shows up in the Gini (.77), the 0.1% reach (71%) and the per-type pool sizes (A: 3
occupations at r >= .80). I keep the original bar, as the protocol requires, and flag this. Also, (a) is by construction
an advantage for Pearson. The normed methods were judged in a currency that is not their own objective, and they still
fail on content grounds (euclid_z funnelling, A-top people receiving no A occupations).

## Caveats

- **The O*NET 31.0 interest ratings are all model-estimated** ("Machine Learning" or "Machine Learning/Expert", 02/2026).
  11.9% of the values are clipped at 1 or 7. The near-duplicate structure may partly reflect the rating model, not the
  jobs.
- **The person sample is not the target population** (E1). The exposure distribution (47% of slots to S-top
  occupations) mirrors this sample's S/I/A lean, and a different user base would shift it.
- Pearson r measures shape only. A high r does not mean a strong interest: low-elevation and flat profiles get r values
  as high as anyone else's.
- People are on a 1-5 scale with 8-item means and occupations on a 1-7 scale. The normed methods depend on the two
  reference populations (the cleaned people table and the 923-occupation catalogue). Both are arbitrary for the product.
- Complete-linkage family counts are an upper bound on the minimum number of r_min-cliques, and families depend on the
  linkage choice. "Reach" depends on n (see the curve).
- Q4 tests are on 923 non-independent occupations (nested SOC groups), so the p-values overstate certainty. The effect
  sizes are the useful part.
- The exploratory re-ranking parameters (cap 2, lambda .7) were chosen a priori and not tuned.

## Implications for the product

1. **Default matching method: Pearson (O*NET-style).** It is proven, the simplest to explain, and the field standard.
   The hexagon kernel is equivalent in quality (.919 vs .928), shares 69% of the top-10 with Pearson, and offers no
   gain here. Keep it as an explanation device ("your interests sit between I and A on the hexagon"), not as the ranker.
   **Do not use euclid_z** (it sends flat or low-elevation users to job zone 2 R work, and A-top users get a median r of
   .03). Do not use cosine_centered as the ranker either (median r .54), although its "distinctive relative to other
   people" view may be useful in explanations.
2. **Effective resolution is about 100-170 profiles.** Present results as **occupation families with 2-3 example
   occupations each**, not as 10 independent jobs. Ten jobs drawn from 1-2 families is the norm for R/C users (a
   97-member R family exists). E5 tests which family granularity is stable enough.
3. **Re-ranking and diversity.** Use a light within-list diversity rule (family cap of 2, about -.01 r) so a top-10 spans
   about 6.6 families instead of 5.3. Do not expect it to fix catalogue exposure. The real concentration comes from the
   S/A/I lean of users and the scarcity of A/S occupations (28 A-top), so it needs **catalogue work** instead: add finer
   A/S/I occupations (e.g. from ESCO) and use the O*NET 31.0 specific interest areas.
4. **A-top users need special handling.** Show their honest, smaller pool and explain it ("few catalogue jobs are
   primarily artistic, so here are artistic jobs plus jobs that use your second interest"). Use the second letter to
   broaden the pool, and use specific interest areas to separate arts sub-domains.
5. **Job zone must be a separate, user-visible filter.** It is confounded with interest shape (V = .45). Without a
   filter, S/I users only see graduate-level careers (mean job zone 4.2), and R users only see job zone 2. Offer "show
   options with less/more preparation" and match within job zone.
6. **Confidence must not come from the match r.** A flat profile gets r .93 just like a clear one. Use differentiation,
   elevation and (in E4) theta standard errors to decide whether to show a ranked list or the "lost user" exploration
   flow.
7. **Fairness input.** Pearson gives equal quality by gender and age but different content. Women get 1.7% R-top
   occupations in their top-10 vs 8.9% for men. This follows the answers (E2 Things-People d = .67). The ethics review
   should decide whether to add a "careers you might not have considered" slot. Item-level DIF fixes (E2) are the
   upstream lever.
