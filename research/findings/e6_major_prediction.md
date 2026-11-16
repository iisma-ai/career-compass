# E6 — Supervised prediction of university major family from interest answers

_Pre-registered 2026-11-15, before running `research/feasibility/e6_major_prediction.py`. The only data
look before this point was a count of major families by age (to apply the n < 300 rule below)._

```
Question:      Can a model learned from the 48 RIASEC answers predict the university major family a person
               reports better than pure RIASEC profile similarity (family centroid + Pearson), and how
               accurate can major-family prediction realistically be?
Hypothesis:    A learned model (multinomial logistic regression or gradient boosting) beats the centroid
               Pearson baseline, as ML-augmented scoring beat profile matching in Song et al. (2024, B; n = 81,267)
               (research/notes/03-ml-career-recommenders.md). The gain should be modest, and low-base-rate
               classes should be under-predicted (same source). Expected top-3 is about .45-.55; the majority
               baseline is already high (about .41 top-3, because Psychology + Business + Engineering cover
               about 41% of rows), so the verdict is likely "promising". The Hanna & Rounds (2020, A) inventory hit
               rate of about 50.8% is for a different task (a few broad Holland categories, often
               occupation, not 21 major families), so it is context, not a target.
Data:          data/processed/riasec_people.parquet (80,085 rows). Major family from the E1 regex rules
               (imported unchanged from research/feasibility/e1_data_audit.py; summary in
               research/findings/e1_major_families_draft.csv).
               Sample: age >= 18 AND a valid mapped major family. "Undecided/General studies" (n = 774 at
               age >= 18) and "Unmapped" (1,370) are excluded from the targets; their sizes are reported.
               Class-size rule: classes with n < 300 in this sample are DROPPED, not merged, because no
               adjacent family is a defensible merge target. This affects only Trades/Vocational (n = 75).
               Result: 21 target families, about 48,000 rows. Gender "Other" (n of about 240) stays in the
               sample but is reported pooled, with a warning, and left out of the gender comparison.
               Robustness: data/processed/riasec_people_incl_shared_network.parquet (115,974 rows), same
               filters.
Split:         Stratified 80/20 train/test (seed 42). All tuning and model selection uses 5-fold stratified
               CV on train only. The test set is touched once per final model.
Features:      F1  48 items (1-5; missing -> train-median imputation for linear/MLP; NaN native in HGB).
               F2  6 scale means + elevation (mean of 6) + differentiation (max - min) = 8 features.
               F3  F1 + TIPI Big Five (5 scales, mean of 2 items each, standard TIPI keying: E = 1, 6R;
                   A = 2R, 7; C = 3, 8R; ES = 4R, 9; O = 5, 10R; R = 8 - x).
               F4  F1 + age + gender (one-hot) + education (one-hot). ANALYSIS ONLY: demographics must
                   never be product inputs. F4 shows how much demographic (mainly gender) information adds.
               Extra analysis: a logistic model predicting gender (male vs female) from F1, to measure how
               much gender information the items carry implicitly (AUC).
Models:        B0 majority: constant ranking by train class prior.
               B1 stratified random: random ranking, drawn without replacement with probability
                  proportional to train priors (Gumbel trick, seed 42).
               B2 RIASEC centroid (knowledge-based): each family's mean 6-scale profile on train; rank
                  families by Pearson r between a person's 6-vector and each centroid (the O*NET-style
                  shape match from src/career_compass/matching.py, applied to family centroids).
               M1 multinomial logistic regression, L2, StandardScaler, C tuned over
                  {0.001, 0.01, 0.1, 1, 10}; unweighted and class_weight="balanced" variants.
               M2 HistGradientBoostingClassifier; grid {learning_rate 0.05, 0.1} x {max_leaf_nodes 15, 31},
                  max_iter 500 with early stopping (10% internal validation); unweighted and balanced
                  (sample weights) variants. To keep runtime down, the grid is tuned by 5-fold CV on F1
                  and the chosen setting is reused for F2/F3/F4.
               M3 (optional) small MLP (one hidden layer of 64, early stopping, alpha 1e-3), F1 and F3 only, untuned.
               Tuning criterion: mean 5-fold CV top-3 accuracy (the primary metric); ties go to lower log loss.
Selection:     "Best interest-only model" = the model x feature set (F1/F2/F3; any M1-M3 variant) with
               the highest mean 5-fold CV top-3 accuracy on TRAIN. It is chosen before looking at test.
Metrics:       On test: top-1, top-3 and top-5 accuracy; macro-F1 and balanced accuracy (top-1); log loss;
               per-class recall and precision; lift over base rate per class (precision of top-1 / test
               prior) and top-3 recall per class; calibration of the top-1 probability (ECE, 15 equal-width
               bins; reliability plot); predicted top-1 share vs actual share per class.
               Percentile bootstrap 95% CIs over test rows (B = 1,000, seed 42) for top-1/3/5, macro-F1 and
               balanced accuracy, plus a paired bootstrap CI for (best model - each baseline) on top-3.
Analyses:      (1) results table, models x feature sets; (2) row-normalised confusion matrix of the best
               model, top off-diagonal confusions, and whether confused pairs have more similar centroids
               (Pearson between centroids, confused pairs vs all pairs); (3) LR coefficients by family
               (top items, mean per RIASEC scale); (4) fairness: by gender (male/female) top-1/top-3,
               macro-F1, predicted vs actual share per family, gap amplification
               (predicted F-M share gap / actual F-M share gap) for F1 vs F4, plus gender AUC from items;
               age bands 18-24 vs 25+ also reported; (5) Psychology dominance: share of top-1 predictions
               that are Psychology; metrics on non-Psychology test rows; refit of the best model and the centroid
               baseline without the Psychology class; (6) robustness: (a) models trained on main train,
               evaluated on the shared-network-only rows aged 18+ (out of sample); (b) a fresh 80/20 split of the
               incl-shared table for majority / centroid / LR-F1.
Success bar:   PRIMARY: the best interest-only model (selected on CV as above) beats BOTH the majority
               baseline (B0) and the RIASEC-centroid baseline (B2) on test top-3 accuracy, with
               non-overlapping 95% bootstrap CIs.
                 PROVEN      if the primary condition holds AND test top-3 >= .50.
                 PROMISING   if the primary condition holds but test top-3 < .50.
                 NOT VIABLE  otherwise.
               Secondary (reported, not gating): macro-F1 and balanced accuracy vs baselines; recall of
               the three smallest classes (Architecture, Math/Statistics, Economics); ECE.
```

**Addendum to the pre-registration (2026-11-15, added after the ethics-review request and before the full run;
only a `--quick` smoke run on a 15% subsample had been executed, and its numbers were not used for any decision):**
- Sample restricted to **adults (age >= 18)**, as stated above. Minors are neither trained on nor evaluated.
- No sensitive columns as features: religion, orientation, race, country, urban and engnat are never used. Age,
  gender and education appear **only** in the analysis-only F4 set.
- Per gender (male/female): top-3 accuracy, plus predicted vs actual share of **STEM majors**, defined in advance as
  STEM-core = Engineering + CS/IT + Math/Statistics + Physical/Earth/Environmental sciences, and STEM-broad =
  STEM-core + Biology/Life sciences. Predicted share = share of top-1 predictions and share of people with at least one
  STEM family in their top-3.
- Outputs are aggregates only: no model weights and no person-level predictions are saved to `research/findings/`
  (the OpenPsychometrics data has no license and the repo is public).
- Framing: any output is "what people with similar interests studied", never a probability of success.

**Execution notes (2026-11-15):**
- The first smoke run was killed by host memory pressure, which happened while other experiments were running.
- CV parallelism was then lowered from 5 to 2 workers. That change affects runtime only; seeds, metrics and B are unchanged.
- Deviation: the pre-registration says "21 target families", but the actual count after dropping
  Trades/Vocational is **20**. That was a counting slip in the text, and no rule changed.
- The full run took 745 s. All numbers below come from `research/findings/e6_major_prediction.json`
  (seed 42, test n = 9,800).

## Results

**Sample:** 80,085 clean rows → 66,203 aged 18+ → 51,218 with a valid mapped major → **48,999 analysed**
(20 families; Psychology 19%, Business 14%, Engineering 7%; Architecture is the smallest at 524). Gender: 67% female, 32% male.

**Headline (test set; 95% bootstrap CIs in the JSON):**

| Model | Features | top-1 | top-3 | top-5 | macro-F1 | bal. acc |
|---|---|---|---|---|---|---|
| B0 majority | — | .192 | .401 [.392, .410] | .524 | .016 | .050 |
| B1 stratified random | — | .087 | .247 | .387 | .052 | .052 |
| B2 RIASEC centroid (Pearson) | 6 scales | .120 | .318 [.308, .327] | .458 | .097 | .134 |
| LR unweighted | F1 items | .308 | .561 | .695 | .144 | .153 |
| LR unweighted | F2 scales + elev/diff | .262 | .497 | .632 | .074 | .100 |
| **LR unweighted (selected)** | **F3 items + TIPI** | **.309** | **.565 [.555, .574]** | **.697** | .146 | .154 |
| LR balanced | F1 | .204 | .463 | .614 | .183 | .222 |
| HGB unweighted | F1 | .307 | .554 | .689 | .152 | .158 |
| MLP | F1 | .305 | .558 | .691 | .150 | .157 |
| LR unweighted (analysis only) | F4 = F1 + demographics | .313 | .568 | .705 | .157 | .161 |

- **Selection:** LR-F3 had the best CV top-3 (.565). LR-F1 is practically tied (paired test difference
  +.004, CI [.0001, .008]), so TIPI adds almost nothing. Gradient boosting and the MLP do **not** beat the linear model.
- **Paired top-3 differences** for the selected model:
  - vs majority: **+.164** [.154, .173]
  - vs centroid: **+.248** [.236, .259]
  - vs the 6-scale summary (F2): +.069 [.060, .076]
- **Item-level information matters:** the 48 items beat their 6 scale scores, which in turn beat simple
  centroid shape matching.
- **Calibration** is good (ECE .006).
- **Class weighting:** balanced weighting trades top-3 (.46) for macro-F1 (.18) and balanced accuracy (.22).

**Per-class top-3 recall (selected model):**
- Psychology .90, Business .85, Engineering .69, Health .67, Arts .55, Biology .54, Languages .53, CS/IT .48,
  Accounting .45
- Social work .39, Education .33, Medicine .27, Physical sciences .26, Communication .23, Social sciences .18,
  Humanities .14, Architecture .13, Economics .11, Law .10, Math/Statistics .09
- The three smallest classes (secondary metric) are nearly invisible.

**Psychology dominance:**
- The model's top-1 is Psychology for **41%** of test people (actual 19%), and Psychology is in the top-3 for 68%.
- The most common confusions are all "→ Psychology" (Social work 71%, Education 47%, Social sciences 46%) or "→ Business"
  (Accounting 53%, Economics 46%).
- Confused pairs have very similar centroids: mean r .92, vs .74 for all pairs.
- On non-Psychology rows: top-3 .486 vs majority .259 and centroid .357.
- Refit without Psychology: top-3 .545 vs majority .337 and centroid .360. The gain over the baselines holds.

**Robustness:**
- Shared-network rows not used in training (n = 12,566): top-3 .591 vs majority .433 and centroid .324.
- A fresh split of the incl-shared table: .570 vs .408 and .310.
- Same conclusion in both.

**Age:** top-3 is .614 for ages 18–24 and .528 for 25+, both well above their baselines.

**Fairness (selected model; male n = 3,107, female n = 6,641):**
- **Accuracy:** top-3 is .537 for men and .578 for women.
- **Share gaps:** overall, the model does **not** amplify the total female–male share gap (ratio of summed |gap|,
  predicted/actual, = .94). It **amplifies the large gaps** and shrinks the small ones:
  - Psychology F−M gap: actual +.111, predicted +.182 (×1.65)
  - Engineering: −.113 vs −.156 (×1.38)
  - Business: ×1.30
- **STEM-core:**
  - The actual M−F share gap is .184 and the predicted gap .205 (**×1.11**; STEM-broad ×1.16).
  - Women who actually studied a STEM-core major get one in their top-3 only **52%** of the time, vs **80%** for men.
- **Gender leakage:** the 48 items alone predict gender with **AUC .84** [.83, .85]. Leaving gender out as an input does
  not remove gender information.
- **Adding demographics (F4)** makes amplification much worse (total ratio 1.47, STEM-core ×1.54, Psychology ×2.42).
  Demographics must never be inputs.
- **Other models:** balanced LR gives STEM-core ×1.26. The centroid baseline *under*-states the gap (×0.58).
- Gender "Other" (n = 44 in test) is too small to evaluate.

Charts: `e6_results.png`, `e6_confusion.png`, `e6_reliability.png`, `e6_per_class_recall.png`, `e6_coefficients.png`,
`e6_gender_shares.png`.

## Verdict
**PROVEN against the pre-registered bar.**
- The selected interest-only model (LR, items + TIPI) reaches test top-3 **.565** [.555, .574].
- Its CI is clear of both majority [.392, .410] and centroid [.308, .327], and it is above .50.
- The result also holds with items only (.561), without Psychology, and out of sample.

**Scope of "proven":**
- What it shows: interest answers carry real, generalisable information about which broad study field people chose.
  Top-1 is right about 31% of the time, against a 19% guess-the-mode rate.
- What it doesn't show: **not** evidence that the predicted field would suit the person or that they would succeed in it.
- **Not ready for users:**
  - Small fields are rarely predicted.
  - Psychology is over-predicted about twofold.
  - Existing gender gaps in Psychology, Engineering and STEM are **amplified**: women who actually studied STEM see it
    in their top-3 far less often than men.

## Caveats
- **Labels:** majors are self-reported free text mapped by regex rules (E1), with no second rater, so the labels are noisy.
- **Majors are not careers.** "What people with your interests studied" reflects past choices, including the social
  pressures behind them, and that is exactly what the gender amplification reproduces.
- **Sample:** self-selected, online, US-heavy (49%), 67% female, young.
- **Reverse causation:** majors were reported after the fact, so interests may have been shaped by the major studied.
- **Item coverage:** the I items are almost all biology- or medicine-themed (I1–I7), so CS, Math and Engineering rely on
  indirect R/C signals. Their low recall (Math .09) fits this.
- **License:** OpenPsychometrics data has no license, so this is research only. No weights or person-level outputs are saved.
- **Regulation:** EU AI Act Annex III point 3 covers education systems used to determine access or to steer learners.
  E6 stays research-only, and any product use needs a high-risk obligations assessment.

## Implications for the design
- **v3 (universities):** a field-of-study suggestion layer is feasible, but it needs re-scoping:
  - show "people with similar interests often studied…" next to the O*NET career families, not as a ranking;
  - apply a de-amplification step before release, then re-run this audit. Examples are post-hoc calibration so that
    predicted shares by gender don't exceed actual shares, or an exposure floor for small and STEM fields;
  - never use demographics as inputs, and audit gender with the AUC .84 leakage in mind.
- **Model choice:** multinomial LR on item responses is as good as gradient boosting or an MLP. It is also calibrated
  and explainable through per-item coefficients, so prefer it.
- **Features:** item-level detail beats 6 scale scores (+.07 top-3), so keep item-level features in v1 alongside the
  RIASEC profile.
- **Item bank:** add non-biology Investigative items (computing, mathematics, physical science) for CS, Math and
  Engineering. E2 and E4 already flagged this.
