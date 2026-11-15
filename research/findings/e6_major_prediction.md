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
                  shape match from src/carrier_helper/matching.py, applied to family centroids).
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
