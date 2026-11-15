# Carrier_helper — Research dossier (v0)

Status: v0 feasibility, assembled 2026-11-16 from `research/notes/01–06` and `research/findings/e1–e7b`.
Companion docs: [DATA_SOURCES.md](DATA_SOURCES.md) (datasets), [MODELS.md](MODELS.md) (model layers),
[ROADMAP.md](ROADMAP.md) (v1–v3). Decisions and work log are in [`docs/`](../docs/README.md).

How to read this document: every number has a source, either a URL or a findings file. Evidence levels follow the
`evidence-and-citations` skill: **A** meta-analysis or official documentation, **B** large peer-reviewed study, **C** small
study, preprint or thesis, **D** vendor, press or blog, **E** our own experiment. `[UNVERIFIED]` marks claims not yet
checked against a primary source. Lines that start with *Interpretation:* are our reading, not evidence.

---

## 1. Executive summary

**Verdict: feasible, with constraints that change the product design.** A short questionnaire can estimate a RIASEC interest
profile and match it to O\*NET occupations well enough to suggest **career families worth exploring**. It cannot produce a
precise ranked list of jobs. Before anything reaches users, several release blockers must be cleared (section 9).

| Question | Answer | Evidence |
|---|---|---|
| Is the model (Holland RIASEC) sound? | Yes as a structure. The hexagon order holds in our data (E2). Its link to outcomes is modest: congruence r = .32 with performance, and only ρ ≈ .08–.20 with satisfaction. | A + E |
| Is there usable data? | Yes for research: 80,085 clean questionnaire rows (α .83–.90), and O\*NET 31.0 for 923 occupations. The questionnaire data has **no license**, so it is research-only. | E1, DATA_SOURCES |
| How many questions? | About 12 items give scale scores at r ≥ .90 with the full test. **24 items** give family-level results about as stable as the full 48-item test. An adaptive test (CAT) adds nothing with this item bank. | E4 |
| How precise are results? | Not precise at the job level. Even the full test reproduces only about 55% of its own top-10 jobs under answer noise. Families are more stable (top-10 family hit about .70). | E5 |
| What to show users | An **unordered set of about 3 career families** with 2–3 example jobs each. No ranks or match percentages. | E3, E5 |
| Can free text help? | Retrieval works well (top-5 family hit .95), and removing names, gender and age from the text before matching fixes most of the bias in our tests. Negation is not handled, so free text stays optional and research-only. | E7, E7b |
| Can it predict a university major? | Better than baselines (top-3 .565 vs .40), but it **amplifies gender gaps**, so it stays research-only (v3). | E6 |
| Is it fair? | Not yet shown. Interests themselves differ by gender (Things–People d = .93 in the literature, .67 here). Matching faithfully passes that difference into the results. Some items show gender DIF. | A + E |

What makes the project different (*interpretation*, from note 05): it is free and short (24 items vs 250 for the SDS),
publishes its evidence and uncertainty, explains why each family fits, and has a dedicated path for users who don't
know what they like.

Main limits, stated plainly:
- O\*NET describes **US** occupations, and its interest profiles are **ML-estimated**.
- The questionnaire sample is self-selected, young and 67% female, with no Spanish-language responses.
- Interests ≠ satisfaction ≠ ability.
- No result has been validated with real users or against career outcomes.

---

## 2. Theory and evidence

### 2.1 The RIASEC model
Holland's six interest types are arranged on a hexagon (R-I-A-S-E-C). Two underlying axes, People↔Things and
Data↔Ideas (Prediger), summarise it.
- **Cross-cultural fit is weak.** The circular order did not hold across 76 international matrices from 18 countries or across 20
  US ethnic-minority matrices (Rounds & Tracey 1996, A).
- **It does hold in our sample** (E2, level E):
  - The ordering test is supported (RTOR CI .97 [.92, 1.00]), and MDS and PCA both recover R-I-A-S-E-C.
  - 45 of 48 items load on their intended scale.
  - Parallel analysis retains 8 factors rather than 6, because Investigative splits into two content facets.
  - Absolute CFA fit is poor (CFI ≈ .80). ([e2_structure.md](findings/e2_structure.md))
- **Measurement invariance** (E2):
  - Factor loadings are invariant across gender and age (metric invariance).
  - Intercepts are not (**scalar invariance fails**), so raw score levels can't be compared across groups.
  - This matches the general pattern in small invariance studies (note 06, C, `[UNVERIFIED]`).
  - We did not test by country or language.

### 2.2 What interests predict
| Outcome | Finding | Level | Source |
|---|---|---|---|
| Job performance | Congruence r = .32; interest scores alone r = .16 (92 studies) | A | [Nye et al. 2017](https://experts.illinois.edu/en/publications/interest-congruence-and-performance-revisiting-recent-meta-analyt/) |
| Performance / turnover | Single scales: performance .14, training .26, actual turnover −.15 | A | [Van Iddekinge et al. 2011](https://digitalcommons.memphis.edu/facpubs/11916) |
| Satisfaction | Congruence ρ ≈ .08–.20 depending on the index | A/B | [SAGE 2021](https://journals.sagepub.com/doi/pdf/10.1177/08948453211033903) |
| Satisfaction | Significant but "not as strong as people expect" (105 studies); exact ρ `[UNVERIFIED]` | A | [Hoff et al. 2020](https://sciencedaily.com/releases/2020/11/201111144353.htm) |
| Career choice | Inventories hit the chosen category 50.8% of the time | A | [Hanna & Rounds 2020](https://www.ideals.illinois.edu/items/109885) |
| Degree completion | Interest–major congruence directly predicts timely completion | B | [Allen & Robbins 2010](https://bvbvf1.bib-bvb.de/vufind/PrimoRecord/cdi_proquest_miscellaneous_816531011) |
| Stability | Interests are fairly unstable in adolescence, stabilise sharply around ages 18–22, then stay high | A | [Low et al. 2005](https://doi.org/10.1037/0033-2909.131.5.713) |

*Interpretation:* these effects are real but modest. That justifies the framing "careers worth exploring", treating
results for teens as a snapshot, and never claiming a predicted fit or future satisfaction.

### 2.3 Instruments disagree with each other
SDS, O\*NET IP, ACT and Strong scores correlate highly, but they often give **different high-point codes**
([Chu et al. 2022](https://experts.illinois.edu/en/publications/what-do-interest-inventories-measure-the-convergence-and-content-/), B).
Our own top letter agrees with itself only 76% of the time under answer noise, and the exact 3-letter order only 38%
([e5_stability.md](findings/e5_stability.md)). So the Holland code is shown as top letter + "also", never as a precise
3-letter label.

### 2.4 Gender and group differences
- Large gender differences exist in measured interests: Things–People d = 0.93, R d = .84, S d = −.68 (47 inventories,
  503,188 respondents; [Su et al. 2009](https://iro.uiowa.edu/esploro/outputs/journalArticle/Men-and-things-women-and-people/9984380502202771), A).
- They are smaller in our sample:
  - R .71 and S −.38 ([e1_data_audit.md](findings/e1_data_audit.md)).
  - Things–People d = .67, and .80 among teens ([e2_structure.md](findings/e2_structure.md)).
- **Consequence for matching (E3):** with Pearson matching, women's top-10 lists contain 1.7% Realistic-top occupations vs 8.9%
  for men ([e3_occupation_space.md](findings/e3_occupation_space.md)). The matcher reproduces what people answer.
  Whether to counter that is a values decision (section 9).

---

## 3. Prior work and competitors

| Tool | Length | Price | Validity evidence | Source (level) |
|---|---|---|---|---|
| O\*NET Interest Profiler / My Next Move | Mini-IP 30, Short Form 60 items | Free, CC BY 4.0 | Official reports; coefficients not decoded `[UNVERIFIED]` | [O\*NET IP](https://www.onetcenter.org/IP.html) (A) |
| Strong Interest Inventory | 244 items (reseller) `[UNVERIFIED]` | Paid, practitioner-gated | Tech brief: alphas ≥ .91 `[UNVERIFIED primary]` | [Strong](https://www.themyersbriggs.com/en-US/Products-and-Services/Strong) (D) |
| Self-Directed Search | 250 questions | $18.95 | Vendor claims only | [SDS](https://www.self-directed-search.com/) (D) |
| CareerExplorer | About 30 min | Free | Vendor "industry-leading accuracy", no independent study | [CareerExplorer](https://www.careerexplorer.com/career-test/) (D) |
| Truity Holland test | Not stated | Free quiz | No statistics on the page | [Truity](https://www.truity.com/test/holland-code-career-test) (D) |

ML recommenders:
- **Vocation Compass.** Its "over 70% accuracy" is a **press figure** for what appears to be a 10-profession task
  ([UNSW press](https://www.unsw.edu.au/newsroom/news/2019/12/new-map-reveals-the-hidden-personality-profiles-of-jobs), D;
  [repo](https://github.com/behavioral-ds/VocationMap)).
- **ML-augmented interest scoring** beats profile matching but under-predicts rare occupations
  ([Song et al. 2024](https://www.econbiz.de/Record/investigating-machine-learning-s-capacity-to-enhance-the-prediction-of-career-choices/10014535947), B).
- **LLM career advice** shows gender, name and nationality bias
  ([Salinas et al. 2023](https://arxiv.org/abs/2308.02053); [Nghiem et al. 2024](https://arxiv.org/abs/2406.12232);
  [Forcada Rodriguez et al. 2025](https://arxiv.org/abs/2505.02456); C).
- No benchmark exists for mapping free-text interests to O\*NET (note 04).

*Interpretation (note 05):* the gaps we can fill are short length with published precision, explanations, a
lost-user path and transparent uncertainty. Counsellor-led, personalised interventions appear to work better than
self-directed tools (secondary summary, `[UNVERIFIED]`), so the product should produce a summary the user can take to a
counsellor rather than present itself as a replacement.

---

## 4. Data

Full detail is in [DATA_SOURCES.md](DATA_SOURCES.md).

| Source | Used for | License | Key limit |
|---|---|---|---|
| OpenPsychometrics RIASEC 2018 (48 items) | E1–E6: structure, IRT, stability, major prediction | **None stated → research only** (ADR 0002) | Self-selected; median age 23, 67% female, 49% US; no Spanish (E1) |
| O\*NET 31.0 | Occupation profiles (923 rated), tasks, titles, job zones | CC BY 4.0, attribution required | US-centric; interest ratings all ML-estimated, 11.9% clipped at 1 or 7 (E3) |
| O\*NET 30.2 Work Values | Reserved for later | CC BY 4.0 | Frozen at 30.2 |
| Embedding models (MiniLM, multilingual MiniLM) | E7 free text | Apache-2.0 | Local inference only |

Two mismatches shape the design:
- People lean S/I/A while the catalogue leans R: 42% of occupations are R-top and only 3% A-top
  ([e1_data_audit.md](findings/e1_data_audit.md)).
- Interest shape is confounded with preparation level (job zone; Cramér's V = .45). Without a filter, S/I users see mostly
  graduate-level careers (mean job zone 4.2), while R users see mostly job zone 2 ([e3_occupation_space.md](findings/e3_occupation_space.md)).

---

## 5. Experiment results (all level E)

Each experiment was pre-registered before it ran, and bars are never changed after results (ADR 0003). Several bars were later
judged mis-specified. The original verdict stands, and the discussion explains why.

| ID | Question | Verdict vs its bar | Headline | Findings |
|---|---|---|---|---|
| E1 | Is the questionnaire data usable? | **Proven** | 80,085 clean rows; α .831–.898; every gender × age cell n ≥ 3,997 | [e1](findings/e1_data_audit.md) |
| E2 | Do 6 factors and the hexagon hold? | Factors promising, hexagon **proven**, archetypes proven but soft | Metric invariance holds, scalar fails; 8 items flagged (3 weak, 5 gender DIF) | [e2](findings/e2_structure.md) |
| E3 | How differentiated is the occupation space? | **Proven** (lenient bar) | Pearson median top-1 r .928; only about 100–170 distinct profiles; exposure Gini .77; 28 A-top occupations | [e3](findings/e3_occupation_space.md) |
| E4 | How few questions are enough? | **Not viable** as written (bar unreachable for any test) | 12 items → r .915; 24 items → r .965–.968, top-3 family .63–.64; CAT gain ≤ +.005 r | [e4](findings/e4_cat_simulation.md) |
| E5 | How stable are recommendations? | **Promising** | Top-10 overlap .553, family hit .697; retest-like .42; flat profiles .17 | [e5](findings/e5_stability.md) |
| E6 | Can answers predict major family? | **Proven** (research-only) | Top-3 .565 vs majority .40, centroid .32; Psychology gap ×1.65; items predict gender (AUC .84) | [e6](findings/e6_major_prediction.md) |
| E7 | Free text → occupations? | **Not viable** (bias bar) | Family Hit@5 .95, occupation .86; +21 points over TF-IDF; rejection FRR 3.9%; gender/name overlap .733 < .90 | [e7](findings/e7_free_text_matching.md) |
| E7b | Does stripping demographic cues fix E7's bias? | **Proven** (not independent) | Held-out overlap .739 → .922 with no quality loss; names .838; rule coverage 67% | [e7b](findings/e7b_cue_stripping.md) |

What this adds up to (*interpretation*):
1. **Measurement is adequate.** Scales are reliable, the hexagon holds and 24 items track the full test closely (E1, E2, E4).
2. **Precision of output is the binding constraint.** The full test reproduces only about 55% of its own top-10 jobs under answer
   noise (E5), and E4's 70% bar was therefore unreachable. Results must be shown at family level.
3. **The occupation catalogue limits diversity.** Near-duplicate R occupations, thin A/S coverage and the job-zone
   confound need catalogue work and a visible preparation filter. Re-ranking alone won't fix them (E3).
4. **Fairness problems come from the inputs, not just the models.** Item DIF (E2), real interest differences (E2/E3),
   label history (E6) and text cues (E7) each enter by a different route and need different fixes.
5. **"Lost" users are a small, identifiable group.** About 4% have flat profiles and 11% low elevation. They get the least
   stable lists (E1, E5), so they need a different flow, not a ranked list.

---

## 6. Recommended architecture (v1)

The specification is in [MODELS.md](MODELS.md).

```
24-item fixed questionnaire (round-robin R-I-A-S-E-C, flagged items removed)          [E4, E2]
  -> six GRMs + EAP with correlated prior -> predicted full-scale profile + SE          [E4]
  -> gates: differentiation < 1.0 or elevation < 2.0 -> lost-user flow                  [E1, E5, E4]
  -> Pearson match vs 923 O*NET profiles (matching.py), within a user-chosen job-zone range [E3]
  -> group into ~100 families (r >= .80), family cap for diversity                      [E3, E5]
  -> show about 3 families x 2-3 example jobs, unordered, with "why it fits" explanations  [E5, ADR 0006]
optional: free text -> strip demographic cues -> MiniLM retrieval -> RIASEC evidence      [E7, E7b]
          (research-only until negation handling, privacy design and an independent test exist)
```

No collaborative filtering (there's no interaction data and it's a cold-start problem; note 03). No LLM-generated
advice, only retrieval of existing O\*NET records (E7, ADR 0007). Demographics are never model inputs (E6: adding them
makes amplification much worse).

---

## 7. Evaluation framework

| Layer | Metric | Current value | Source |
|---|---|---|---|
| Measurement | r(short form, full test) per scale; reliability | .965–.968 at 24 items; α .83–.90 | E4, E1 |
| Output stability | Top-3 family agreement; family hit rate under SEM noise | .63–.64; .697 | E4, E5 |
| Coverage | Exposure Gini; occupations reached by ≥ 0.1% of people | .77; 71% | E3 |
| Fairness | Per-group family agreement; R/S share by gender; counterfactual overlap (free text) | Boys 13–17 top-10 .46; R-top share 1.7% vs 8.9%; overlap .922 | E5, E3, E7b |
| Free text | Occupation Hit@5; rejection FRR / off-topic | .86; 4.8% / 91.2% | E7, E7b |
| Users (not yet measured) | Perceived usefulness; career decision self-efficacy; exploration actions | — | design, note 06 |
| Outcomes (not yet measured) | Later satisfaction, persistence | — | note 01 |

Rules:
- **Never quote match r or similarity scores as accuracy.** A flat profile still gets r ≈ .93 (E3).
- Compare to base rates (Hanna & Rounds 2020).
- Report simulation results alongside live results: one CAT study found simulated agreement of .91–.97 but only .73–.91 live
  ([Alkan & Deniz 2023](https://dergipark.org.tr/en/pub/epod/issue/76343/1153713), C).

---

## 8. Why a ranked list is the wrong output

- Even the full 48-item test keeps only about 55% of its top-10 under noise (42% for a retest-like comparison), and Kendall τ
  on the top-20 is .41 (E5).
- 24 items reach .54 top-10 overlap with the full test (E4).
- Families at r ≥ .80 are more stable than individual jobs (+.14 to +.25 at family level, E5).

That is why ADR 0006 removes ranks and percentages. Within a family, examples can be ordered by criteria the user can see
(preparation, wages, outlook) rather than by tiny differences in r.

---

## 9. Risks and ethics

The ethics review (2026-11-15) is summarised in CLAUDE.md and in E7 Addendum A. Release blockers:

| Blocker | Status | Why |
|---|---|---|
| O\*NET attribution | Done (README) | CC BY 4.0 |
| Privacy/legal design + DPIA | Open | Profiling of minors. GDPR Art. 8: consent age 16 by default, 13 minimum ([GDPR Art. 8](https://gdpr-info.eu/art-8-gdpr/), A). Spain: 14 ([LOPDGDD Art. 7](https://www.boe.es/buscar/act.php?id=BOE-A-2018-16673), A). Art. 22, DPIA and the AI Act are `[UNVERIFIED]` and need a lawyer or DPO. |
| Re-audited DIF on the final item set | Open | E2 found gender DIF; replacement items aren't written yet |
| Validated lost-user flow | Open | Design only. Indecision is linked to low self-efficacy, not just missing information ([Udayar et al. 2020](https://serval.unil.ch/fr/notice/serval:BIB_AF059FD4623A), A) |
| Permission for OpenPsychometrics-derived parameters | Open | No license (ADR 0002). Alternatively, use our own calibration sample |

Other risks:
- **Gender steering.** Faithful matching passes interest differences into results (E3), and supervised models amplify them (E6).
  Mitigations: DIF-screened items, a "careers you might not have considered" option (an ethics decision), and per-group monitoring.
- **US-centric catalogue.** EU users would see US job titles and preparation levels. ESCO mapping is planned for v2.
- **Overclaiming.** Copy must say "worth exploring". Never percentages, ranks or "your perfect career".
- **Free text.** It can contain sensitive disclosures (self-harm, abuse), so it needs a signposting response. Process it in
  memory only, with no logging (E7 Implications 7).
- **Minors' interests change** (Low et al. 2005). Present results as a snapshot and invite a retest.
- **AI Act.** Steering learners in education may be high-risk (Annex III point 3, cited in E6). This is why E6 stays research-only.

---

## 10. Open questions

1. How do live 24-item results compare with simulations on real users (E4 caveat)?
2. Does the hexagon/RIASEC structure hold in Spanish and for Spanish/EU users? (Untested; Rounds & Tracey 1996.)
3. Exact numbers that still need a primary source: Hoff et al. 2020 ρ; O\*NET Mini-IP / Short Form reliability; Prediger
   weights; the Morris 2016 correction; Vocation Compass accuracy definition (notes 01–03, 05, 06).
4. Should the product counter gender differences in results (e.g. a counter-stereotypic slot), or only remove measurement
   bias? (Values question for the ethics review.)
5. What lost-user flow improves career decision self-efficacy? (No direct evidence found.)
6. Can permission be obtained from OpenPsychometrics, or do we need our own calibration sample (size, consent)?
7. ESCO ↔ O\*NET crosswalk quality for EU users (note 04).
8. Free-text negation handling, and an independent held-out set for cue stripping (E7, E7b).

---

## Sources

Literature (details and levels in `research/notes/`):
- Allen, J., & Robbins, S. (2010). J Counseling Psychology 57(1), 23-35. https://bvbvf1.bib-bvb.de/vufind/PrimoRecord/cdi_proquest_miscellaneous_816531011
- Alkan, V., & Deniz, K. Z. (2023). CAT form of the Occupational Field Interest Inventory. https://dergipark.org.tr/en/pub/epod/issue/76343/1153713
- Chu, Russell, Hoff, Phan & Rounds (2022). What do interest inventories measure? J Career Assessment 30(4). https://experts.illinois.edu/en/publications/what-do-interest-inventories-measure-the-convergence-and-content-/
- Forcada Rodriguez, E., et al. (2025). arXiv 2505.02456. https://arxiv.org/abs/2505.02456
- Hanna, G., & Rounds, J. (2020). How accurate are interest inventories? Psychological Bulletin. https://www.ideals.illinois.edu/items/109885
- Hoff, K. A., et al. (2020). Interest fit and job satisfaction (summary). https://sciencedaily.com/releases/2020/11/201111144353.htm
- Kern, M. L., et al. (2019) / UNSW press release (D). https://www.unsw.edu.au/newsroom/news/2019/12/new-map-reveals-the-hidden-personality-profiles-of-jobs ; https://github.com/behavioral-ds/VocationMap
- Low, K. S. D., Yoon, M., Roberts, B. W., & Rounds, J. (2005). Psychological Bulletin 131(5), 713-737. https://doi.org/10.1037/0033-2909.131.5.713
- Nghiem, H., et al. (2024). arXiv 2406.12232. https://arxiv.org/abs/2406.12232
- Nye, C. D., Su, R., Rounds, J., & Drasgow, F. (2017). JVB 98, 138-151. https://experts.illinois.edu/en/publications/interest-congruence-and-performance-revisiting-recent-meta-analyt/
- Rounds, J., & Tracey, T. J. G. (1996). J Counseling Psychology 43(3), 310-329. https://experts.illinois.edu/en/publications/cross-cultural-structural-equivalence-of-riasec-models-and-measur/
- Salinas, A., et al. (2023). arXiv 2308.02053. https://arxiv.org/abs/2308.02053
- Song, Q. C., et al. (2024). Personnel Psychology 77(2), 295-319. https://www.econbiz.de/Record/investigating-machine-learning-s-capacity-to-enhance-the-prediction-of-career-choices/10014535947
- Su, R., Rounds, J., & Armstrong, P. I. (2009). Psychological Bulletin 135(6), 859-884. https://iro.uiowa.edu/esploro/outputs/journalArticle/Men-and-things-women-and-people/9984380502202771
- Congruence–satisfaction review (2021). https://journals.sagepub.com/doi/pdf/10.1177/08948453211033903
- Udayar, S., et al. (2020). J Career Assessment. https://serval.unil.ch/fr/notice/serval:BIB_AF059FD4623A
- Van Iddekinge, C. H., et al. (2011). J Applied Psychology 96, 1167-1194. https://digitalcommons.memphis.edu/facpubs/11916

Products, law and data:
- O\*NET Interest Profiler. https://www.onetcenter.org/IP.html · O\*NET ML occupational interest profiles. https://www.onetcenter.org/reports/ML_OIPs.html
- Strong. https://www.themyersbriggs.com/en-US/Products-and-Services/Strong · SDS. https://www.self-directed-search.com/ · CareerExplorer. https://www.careerexplorer.com/career-test/ · Truity. https://www.truity.com/test/holland-code-career-test
- GDPR Art. 8. https://gdpr-info.eu/art-8-gdpr/ · LOPDGDD Art. 7. https://www.boe.es/buscar/act.php?id=BOE-A-2018-16673

Own experiments (level E): `research/findings/e1_data_audit.md`, `e2_structure.md`, `e3_occupation_space.md`,
`e4_cat_simulation.md`, `e5_stability.md`, `e6_major_prediction.md`, `e7_free_text_matching.md`, `e7b_cue_stripping.md`.
