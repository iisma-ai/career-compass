# E7b — Demographic-cue stripping before free-text matching

Pre-registered 2026-11-15, before writing `research/feasibility/e7b_cue_stripping.py` and before the held-out set exists.
Order of events, each verifiable in git (ADR 0003, ADR 0011):
1. **This commit:** pre-registration + frozen stripper `src/carrier_helper/text_cues.py` + unit tests. The stripper was
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
