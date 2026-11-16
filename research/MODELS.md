# Career Compass — Model specification (v0 → v1)

Assembled 2026-11-16. This document specifies each model layer: its inputs, outputs, maths, how it was validated, and its
status. The evidence for each choice is in `research/findings/` (level E unless noted), and the decisions are in
`docs/decisions/`. The overall verdict and caveats are in [RESEARCH.md](RESEARCH.md).

Status labels:
- **Specified**: v1 setting chosen and backed by an experiment.
- **Design**: proposal without direct evidence.
- **Research-only**: built and tested, not for users.
- **Not started**.

| # | Layer | Status | Code | Evidence |
|---|---|---|---|---|
| L1 | Item bank and questionnaire form | Specified (items need replacing before release) | — | E1, E2, E4 |
| L2 | User model: GRM + EAP profile estimate | Specified | `research/feasibility/e4_cat_simulation.py` (research) | E4 |
| L3 | Lost-user detection and flow | Trigger specified, flow is design only | — | E1, E4, E5 |
| L4 | Matching, families and re-ranking | Specified | `src/career_compass/matching.py` | E3, E5 |
| L5 | Free-text layer | Research-only | `src/career_compass/text_cues.py`, `research/feasibility/e7*.py` | E7, E7b |
| L6 | Explanations | Design | — | E2, E3 |
| L7 | Feedback learning | Not started (blocked by privacy design) | — | — |
| L8 | Field-of-study prediction | Research-only (v3) | `research/feasibility/e6_major_prediction.py` | E6 |

---

## L1 — Item bank and questionnaire form
- **Bank:** OpenPsychometrics 48-item RIASEC (8 per scale, 5-point Likert). Only research use is allowed (ADR 0002). The item
  order, GRM parameters (L2) and families (L4) below are all derived from this data. **None of them can ship until release
  blocker 2 is cleared** (permission, or our own calibration).
- **Form (v1):** a **fixed 24-item form**, 4 items per scale, in content-balanced round-robin order (R-I-A-S-E-C), ordered by
  discrimination over the 40 retained items. The starter items are R5, I5, A4, S5, E6, C8. The full order is `best_fixed_order` in
  `research/findings/e4_cat_simulation.json`. An optional "refine" step extends the form to 30 items. The cap is 40 items. ([e4](findings/e4_cat_simulation.md), ADR 0005)
- **Excluded items (8):** R1, A7 and S4 are weak; E4, R3, I8, R4 and E1 show gender DIF. Excluding them had no measurable cost
  (r −.001 at k = 20). ([e2](findings/e2_structure.md), [e4](findings/e4_cat_simulation.md))
- **Known gaps:**
  - Investigative content is almost all biology/medicine, which leaves CS, maths and physics under-covered (E2, E6).
  - Enterprising is the least age-invariant scale (E2).
  - R items have strong floor effects (up to 61% answer "1"; E1).
- **Before release:** write new DIF-screened items (non-biology I, non-sales E), calibrate them on our own or licensed data, and
  re-audit DIF on the final set. These are release blockers. Item-writing rules are in E2, Implications 1.
- **Candidate licensed source:** the O\*NET Interest Profiler items (CC BY 4.0; Mini-IP 30, Short Form 60,
  parent 180) ([O\*NET IP](https://www.onetcenter.org/IP.html), A). These need calibration.

## L2 — User model: profile estimate with uncertainty
**Inputs:** responses x_j ∈ {1..5} to the administered items. **Outputs:** θ̂ and SE per scale (internal), the *predicted
full-scale raw profile* p ∈ [1,5]^6 (used for matching), elevation and differentiation.

**Model (per scale s, unidimensional logistic graded response model):**

  P(X_j ≥ k | θ_s) = 1 / (1 + exp(−a_j (θ_s − b_jk))),  k = 2..5,  with P(X_j = k) taken as the difference of adjacent terms.

- **Calibration:** MML (girth `grm_mml`) followed by an EM polish, because girth underestimates a by about 3–5%.
- **Scoring:** EAP on an 81-point grid per scale, with a correlated 6-D normal prior N(0, Φ). Φ is the latent correlation
  matrix, which agrees with E2's CFA (r = .996 across the 15 pairs). The 6-D posterior is approximated with Gaussian sites.
  The predicted raw profile is the expected full-scale mean given the posterior. ([e4](findings/e4_cat_simulation.md))
- **Derived:**
  - elevation = mean(p)
  - differentiation = max(p) − min(p)
  - shape = p − mean(p), used by L4
- **Validation (replay on 80,085 people, plus a synthetic check with known θ):**

  | Items | mean r with full test | Top-3 family agreement | First letter |
  |---|---|---|---|
  | 12 | .915 | — | — |
  | 24 | .965–.968 | .63–.64 | .83 |
  | 30 | .98 | .68 | — |

  The full test's own ceiling under SEM noise is about .60 for top-3 families (E5). That is a different quantity
  (stability under noise, not agreement with the full test), so it is not an upper bound for the column above. These numbers are replay, not live
  administration, so expect lower live agreement (note 02: .73–.91 live vs .91–.97 simulated, C).
- **Why not CAT:** with 8 items per scale, adaptive selection beat the best fixed order by at most +.005 r. SE-based stopping
  doesn't work with this bank: SE .30 is never reached, and SE .40 is not reached for 54% of people. Keep the selector interface,
  and re-run E4 once the bank has 15–20 or more calibrated items per scale.
- **Caveats:**
  - Scalar non-invariance by gender and age (E2) means one parameter set for all groups is an approximation, although
    subgroup r is equal (.954–.958).
  - Local dependence within I (Q3 up to .33).

## L3 — Lost-user detection and flow
- **Trigger (after the 24 items):**
  - **differentiation < 1.0** (hard gate):
    - 4% of people on the full test (E1); 5.7% using the predicted 24-item profile (E4);
    - their top-10 agreement is only .17 under noise (E5) and .26 against the full test (E4).
  - **or elevation < 2.0** (11% of people; not yet tested in E4).
  - Differentiation between 1.0 and 1.5 is a soft gate: show broad families with "your answers point in several directions".
  - Do **not** trigger on posterior SE (its correlation with list stability is only .11). ([e1](findings/e1_data_audit.md), [e4](findings/e4_cat_simulation.md),
    [e5](findings/e5_stability.md))
- **Flow (design only, no evidence yet):**
  - broader, scenario-based items, plus a "don't know / never tried" option;
  - a wider and more diverse set of families;
  - explicit uncertainty wording;
  - concrete next steps (try-outs, activities);
  - a written summary for a counsellor;
  - **human-help signposting (required):** every result page links to a vetted list of human help (school or career
    counsellor, national youth helpline), localised by country. When elevation is low, add a non-diagnostic line such as
    "Feeling uninterested in everything can be worth talking to someone about." This content must be reviewed by a
    counsellor before release.
  - "Lost" is an internal name only and is never shown to users.

  Rationale: indecision relates most strongly to low process self-efficacy, not only to missing information
  ([Udayar et al. 2020](https://serval.unil.ch/fr/notice/serval:BIB_AF059FD4623A), A).
- **Fairness:** flat profiles are more common in boys aged 13–17 (8.6% vs about 4% overall; E1), so this flow is also a fairness mitigation.
  Validating the flow is a release blocker.

## L4 — Matching, families and re-ranking
**Inputs:** person shape p (1–5 scale); the O\*NET 31.0 OI profiles o (1–7 scale) of 923 occupations, plus job zone.
**Output:** about 3 families, each with 2–3 example occupations, unordered.

- **Score:** Pearson correlation of the two 6-vectors,
  s(p, o) = Σ (p_i − p̄)(o_i − ō) / sqrt(Σ(p_i − p̄)² Σ(o_i − ō)²).

  This is `matching.score_matrix(..., method="pearson")`. Rejected alternatives:
  - `euclid_z` sends flat or low-elevation users to job zone 2 R work, and A-top users get a median r of .03.
  - `cosine_centered` gives a median top-1 r of only .54.
  - `hexagon` is equal in quality to Pearson and is kept for explanations only.

  ([e3](findings/e3_occupation_space.md), ADR 0004)
- **Families:** complete-linkage clusters in which every within-family pair of occupations has r ≥ .80. This gives 101 families
  (`research/findings/e3_families.csv`, column `family_r80`). They are the most stable useful granularity: top-10 family hit .74 and
  top-3 overlap .60 at r ≥ .80 (E5 family-granularity table). The .697 quoted elsewhere is the family hit rate for the finer
  r ≥ .90 families. Families at r ≥ .90 (172) are too fine, and at r ≥ .50 (36) too broad. Family names need hand-written
  user-facing labels. ([e5](findings/e5_stability.md))
- **Diversity:** cap the number of occupations per family in a list at 2. This takes a top-10 from 5.3 to 6.6 families at a
  cost of about −.01 r. It doesn't fix catalogue exposure (Gini .77), which needs catalogue work (ESCO, O\*NET specific interest areas).
- **Job-zone filter (user-visible):** shape is confounded with preparation (V = .45). Without a filter, S/I users only see job
  zone ≈ 4.2 careers. Offer "less / more preparation" and match within the chosen range. ([e3](findings/e3_occupation_space.md))
  - The **default is all job zones**, and the user can narrow it.
  - High-preparation careers are never labelled "not for you". Show the preparation needed and the pathways to it.
- **Ordering within a family:** by criteria the user can see (preparation, wages, outlook), not by small r differences (E5).
- **Thin pools:**
  - A-top users have only 28 A-top occupations, in 11 families. Broaden the pool with the second letter and explain why.
  - Ties in the Holland code: show the top letter + "also" (top letter agrees 76% of the time under noise; 3-letter order 38%).
- **Never shown:** ranks, match percentages, or r as "accuracy". A flat profile still gets r ≈ .93.

## L5 — Free-text layer (research-only)
**Input:** an optional sentence describing interests. **Output:** RIASEC evidence that is fused with L2, or a
"no good match, try the questionnaire" reply.

1. **Cue stripping:** `strip_demographic_cues(text)` is a deterministic regex pipeline. It removes name, age and origin
   introductions, maps gendered and age self-descriptions to "person", and rewrites she/he → they and kinship nouns → neutral
   nouns. The input is never stored. ([e7b](findings/e7b_cue_stripping.md), ADR 0011/0012)
2. **Retrieval:** embed the text with `sentence-transformers/all-MiniLM-L6-v2` (Apache-2.0 per its model card, checked
   2026-11-15; training-data provenance not reviewed; local inference). Rank by cosine
   against the index text "title. Also called: <≤10 reported titles>. description. Tasks: <top-5 tasks by importance>" (variant d).
   Take the top 10. For Spanish, use `paraphrase-multilingual-MiniLM-L12-v2`.
3. **Rejection:** if the top-1 cosine is below 0.262 (MiniLM; 0.332 for the multilingual model), return "no good match". This must be
   recalibrated on real traffic.
4. **Evidence vector:**
   f = Σ_i w_i c_i over the top 10, where c_i is the self-centred OI profile of occupation i and
   w_i = max(sim_i, 0) / Σ max(sim, 0).
   f agrees with the intended letters at r .75, with top-letter accuracy .84. Fusing it with L2 at a modest weight has not been tested yet.

**Validation (E7/E7b, self-written test set):**

| Metric | Result |
|---|---|
| Family Hit@5 | .947 |
| Occupation Hit@5 | .860 |
| Gain over TF-IDF | +21 points |
| Held-out FRR / off-topic rejection | 4.8% / 91.2% |
| Counterfactual overlap, gender + name | .922 (names .838) |
| Lists rated "sensible" (rater = the experimenter, not independent) | 85% |

How to read these numbers:
- Overlap is 1.0 by construction wherever a rule fires (67% of held-out pairs). The CI's lower bound is .84.
- The test set was written by the same author as the rules, and covers explicit cues only.

Known limits of the stripper (E7b; `text_cues.py`):
- Names are recognised only if capitalised (lower-case names typed by teens are missed).
- It does not cover non-Latin scripts, multi-part names, ethnicity, religion, disability or dialect.
- Spanish handling is partial: no noun or adjective gender agreement (enfermera/enfermero).
- It removes identity words silently. If shipped, tell users that names and gender or age words are ignored, and test name
  handling by script and case.

**Blockers before users:**
- Negation reduces the negated type but almost never reverses it (E7 M4).
- An independent held-out set is needed.
- Privacy design: no logging; minors.
- Signposting for sensitive disclosures.
- Better name coverage (E7c).

## L6 — Explanations (design)
For each family shown, the explanation:
1. names the user's two strongest types and where they sit on the hexagon / Prediger map;
2. names the family's typical tasks (O\*NET task statements) and preparation level;
3. says what the match does **not** mean: not ability, and not guaranteed satisfaction (the interest–satisfaction link is
   weak, ρ ≈ .08–.20; RESEARCH §2.2).
4. carries the required data copy: "based on US occupational data (O\*NET)" and "occupation interest ratings are estimated".
   Include the O\*NET attribution on the site and on any derived files (family labels, example lists).

Prediger axes are computed as the angle projection on the hexagon. This is equivalent (|r| = 1.00) to the vendor formulas
People–Things = 2R + I − A − 2S − E + C and Data–Ideas = 1.73(E + C − I − A)
([Strong supplement](https://strongsupplement.themyersbriggs.com/chapter4.html), D; [e2](findings/e2_structure.md)).
These are vendor formulas `[UNVERIFIED against Prediger's original weights]`. The product uses the angle projection, so it
doesn't depend on them.
Things–People is the axis carrying the gender gap (d = .67), so explanations must not frame any career by gender or
mention the user's gender (ADR 0015).
Status: no user testing yet. Copy must follow the honesty rules in RESEARCH.md §9.

## L7 — Feedback learning (not started)
Possible later signals: user ratings of families, "explore" clicks, retests. None of these can be collected until the privacy
design and DPIA exist (CLAUDE.md rule 5). Collaborative filtering isn't feasible at v1 (cold start, no consented interaction
data; note 03). If it is ever used, it must be audited for popularity bias, because ML scoring favours high-base-rate jobs
([Song et al. 2024](https://www.econbiz.de/Record/investigating-machine-learning-s-capacity-to-enhance-the-prediction-of-career-choices/10014535947), B).

## L8 — Field-of-study prediction (research-only, v3)
- **Model:** multinomial logistic regression on the 48 item responses (+ TIPI), predicting 21 major families.
- **Results:**
  - top-3 .565 [.555, .574], vs majority .40 and centroid .32;
  - top-1 about 31% vs 19% for the mode;
  - beats gradient boosting and an MLP.
- **Not for users:**
  - Psychology is over-predicted about twofold.
  - Gender gaps are amplified (Psychology ×1.65, STEM-core ×1.11).
  - Women who studied STEM see it in their top-3 52% of the time, vs 80% for men.
  - The items alone predict gender at AUC .84.

  Adding demographics makes all of this worse, so demographics are never inputs. Any product use requires de-amplification,
  a re-audit and a legal assessment under EU AI Act Annex III(3) `[UNVERIFIED: secondary sources only]`. ([e6](findings/e6_major_prediction.md), ADR 0008)

---

## Sources
- O\*NET Interest Profiler. https://www.onetcenter.org/IP.html
- Strong Interest Inventory technical supplement, ch. 4 (vendor formulas; level D). https://strongsupplement.themyersbriggs.com/chapter4.html
- Udayar, S., et al. (2020). Career indecision meta-analysis. https://serval.unil.ch/fr/notice/serval:BIB_AF059FD4623A
- Song, Q. C., et al. (2024). Personnel Psychology 77(2). https://www.econbiz.de/Record/investigating-machine-learning-s-capacity-to-enhance-the-prediction-of-career-choices/10014535947
- Own experiments: `research/findings/e1_data_audit.md` … `e7b_cue_stripping.md`.
