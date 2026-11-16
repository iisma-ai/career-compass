# E7b — Demographic-cue stripping before free-text matching

Pre-registered 2026-11-15, before writing `research/feasibility/e7b_cue_stripping.py` and before the held-out set exists.
Order of events, each verifiable in git (ADR 0003, ADR 0011):
1. **This commit:** pre-registration + frozen stripper `src/career_compass/text_cues.py` + unit tests. The stripper was
   developed on the **text** of E7's counterfactual pairs only (they collapse to identical strings, and E7's cue-free
   statements and off-topic inputs are untouched). No retrieval was run with the stripper.
2. **Next commit:** the held-out set `research/findings/e7b_heldout_pairs.csv`, written after the stripper is frozen.
   The stripper is not changed after this point. Any later change makes a new experiment (E7c).
3. **Then:** script, `--quick` smoke run, full run, results.

## Pre-registration

```
Question:      Does deterministic demographic-cue stripping (names, gender, age, origin, pronouns, kinship
               nouns) before embedding make free-text matching invariant to those cues on NEW phrasings,
               without hurting retrieval quality, off-topic rejection, or statements where gendered words
               are content?
Hypothesis:    E7 found gender/name top-10 overlap of .733 (bar .90). A post-hoc control found that most of the
               instability is sensitivity to *any* added words (research/findings/e7_posthoc_counterfactual.json),
               so removing the cue words should remove most of it. Stripping is expected to (1) raise held-out
               gated-pair overlap to >= .90 where the rules fire, with misses where phrasing is not covered;
               (2) leave EN-core Hit@5 within about 2 points (cue words carry no interest content);
               (3) leave rejection unchanged; and (4) leave content-trap statements unchanged, because the rules
               only target self-descriptions and introductions.
Data:          O*NET 31.0 index exactly as E7 (923 rated occupations, variant d text).
               E7 test set (107 rows) and off-topic set (32) unchanged: research/findings/e7_test_statements.csv,
               e7_offtopic_inputs.csv.
               Held-out set research/findings/e7b_heldout_pairs.csv (written after the stripper is frozen):
                 gated: 10 gender pairs (of which >= 3 pronoun or kinship pairs) + 8 name pairs = 18 pairs,
                        >= 3 in Spanish; reported, not gated: 4 age pairs + 4 origin pairs.
                 Every pair has a cue-free "content" sentence. At least half of the gated pairs use a
                 phrasing that does not appear in E7's pairs (e.g. a different introduction or cue position, or
                 a cue mid-sentence). Names and origins do not repeat E7's.
                 10 content-trap statements, where a gendered or age word is part of the interest (e.g.
                 "coach a girls' football team", "design menswear").
Method:        Fixed configuration, no reselection: sentence-transformers/all-MiniLM-L6-v2, variant (d), cosine,
               top-10, ties by catalogue order (identical to E7's best cell). Every query (statements, off-topic
               inputs, held-out rows) goes through strip_demographic_cues() before embedding. "Raw" = E7
               behaviour (no stripping), computed in the same run as the comparison. Secondary model, reported
               only: paraphrase-multilingual-MiniLM-L12-v2, variant (d).
Baselines:     Raw (unstripped) minilm:d on the same inputs. Reference: E7 published values (.947 family Hit@5,
               .860 occupation Hit@5, FRR 3.9%, off-topic rejection 90.5%, gated overlap .733).
Metrics:       M1 Counterfactual invariance: mean top-10 overlap |A & B| / 10 per pair set: held-out gated (18),
                  held-out age (4), held-out origin (4), E7 dev gated (12, development set, so expected near 1.0
                  by construction). Raw and stripped. Bootstrap 95% CI over pairs (B = 2000).
                  Coverage = share of pairs whose stripped texts are identical. Also: overlap of each stripped
                  member with its stripped content sentence.
               M2 Retrieval quality on E7 EN-core (n = 57): family Hit@5 (r>=.80) and occupation Hit@5, stripped
                  vs raw, with a paired bootstrap CI of the difference. Also vague (6) and Spanish (12), reported.
               M3 Rejection: same procedure as E7 M3 (76 real EN vs 27 off-topic EN, 200 stratified 50/50
                  splits, Youden threshold on the calibration half), on stripped inputs. Held-out FRR and
                  off-topic rejection; threshold on all data.
               M4 Content preservation: for the 10 trap statements, the share left unchanged by the stripper,
                  and the mean top-10 overlap raw vs stripped.
               M5 Cue audit: counts of cue types fired on each set; the number of E7 cue-free statements and
                  off-topic inputs changed (expected 0).
Success bar:   PROVEN if all of:
                 (1) held-out gated mean top-10 overlap (stripped, minilm:d) >= .90;
                 (2) EN-core family Hit@5 >= .92 AND occupation Hit@5 >= .83 (stripped);
                 (3) held-out FRR <= 10% AND off-topic rejection >= 80% (stripped);
                 (4) content-trap mean top-10 overlap raw vs stripped >= .90.
               PROMISING if not proven but: (1) >= .80, (2) family >= .88 AND occupation >= .78,
                 (3) FRR <= 20% AND off-topic >= 60%, (4) >= .80.
               NOT VIABLE otherwise.
               E7 dev pairs, age, origin, Spanish and the multilingual model are reported, not gated.
Seed:          42 (bootstrap and splits).
Limits known in advance:
               The same agent wrote the stripper and the held-out set, so the held-out set is not independent.
               The commit order and the phrasing rule are the only safeguards. A held-out set written by
               someone who hasn't seen the rules is recommended before any user-facing claim. Passing this bar
               shows invariance to the cue types covered, not fairness in general (ethnicity, religion,
               disability and dialect are out of scope). Negation is not addressed.
```

---

## Results

Run: `uv run python -I research/feasibility/e7b_cue_stripping.py --seed 42` (198 s on CPU), after a `--quick` smoke run.
Raw results: `research/findings/e7b_cue_stripping.json`. Chart: `e7b_heldout_overlap.png`. All of this is level E
evidence (our own experiment on a self-written test set).
The stripper is identical to the pre-registration commit `3ceb48a`, and the held-out set is identical to commit `ad5fa28`.

**Sanity check.** The raw (unstripped) arm reproduces E7 exactly: EN-core family / occupation Hit@5 .947 / .860, and
E7 dev gated-pair overlap .733. Raw rejection gives FRR 4.3% vs E7's 3.9%, because the 200 random splits draw from a
fresh RNG stream. Raw and stripped use the same splits.

### M1: Counterfactual invariance (top-10 overlap between members A and B, bootstrap 95% CI over pairs)

| Set (minilm:d) | n pairs | Raw | **Stripped** | Identical text after stripping |
|---|---|---|---|---|
| **Held-out gated (gender + name)** | 18 | .739 [.66, .82] | **.922 [.84, .99]** | 12 / 18 (67%) |
| … gender (incl. pronoun / kinship) | 10 | .840 | .990 | 7 / 10 |
| … name | 8 | .613 | **.838** [.68, 1.00] | 5 / 8 |
| … new phrasing (not in E7) | 13 | | .892 | |
| … phrasing as in E7 | 5 | | 1.000 | |
| Held-out age (reported) | 4 | .650 | .925 | 3 / 4 |
| Held-out origin (reported) | 4 | .650 | .850 | 2 / 4 |
| E7 dev gated (development set) | 12 | .733 | 1.000 | 12 / 12 |
| E7 dev age | 3 | .633 | .900 | 2 / 3 |

Multilingual model (mml12:d, reported only): held-out gated .839 raw → **.944** stripped. Name pairs .775 → .913.

When the stripper fires on both members, the texts become identical, so their overlap is 1.0 **by construction**.
The informative numbers are therefore **coverage** (67% of held-out gated pairs) and the overlap of the pairs it misses.
The six misses, with stripped overlaps:
- **Gender:** HG03 "…when I was a little girl/boy" (1.0, because the raw lists were already identical); HG04 "for a guy/girl I'm…"
  (1.0, same reason); HG10 Spanish agreement "enfermera/enfermero" (.9; kinship was neutralised, the noun ending was not).
- **Name:** HN01 "Hey! Priya/Tyler here" (.4, because the "X here" rule only fires at the very start), HN04 sign-off "- Mei/Jake" (.6), and HN06
  "Everyone calls me Rosa/Diego" (.7, because the rule has "call me" but not "calls me").

All three name misses are phrasings outside the rules, and they carry most of the remaining instability. Names are the
weak spot: .838 on its own would only be "promising".

Overlap of stripped members with their cue-free content sentence: .84 (raw .74). Where stripping leaves a neutral noun
("I'm a person and…"), the list stays close to, but not identical to, the cue-free one. This is the "any added words"
effect from E7, and it is now the same for both members.

### M2: Retrieval quality is unchanged (E7 EN-core, n = 57)

| minilm:d | Raw | Stripped | Paired difference |
|---|---|---|---|
| Family Hit@5 | .947 | **.947** | 0.0 [0, 0] |
| Occupation Hit@5 | .860 | **.860** | 0.0 [0, 0] |
| Vague (6), family / occupation | .83 / .83 | .83 / .83 | 0 |
| Spanish (12), family / occupation | .50 / .33 | .50 / .33 | 0 |

mml12:d: EN-core family .912 → .912, occupation .754 → .772, Spanish .917 / .75 unchanged.

### M3: Rejection is unchanged

| | Held-out FRR | Off-topic rejection | Threshold (all data) | AUC |
|---|---|---|---|---|
| minilm:d raw | 4.3% | 90.8% | 0.262 | .983 |
| **minilm:d stripped** | **4.8%** | **91.2%** | 0.262 | .987 |
| mml12:d stripped | 5.8% | 92.6% | 0.332 | .973 |

### M4: Content preservation
The stripper left all 10 content-trap statements unchanged ("girls' football team", "menswear", "women's shelter", "midwife…
mothers", "barbershop for men", Spanish "niñas y niños"…). The raw vs stripped overlap is 1.00.

### M5: Cue audit
- **Cue-free text is untouched:** 0 of 65 E7 cue-free statements and 0 of 32 off-topic inputs were changed.
- **Cue types fired on the held-out set:** name 12, gender/age 7, kinship 6, pronoun 6, age 6, origin 4.
- **Held-out pair rows where no cue was found:** HG03, HG04, HN01, HN04, HN06, HA03 (A), HO02, HO03.
- **Cosmetic artefacts seen in the stripped text:**
  - "And I enjoy…" (HN03) and "Hola, y me gustaría…" (HN08): connectives left behind.
  - "As a person citizen" (HA03 "senior citizen": "senior" is in the noun list).
  - "they love plants and wants" (only the first verb is re-conjugated).
  - Spanish "Soy persona de 16 años".
  
  These were seen only after the run and were **not fixed**, because the stripper is frozen. They don't affect invariance
  (both members get the same artefact), but they are on the E7c list.

## Verdict

**PROVEN against the pre-registered bar.**

| Criterion | Result | Bar | Pass |
|---|---|---|---|
| (1) held-out gated overlap (stripped) | .922 [.84, .99] | ≥ .90 | yes (point estimate) |
| (2) EN-core family / occupation Hit@5 | .947 / .860 | ≥ .92 / ≥ .83 | yes |
| (3) held-out FRR / off-topic rejection | 4.8% / 91.2% | ≤ 10% / ≥ 80% | yes |
| (4) content-trap overlap | 1.00 | ≥ .90 | yes |

The bar was set on the point estimate, and that is how it is applied. The CI's lower bound (.84) is below .90, so with
18 pairs a true value under .90 cannot be ruled out.

## Caveats
- **Not an independent test.** The same agent wrote the stripper and the held-out set. The commit order (`3ceb48a` stripper
  frozen → `ad5fa28` held-out set → run) proves the set wasn't used for tuning. It doesn't prove the set was written
  without knowledge of the rules, and 13 of 18 pairs were deliberately given new phrasings, of which 6 were missed.
  A held-out set written by people who haven't seen the rules (ideally real user text, after the privacy design) is
  still needed.
- Small n: 18 gated pairs, 4 age and 4 origin. The name subset alone (.84) would not pass.
- Invariance is guaranteed only where a rule fires. Unseen phrasings fall back to raw E7 behaviour (about .74).
- Out of scope: ethnicity, religion, disability, dialect and code-switching. Negation is still not handled (E7 M4).
- Gendered Spanish nouns and adjectives (enfermera/enfermero, colombiana) are only partly handled.

## Implications for the product (proposals for the research-editor)
1. **Pipeline:** free text → `strip_demographic_cues` → embed (minilm:d) → top-10 → RIASEC evidence. It costs nothing in
   retrieval quality or rejection.
2. **Regression test:** keep the E7 and E7b pairs as a CI check. Text-level pair tests are already in `tests/test_text_cues.py`.
   Add an embedding-level overlap ≥ .90 check when a CI runner with the model exists.
3. **E7c (next, separate pre-registration):** name coverage is the weak point. Options are a NER pass for person names
   (option 2 in ADR 0011) and a broader "X here" / "calls me" / sign-off set. Also fix the cosmetic artefacts, add Spanish
   noun-ending neutralisation, and write the held-out set with someone who hasn't seen the rules.
4. Free text still needs negation handling, the privacy design and an independent user study before it is user-facing.
