# E2 — Factor structure, hexagon fit, invariance and interest archetypes

Pre-registered 2026-11-14 before any E2 analysis was run (only row counts and column names had been inspected).
Script: `research/feasibility/e2_structure.py` (`--seed 42`, `--quick` for a smoke run).
Outputs: `research/findings/e2_structure.json`, `research/findings/e2_*.png`.

## Pre-registration

**Question.** Do the 48 OpenPsychometrics RIASEC items recover six interest factors arranged in Holland's
circular (hexagonal) order, is that structure the same across gender and age groups, and are there stable,
interpretable interest "archetypes" that could be used for user-facing personas or for the "lost user" logic?

**Hypotheses (with sources).**
- H1 (factors). Six correlated factors, one per RIASEC type, because the items come from the O*NET Interest
  Profiler item pool written to measure six types (items listed in the dataset codebook; source:
  https://openpsychometrics.org/_rawdata/). Expect simple structure for most items; Investigative items are
  biology-heavy (e.g. I6 "Study whales") so a narrower I factor is expected.
- H2 (hexagon). In U.S. majority samples the circular order is supported (Tracey & Rounds 1993, secondary only,
  see `research/notes/01-interest-theory-and-outcomes.md`), but it fails in many international and U.S.
  ethnic-minority samples (Rounds & Tracey 1996, level A, note 01). Our sample is 55% U.S. with many other
  countries, so we expect the order to hold overall but with a weaker fit than an all-U.S. sample.
- H3 (invariance). Configural and metric invariance usually hold across gender, scalar often fails (small
  studies summarised in `research/notes/06-fairness-ethics-undecided-users.md`, level C). Mean differences by
  gender should resemble Su, Rounds & Armstrong 2009 (level A, note 06): men higher on R (d = 0.84) and
  I (0.26); women higher on A (-0.35), S (-0.68) and C (-0.33); Things-People d = 0.93. Sign convention here:
  d = (male - female) / pooled SD, as in Su et al.
- H4 (archetypes). Interest profiles are continuous, so GMM is expected to show weak cluster separation:
  BIC may keep improving with k, and stability may be modest. We have no literature benchmark for this.

**Data.** `data/processed/riasec_people.parquet` (n = 80,085 after the riasec-scoring filters; shared-network
rows dropped). Robustness: `data/processed/riasec_people_incl_shared_network.parquet` (n = 115,974).
Items R1-C8, 1-5, NaN = missing. Gender: 1 male (25,499), 2 female (53,870); "other" (622) and missing are
excluded from gender comparisons only. Age bands: 13-17, 18-24, 25+.

**Method.**
1. Random 50/50 split (seed 42): half A = exploration, half B = confirmation.
2. Factor retention on half A: Horn's parallel analysis (PA) on PCA eigenvalues vs the 95th percentile of
   eigenvalues from random normal data of the same n and p (primary). Secondary: PA on the reduced
   (SMC) correlation matrix, Velicer's MAP.
3. EFA on the Pearson item correlation matrix (pairwise complete), minres, 6 factors, oblimin (primary) and
   promax (comparison). Factors matched to scales by Hungarian assignment on mean loadings. An item "loads
   correctly" if its largest absolute loading is on its intended factor and that loading is >= .40.
   Cross-loading flag: any other |loading| >= .30. The same EFA on half B; Tucker congruence A vs B.
4. Reliability per scale: Cronbach's alpha, McDonald's omega total (one-factor model), item-rest r.
5. CFA (independent-clusters, 6 correlated factors, ML on covariance matrices), implemented in numpy/scipy
   because `semopy`/`lavaan` are not installed. Multi-group configural / metric / scalar models by gender and
   by age band. Criteria (Chen 2007 convention, to be cited as `[UNVERIFIED]` until sourced): a step is
   acceptable if delta CFI >= -.010 and delta RMSEA <= .015. Item-level uniform DIF by gender: OLS of item on
   the rest score of its scale plus gender; DIF = gender coefficient / item SD.
6. Hexagon: scale correlations (6 x 6); mean adjacent, alternate and opposite r; Hubert & Arabie-style
   randomisation test of hypothesised order (RTOR): 72 order predictions (adjacent > alternate, adjacent >
   opposite, alternate > opposite), correspondence index CI = (agreements - violations) / 72; p = share of
   all 720 label permutations with CI >= observed (the smallest attainable p is 12/720 = .017 because 12
   permutations are rotations/reflections of the hexagon). Bootstrap 95% CI of the index (persons resampled).
   Metric MDS on 1 - r, and PCA of person-centred scale scores; the order check passes if the angular order
   of the 6 points is R-I-A-S-E-C up to rotation and reflection.
7. Prediger coordinates: angle-based projection from the riasec-scoring skill on the person-centred profile,
   theta_k = k * 60 deg (R = 0): x = sum s_k cos theta_k (Things +, People -), y = sum s_k sin theta_k
   (Ideas +, Data -). Vendor formulas in note 01 (Strong supplement, level D) as a secondary comparison only.
8. Groups: male vs female; 13-17 vs 18-24 vs 25+. Per group: 6-factor oblimin EFA, Tucker congruence for
   each factor between every pair of groups, the hexagon tests in item 6, and Cohen's d by gender
   (with 95% CI) for the six scales and both Prediger axes, compared with Su et al. 2009.
9. Archetypes: Gaussian mixture models (full covariance) on (i) the person-centred raw profile (shape only,
   represented in a 5-D orthonormal basis because centred profiles sum to zero), and (ii) shape plus
   elevation (person mean of the six scales). k = 1-15 (k = 1 as reference). Sensitivity: the same on
   z-scored-then-centred profiles.
   - k selection rule (fixed now): k_BIC = argmin BIC over 2-15. If the minimum is at k >= 13 (no interior
     minimum), use the elbow: the smallest k for which the BIC gain from k to k+1 is below 10% of the gain
     from 1 to 2. Then apply interpretability limits: every cluster >= 3% of the sample and no two centroid
     profiles correlated > .90; if violated, step k down until satisfied.
   - Stability: 10 GMM fits with different seeds on the full data, mean (and min) pairwise ARI of hard
     labels; split-half: fit on half A and on half B, label everyone with both, ARI (10 random splits).
   - "Flat/undecided" member (fixed now): differentiation (max - min raw scale mean) < 1.0 scale point.
     Also reported: low elevation (mean of 6 scales < 2.0).
   - Gender fairness flag per archetype: one gender >= 80% of its male/female members, or the
     representation ratio (share in archetype / share in sample) of either gender >= 1.5 or <= 0.67.
10. Robustness: re-run PA, EFA item counts, A/B congruence, hexagon tests, gender d, chosen-k GMM stability
    on the incl-shared-network table.

**Baselines.** For the hexagon: the 720 random label permutations (RTOR null). For factor retention: random
data eigenvalues (PA). For archetypes: k = 1 (a single Gaussian) in the BIC curve. No O*NET Pearson
baseline applies (no matching in E2).

**Metrics.** Number of factors retained; items loading correctly (of 48); Tucker congruence; alpha, omega;
CFA CFI / RMSEA / SRMR; RTOR CI and p; mean r by hexagon distance; MDS order; Cohen's d (95% CI); BIC; ARI.

**Success bars (fixed before running; not to be changed).**
- (a) Factors. **Proven**: PA (primary) retains exactly 6 AND >= 44/48 items load correctly in the 6-factor
  EFA on half A AND Tucker congruence A vs B >= .95 on all 6 factors. **Promising**: >= 44/48 items load
  correctly and congruence >= .90, but PA suggests a number other than 6 (or only 40-43 items correct).
  **Not viable**: < 40 items correct or any factor congruence < .90.
- (b) Hexagon. **Proven**: mean adjacent r > mean alternate r > mean opposite r AND RTOR p <= .05 (the
  minimum attainable, .017) AND MDS order R-I-A-S-E-C (up to rotation/reflection). **Promising**: the mean
  ordering and RTOR p <= .05 hold but MDS shows one adjacent swap. **Not viable**: otherwise.
- (c) Group structure. **Proven**: Tucker congruence >= .90 for every factor in every group pair (gender and
  age) AND the hexagon order (mean ordering, RTOR p <= .05, MDS order) holds in every group. **Promising**:
  congruence >= .90 for >= 5 of 6 factors in every pair and the hexagon holds in every group (or all
  congruences pass but one group fails the MDS order). **Not viable**: otherwise. The multi-group CFA is a
  bonus (reported, not part of the bar).
- (d) Archetypes. **Proven**: the chosen k gives mean pairwise seed ARI >= .70 AND mean split-half ARI >= .70,
  with interpretable centroids (distinct top-2 codes or clearly distinct shapes). **Promising**: one of the
  two ARIs >= .70 and the other >= .50. **Not viable**: otherwise. Judged separately for the shape-only and
  shape + elevation variants.

---

## Results

Run: `.venv/Scripts/python -I research/feasibility/e2_structure.py --seed 42`, then `--robust-only` to write the
extended robustness block (21 min total on a laptop). n = 80,085 (half A 40,042, half B 40,043); 5,829 missing item
cells (0.15%). Sample: self-selected website visitors, median age 23 in this table, 67.9% female among male/female,
about 55% U.S. (`research/DATA_SOURCES.md`). All numbers are evidence level E (our own experiment).
Raw results: `research/findings/e2_structure.json`.

### (a) Factor structure (`e2_parallel_analysis.png`, `e2_efa_loadings.png`)

| Check | Result |
|---|---|
| PCA eigenvalues 1-10 (half A) | 9.20, 5.63, 4.54, 2.89, 2.13, 1.72, **1.30, 1.06**, 0.92, 0.89 |
| Random-data 95th percentile (PCA) | 1.07, 1.06, 1.06, 1.06, 1.05, 1.05, 1.05, 1.04, ... |
| Parallel analysis, PCA (primary) | **8** factors (7th and 8th only just above random) |
| PA on reduced (SMC) matrix / Velicer MAP / Kaiser | 21 / **7** / 8 |
| 7-factor EFA | 7th factor has no item loading >= .40 (empty factor) |
| 8-factor EFA | splits Investigative into medical/lab (I1, I4, I5, I7) and nature/animal (I2, I3, I6, I8) |
| 6-factor oblimin EFA: items loading correctly (>= .40, on intended factor) | **45/48** in half A, 45/48 in half B, 45/48 promax |
| Failing items (all three solutions) | R1 (.36 R; .27 C), A7 (.28 A; .27 R; .23 E), S4 (.36 S) |
| Weak but passing | E8 .43, E5 .46 (.29 C), I8 .47 (.24 R), S1 .47 |
| Cross-loadings >= .30 | none |
| Tucker congruence half A vs half B | .9996-.9998 for all six factors |
| Tucker oblimin vs promax | .994-.998 |
| CFA (independent clusters, ML), half B | chi2 = 185,923, df = 1,065, **CFI .804**, RMSEA .066, SRMR .064 |

PA with n = 40,000 flags very small extra components, which is a known tendency of PA in very large samples. The
extra dimension that is real is a content split inside the Investigative scale (biology/medicine vs nature/animals).
There is no extra RIASEC-type factor.

Reliability (full sample):

| Scale | alpha | omega_t | lowest item-rest r | alpha rises if item deleted |
|---|---|---|---|---|
| R | .870 | .874 | R1 .47 | R1 |
| I | .890 | .892 | I8 .54 | - |
| A | .857 | .860 | A7 .39 | A7 |
| S | .841 | .844 | S4 .42 | S4 |
| E | .831 | .833 | E4 .47 | - |
| C | .898 | .899 | C6 .60 | - |

Factor correlations. EFA oblimin (half A) ranges from -.07 (A-C) to .40 (E-C). CFA latent correlations (half B):
E-C .58, R-C .50, S-E .42, R-E .34, A-S .34, I-A .33, R-I .32, A-E .30, then <= .18 for alternate and opposite pairs
(R-S .06, I-E .02, A-C -.04).

### (b) Hexagon (`e2_hexagon_mds.png`)

Scale correlations (n = 80,085):

|   | R | I | A | S | E | C |
|---|---|---|---|---|---|---|
| R | 1 | .30 | .19 | .08 | .30 | .47 |
| I | | 1 | .32 | .18 | .03 | .08 |
| A | | | 1 | .31 | .28 | -.02 |
| S | | | | 1 | .38 | .15 |
| E | | | | | 1 | .49 |

| Check | Result |
|---|---|
| Mean r: adjacent / alternate / opposite | **.378 > .198 > .032** |
| RTOR correspondence index (72 predictions) | **CI = .97** (bootstrap 95% .92-1.00), p = .017 (minimum attainable, 12/720) |
| Half A / half B | CI = 1.00 / .94, both p = .017 |
| Metric MDS on 1 - r | order AIRCES = R-I-A-S-E-C (rotation/reflection) **pass**; normalised stress .118 |
| MDS angles after Procrustes to ideal (0, 60, ..., 300) | R 352, I 61, A 122, S 183, E 245, C 297 degrees (all within 8 degrees) |
| PCA of person-centred scales | order ESAIRC **pass**; PC1-2 explain 62% of centred variance |

Prediger axes. On the person-centred profile, the angle-based x (Things-People) correlates r = 1.00 with the
Strong-supplement People-Things formula, and y (Ideas-Data) correlates r = -1.00 with the vendor Data-Ideas formula
(note 01; level D). This is algebra, not evidence. x is exactly 1/2 x (2R + I - A - 2S - E + C). y is
(sqrt 3 / 2)(I + A - E - C), which is -1/2 x the vendor D/I, because the vendor scores Data as positive. So the two
variants rank people identically and differ only in scale and sign. Corr(x, y) = -.09. Sample means are x = -1.22
(People-leaning) and y = +0.84 (Ideas-leaning).

### (c) Groups (`e2_group_hexagons.png`, `e2_gender_d.png`)

n: male 25,499; female 53,870; 13-17 13,882; 18-24 30,689; 25+ 35,514.

Tucker congruence of 6-factor oblimin loadings between groups:

| Pair | R | I | A | S | E | C |
|---|---|---|---|---|---|---|
| male vs female | .993 | .996 | .990 | .994 | .970 | .984 |
| 13-17 vs 18-24 | .996 | .998 | .997 | .991 | .971 | .973 |
| 13-17 vs 25+ | .987 | .996 | .990 | .985 | **.923** | **.921** |
| 18-24 vs 25+ | .996 | .997 | .993 | .995 | .976 | .979 |

Items loading correctly by group: male 44, female 45, 13-17 **42** (E3, E5, E8 also fail), 18-24 44, 25+ 45.

Hexagon by group: the mean ordering adjacent > alternate > opposite, RTOR p = .017 and the MDS order R-I-A-S-E-C
**hold in all five groups**. RTOR CI: male .92, female .86, 13-17 .83, 18-24 .83, 25+ 1.00. Teenagers have
the flattest gradient (adjacent .42, alternate .26, opposite .12): their scales are more uniformly correlated, which
is consistent with a stronger general "liking" factor at younger ages (interpretation).

Multi-group CFA (bonus; own numpy ML implementation, gradient checked numerically):

| Grouping | Model | CFI | RMSEA | SRMR | delta CFI | delta RMSEA | Step OK? |
|---|---|---|---|---|---|---|---|
| Gender | configural | .806 | .065 | .063 | | | |
| | metric | .805 | .065 | .063 | -.001 | -.000 | yes |
| | scalar | .788 | .067 | .064 | **-.017** | +.002 | **no** |
| Age band | configural | .803 | .066 | .066 | | | |
| | metric | .802 | .066 | .067 | -.001 | -.001 | yes |
| | scalar | .790 | .067 | .067 | **-.012** | +.001 | **no** |

Metric invariance holds: loadings are equivalent, so correlations and structure are comparable. Scalar invariance
fails for both gender and age. Some item intercepts differ between groups at equal latent interest, so raw mean
comparisons across these groups are partly item artefacts. This matches the pattern summarised in note 06. Configural
absolute fit is poor (CFI .80) because the independent-clusters model forbids the adjacent-scale cross-loadings the
circumplex implies; see Caveats.

Gender mean differences, d = (male - female) / pooled SD, 95% CI, compared with Su, Rounds & Armstrong 2009 (note 06):

| | E2 d [95% CI] | Su et al. 2009 | Comment |
|---|---|---|---|
| R | **0.72** [0.71, 0.74] | 0.84 | same direction, slightly smaller |
| I | 0.12 [0.10, 0.13] | 0.26 | smaller |
| A | 0.02 [0.00, 0.03] | -0.35 | **no gap** here |
| S | **-0.38** [-0.40, -0.37] | -0.68 | about half |
| E | -0.00 [-0.02, 0.01] | not in note 06 | |
| C | 0.13 [0.12, 0.15] | -0.33 | **opposite sign** |
| Things-People (x) | **0.67** [0.65, 0.68] | 0.93 | smaller, still large |
| Ideas-Data (y) | 0.01 [-0.01, 0.02] | | |
| Elevation | 0.15 [0.14, 0.17] | | men slightly higher overall liking |
| Differentiation | -0.38 [-0.39, -0.36] | | women have more differentiated profiles |
| Mahalanobis D (6 scales) | 0.90 | Morris 2016: 1.61 (Strong, different instrument) | |

By age band, Things-People d is 0.80 (13-17), 0.72 (18-24) and 0.59 (25+), and R is 0.74, 0.76 and 0.69. The
largest gaps are in the youngest group. This matches the direction Morris 2016 reports (larger sex differences in
younger samples; note 06). Our Things-People d uses angle weights on raw centred means, while Su et al. used their
own composite, so the comparison is approximate. The smaller A/S gaps and the reversed C sign likely reflect item
content. The C items are office/computer tasks ("Use a computer program to generate customer bills"), not
traditional clerical stereotypes, and the sample is a self-selected online audience. This is interpretation, untested.

Item-level gender DIF (item regressed on its scale's rest score; coefficient / item SD; + = women higher at equal
scale level). Largest:

| Item | DIF | Item | DIF |
|---|---|---|---|
| E4 Operate a beauty salon or barber shop | **+0.44** | C4 Maintain employee records | +0.28 |
| R3 Work on an offshore oil-drilling rig | **-0.34** | S2 Volunteer work at a non-profit | +0.27 |
| A7 Perform stunts for a movie or TV show | **-0.34** | E6 Manage a clothing store | +0.26 |
| I8 Make a map of the bottom of an ocean | **-0.33** | A3 Design artwork for magazines | +0.24 |
| R4 Assemble electronic parts | **-0.32** | S4 Teach an exercise routine | -0.24 |
| E1 Sell restaurant franchises | **-0.30** | C5 / E5 statistical data / manage a department | -0.24 / -0.24 |

Age DIF (13-17 minus 25+): S1 "Give career guidance to people" **-0.53** (teens much lower at equal S level),
R6 "Fix a broken faucet" -0.36, E1 +0.26, S6 +0.25, I7 +0.23.

### (d) Archetypes (`e2_gmm_bic.png`, `e2_archetypes_shape.png`, `e2_archetypes_shape_elev.png`, `*_posthoc_kbic.png`)

The BIC has no interior minimum for shape-only profiles. 56% of the total improvement (k = 1 to 15) comes at k = 2,
and the rest declines slowly (argmin 15). The pre-registered elbow rule gives **k = 5**, and no interpretability
step-down was needed. Profiles look like a continuum with soft modes, not discrete types.

**Shape-only, k = 5** (seed ARI mean **.86**, min .38; split-half ARI mean **.81**, min .33; mean max posterior .66):

| Archetype (relative code) | Share | Raw means R I A S E C | % female (sample 67.9%) | Gender flag | Plain-language description |
|---|---|---|---|---|---|
| "Creative communicators" (AE; raw SAE) | 25.1% | 1.8 2.4 3.4 3.4 2.8 2.1 | 73% | no | Likes arts and working with people, including persuading and leading; cool to science, machines and office routines. |
| "Hands-on analysts" (RIC; raw IRC) | 23.6% | 2.8 3.4 2.7 2.7 2.4 2.7 | **47%** | **yes** (men x1.65) | Fairly even, mildly "things"-oriented: more open to practical, technical and organising tasks than most; less drawn to helping and selling. Most flat members (9%) are here. |
| "Curious creators" (AI; raw IAS) | 19.7% | 1.8 3.8 3.7 3.4 2.2 1.7 | 72% | no | Strong science and arts interest, likes ideas; strong dislike of business, sales and office work. The most differentiated profile. |
| "Organisers and managers" (CE; raw CSE) | 15.9% | 2.1 2.1 2.3 3.4 3.1 3.5 | 73% | no | Likes structured office work, data and running things, plus helping people; low interest in science and the arts. |
| "Helpers with a science side" (SI; raw SIE) | 15.7% | 1.7 3.3 2.1 3.7 2.2 2.1 | **81%** | **yes** (men x0.58) | Helping, teaching and caring, plus biology/health-science interest (a nursing/medicine/psychology shape); low arts, business and mechanical interest. Lowest elevation (20% have mean < 2). |

**Shape + elevation.** The pre-registered rule gives k = 2 (the BIC elbow at k = 6 was stepped down because the
centred centroids correlate > .90, so the clusters differ mainly in elevation):

| Archetype | Share | Raw means R I A S E C | Elevation | % female | Flag |
|---|---|---|---|---|---|
| "Broadly engaged" (relative code C) | 69.0% | 2.4 3.1 3.0 3.3 2.8 2.8 | 2.90 | 62% | no |
| "Selective: people and ideas, not things or data" (SA) | 31.0% | 1.3 2.8 2.8 3.2 2.1 1.5 | 2.25 | **80%** | **yes** |

Stability: seed ARI .998, split-half .94, mean posterior .92. Post hoc (not pre-registered), the BIC-rule k = 6
solution is **unstable** (seed ARI .67, split-half .52). It includes an "S" cluster (11.7%) whose members have
R = 1.00 exactly: they answered "Dislike" to all eight Realistic items. **12.1% of the sample is at the R floor**
(C 7.8%; 20.5% have at least one scale at floor). These point masses make the elevation-model BIC curves jump
non-monotonically (`e2_gmm_bic.png`). The cause is GMM fitting the lattice of floor scores, not real types.

z-scored sensitivity: shape-only k = 3, seed ARI .81, split-half .65. Shape + elevation k = 3, .74 / .76.
The shape-only and shape + elevation solutions barely overlap (ARI .07).

**Flat/undecided.** 3.96% of people have differentiation < 1.0 point, and 11.3% have elevation < 2.0. Flat members
concentrate in "Hands-on analysts" (9%) and "Creative communicators" (7%). They are about 0% in "Curious creators"
and "Helpers". No GMM variant produced a distinct "flat" archetype: flat profiles sit near the centre of shape space
and are absorbed by the nearest clusters.

### Robustness: incl-shared-network table (n = 115,974; `robustness_incl_shared_network` in the JSON)

| Headline | Main (80,085) | Incl. shared network (115,974) |
|---|---|---|
| PA (PCA) factors | 8 | 7 |
| Items correct half A / B | 45 / 45 | 45 / 45 |
| Tucker A vs B (min) | .9996 | .9997 |
| Adjacent / alternate / opposite r | .378 / .198 / .032 | .394 / .228 / .070 |
| RTOR CI (p) | .97 (.017) | .92 (.017) |
| MDS order | pass | pass |
| Hexagon holds in all 5 groups | yes | yes |
| Min group congruence | .921 (C, 13-17 vs 25+) | .915 (C, 13-17 vs 25+) |
| Items correct, 13-17 | 42 | 41 |
| Gender d: R / S / C / Things-People | .72 / -.38 / .13 / .67 | .77 / -.44 / .15 / .75 |
| Things-People d in 13-17 | .80 | .96 |
| Shape k = 5 seed ARI | .86 | .96 (5 seeds) |
| Shape + elevation k = 2 seed ARI | .998 | .991 |

Minors (E1 found that the shared-network filter removes many minors). 46% of shared-network rows are 13-17
(16,530, vs 13,882 minors kept). Structure in shared-network minors matches kept minors (congruence .994-.998 on all
six factors; hexagon passes, though with the flattest gradient seen: CI .72, adjacent .43, alternate .30, opposite
.17). Shared-network minors have lower I, A and S means (2.76, 2.59, 2.89 vs 3.02, 2.92, 3.04), which fits school
settings with less engaged respondents (interpretation). Including them raises the teen gender gap on Things-People to
d = .96. **No headline conclusion changes.**

## Verdict (against the pre-registered bars)

| Bar | Verdict | Why |
|---|---|---|
| (a) Factors | **Promising** | 45/48 items load correctly and A/B congruence is >= .9996, but PA retains 8, not 6 (MAP 7; the 7th factor is empty and the 8th splits I into two content facets). "Proven" required PA = 6. |
| (b) Hexagon | **Proven** | .378 > .198 > .032; RTOR CI .97 [.92, 1.00], p = .017 (minimum); MDS and PCA orders R-I-A-S-E-C; angles within 8 degrees of ideal. |
| (c) Group structure | **Proven** | Every factor congruence is >= .92 in every gender/age pair (min .921, E and C, 13-17 vs 25+), and the hexagon holds in all five groups. Bonus MGCFA: metric invariance holds, **scalar fails** for gender and age. |
| (d) Archetypes, shape only | **Proven (by the bar), with caveats** | k = 5: seed ARI .86, split-half .81, distinct relative codes. But min ARIs are .38/.33 (some runs land elsewhere), mean posterior is .66, and BIC shows no natural k. |
| (d) Archetypes, shape + elevation | **Proven (by the bar), but trivial** | k = 2, ARI .998/.94. It is essentially a high- vs low-elevation split with a floor-driven low-R/C profile. The post-hoc k = 6 is not viable (.67/.52). In hindsight the bar was too weak: it rewards a stable but uninformative 2-cluster split. We keep the original bar, as the protocol requires. |

## Caveats

- **Sample**: self-selected online test-takers, 68% female, young and about 55% U.S. (`DATA_SOURCES.md`), so not
  representative. Rounds & Tracey (1996, note 01) show that circular-order fit varies across cultures. We did not test
  by country or language, and the target market (Spain/EU) is untested.
- **Pearson correlations on 5-point Likert items** (polychoric/WLSMV not available). This attenuates loadings and can
  add difficulty factors. ML CFA on Pearson covariances is an approximation. `semopy` / R `lavaan` were not installed
  (no installs were allowed), so the CFA and MGCFA use our own numpy/scipy ML implementation (analytic gradient,
  checked against finite differences to 1e-9; converged from perturbed starts to the same optimum). It is not
  validated against lavaan.
- **CFA absolute fit is poor (CFI ~.80)** for the strict independent-clusters model. The invariance conclusions rest
  on delta-fit between nested models (delta CFI .010 / delta RMSEA .015 convention, Chen 2007 `[UNVERIFIED: not in
  notes]`). These deltas are reliable at this n, but the baseline model is misspecified.
- **Parallel analysis in very large samples** retains trivially small components; we pre-registered it as primary
  anyway, and the verdict follows the bar.
- **The Su et al. comparison is approximate**: different inventories, items and composite formulas. The note-06
  numbers come from abstracts and search summaries. E is not listed in note 06.
- **Item-DIF** uses a simple rest-score regression (uniform DIF only), not IRT-based DIF.
- **GMM** is sensitive to floor point masses (12% at R = 1.0). Cluster structure is soft (mean posterior .66), and the
  k-selection rule was ours, fixed in advance. It is not from the literature.
- `factor_analyzer` 0.5.1 is incompatible with scikit-learn 1.9.1 (`force_all_finite` was renamed). The script
  patches `check_array` in-process (same approach as E1); no package files were changed.
- Deviations from the pre-registration (all additive): post-hoc reporting of the BIC-rule k when the interpretability
  rule stepped k down; group-level and minors robustness checks added after E1 reported the minors imbalance.

## Implications for the product

1. **Questionnaire items.** Drop or rewrite R1 (quality inspection reads as clerical/C), A7 (movie stunts: loads on
   R, A and E, and has strong male DIF) and S4 (exercise routine: weak S, male DIF). Rewrite or balance the strongest
   gender-DIF items: E4 (beauty salon/barber, +.44 female), R3 (oil rig), I8 (ocean mapping), R4, E1. Pair them with
   counter-stereotypic items so each scale's DIF nets to about zero. For teen users, S1 "career guidance" behaves
   differently (DIF -.53). The Enterprising scale is the least invariant across age and should get new items written
   for teenagers. Investigative content is nearly all biology/medicine: add computing, physics, maths and engineering-
   science activities, or I will under-recommend tech/physical-science careers. Item-writing guidelines (for the
   research-editor): one concrete activity per item, reading level around age 12, no gendered occupations or settings
   (salon, oil rig, stunts), no culture-specific institutions, avoid "sell X" for all of E (vary between leading,
   persuading and starting things), and DIF-screen every new item by gender and age before release.
2. **Adaptive test (E4).** Six correlated factors are justified. Latent correlations reach .58 (E-C), .50 (R-C) and
   .42 (S-E), so a correlated multivariate-normal prior in EAP can borrow information between adjacent scales. Most
   alternate/opposite correlations are < .20, so the gain will be modest. Recommendation: six unidimensional GRMs with
   a 6-D correlated prior (CFA phi from this run) as the default, and full MIRT only if E4 shows a clear gain.
   Calibrate GRMs per scale. Treat I as possibly two facets (check local dependence among I2/I3/I6 and I1/I4/I5/I7).
3. **Scoring.** Score **normatively** (theta per scale; IRT needs it), then derive the **shape** (person-centred
   profile) for occupation matching and keep **elevation** separate for the lost-user logic. Ipsative-only scoring
   would hide the 11% with low elevation and the 12% who reject all Realistic items. Scalar non-invariance means raw
   cross-group level comparisons (e.g. "women score lower on R") partly reflect item content. Do not norm or compare
   by gender, and remove high-DIF items rather than adjusting scores by group.
4. **Prediger map.** Use the angle-based projection. It is mathematically equivalent (r = |1.00|) to the vendor
   formulas, so there is no conflict. The hexagon is well supported in this sample, so a 2-D map with "Things-People"
   and "Ideas-Data" axes is a defensible explanation device. Things-People is where the gender gap lives (d = .67;
   .80 for teens). The fairness audit should report how often women and men are steered along this axis.
5. **Archetypes and personas.** The 5 shape archetypes are reproducible on average but soft (two-thirds posterior),
   and 2 of 5 are gender-flagged ("Hands-on analysts" 53% male vs 32% base; "Helpers with a science side" 81% female).
   Use them at most as internal segments or as soft "you resemble" descriptions with gender-neutral wording. Do not use
   them as user-facing labels. Prefer the continuous profile and map.
6. **Lost users.** A flat profile (differentiation < 1.0) is rare in this sample (4%), and no "flat" archetype
   emerges. Low elevation (11%) is the more common signal. The lost-user rule should combine low elevation, low
   differentiation and high theta uncertainty (from E4), not rely on a cluster.

## Sources
- Rounds, J., & Tracey, T. J. G. (1996). Cross-cultural structural equivalence of RIASEC models and measures. J Counseling Psychology 43(3). https://experts.illinois.edu/en/publications/cross-cultural-structural-equivalence-of-riasec-models-and-measur/ (via note 01)
- Tracey & Rounds (1993), Psychological Bulletin 113: secondary only, `[UNVERIFIED]` (note 01)
- Su, R., Rounds, J., & Armstrong, P. I. (2009). Men and things, women and people. Psychological Bulletin 135(6), 859-884. https://iro.uiowa.edu/esploro/outputs/journalArticle/Men-and-things-women-and-people/9984380502202771 (via note 06)
- Morris, M. L. (2016). Vocational interests in the United States. J Counseling Psychology 63(5). https://hk.themyersbriggs.com/content/Research%20and%20White%20Papers/Strong/Morris_2016_Vocational_Interests_in_the_United_States_JCounselingPsych.pdf (via note 06; correction notice unchecked)
- Strong Interest Inventory technical supplement ch. 4 (vendor formulas, level D). https://strongsupplement.themyersbriggs.com/chapter4.html (via note 01)
- Invariance pattern in small studies (level C, `[UNVERIFIED]`), note 06.
- Chen, F. F. (2007). Sensitivity of goodness of fit indexes to lack of measurement invariance. Structural Equation Modeling 14(3): `[UNVERIFIED: not yet in notes; convention used for delta CFI / delta RMSEA]`.
- Hubert, L., & Arabie, P. (1987). Evaluating order hypotheses within proximity matrices. Psychological Bulletin 102: `[UNVERIFIED: method reference, not in notes]`.
- OpenPsychometrics RIASEC data and codebook (item wording). https://openpsychometrics.org/_rawdata/
