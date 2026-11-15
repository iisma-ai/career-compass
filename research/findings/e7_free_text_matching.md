# E7 — Free-text interests → O*NET occupations with sentence embeddings

Pre-registered 2026-11-15, before writing or running `research/feasibility/e7_free_text_matching.py` and before any
embedding model was downloaded. The test set (`e7_test_statements.csv`, 95 statements) and the off-topic set
(`e7_offtopic_inputs.csv`, 32 inputs) were written first. The only thing I consulted while writing them was the list of
the 923 rated occupation codes and titles (and their Holland codes) in `data/processed/onet_occupations.parquet`. No
retrieval output of any kind existed when they were written.

## Pre-registration

```
Question:      Can a local sentence-embedding retriever map a short free-text interest statement
               ("I love fixing bikes") to O*NET occupations a counsellor would call sensible,
               reject off-topic input, cope with negation and Spanish, and stay invariant to
               gender, name and age cues?
Hypothesis:    No benchmark exists for this task (research/notes/04-free-text-and-llm-matching.md).
               Job-title -> occupation retrieval reaches roughly 54-72% at fine SOC levels
               [UNVERIFIED there], and our statements are vaguer than titles, so we expect
               occupation-level Hit@5 of about 35-55%, but family-level Hit@5 (E3 r >= .80
               families, 101 families) of about 65-80%, because families absorb near-duplicates.
               (1) A richer index (title + description + top tasks + alternate titles, variant d)
               or task max-similarity (c) beats title + description (a).
               (2) Embeddings beat TF-IDF by >= 10 points, mainly on hobby/paraphrase statements
               that share no words with O*NET text.
               (3) Negation is handled poorly (bi-encoders are known to be weak on negation), so
               negated statements and their positive twins will share many top-10 occupations.
               (4) The English MiniLM fails on Spanish. The multilingual model is within about
               15 points of its English performance.
               (5) Gender, name and age cues shift a few results (overlap ~.8-.9), and the shift
               is in a stereotyped direction (female -> more S/A), as reported for LLMs (Salinas et
               al. 2023, arXiv 2308.02053; Nghiem et al. 2024, arXiv 2406.12232).
               (6) Off-topic input gets clearly lower top-1 similarity than real statements, but
               vague "lost" statements sit in between.
Data:          O*NET 31.0 (CC BY 4.0), restricted to the 923 rated occupations in
               data/processed/onet_occupations.parquet (title, description, RIASEC OI 1-7).
               Read-only from data/raw/onet_31_0/db_31_0_csv/: task_statements.csv (18,420 tasks;
               every rated occupation has >= 4), task_ratings.csv (IM importance, to pick top
               tasks), sample_of_reported_titles.csv (alternate titles; 8 rated occupations have
               none), interests_illustrative_activities.csv (RIASEC prototypes for the fusion test),
               career_interest_type_keywords.csv (keyword baseline).
               Families: research/findings/e3_families.csv (family_r80 primary, family_r90 secondary).
               Test set: research/findings/e7_test_statements.csv, 95 statements (79 EN, 16 ES):
                 pure 12 (2 per type), mixed 10, hobby 10, negation 6 + 6 positive twins,
                 vague 6 + vague_empty 3 (no sensible set), Spanish translations 12,
                 gender pairs 7 (14 rows, 1 Spanish), name pairs 5 (10 rows, 1 Spanish),
                 age pairs 3 (6 rows).
               Off-topic set: research/findings/e7_offtopic_inputs.csv, 32 inputs (27 EN, 5 ES):
                 gibberish, chit-chat, off-topic questions, a prompt-injection string.
Method:        Models (local, from the Hugging Face hub, default cache, nothing stored in the repo):
                 primary   sentence-transformers/all-MiniLM-L6-v2 (English, 384-d, ~90 MB);
                 secondary sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
                           (50+ languages, 384-d, ~470 MB).
               Embeddings L2-normalised; similarity = cosine. Queries are encoded as written (no
               preprocessing, no removal of demographic words). Nothing leaves the machine
               except the one-time model download.
               Index variants over the 923 occupations:
                 (a) "title. description"
                 (b) mean of the embeddings of all its task statements (re-normalised)
                 (c) occupation score = max cosine over its individual task statements
                 (d) "title. Also called: <up to 10 reported titles>. description. Tasks: <top 5
                     tasks by IM importance>" (truncated at the model's max sequence length,
                     256 / 128 word pieces; the truncation share is logged)
               Retrieval: top-10 by score; exact ties broken by catalogue order.
               Best variant = the (model, variant) cell with the highest family Hit@5 on EN-core
               (ties: occupation Hit@5, then the simpler variant a < b < c < d, then the primary
               model). This selects on the test set (8 cells), which is disclosed as optimism.
Baselines:     (i) TF-IDF (scikit-learn, English stop words, 1-2-grams, sublinear tf) fitted on the
                   index texts of variant (a) and of variant (d); cosine retrieval. The comparison
                   uses the better of the two ("best TF-IDF").
               (ii) Keyword -> RIASEC -> Pearson (O*NET-style): count case-insensitive matches of
                   the 75 O*NET career-interest keywords (prefix match on word stems) per type,
                   use the 6 counts as a profile, rank by matching.py "pearson". No keyword hit
                   gives a flat profile (catalogue-order ranking, which is how the module behaves).
               (iii) Random top-10 (2,000 draws per statement).
Metrics:       Sets: EN-core = English rows in pure, mixed, hobby, negation, negation_twin (44)
               plus the first member (female / name_female / name_a / young) of each English pair
               (13) = 57 statements. Also reported: vague (6 EN), Spanish (12), per category.
               M1 Hit@k (k = 5, 10): occupation level = any top-k code in the sensible set;
                  family level = any top-k code's family_r80 among the sensible codes' families.
                  family_r90 is secondary. 95% CI: percentile bootstrap over statements (B = 2000).
                  Paired bootstrap CI for best variant minus best TF-IDF.
               M2 RIASEC agreement: target t = weights 3/2/1 for the 1st/2nd/3rd intended letter,
                  0 otherwise. p = mean OI profile of the top-10. Report the mean Pearson r(p, t), the
                  share with argmax(p) = first intended letter, and the share with argmax(p) among
                  the intended letters.
               M3 Rejection: score = top-1 similarity of the variant. Real = all English statements
                  with a sensible set (76; includes vague and pair rows). Off-topic = 27 English
                  inputs. 200 random stratified 50/50 splits; on the calibration half the threshold
                  maximises Youden's J (midpoints between sorted scores; ties go to the lower
                  threshold); on the held-out half report FRR (real rejected) and the off-topic
                  rejection rate. Proposed product threshold = Youden on all data. vague_empty
                  statements are reported descriptively (rejecting them would send them to the
                  questionnaire, which is arguably correct). For the multilingual model the same
                  analysis is repeated with EN + ES inputs.
               M4 Negation (6 pairs N01-N06 vs NT01-NT06): top-10 overlap between each negated
                  statement and its positive twin (lower = better; reference = mean overlap between
                  unrelated EN-core statements). Centred score of the negated letter(s) in the
                  top-10 mean profile, negated vs twin. Family Hit@5 of negation rows.
               M5 Spanish: for the 12 translation pairs, family/occupation Hit@5 on the ES version
                  vs the EN original, per model; cross-lingual top-10 overlap (EN vs ES).
               M6 Bias: for gender (7), name (5) and age (3) pairs: top-10 overlap |A & B| / 10;
                  shift in the centred top-10 mean profile (L2, and signed per letter as
                  female - male / young - older); Hit@5 by pair member (female vs male, young vs
                  older) as the subgroup metric.
               M7 Fusion: evidence vector f = sum_i w_i * c_i over the top-10, c_i = self-centred OI
                  profile, w_i = max(sim_i, 0) normalised. Agreement with t: mean Pearson r(f, t)
                  and top-letter accuracy. Alternative route: cosine to six RIASEC prototypes (the
                  mean embedding of each type's O*NET illustrative activities), centred. Chance:
                  r = 0, top-letter accuracy 1/6.
               M8 Blind rating: 30 top-5 lists. 20 from the best variant on 20 statements sampled
                  (seed 42) from EN-core + vague, 5 from best TF-IDF and 5 random lists (other
                  sampled statements), shuffled. The sheet shows only statement + 5 titles; the
                  method key is written to a separate file that the rater does not open before
                  rating. Scale: sensible = >= 3 of 5 titles a counsellor would call sensible and
                  none contradicts the statement; partly = 1-2 sensible; not = 0 sensible or a
                  clear contradiction (e.g. the negated activity). The rater is the experimenter
                  (who also wrote the statements), so this is not independent.
Success bar:   (proposal from the task brief; the rejection criterion adds an off-topic
               requirement, so that the FRR bar can't be met trivially with a threshold of 0)
               PROVEN if all of:
                 (1) best variant family Hit@5 >= .70 on EN-core (point estimate);
                 (2) best variant minus best TF-IDF >= 10 points of family Hit@5 on EN-core;
                 (3) held-out FRR <= 10% (mean over splits) AND held-out off-topic rejection
                     >= 80%, for the best variant;
                 (4) mean top-10 overlap >= .90 over the 12 gender + name pairs (best variant).
               PROMISING if not proven but: (1) >= .55, (2) >= 5 points, (3) FRR <= 20% with
                 off-topic rejection >= 60%, and (4) >= .80.
               NOT VIABLE otherwise.
               Secondary bar (feasibility-experiment skill): >= 70% of the 20 blind-rated
               best-variant top-5 lists rated "sensible". Reported as a separate line and not
               merged into the verdict above.
               Spanish, negation, fusion and age pairs are reported but not gated.
```

---

### Addendum A: ethics-review checks (added 2026-11-15, still before any model download or run)

This addendum adds checks requested by the ethics review. **Nothing above is changed**: the EN-core set (57), the
rejection "real" set (76), the 12 gated gender + name pairs and the success bar keep their definitions. The added rows are
excluded from those sets.

- **New counterfactual rows (12):** 3 pronoun / gendered-noun pairs (`pronoun_pair`: she/he, my daughter/my son) and
  3 nationality pairs (`nationality_pair`: Mexico/Canada, Nigeria/Sweden, ES Marruecos/España). Test set total 107 rows.
  These pairs are reported under M6 and are **not gated**.
- **Trades / low-preparation coverage:** a statement counts as "trades" if more than half of its sensible codes have job
  zone <= 3. 42 of the 104 statements with a sensible set (40%) count as trades. For comparison, 545 of the 923 catalogue
  occupations (59%) are job zone 2-3, so the set leans toward degree-level interests relative to the catalogue. Hit@5 is
  also reported for trades vs non-trades statements.
- **M6 extended:** for every pair type, the reports cover top-10 overlap plus the shift in the top-10's **job-zone
  composition** (mean job zone and share of job zone >= 4, A - B) and **RIASEC composition** (share of top-10
  occupations by top letter, and the centred mean-profile shift). ES vs EN is covered by M5 (cross-lingual overlap).
- **"No good match" response:** the evaluation reports, per input, whether the proposed threshold would give a "no good
  match, try the questionnaire" response instead of a forced list.
- **Licenses:** each model's license is read from its downloaded model card and recorded in Results.
- **Retrieval only:** the pipeline only ranks existing O*NET records. No text is generated.

---

## Results

Run: `.venv/Scripts/python -I research/feasibility/e7_free_text_matching.py --seed 42` (323 s on CPU), after a `--quick`
smoke run (MiniLM only). The blind ratings were then scored with `--score-blind`. Raw results:
`research/findings/e7_free_text_matching.json`. Per-statement table: `e7_per_statement.csv`. Blind sheet / key / ratings:
`e7_blind_sheet.csv`, `e7_blind_key.json`, `e7_blind_ratings.csv`. Post-hoc control: `e7_posthoc_counterfactual.json`
(script `research/feasibility/e7_posthoc_counterfactual.py`).
Counts as pre-registered: EN-core n = 57; rejection real EN = 76, off-topic EN = 27.
**Correction to the Data line:** the rated occupations have **18,838 task statements**. The 18,420 in the Data line was
the number of IM rating rows; tasks without an IM rating are ranked last when picking the top 5. Everything is level E
evidence (own experiment on a self-written test set).

### Models (downloaded once into the default Hugging Face cache, outside the repo; all inference local)

| Model | Size (approx.) | License (model card) | Max tokens | Variant (d) texts truncated | Index + query time |
|---|---|---|---|---|---|
| `sentence-transformers/all-MiniLM-L6-v2` | ~90 MB | **apache-2.0** | 256 | 6.7% | 77 s |
| `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` | ~470 MB | **apache-2.0** | 128 | **99.1%** (median 227 tokens) | 153 s |

Both licenses allow commercial use. The multilingual model's 128-token limit cuts off almost every variant-(d) text,
which mostly keeps the title, alternate titles and the start of the description.

### M1: Hit@k on EN-core (n = 57; 95% bootstrap CI over statements, B = 2000) (`e7_hit_at_k.png`)

| Method | Family Hit@5 (r>=.80) | Family Hit@10 | Occupation Hit@5 | Occupation Hit@10 | Family Hit@5 (r>=.90) |
|---|---|---|---|---|---|
| minilm:a title+desc | .93 [.86, .98] | .93 | .79 [.68, .89] | .82 | .89 |
| minilm:b mean tasks | .88 [.79, .96] | .91 | .74 | .81 | .84 |
| minilm:c max task | .88 [.79, .96] | .91 | .70 | .79 | .84 |
| **minilm:d rich text (best)** | **.95 [.88, 1.00]** | .98 | **.86 [.77, .95]** | .93 | .91 |
| mml12:a | .91 | .96 | .82 | .93 | .89 |
| mml12:b | .93 | .96 | .77 | .89 | .86 |
| mml12:c | .84 | .89 | .60 | .77 | .77 |
| mml12:d | .91 [.84, .98] | .95 | .75 | .86 | .89 |
| TF-IDF (a) | .68 | .79 | .44 | .56 | .61 |
| **TF-IDF (d) (best TF-IDF)** | .74 [.61, .84] | .91 | .49 [.37, .61] | .58 | .67 |
| Keyword -> RIASEC -> Pearson | .30 [.18, .42] | .33 | .18 | .23 | .26 |
| Random top-10 (expected) | .30 [.25, .37] | .47 | .03 | .07 | .21 |

- Best minus best TF-IDF: **+21.1 points** family Hit@5 (paired CI [+8.8, +33.3]) and **+36.8 points** occupation Hit@5
  ([+22.8, +50.9]). Best minus keyword baseline: +64.9 points family Hit@5.
- **The family metric is lenient.** A random top-5 already gets 30% at family level, because E3's r >= .80 families are
  broad (the big R block). Occupation Hit@5 (.86 vs random .03) is the more informative number.
- Hypothesis (1) is only partly supported. Variant d is best, but task max-similarity (c) and task means (b) are
  *worse* than plain title + description: single task sentences pull in incidental matches.
- The keyword baseline finds no keyword in 39% of EN-core statements.

**By category, family / occupation Hit@5 of minilm:d (`e7_by_category.png`):** pure 1.00/1.00 (n = 12), mixed 1.00/1.00 (10),
hobby .90/.90 (10), negation .83/.50 (6), negation twins .83/.50 (6), vague .83/.83 (6), gender pairs .86/.71 (14),
name pairs 1.00/1.00 (10), Spanish .50/.33 (12; English model). For TF-IDF(d), hobby .70/.60 and pure .83/.50.
**Trades vs non-trades statements** (all languages): minilm:d .86/.74 (n = 42) vs .90/.84 (n = 62), and mml12:d .90/.62 vs
.95/.85. Occupation-level retrieval is weaker for trades and low-preparation interests, the group the ethics review
asked about.

### M2: RIASEC agreement of the top-10 mean profile with the intended letters

| Method | EN-core mean r(p, t) [CI] | argmax = 1st intended letter | Vague (n = 6) r | Spanish (n = 12) r |
|---|---|---|---|---|
| minilm:d | .74 [.68, .79] | .84 | .24 | .41 |
| mml12:d | .75 [.69, .80] | .86 | .14 | **.79** |
| TF-IDF (d) | .45 [.34, .55] | .53 | .24 | -.25 |
| Keyword | .41 [.27, .54] | .51 | .07 | .20 |
| Random | .04 | .21 | .01 | .11 |

### M3: Rejection and the "no good match" response (`e7_rejection_hist.png`)

| Method | Held-out FRR (mean of 200 splits) | Held-out off-topic rejection | Threshold (all data) | AUC real vs off-topic |
|---|---|---|---|---|
| **minilm:d** | **3.9%** | **90.5%** | **0.262** (split SD .016) | .98 |
| minilm:a | 2.9% | 90.5% | 0.247 | .98 |
| minilm:c | 9.1% | 78.0% | 0.400 | .93 |
| mml12:d (EN only) | 5.7% | 93.9% | 0.332 | .97 |
| mml12:d (EN + ES) | 6.5% | 94.1% | 0.327 | |
| TF-IDF (d) | 2.2% | 58.3% | 0.050 | .80 |
| Keyword | 42.9% | 96.7% | 0.374 | .77 |

- At the minilm:d threshold of 0.262, the two off-topic inputs that are still accepted are "test test" and "what's the
  weather today". All gibberish inputs and the prompt-injection string are rejected.
- Share of each category that would get "no good match": pure, mixed, hobby, negation 0%; vague 17% (1 of 6); gender
  pairs 14%; nationality pairs 33%; **Spanish 67% with the English model**.
- Pure "lost" statements (vague_empty): "I have no idea… good at everything and nothing" 0.287 and "I just want a job that
  is chill and pays okay" 0.300 are **accepted** (they would get a forced list). "My parents want me to choose something
  stable" 0.147 is rejected. So top-1 similarity does not tell "lost" apart from "specific".

### M4: Negation (6 negated statements vs their positive twins)

| Method | Top-10 overlap, negated vs twin | Unrelated-pair reference | Negated letter (centred) in negated / twin lists | Negated letter < 0 |
|---|---|---|---|---|
| minilm:d | .27 | .03 | +0.90 / +1.87 | 1 of 6 |
| mml12:d | .22 | .03 | +0.68 / +2.49 | 2 of 6 |
| TF-IDF (d) | .50 | .03 | +0.85 / +1.44 | 1 of 6 |

Negation halves the negated type's weight but almost never reverses it. Worst case, minilm:d: "I never want a job where I
get my hands dirty…" shares 7 of 10 occupations with "I like jobs where I get my hands dirty" (R score +3.2 vs +3.3). Its
blind-rated top 5 included janitorial and dishwashing jobs. Hypothesis (3) is supported.

### M5: Spanish vs English (12 translation pairs; `e7_spanish.png`)

| Model : variant | EN family / occ Hit@5 | ES family / occ Hit@5 | EN-ES top-10 overlap | ES RIASEC r |
|---|---|---|---|---|
| minilm:d | 1.00 / .92 | .50 / .33 | .11 | .41 |
| mml12:a | .92 / .92 | **1.00 / .83** | .75 | .83 |
| mml12:b | 1.00 / .92 | 1.00 / .92 | .78 | .84 |
| mml12:d | 1.00 / .83 | .92 / .75 | .75 | .79 |
| TF-IDF (d) | .75 / .42 | .17 / .08 | .09 | -.25 |

The English model fails on Spanish, as expected. The multilingual model holds up: ES is within about 0-8 points of EN
on these 12 pairs, with 75% cross-lingual top-10 overlap. Hypothesis (4) is supported (n = 12, so the CIs are wide).

### M6: Counterfactual pairs (`e7_bias_pairs.png`)

Gated (pre-registered): **mean top-10 overlap over the 12 gender + name pairs = .733 for minilm:d** (bar .90; promising
needs .80). For the other cells: mml12:d .767, minilm:a .758, TF-IDF(d) .933 (TF-IDF ignores names entirely, but it
retrieves worse).

| minilm:d | Pairs | Mean (min) top-10 overlap | Mean L2 profile shift | Signed shift A - B (R / S) | Mean job-zone shift A - B | Hit@5 fam A / B | Hit@5 occ A / B |
|---|---|---|---|---|---|---|---|
| gender (girl/boy, woman/man) | 7 | .77 (.50) | .61 | -.17 / -.08 | +0.16 | .86 / .86 | .71 / .71 |
| name (Maria/Juan, Emily/Jamal, Aisha/Connor, Lucía/Carlos) | 5 | .68 (.50) | .64 | -.16 / +.24 | +0.22 | 1.00 / 1.00 | 1.00 / 1.00 |
| pronoun / gendered noun (she/he, daughter/son) | 3 | .77 (.70) | .89 | **-.58 / +.51** | +0.03 | 1.00 / 1.00 | 1.00 / 1.00 |
| nationality (Mexico/Canada, Nigeria/Sweden, Marruecos/España) | 3 | .60 (.50) | .80 | -.04 / +.40 | -0.07 | 1.00 / 1.00 | 1.00 / .67 |
| age (16 / 45, teenager / 50-year-old, student / middle-aged) | 3 | .63 (.60) | .80 | -.59 / +.31 | +0.27 | 1.00 / 1.00 | 1.00 / 1.00 |

(A = female / first name / first nationality / younger. The job-zone shift is in job-zone units, so female and younger
cues got slightly *higher*-preparation lists. The letter-composition shifts are in the JSON.)

- **Hit rates do not differ by member** (female vs male family Hit@5 .86 vs .86; young vs older 1.00 vs 1.00). The lists
  change, but they mostly stay sensible.
- **Post-hoc control (not pre-registered; minilm:d):** same-gender swaps ("girl" -> "young woman", "Maria" -> "Laura")
  give a mean overlap of .775, about the same as the cross-gender swaps (.733). Adding *any* cue to the cue-free sentence
  moves the list (overlap .68-.71). So most of the instability is **brittleness to any added words**, not a
  gender-specific effect. However, across the 10 gender + pronoun pairs, the female version had a lower R share in 8 of
  10 (exact sign test p = .11, mean R shift -0.30), which is consistent with a stereotyped direction but not significant
  at this n. The strongest single case is PR02, elderly care: "She…" vs "He…" shifts R -0.98 and S +0.87.

### M7: Fusion: free text as RIASEC evidence

| Evidence vector | EN-core r with intended letters [CI] | Top-letter accuracy | Vague r | Spanish r |
|---|---|---|---|---|
| Top-10 fusion, minilm:d | **.75** [.69, .80] | **.84** | .24 | .40 |
| Top-10 fusion, mml12:d | .75 [.69, .80] | .86 | .14 | **.79** (top-letter .92) |
| Prototype route (6 type prototypes from O*NET activities), minilm | .55 [.46, .63] | .60 | .36 | .21 |
| Prototype route, mml12 | .58 [.48, .66] | .63 | .17 | .53 |
| Chance | 0 | .17 | | |

Retrieval-then-aggregate is a much better RIASEC signal than the direct prototype route. For vague statements, though,
neither route carries much signal (r .14-.36, n = 6).

### M8: Blind rating (rater = experimenter; 30 shuffled lists, key opened only after rating)

| Source (from key) | n | Sensible | Partly | Not | Share sensible |
|---|---|---|---|---|---|
| **Best variant (minilm:d)** | 20 | 17 | 2 | 1 | **85%** |
| TF-IDF (d) | 5 | 3 | 0 | 2 | 60% |
| Random | 5 | 0 | 2 | 3 | 0% |

The three best-variant lists that weren't rated "sensible" were N06 "never get my hands dirty" ("not": cleaning and
janitorial jobs, a negation failure), NT06 "jobs where I get my hands dirty" ("partly") and G02F "woman … interested in
engineering" ("partly": machine operators but no engineers). A post-rating check showed that the male and cue-free versions
of G02 also return machine-setter/operator lists (the woman version actually had 2 engineering-technologist titles in its
top 10). So this is a retrieval failure: the word "machines" outweighs "engineering", and the catalogue's dense block of
job-zone-2 machine occupations (E3) absorbs the query. It is not a gender effect. The secondary bar from the
skill (>= 70% sensible) is **met**.

## Verdict

Against the pre-registered composite bar: **NOT VIABLE** (as specified), because criterion (4) fails.

| Criterion | Result | Bar | Pass |
|---|---|---|---|
| (1) best family Hit@5, EN-core | .947 [.88, 1.00] (minilm:d) | >= .70 | yes |
| (2) best - best TF-IDF | +21.1 points [+8.8, +33.3] | >= 10 | yes |
| (3) held-out FRR / off-topic rejection | 3.9% / 90.5% | <= 10% / >= 80% | yes |
| (4) gender + name mean top-10 overlap | **.733** | >= .90 (promising >= .80) | **no** |
| Secondary: blind rating (skill bar) | 85% sensible (17/20) | >= 70% | yes |

Interpretation, separate from the formal verdict: retrieval quality, the TF-IDF margin and rejection are clearly good
enough for an *optional extra input*. The blocking issue is counterfactual invariance. The post-hoc control suggests it
comes mostly from general sensitivity to irrelevant words, plus a non-significant hint of a stereotyped R-direction
shift. Both can be engineered against: strip demographic cues before embedding and add counterfactual tests to CI. That
would need a **new pre-registered run** (E7b) before free text can be called promising. The bar is not relaxed here.

## Caveats

- **Self-written, small test set.** 107 statements and 32 off-topic inputs, written by the same agent that designed the
  method and did the blind rating. The sensible sets reflect our expectations and the catalogue titles, and real users
  write messier, longer and more varied text. **A user study with independent counsellor ratings is needed** before any
  user-facing claim.
- Best-variant selection used the test set (8 cells), so its numbers are slightly optimistic. Variants a and d are within
  CI of each other.
- Family-level Hit is lenient (random gets .30); prefer occupation-level Hit and the blind rating.
- The rejection threshold comes from 76 real vs 27 off-topic inputs. It is model-specific (MiniLM 0.262, multilingual
  0.33) and must be recalibrated on real traffic. It does not detect "lost" users.
- Negation is not handled. Spanish is tested on 12 translations only, without regional variety or code-switching.
- The trades share of the test set (40%) is below the catalogue's job-zone 2-3 share (59%).
- O*NET texts are US-centric, and the interest profiles used in M2/M7 are ML-estimated (onet-data skill).
- Counterfactual pairs are few (7 gender, 5 name, 3 pronoun, 3 nationality, 3 age), so the shift directions are
  indicative only. The post-hoc control was designed after seeing the results.

## Implications for the product (proposals for the research-editor)

1. **Index:** use variant (d) (title + alternate titles + description + top-5 tasks) with all-MiniLM-L6-v2 for
   English. Plain title + description (a) is a close second and is cheaper. Don't use task max-similarity. For Spain, use
   paraphrase-multilingual-MiniLM-L12-v2. Its 128-token limit truncates (d), so consider variant (a) or (b) for it, both of
   which did as well on Spanish here. Both models are Apache-2.0.
2. **Free text is evidence, not a recommender.** Convert the top-10 into a RIASEC evidence vector (r .75 with intent) and
   fuse it with the questionnaire posterior at a modest weight. Show results as **families with example jobs**, in line
   with E3/E5, never as a ranked list from text alone.
3. **"No good match" response:** below the similarity threshold (MiniLM about 0.26, recalibrated on real data), reply with
   "we couldn't match that; try describing an activity you enjoy, or take the questionnaire" instead of forcing a list.
   Vague or "lost" statements pass the threshold, so detect them separately (e.g. low evidence differentiation) and send
   them to the lost-user flow.
4. **Bias mitigation is required before release:** strip names, gendered words, pronouns, ages and nationalities from the
   text before embedding (the questionnaire doesn't need them), and keep the counterfactual pairs as a regression test,
   with the >= .90 overlap bar.
5. **Negation:** detect negation cues ("don't", "hate", "never", "no", "odio") and either down-weight the free-text
   evidence or ask a follow-up ("what would you rather do?"). Don't trust negated text as positive evidence.
6. **Retrieval only:** every displayed item is an existing O*NET record with its own O*NET text. No generated claims.
   The bi-encoder runs locally, so no user text goes to third parties.
7. **Privacy and safety (from the ethics review):** free text from minors must be processed without logging or
   retention (embed in memory, discard). Free text can contain sensitive disclosures (self-harm, abuse, health), so it
   needs a signposting response (help resources) that runs before or alongside matching. Both need the privacy design
   (CLAUDE.md rule 5) before launch.
