# E5 — Recommendation stability under measurement noise

Pre-registered 2026-11-15, before running `research/feasibility/e5_stability.py`. E3 was pre-registered at the
same time. The family definition (complete linkage, all within-family pairs r >= .90; 172 families) was fixed in E3
and seen during module tests. No stability outcome has been computed yet.

## Pre-registration

```
Question:      How stable are top-k occupation recommendations from the full 48-item test when the
               answers are perturbed by realistic measurement noise? This sets the ceiling that the
               adaptive test (E4) cannot beat.
Hypothesis:    Scale alphas are .83-.90 (E1), but the people-vs-occupation shape correlation is
               modest and the catalogue has many near-duplicate profiles (E3). So exact top-10 lists
               will be only moderately stable (mean overlap ~ 50-65% for differentiated profiles),
               and family-level lists will be much more stable (>= 80%). Flat profiles
               (differentiation < 1.0) will be clearly less stable. Holland 3-letter codes in exact
               order will agree less often than top-1 letters.
Data:          data/processed/riasec_people.parquet (80,085); random sample of 5,000 people (seed 42).
               Items R1-C8 (1-5, NaN = missing). Robustness: 5,000 people from
               data/processed/riasec_people_incl_shared_network.parquet. Alphas from
               research/findings/e1_data_audit.json (reliability, reliability_incl_shared).
Method:        Noise models, 50 replicates each:
               (a) Item bootstrap: per person, per replicate and per scale, draw 8 of that person's
                   answered items with replacement; the scale score is their mean.
               (b) Reliability (CTT) noise: x_k + N(0, SEM_k), SEM_k = SD_k * sqrt(1 - alpha_k), with
                   SD_k the scale SD in the full table and alpha_k from E1. No clipping (primary).
               Comparisons: PRIMARY = original full-test profile vs each perturbed replicate. The
               difference has error variance SEM^2, which approximates true-score vs observed
               agreement, i.e. the E4 setting (CAT estimate vs full test). SECONDARY = replicate 2j
               vs 2j+1 (25 pairs; error variance 2*SEM^2, approximates test-retest with parallel forms).
               Methods: pearson, cosine_centered, euclid_z, hexagon (src/career_compass/matching.py).
               Metrics per person (averaged over replicates):
                 - top-10 overlap |A & B| / 10 and top-3 overlap / 3; top-1 occupation agreement;
                 - Kendall tau-b between original and perturbed scores of the original top-20;
                 - Holland code (person scores, ties broken in R-I-A-S-E-C order; tie rate
                   reported): top-1 letter agreement, same 3-letter set, exact ordered 3-letter code;
                 - family level (E3 families, r >= .90): symmetric family hit rate
                   = 1/2 [share of A's occupations whose family is among B's families + the reverse];
                   secondary: Jaccard of the distinct-family sets; sensitivity with r >= .80 families.
               Breakdowns: differentiation (max - min raw scale mean; flat < 1.0 vs differentiated
               >= 1.0 per E1; finer bins <1.0, 1.0-1.5, 1.5-2.0, 2.0-2.5, >= 2.5), low elevation
               (< 2.0), person top type, gender (male / female; "other" pooled, with a warning),
               age band (13-17, 18-24, 25+).
               95% CIs: bootstrap over people (B = 1000) of the person-level means.
Baselines:     (i) Random top 10 vs the original top 10 (occupation and family level; chance level).
               (ii) "Random other person": another sampled person's top 10 vs the original (the
                    overlap you get just from the catalogue's popular region).
               (iii) Pearson (O*NET-style) is the reference method.
Metrics:       as above; the headline is mean top-10 overlap and family hit rate for differentiated
               profiles under noise model (b), primary comparison.
Success bar:   Per method, for differentiated profiles (differentiation >= 1.0), noise model (b),
               primary comparison (original vs perturbed), point estimate of the mean:
               PROVEN if mean top-10 overlap >= .60 at occupation level OR mean family hit rate
                 >= .80 (r >= .90 families);
               PROMISING if overlap >= .45 OR family hit rate >= .65;
               NOT VIABLE otherwise.
               The E5 verdict is reported for the Pearson baseline and for each other method.
               The bootstrap model (a), the secondary comparison and the subgroups are reported but
               not gated.
```

---

## Results

Run: `.venv/Scripts/python -I research/feasibility/e5_stability.py --seed 42` (about 4 min). Smoke run first with
`--quick`. The full run was executed twice: the second run added the post-hoc block, which uses a separate RNG stream,
and every pre-registered number was identical between the two runs. Raw results: `research/findings/e5_stability.json`.
- Sample: 5,000 random people from the main table. 4,812 are differentiated (>= 1.0) and 188 are flat (< 1.0).
  9.5% have a tied top type.
- SEM per scale (SD x sqrt(1 - alpha), alpha from E1): R .31, I .34, A .38, S .36, E .36, C .31 scale points.
  The mean absolute change in a scale score per replicate is .27 (SEM noise) and .24 (item bootstrap).
- Families: E3 complete linkage, 172 families at r >= .90 and 101 at r >= .80.
- 95% CIs are percentile bootstraps over people (B = 1000).

### Headline: differentiated profiles, reliability (SEM) noise, original vs perturbed

| Method | Top-10 overlap [95% CI] | Top-5 | Top-3 | Same top-1 occupation | Kendall tau-b, top-20 | **Family hit, r >= .90 [CI]** | Family Jaccard | Family hit, r >= .80 |
|---|---|---|---|---|---|---|---|---|
| **pearson** | **.553** [.549, .558] | .485 | .436 | .326 | .41 | **.697** [.692, .700] | .51 | .741 |
| hexagon | .546 [.541, .550] | .468 | .416 | .313 | .40 | .703 [.699, .708] | .52 | .751 |
| euclid_z | .515 [.512, .518] | .451 | .405 | .309 | .36 | .663 [.660, .667] | .46 | .715 |
| cosine_centered | .451 [.446, .455] | .379 | .331 | .233 | .33 | .610 [.605, .614] | .42 | .666 |
| Baseline: random top-10 | .011 | | | | | .043 | | .068 |
| Baseline: random other person (Pearson) | .068 | | .039 | | | .120 | | |

**Holland code agreement** (person scores, so the same for every method; differentiated, SEM noise):
- Top-1 letter: .76 (random other person .23).
- Same 3-letter set: .66 (.14).
- Exact ordered 3-letter code: **.38** (.02).

**Other noise models and the secondary comparison (Pearson, differentiated):**

| Noise model / comparison | Top-10 overlap | Family hit r >= .90 | Exact Holland code |
|---|---|---|---|
| SEM noise, original vs perturbed (primary) | .553 | .697 | .38 |
| SEM noise clipped to [1, 5] (25 reps) | .558 | .700 | .37 |
| Item bootstrap, original vs perturbed | .572 | .710 | .41 |
| SEM noise, replicate vs replicate (retest-like) | .424 | .568 | .25 |
| Item bootstrap, replicate vs replicate | .449 | .588 | .29 |

### By differentiation (`e5_overlap_by_differentiation.png`; Pearson, SEM noise, primary)

| Differentiation | n | Top-10 overlap | Family hit r >= .90 | Top-3 overlap | Exact Holland code |
|---|---|---|---|---|---|
| < 1.0 (flat) | 188 | **.17** | .27 | .10 | .08 |
| 1.0-1.5 | 550 | .33 | .46 | .22 | .17 |
| 1.5-2.0 | 976 | .46 | .60 | .33 | .27 |
| 2.0-2.5 | 1,163 | .55 | .70 | .42 | .36 |
| >= 2.5 | 2,123 | **.66** | **.80** | .55 | .48 |
| Low elevation (< 2.0) | 506 | .46 | .62 | .33 | .30 |

The Spearman correlation between person-level top-10 overlap and differentiation is .76 (Pearson), .73 (hexagon),
.63 (cosine_centered) and .35 (euclid_z). Differentiation is a strong, cheap predictor of how much a person's list can
be trusted. euclid_z is the exception: flat profiles are almost as "stable" as differentiated ones (.48), because it
ranks on elevation and sends them to the same job zone 2 R occupations (E3), so its stability is not a virtue.

### Subgroups (Pearson, SEM noise, all profiles; `e5_subgroups.png`)

| Group | n | Top-10 overlap | Family hit | Exact Holland |
|---|---|---|---|---|
| Male | 1,611 | .50 | .64 | .33 |
| Female | 3,355 | .56 | .70 | .38 |
| Other (pooled; small n) | 29 | .59 | .71 | .41 |
| 13-17 | 918 | .54 | .67 | .35 |
| 18-24 | 1,875 | .53 | .67 | .36 |
| 25+ | 2,207 | .55 | .69 | .38 |
| Male 13-17 / 18-24 / 25+ | 277 / 556 / 778 | **.46** / .49 / .52 | .60 / .62 / .66 | .30 / .33 / .34 |
| Female 13-17 / 18-24 / 25+ | 632 / 1,302 / 1,421 | .57 / .54 / .56 | .70 / .69 / .71 | .37 / .37 / .39 |
| Top type R / I / A / S / E / C / tied | 149 / 1,224 / 905 / 1,527 / 291 / 430 / 474 | .36 / .55 / **.65** / .54 / .50 / .41 / .48 | .53 / .69 / .75 / .71 / .64 / .56 / .62 | |

Lists are less stable for men, especially teenage boys (.46 vs .57 for teenage girls). This matches E1/E2, where males
have less differentiated profiles (flat 8.6% in males 13-17). A-top people have the *most* stable lists, because their
pool is tiny (E3: 3 occupations at r >= .80), so the same few occupations come back. R- and C-top people have the
least stable lists, because their region holds dozens of near-duplicate occupations (E3: a 97-member R family), and
noise reshuffles near-ties.

### Robustness: incl-shared-network table (5,000 people, 20 replicates, alpha from E1 incl-shared)

| Pearson | Main | Incl. shared |
|---|---|---|
| Differentiated: top-10 overlap / family hit (SEM) | .553 / .697 | .545 / .688 |
| Differentiated: top-10 overlap / family hit (item bootstrap) | .572 / .710 | .566 / .703 |
| Flat: top-10 overlap (SEM) | .17 | .19 |
| 13-17: top-10 overlap / family hit (SEM) | .54 / .67 | .52 / .66 |

The other methods move by <= .01. No conclusion changes.

### Post hoc (exploratory, NOT pre-registered; `e5_posthoc_curves.png`, `posthoc_exploratory` in the JSON)

**(1) Stability vs noise size: a ceiling guide for E4.** Differentiated profiles, Pearson, 20 replicates per point.
"Scale r" is the mean per-scale correlation across people between the original and perturbed scores, which is the
quantity E4 calls "r with full scores".

| Noise SD | Scale r | Profile r (median, within person) | Top-10 overlap | Family hit r >= .90 | Top-3 families (r >= .90) |
|---|---|---|---|---|---|
| 0.25 x SEM | .996 | .997 | .87 | .94 | .86 |
| 0.5 x SEM | .983 | .987 | .75 | .86 | .75 |
| 0.75 x SEM | .964 | .972 | .64 | .78 | .64 |
| 1.0 x SEM | .938 | .952 | .55 | .70 | .56 |
| 1.5 x SEM | .875 | .900 | .41 | .56 | .42 |
| 2.0 x SEM | .805 | .839 | .32 | .45 | .32 |

The hexagon method gives the same curve (within .01). **Under this noise model, a top-10 overlap of 70% needs a scale r
of about .975 with the full test (noise about 0.6 x SEM), and r = .90 corresponds to only about 45% overlap.**

**(2) Family granularity** (Pearson, 1 x SEM, differentiated; chance = a random 10 or a random 3 families):

| r_min | Families | Family hit, top-10 (chance) | Top-3 families overlap (chance) |
|---|---|---|---|
| .50 | 36 | **.81** (.13) | .69 (.08) |
| .60 | 50 | .79 (.11) | .67 (.06) |
| .70 | 68 | .77 (.10) | .64 (.04) |
| .80 | 101 | .74 (.07) | .60 (.03) |
| .90 | 172 | .70 (.04) | .56 (.02) |
| .95 | 286 | .64 (.02) | .50 (.01) |

Coarsening helps only slowly. Even 36 very broad families give a family hit rate of .81 and a top-3-family overlap of .69.

## Verdict (against the pre-registered bar)

Bar: differentiated profiles, SEM noise, original vs perturbed. Proven needs top-10 >= .60 or family hit >= .80;
promising needs >= .45 or >= .65.

| Method | Top-10 overlap | Family hit (r >= .90) | Verdict |
|---|---|---|---|
| pearson | .553 [.549, .558] | .697 [.692, .700] | **PROMISING** |
| hexagon | .546 | .703 | **PROMISING** |
| euclid_z | .515 | .663 | **PROMISING** |
| cosine_centered | .451 | .610 | **PROMISING** (just: .451 >= .45) |

**Overall: PROMISING, not proven.** The 48-item test gives clearly better than chance agreement (about 50x chance at
occupation level and 16x at family level), but even the full test does not produce a top-10 list that is stable at
the level of individual occupations. Only the most differentiated third of people (>= 2.5) reach the bar (.66 / .80).
My hypothesis (50-65% for occupations, >= 80% for families) was right for occupations and too optimistic for families.

## Caveats

- **The noise models are approximations.** The CTT model adds independent, homoscedastic Gaussian noise per scale and
  ignores the R floor (12% at R = 1.0) and correlated errors between scales. Clipping made no difference (.558 vs .553).
  The item bootstrap treats the 8 items as exchangeable, but they differ in content (E2: I has two facets) and in quality.
- "Original vs perturbed" has error variance SEM^2, so it approximates *true vs observed* agreement, not test-retest.
  The retest-like comparison (replicate vs replicate) is about .13 lower (.42 top-10). No real retest data exist for
  this sample, and real test-retest stability of interests over weeks is also affected by true change. Both numbers
  should be quoted.
- Alpha is a lower bound on reliability for congeneric items. With omega (about .01 higher, E1), the SEM shrinks by
  about 3-5% and overlap would rise by about .01-.02 (from the post-hoc curve).
- Overlap metrics treat all positions equally. A swap between rank 10 and 11 counts the same as losing the top-1.
  Kendall tau-b on the top-20 (.41) shows that the order inside the lists is also unstable.
- The sample of 5,000 gives tight CIs overall (+/- .005), but small subgroup cells (R-top 149, gender "other" 29) are
  noisy.
- Same population caveats as E1-E3: self-selected, young, female-majority and US-heavy online sample. O*NET interest
  ratings are model-estimated.

## Implications for the product and for E4

1. **Ceiling for E4.** The E4 skill's proposed bar (r >= .90 with full scores and >= 70% top-10 overlap within 20 items)
   is internally inconsistent under these models:
   - r = .90 with the full test corresponds to about 45% top-10 overlap, and 70% needs r of about .975 (noise of
     about 0.6 x SEM).
   - Even a perfect re-measurement with the full 48 items only reaches 55% (true vs observed) or 42% (retest-like).
   - Recommendation for the psychometrician: judge E4 by **retained stability relative to the full test**, e.g. "the
     CAT top-10 overlap with the full test is >= X% of the full test's own SEM-noise overlap". Also judge it at the
     **family level** (top-3 families or a family hit rate), not by exact occupation lists. Use the noise-scale table
     above to convert θ-recovery r into expected overlap.
2. **Present families with examples, not a ranked list of 10 jobs.** Family-level presentation is consistently more
   stable (+.14 to +.25 over occupation level). The exact ranking and the exact 10 jobs are mostly noise beyond the top
   few families.
   - Suggested display: the top 3 families, each with 2-3 example occupations, using r >= .80 (101 families; top-10
     family hit .74, top-3 overlap .60) or r >= .70 (68 families; .77 / .64).
   - r >= .90 families (172) are too fine to be stable, and r >= .50 (36) are too broad to be informative. **Default
     recommendation: r >= .80 families (about 100)**, later relabelled by hand into user-friendly names.
   - Never show a numeric rank or match percentage at finer than family level.
3. **Use differentiation as the confidence gate.** Below 1.0 (4% of people) the top-10 overlap is .17, which is close
   to "random person" levels. Show these users the "lost user" exploration flow (broad families, activities, try-outs),
   not a ranked list. Between 1.0 and 1.5 (11%) the overlap is .33: show broad families with a "your answers point in
   several directions" message. The E1 flat threshold (1.0) is confirmed as the hard gate, and 1.5 is a sensible soft
   gate.
4. **Show the Holland code as a 2-letter code or as top-1 plus "also", not as an ordered 3-letter code.** The exact
   3-letter order agrees only 38% of the time under noise, the top letter 76%. Display ties explicitly.
5. **Matching method.** Pearson and hexagon are equally stable and the most stable shape methods. cosine_centered is
   the least stable. euclid_z looks stable for flat profiles only because it ignores shape. This supports **Pearson as
   the default** (E3).
6. **Fairness input.** Lists are less stable for males (.50 vs .56), especially boys 13-17 (.46), because their profiles
   are flatter (E1/E2). If unaddressed, teenage boys will get noisier recommendations. Mitigations: the differentiation
   gate, more items for flat profiles in the CAT (stop on SE, not on item count), and rewritten DIF-affected items
   (E2).
7. **R- and C-leaning users get unstable lists among near-duplicates.** Family grouping fixes most of this. Within a
   family, rank by other criteria the user can see (job zone, wages, outlook) rather than by tiny differences in
   interest r.
