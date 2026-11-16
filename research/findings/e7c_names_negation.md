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
