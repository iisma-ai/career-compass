# E7c — Broader name coverage and negation handling for free text

Pre-registered 2026-11-16, before the held-out set exists and before `research/feasibility/e7c_names_negation.py` is
written. Order of events, each verifiable in git (ADR 0003, ADR 0016):
1. **This commit:** this pre-registration, plus the frozen code:
   - `src/career_compass/text_cues.py` v2 (names);
   - `src/career_compass/negation.py` (negation split and adjusted scores);
   - `research/feasibility/e7c_common.py` (pipeline);
   - the development tuning `e7c_dev_tuning.py` and its output `e7c_dev_tuning.json`;
   - unit tests (52 pass).
2. **Next commit:** the held-out set `research/findings/e7c_heldout.csv`. It is written by a separate agent that is told
   not to open the rules, the code, the E7/E7b findings or the logs. It gets only the format spec in the appendix below.
   The code is not changed after this point.
3. **Then:** the script, a `--quick` smoke run, the full run, and the results.

## Development so far (disclosed)
- **Names v2** was developed on the text of E7's pairs, E7b's held-out pairs (which I have seen, so they are now
  development data) and my own probe sentences. On E7b's gated pairs, identical-after-strip went from 12/18 (v1) to
  14/18 (v2). No retrieval was run for names.
- **Cue-free text is unchanged:**
  - E7: 107 statements and 32 off-topic inputs. The only differences from v1 are the greeting in E7's two "Hi, I'm …"
    rows ("Hi, I want…" → "I want…").
  - E7b: 88 held-out rows. Six rows differ from v1, all in pairs v1 missed (sign-offs, "Everyone calls me …",
    "Hola, soy …").
- **Negation** was developed on E7's 6 negation rows, E7's 83 non-negation English rows (0 false triggers) and my own
  probe sentences.
- **α tuning:** α was tuned on E7 only (`e7c_dev_tuning.json`). The rule was written in the script docstring before it
  ran: take the smallest α in {0, .25, .5, .75, 1, 1.5} with negated letter < 0 in ≥ 5 of 6, EN-core family
  Hit@5 ≥ .92 and occupation Hit@5 ≥ .83. Results:

  | α | negated letter < 0 (of 6) | EN-core family Hit@5 | EN-core occupation Hit@5 |
  |---|---|---|---|
  | 0 | 5 | .947 | .877 |
  | .25 | 5 | .965 | .877 |
  | .5 | 6 | .965 | .877 |
  | .75 | 6 | .965 | .860 |
  | 1 | 6 | .930 | .842 |
  | 1.5 | 4 | .930 | .842 |

  **Frozen: α = 0**, by the rule: the rejected clause is dropped, with no penalty. α = 0.5 is reported as a secondary
  result and is not gated. Raw E7 behaviour on the same rows was 1 of 6 (E7 M4).

## Pre-registration

```
Question:      (a) Do broader, rule-based name rules (any case, any script, greetings, sign-offs, relation nouns,
               later mentions) make free-text matching invariant to names on phrasings written by someone who has
               not seen the rules? (b) Does splitting rejected clauses out of the query make negated interests
               stop pulling matching towards the rejected type, without hurting retrieval elsewhere?
Hypothesis:    (a) Held-out name-pair overlap >= .90 where the writer uses an introduction, greeting or sign-off;
               misses for bare third-person names. (b) The negated letter's centred share in the top-10 profile
               falls below zero in most mixed statements; non-negated statements are unaffected.
Data:          O*NET 31.0 index exactly as E7 (923 rated occupations, variant d text). E7 test set (107) and
               off-topic set (32), unchanged. Held-out set research/findings/e7c_heldout.csv (spec in the appendix),
               written blind to the rules by a separate agent:
                 gated_name 16 pairs (+ content rows), gated_gender 8 pairs, neg_mixed 12, neg_only 4,
                 neg_trap 8, name_trap 6.
Method:        Fixed, no reselection: all-MiniLM-L6-v2, variant (d), cosine, top-10, ties by catalogue order.
               Full pipeline = strip_demographic_cues (v2) -> split_negation -> embed the positive part and each
               rejected part -> score = sim(positive) - alpha * max sim(rejected), alpha = 0 (frozen).
               Statements with only rejected content are flagged needs_followup (the product asks a question).
               Raw = E7 behaviour (no stripping, no negation handling), computed in the same run. E7b pipeline
               (v1 stripper from commit 3ceb48a, no negation) is NOT re-run; its published numbers are the reference.
Metrics:       N1 Name/gender invariance on held-out: mean top-10 overlap A vs B, gated (24 pairs), name (16),
                  gender (8); raw vs full; bootstrap 95% CI (B = 2000). Coverage = identical after strip. By writer
                  tag: lower-case, non-Latin, Spanish, sign-off, third-person.
               N2 Negation on neg_mixed (12): share with the negated letter(s)' mean centred score in the top-10
                  profile < 0; raw vs full. Same on E7's 6 negation rows (development, reported and gated as a
                  floor). Intended top letter in the top-10 profile's top letter ("riasec_in"), raw vs full.
               N3 Retrieval quality on E7 EN-core (n = 57): family Hit@5 (r >= .80) and occupation Hit@5, full vs raw.
               N4 Rejection, same procedure as E7 M3 (76 real EN vs 27 off-topic EN, 200 stratified 50/50 splits,
                  Youden threshold) on the top-1 similarity of the positive part (full pipeline).
               N5 Traps: neg_trap (8) and name_trap (6): mean top-10 overlap full vs raw; share left unchanged by
                  both rule modules.
               N6 Reported only: neg_only followup rate (expected 4/4); alpha = 0.5 results for N2/N3;
                  cue-type audit; changes to E7 cue-free statements and off-topic inputs.
Success bar:   PROVEN if all of:
                 (1) held-out gated overlap (full) >= .90 AND name subset >= .90;
                 (2) neg_mixed negated letter < 0 in >= .83 of statements (10 of 12) AND E7 dev >= 5 of 6;
                 (3) EN-core family Hit@5 >= .92 AND occupation Hit@5 >= .83 (full);
                 (4) held-out FRR <= 10% AND off-topic rejection >= 80% (full);
                 (5) trap mean top-10 overlap full vs raw >= .90 (neg_trap and name_trap pooled, 14).
               PROMISING if not proven but: (1) >= .80 and names >= .80, (2) >= .67 and dev >= 4 of 6,
                 (3) family >= .88 and occupation >= .78, (4) FRR <= 20% and off-topic >= 60%, (5) >= .80.
               NOT VIABLE otherwise.
Seed:          42.
Limits known in advance:
               The held-out writer is a language model given only the format spec, not a human. That is
               independent of the rules but not of the model family that wrote them, so it is weaker than the
               human-written set ROADMAP 2.4 asks for. n is small (24 pairs, 12 mixed negations), so CIs are wide.
               English-first; Spanish is basic. Passing shows invariance to names and gender words of the kinds
               tested, not fairness in general. Free text stays research-only whatever the result (ADR 0012).
```

## Appendix: held-out set specification (given to the writer)

The writer gets this text only.

> Write `research/findings/e7c_heldout.csv`, UTF-8, columns:
> `id,set,pair_id,member,language,text,intended_riasec,negated_letters,tags`.
> These are short statements (1–3 sentences) that a 14–30-year-old might type into a career website when asked
> "Tell us what you enjoy or what you'd like to do". Make them sound natural, varied in style (casual, typos are OK,
> some formal), and don't reuse phrasings across rows. RIASEC letters: R realistic/hands-on, I investigative/science,
> A artistic, S social/helping, E enterprising/business, C conventional/organising.
> - `gated_name`: 16 pairs. Members `a` and `b` are identical except for the person's name, plus one `content` row: the
>   same statement with the name and any introduction removed. Use names from many cultures. In at least 4 pairs,
>   write names in lower case. In at least 4, write names in a non-Latin script (e.g. Chinese, Arabic, Cyrillic,
>   Devanagari, Korean). At least 3 pairs in Spanish (`language` = `es`). Vary where and how the name appears: a
>   self-introduction at the start, mid-sentence, a sign-off at the end, a nickname, and talking about a friend or
>   relative by name. Tag each row with any of: `lower`, `nonlatin`, `signoff`, `third_person`, `intro`, `greeting`.
> - `gated_gender`: 8 pairs (`a`/`b`) identical except for gender words: self-descriptions, or pronouns and nouns for
>   the person the statement is about. One `content` row each. At least 2 in Spanish.
> - `neg_mixed`: 12 statements, each rejecting one kind of work and stating a preference for another. Fill
>   `intended_riasec` (1–2 letters for what they want) and `negated_letters` (1–2 letters for what they reject; must not
>   overlap). Vary the ways people say they don't want something. 2 in Spanish.
> - `neg_only`: 4 statements that only say what the person does not want. Fill `negated_letters`.
> - `neg_trap`: 8 statements that contain negative-sounding words but express a positive interest. Fill
>   `intended_riasec`.
> - `name_trap`: 6 statements where a capitalised proper noun is part of the interest itself (a brand, an
>   organisation, a place, a famous person). Fill `intended_riasec`.
> Use ids like `GN01A`, `GN01B`, `GN01C` (content), `GG01A`, `NM01`, `NO01`, `NT01`, `PT01`. Leave unused cells empty.

---

## Results

Run: `uv run python -I research/feasibility/e7c_names_negation.py --seed 42` (75 s on CPU), after a `--quick` smoke run
(same verdict). Full output is in `e7c_names_negation.json`; the chart is `e7c_heldout.png`. Held-out set:
`e7c_heldout.csv` (102 rows, commit aef76dc). No code changed after the freeze (commit afb7535).

### N1: name and gender invariance (held-out, written blind to the rules)
| Set | Raw top-10 overlap [95% CI] | E7c pipeline [95% CI] | Identical after strip | Overlap with content row |
|---|---|---|---|---|
| Gated (24 pairs) | .808 [.74, .86] | **.929** [.86, .98] | 71% | .867 |
| Names (16) | .775 [.69, .86] | **.906** [.83, .98] | 69% | .884 |
| Gender (8) | .875 [.81, .93] | .975 [.93, 1.00] | 75% | .831 |

Names by writer tag (E7c pipeline, n per tag 3–7):
| Tag | Overlap |
|---|---|
| Sign-off | 1.00 |
| Spanish | 1.00 |
| Introduction | .97 |
| Greeting | .96 |
| Non-Latin | .90 |
| Lower-case | .88 |
| Third person | .80 |

Pairs below 1.0:
- **GN14 (.5):** "Everyone *at school* calls me Mo". The rule only covers "everyone calls me".
- **GN12 (.6):** a Devanagari name leaves combining vowel marks behind (they aren't letters to `\w`). This is a bug.
- **GN15 (.6):** a lower-case relative's name ("my little sibling diego"). The relation rule needs a capital letter.
- **GN10 (.9):** "I, Olumide Adeyemi, am…" has no rule.
- **GN11 (.9):** "its sofia here" with no apostrophe and not at the start.
- **GG04 (.8):** Spanish adjective agreement ("creativa/creativo"), a known gap.

### N2: negation
| Set | Negated letter < 0, raw | E7c (α = 0) | α = 0.5 (reported only) | Intended letter on top, raw → E7c |
|---|---|---|---|---|
| Held-out mixed (12) | 5 | **4** | 6 | .33 → .67 |
| E7 development (6) | 1 | 5 | 6 | .67 → 1.00 |

The rules overfit the development data: 5 of 6 on E7, 4 of 12 on the blind set. Failure modes on the held-out set
(`split_audit_heldout_mixed`):
- **Over-extended inherited polarity:** a list after a negated clause ("…in an office. Painting, photography,
  film…", "lo mío es ordenar archivos…") was treated as rejected. In NM04, NM09 and NM11 the user's actual preference
  ended up in the rejected part.
- **Over-wide connector scope:** "Rather than designing or drawing…, I'd like to manage a team" sent the whole
  sentence to the rejected part (NM07).
- **Missing cues:**
  - "Anything but sales": `but` splits the clause before the cue is seen (NM02).
  - Not covered: "sounds boring" (NM12), "not keen", "…are out", "done with".
  - The negated content was misidentified in "not really a people person, so teaching… are out" (NM03).
- **Neg-only (reported):** follow-up was triggered for 1 of 4 statements (expected 4 of 4).

### N3–N5
- **N3 quality (E7 EN-core, n = 57):**
  - family Hit@5 .947, raw .947 (difference 0 [−.05, .05]);
  - occupation Hit@5 .877, raw .860 (+.018 [0, .05]).
- **N4 rejection:**
  - E7c: held-out FRR 4.2%, off-topic rejection 91.9%, AUC .988;
  - raw: 4.3%, 90.8%, AUC .983.
- **N5 traps (14):** mean top-10 overlap with raw .643. Name traps 1.00 (6 of 6 unchanged): brands, places and famous
  people were kept. Negation traps .375: "Nothing beats…", "No better feeling than…", "I never miss a chance…",
  "No joke…", "Can't imagine a life without…" and "No hay nada que me guste más…" were all read as rejection, and in
  5 of 8 statements the positive part was emptied.
- **N6:** the E7 cue-free rows are unchanged by stripping (0 of 59). Negation fired on 2 E7 Spanish rows, ES09 and ES10.
  The off-topic inputs are unchanged.

## Verdict: NOT VIABLE (as pre-registered)
| Criterion | Value | Bar (proven) | Met |
|---|---|---|---|
| (1) Invariance: gated / names | .929 / .906 | ≥ .90 / ≥ .90 | yes |
| (2) Negation: held-out / dev | 4 of 12 (.33) / 5 of 6 | ≥ .83 / ≥ 5 | **no** (not even PROMISING, which needs ≥ .67) |
| (3) Quality: family / occupation | .947 / .877 | ≥ .92 / ≥ .83 | yes |
| (4) Rejection: FRR / off-topic | 4.2% / 91.9% | ≤ 10% / ≥ 80% | yes |
| (5) Traps | .643 | ≥ .90 | **no** (PROMISING needs ≥ .80) |

The failures (2) and (5) come entirely from the negation module. The name-trap half of (5) scored 1.00.

**Interpretation** (ours; the separate criteria were pre-registered, but splitting the verdict is a post-hoc reading):
- **Names v2 works on text written blind to the rules.** Criterion 1 passes, with no quality, rejection or name-trap
  cost. This is the first evidence for name invariance from a set the rule author didn't write. The CI is still wide
  (.83–.98), and the writer was a model, not a human.
- **Rule-based clause negation doesn't generalise.** It helped the positive part surface (intended letter on top .33 →
  .67) but broke on idioms and scope. Keyword rules can't separate "nothing beats X" from "nothing to do with X".
  A next attempt needs a learned model (e.g. NLI or a fine-tuned polarity classifier), or a product design that
  doesn't rely on free-text negation: ask "What would you rather do?" whenever any negation cue appears.

## Caveats
- The blind writer is a language model, not a human, and n is small: 24 pairs, 12 negations, 14 traps.
- The tag subsets have 3–7 pairs each.
- α = 0.5 did better on negation (6 of 12) but was not the frozen value. Choosing it now would be post-hoc selection,
  so it doesn't count.
- Known bug, found by this run: Devanagari combining marks are left behind (GN12). It is not fixed here; any fix is a
  new experiment.
