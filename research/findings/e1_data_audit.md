# E1 — Data audit of the OpenPsychometrics RIASEC dataset

_Pre-registered 2026-11-14, before running `research/feasibility/e1_data_audit.py`._

```
Question:      Is the OpenPsychometrics RIASEC 2018 dataset (after the documented cleaning) fit for
               Career Compass's v0 experiments (E2-E6), and what are its biases and limits?
Hypothesis:    Yes for structure/IRT/CAT work: the 8-item scales of this inventory should be internally
               consistent (alpha >= .80 each) and the cleaned table has ~80k rows. Expected limits (from
               research/DATA_SOURCES.md): young (median ~21-23), ~65-67% female, ~55% US, self-selected,
               no license; the `major` field is free text, filled for ~70% of rows, and dominated by
               psychology. Gender differences in R and S should be in the direction reported by
               Su, Rounds & Armstrong (2009) (men higher R, women higher S; see research/notes/06).
Data:          data/processed/riasec_people.parquet (80,085 rows; main)
               data/processed/riasec_people_incl_shared_network.parquet (115,974 rows; robustness)
               data/processed/onet_occupations.parquet (923 occupations; descriptive comparison)
               data/raw/openpsych_riasec_2018/RIASEC_data12Dec2018/data.csv + codebook.txt (read-only,
               to recompute the filter funnel and confirm codebook fields)
Method:        1. Recompute the filter funnel from raw and compare with the build log; compare the main
                  table with the shared-network rows (standardised mean differences, SMD) on scale
                  means/SDs and demographics.
               2. Item stats: mean, SD, % missing, corrected item-total r, % floor (1) / ceiling (5).
               3. Reliability per scale: Cronbach alpha and McDonald's omega (1-factor minres solution,
                  factor_analyzer, standardised loadings); percentile bootstrap 95% CIs
                  (alpha B=1000, omega B=500; seed 42). Also by gender and age band.
               4. Demographics decoded with codebook.txt; gender x age-band grid counts.
               5. Profile shape: differentiation (max-min of the 6 scale means) and elevation (mean of
                  the 6); % "flat" profiles with differentiation < 1.0 (pre-registered threshold;
                  0.5 and 1.5 reported as sensitivity), with bootstrap CI and by subgroup.
               6. `major`: fill rate by age band, top-50 normalised values, unique raw values, and a
                  rule-based first-pass mapping into ~15-25 major families ->
                  research/findings/e1_major_families_draft.csv.
               7. Descriptive comparison of the mean centred person profile with the mean centred O*NET
                  occupation profile, and of top-type base rates (scales differ: 1-5 vs 1-7).
Baselines:     Audit, not a predictive model, so no majority-class baseline applies. Reference points:
               (a) the build log in DATA_SOURCES.md (funnel must reproduce exactly);
               (b) the incl-shared-network table (robustness);
               (c) a random-response baseline for reliability: alpha/omega after independently
                   permuting each item column (expected ~0);
               (d) literature gender effect sizes (Su et al. 2009, via research/notes/06);
               (e) the mean O*NET occupation profile (descriptive only).
Metrics:       clean row count; per-item % missing; alpha and omega with 95% CI; subgroup cell n;
               SMD (|SMD| < 0.10 treated as negligible, common rule of thumb); % flat profiles;
               major fill rate; % of filled (non-junk) major rows mapped to a family (coverage).
Success bar:   PROVEN (fit for purpose) if ALL of:
                 (i)   >= 50,000 clean rows in the main table;
                 (ii)  all 48 items have <= 2% missing after cleaning;
                 (iii) Cronbach alpha >= .80 for each of the 6 RIASEC scales (point estimate) in the main table;
                 (iv)  every cell of gender (male/female) x age band (13-17, 18-24, 25+) has n >= 1,000.
               PROMISING if (i) and (ii) hold and at most one of (iii)/(iv) fails narrowly
                 (one scale with .70 <= alpha < .80, or one or two grid cells with 500 <= n < 1,000).
               NOT VIABLE if (i) or (ii) fails, or any scale alpha < .70.
               Secondary (reported, not gating): the funnel reproduces the build log; codebook fields
               are confirmed in the raw header; the major-family draft maps >= 80% of filled
               non-junk major rows.
```

## Results

Full run on 2026-11-14 with `python -I research/feasibility/e1_data_audit.py --seed 42` (about 2 min).
Every number below comes from `research/findings/e1_data_audit.json`. Main table n = 80,085 unless stated otherwise.

### 1. Filter funnel and the shared-network filter
I recomputed the funnel from the raw `data.csv`. It matches the build log in `research/DATA_SOURCES.md`
exactly at every step. All 93 codebook fields are in the raw header, and every coded field is inside its
codebook range (0 = no answer). There are 21,435 item cells coded `0`.

| Step (sequential) | Rows after | Removed | Hits if applied alone |
|---|---|---|---|
| raw | 145,828 | 0 | |
| any fake VCL word | 116,543 | 29,285 | 29,285 |
| straight-lining (48 answered, same value) | 116,298 | 245 | 388 |
| >= 5 of 48 items missing | 116,042 | 256 | 361 |
| age < 13 or > 90 | 115,990 | 52 | 101 |
| exact duplicates | 115,990 | 0 | 0 |
| shared network | 80,096 | 35,894 | 45,101 |
| any scale < 6 of 8 answered | **80,085** | 11 | |

**Main table vs the 35,889 shared-network rows.** SMD = main minus shared. |SMD| >= 0.10 is flagged in `e1_main_vs_shared_smd.png`.

| Variable | Main | Shared-network | SMD |
|---|---|---|---|
| R / I / A mean (1-5) | 2.07 / 3.01 / 2.90 | 2.11 / 2.85 / 2.71 | -0.04 / **0.15** / **0.18** |
| S / E / C mean | 3.28 / 2.54 / 2.40 | 3.19 / 2.62 / 2.37 | 0.09 / -0.09 / 0.02 |
| Scale SDs | 0.86-1.03 | 0.93-1.06 | main/shared ratio 0.91-0.97 |
| Age, mean | 27.2 | 22.0 | **0.47** |
| Minors (13-17) | 17.3% | 46.1% | **-0.65** |
| Female | 67.3% | 61.6% | 0.12 |
| US | 49.2% | 61.4% | **-0.25** |
| English native | 63.0% | 71.9% | **-0.19** |
| University degree or higher | 47.6% | 23.4% | **0.52** |
| Valid major filled | 68.4% | 48.1% | **0.42** |

Compared with the full incl-shared table (115,974 rows), every scale SMD is <= 0.06. Alpha on the incl-shared
table is .833-.900, which is within .01 of the main table.

### 2. Item-level statistics (`e1_item_distributions.png`)
- Missing per item is 0.05% to **0.31%** (the maximum is R5). The bar is <= 2%.
- Corrected item-rest r ranges from .39 to .78. The lowest is A7 "Perform stunts" (.39), then S4 .42, R1 .47, E4 .47
  and S1 .49. The highest is I5 (.78). No item is below .30.
- **Strong floor effect on R.** The share of "1 = Dislike" answers is 61% for R3 (oil rig), 58% for R5, 50% for R8
  and 30-46% for the other R items. E1 is at 41% and C1/C7/C8 at 37-40%. The ceiling ("5") is never above 29% (S2, S5).
- Item means: R 1.72-2.57, I 2.54-3.47, A 2.48-3.27, S 2.86-3.66, E 2.14-3.01, C 2.17-2.65.

### 3. Reliability (`e1_reliability.png`; bootstrap 95% CIs, alpha B=1000, omega B=500)
| Scale | n complete | Cronbach alpha [95% CI] | McDonald omega [95% CI] | Permuted baseline alpha / omega |
|---|---|---|---|---|
| R | 78,716 | .870 [.868, .871] | .874 [.873, .876] | .01 / .02 |
| I | 79,492 | .890 [.889, .891] | .892 [.891, .893] | .01 / .13 |
| A | 78,866 | .857 [.856, .859] | .860 [.859, .862] | .00 / .13 |
| S | 79,496 | .841 [.839, .843] | .844 [.842, .845] | .00 / .02 |
| E | 79,038 | .831 [.829, .833] | .833 [.831, .835] | -.01 / .02 |
| C | 79,338 | .898 [.896, .899] | .899 [.898, .900] | .01 / .01 |

By subgroup, alpha stays between .814 and .911 for every scale, in every gender x age cell and in both `engnat` groups.
The lowest value is S for females 25+ (.814) and the highest is I for males 13-17 (.911). The 1-factor omega has a small
positive bias on pure noise (permuted baseline up to .13) because it uses absolute loadings. This does not change the conclusion.

### 4. Demographics (`e1_demographics.png`; decoded with codebook.txt)
- **Age:** median 23 (IQR 18-33; P10 17, P90 46; range 13-87). By band: 13-17 has 13,882 (17.3%), 18-24 has 30,689 (38.3%) and 25+ has 35,514 (44.3%).
- **Gender:** female 67.3%, male 31.8%, other 0.8%, no answer 0.1%.
- **Country** (network location; 183 codes): US 49.2%, MY 7.0%, GB 5.0%, CA 4.8%, PH 3.7%, SG 3.2%, AU 3.2%, IN 1.9%,
  ID 1.4%, NZ 1.3%, NONE 1.2%, HK 1.0%, PT 1.0%, DE 0.9%, BR 0.8%. Spain is not in the top 15.
- **Education:** less than high school 9.5%, high school 42.1%, university degree 31.2%, graduate degree 16.4%.
- **English native:** yes 63.0%, no 36.8%. **Urban childhood:** urban 44.5%, suburban 34.2%, rural 20.4%.
- **Race:** the codebook merges White, Native American and Indigenous Australian into code 4. Code 4 is 54.4%,
  Asian 24.9%, Other 10.7%, Black 7.2%, Arab 1.3%.
- **Source:** other/undetermined 65.0%, Google 25.4%, internal link 9.6%.

**Fairness grid (gender x age band)**
| | 13-17 | 18-24 | 25+ |
|---|---|---|---|
| Female | 9,634 | 20,995 | 23,241 |
| Male | 3,997 | 9,416 | 12,086 |
| Other | 228 | 250 | 144 |

The smallest male/female cell is 3,997 (male 13-17), well above the bar of 1,000. Gender "Other" has only 622 rows in total, which is
too few for stratified estimates. The `engnat` x gender cells range from 9,938 to 34,439.

**Gender differences (Cohen's d, male minus female) vs Su et al. 2009 (via research/notes/06)**
| | R | I | A | S | E | C |
|---|---|---|---|---|---|---|
| This sample | **.71** | .12 | .02 | **-.38** | .00 | .13 |
| Su et al. 2009 | .84 | .26 | -.35 | -.68 | n/a | -.33 |

R, I and S go in the same direction as the literature, but the gaps are smaller. A and C do not match: here A is about 0 and C is
slightly higher for males. The S gap is stable across age bands (-.37 to -.41). The C gap shrinks with age, from .32 at 13-17 to .00 at 25+.

### 5. Profile shape (`e1_differentiation.png`)
- Differentiation (max-min on the 1-5 scale): median 2.25 (IQR 1.75-2.75). Elevation: median 2.73 (IQR 2.33-3.08).
  The two are uncorrelated (r = .02).
- **Flat profiles (differentiation < 1.0): 3.96% [95% CI 3.83, 4.11]**, about 3,200 people.
  - Sensitivity: with < 0.5 the share is 0.38%, and with < 1.5 it is 15.1% [14.8, 15.3].
  - Flat and low elevation (< 2.0, "dislikes everything"): 1.04% [0.97, 1.11]. Flat and high elevation (>= 3.0): 1.57%.
  - Low elevation alone (< 2.0): 11.3%. In the incl-shared table, 4.65% of profiles are flat.
- By subgroup, flat profiles are **more common in males and in younger people**: male 13-17 8.6%, male 18-24 6.9%,
  male 25+ 4.9%, female 13-17 3.7%, female 18-24 3.0%, female 25+ 2.4%. People with no major are 4.8% flat, and people with a major 3.6%.
- **Ties:** 9.2% of people have a tied top type, and 12.9% have a tie between the 3rd and 4th letters.

### 6. The `major` field (`e1_major_families.png`, `e1_major_families_draft.csv`)
- There are 10,275 unique raw non-blank values. I normalised them (NFKD to ASCII, lowercase, collapsed whitespace,
  stripped edge punctuation) and removed 899 junk rows (n/a 219, no 172, "-" 92, none 78, na 64, nil 29, "i dont know" 27, ...).
  That leaves 7,445 unique values on 54,814 rows, which is **68.4%** of the main table.
- **Fill rate by age band:** 13-17 **25.9%**, 18-24 71.2%, 25+ 82.7%. By education: less than high school 18.9%, high school 48.4%,
  university 97.1%, graduate 94.6%. Males (68.4%) and females (68.7%) are similar.
- Top values: psychology 8,456 (15.4% of filled rows), business 2,270, english 1,890, nursing 1,332, biology 1,277, education 1,191,
  engineering 865, computer science 829, accounting 803, economics 766, law 709, and so on (top 50 in the JSON).
  It takes 308 distinct values to reach 80% of filled rows.
- **Draft mapping: 22 families plus "Undecided/General studies"**, built from ordered regex rules in the script.
  **Coverage: 97.1% of filled non-junk rows are mapped.** The other 1,617 rows (2.9%) are Unmapped, e.g. "stem", "social", "ba" and rare typos.
  The CSV lists the 1,081 values that have count >= 3 or fall inside the top 80%. Together they cover 87.2% of filled rows.
  Singletons are left out so that quasi-identifying free text is not published.

| Family | n | Family | n |
|---|---|---|---|
| Psychology | 9,963 | Accounting/Finance | 1,838 |
| Business/Management/Marketing | 7,048 | Physical/Earth/Env. sciences | 1,808 |
| Engineering | 3,905 | Medicine/Dentistry/Pharmacy | 1,687 |
| Health/Nursing/Allied health | 3,239 | Communication/Media/Journalism | 1,664 |
| Languages/Literature | 3,136 | Law/Criminal justice | 1,641 |
| CS/IT | 2,334 | Social work/Counselling | 1,614 |
| Social sciences | 2,299 | Humanities | 1,344 |
| Arts/Design/Performing arts | 2,269 | Economics | 1,024 |
| Education | 2,214 | Undecided/General studies | 805 |
| Biology/Life sciences | 1,998 | Math/Statistics | 659 |
| (Unmapped) | 1,617 | Architecture/Planning | 616 |
| | | Trades/Vocational | 92 |

- **Base rates differ strongly by gender** (share of mapped majors, female vs male): Psychology 22.2% vs 11.4%,
  Engineering 3.8% vs 15.0%, CS/IT 2.4% vs 8.6%, Health/Nursing 7.4% vs 3.4%, Education 5.1% vs 2.2%, Social work 3.8% vs 1.3%.

### 7. People vs O*NET occupations (`e1_profile_vs_onet.png`; descriptive only, the scales differ)
| | R | I | A | S | E | C |
|---|---|---|---|---|---|---|
| People: mean centred profile (1-5) | -0.63 | +0.31 | +0.20 | +0.58 | -0.16 | -0.30 |
| O*NET: mean centred profile (1-7) | +1.21 | 0.00 | -1.42 | -0.42 | -0.54 | +1.17 |
| People: % with this top type | 4.0 | 28.2 | 19.8 | 33.1 | 6.4 | 8.5 |
| O*NET: % of occupations with this top type | 42.0 | 12.1 | 3.0 | 14.0 | 10.8 | 18.0 |

The average person profile and the average occupation profile are **negatively correlated (r = -.68)**. The people in this sample
lean S/I/A, while the O*NET catalogue is dominated by R and C occupations: 42% are R-top, and only 3% (28 occupations) are A-top.
The medians also differ. Differentiation is 2.25 on the 1-5 scale for people vs 4.95 on the 1-7 scale for occupations. Elevation is 2.70 vs 3.36.
Because the scales differ, only the shapes are comparable. The level comparison is just an illustration.

## Verdict: PROVEN (fit for purpose), against the pre-registered bar
| Criterion | Bar | Result | Pass |
|---|---|---|---|
| (i) clean rows | >= 50,000 | 80,085 | yes |
| (ii) item missing | all <= 2% | max 0.31% (R5) | yes |
| (iii) alpha per scale | all >= .80 | .831 (E) to .898 (C); all lower CI bounds >= .829 | yes |
| (iv) gender x age cells | all >= 1,000 | min 3,997 (male 13-17) | yes |
| Secondary: funnel reproduces the build log | | exact match | yes |
| Secondary: codebook fields in the raw header | | 93/93, ranges OK | yes |
| Secondary: major-family coverage >= 80% | | 97.1% | yes |

"Fit for purpose" applies to the v0 experiments: structure, IRT/CAT simulation, stability and major prediction.
It does **not** mean the data represents Career Compass's target users (see Caveats).

## Caveats
- **Sample bias.** Respondents are self-selected visitors to a free online test who also opted into a survey. Median age is 23,
  67% are female, 49% are US (by IP) and 63% are native English speakers. There are 183 countries, but most have very few
  respondents, and Spain is not in the top 15. Country is the network location, not nationality. There are no Spanish-language responses.
- **License.** None is stated ("public edification", research consent). Use the data only for research and model training, and never
  redistribute person-level rows. The major CSV contains only aggregated value counts (count >= 3).
- **The shared-network filter is not neutral.** The removed rows are 46% minors, compared with 17% in the kept rows. They are also
  more US and lower in education. So the filter **under-represents school-age users**, who are a core target group. Scale means barely
  move (all |SMD| <= .18), but results for minors should be re-checked on the incl-shared table, with likely retakes de-duplicated.
- **Gender effects are smaller than in the literature** (R .71 vs .84, S -.38 vs -.68), and A and C differ in sign or size. This may come
  from self-selection or from this item set. Do not use this sample as a general-population norm.
- The `race` field is broken by design (three groups share code 4). Gender "Other" has only 622 rows. In the 13-17 band, the major field
  is mostly empty (26% filled), and when it is filled it is probably an intended major rather than one studied.
- The major mapping is a rule-based **first pass** with no second rater. Some ambiguous cases need review before E6:
  "biomedical science" goes to Medicine, "sport management" and "kinesiology" to Health, "public administration" to Business, and joint
  majors take the first matching rule.
- R items have strong floor effects (up to 61% answer "1"), so they carry little information at low R levels.
- Interests are not satisfaction or aptitude. This audit says nothing about outcomes.
- Technical: factor_analyzer 0.5.x passes the `force_all_finite` argument, which the installed scikit-learn has removed. The script includes
  a small compatibility shim that renames it to `ensure_all_finite`, so no new dependency was needed.

## Implications for the product and for E2-E6
- **Product.** A 48-item RIASEC with alpha >= .83 per scale is a sound base for the full test and for the item bank.
  - Strictly flat profiles (< 1.0) are a small segment: about 4%, and only about 1% "dislike everything". They are 2-3x more common in
    young males (8.6% of males 13-17). With a < 1.5 threshold the segment is 15%.
  - The "lost user" mode should trigger on **low differentiation OR low elevation** (11% have elevation < 2.0), not on flatness alone.
    The threshold still needs a decision, and E5 can calibrate it under answer noise.
  - The Holland code display must handle ties, since 9% of people have a tied top type (scales are 8-item means).
- **Catalogue imbalance.** People lean S/I/A, but 42% of O*NET occupations are R-top and only 3% are A-top. Shape-based (Pearson)
  matching will therefore give A-leaning users a small, repetitive pool of occupations and R-leaning users a large one. E3 should
  measure this, and E4/E5 should report top-10 overlap per top type.
- **E2.** There is enough data for factor analysis in every gender x age cell (n >= 3,997). Test invariance by gender, age band and `engnat`.
  The weakest items (A7, S4, R1, E4) may show low loadings or cross-loadings. The scale correlations look hexagon-like: R-C (.47) and
  E-C (.49) are the highest, and I-E (.03) and A-C (-.02) are the lowest.
- **E4 (IRT/CAT).** Because of the R floor effect, R items give little information below the mean. Expect θ for low-R people to rest on
  a few items and the GRM thresholds for R to be bunched. Use the 13-17 band (n = 13,882) as a separate CAT test set.
- **E5.** Test stability separately for flat and low-elevation profiles, since they will have the least stable top-10.
- **E6.**
  - 54,814 rows have a mapped major (97% coverage, 22 families).
  - Psychology is 18% of labelled rows, so the majority-class baseline is about 18% top-1.
  - Trades (92), Architecture (616) and Math (659) are low base-rate classes.
  - Majors depend on age and education. To avoid "intended major" noise from teens, restrict to age >= 18 or to education >= university (fill ~95%).
  - Gender base rates differ a lot (Engineering 15% of males vs 4% of females). E6 must report subgroup accuracy and must not use gender as a feature.
- **Fairness.** Every subgroup cell is large enough for per-group metrics except gender "Other" (622). Report that group pooled, with a warning.
