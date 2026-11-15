# 0011 — E7b: rule-based demographic-cue stripping, frozen before the held-out test
Date: 2026-11-15        Status: Accepted

## Context
E7 failed its counterfactual bar (gender/name top-10 overlap .733 < .90). The post-hoc control suggests the cause is
mostly sensitivity to any added words, not a learned gender association. The questionnaire never needs a user's name,
gender, age or origin, so they can be removed from free text before matching.

## Options
1. **Rule-based stripper** (regex lexicon: introductions, self-descriptions, pronouns, kinship nouns). It is deterministic,
   auditable, offline and fast. It misses phrasings it doesn't cover, and it can damage content where gendered words matter.
2. NER model (e.g. spaCy) for names and places. It covers names better, but it adds a model download and dependency, is
   non-deterministic across versions, and still needs rules for gender and age words.
3. Counterfactual data augmentation or debiasing the embedding. Much heavier, and it doesn't stop the cue from shifting
   the list via "any added words".
4. An LLM rewrite to neutral text. It would send user text to a third party, or need a local LLM, and it's hard to audit.
   Rejected for privacy (minors).

## Decision
Option 1, implemented in `src/carrier_helper/text_cues.py`. Gendered self-descriptions are mapped to a neutral noun
("person" / "persona") instead of being deleted, so both members of a pair become identical without fragile grammar
surgery. Name, age and origin introductions are deleted. Third-person pronouns become they/their/them. The stripper
was developed on the **text** of E7's pairs only and **frozen in the pre-registration commit**. The held-out set is
written afterwards (a separate commit), and the stripper is not tuned on it. "Student" is deliberately not treated as an
age cue, because it is a role.

## Consequences
- If E7b passes, the product pipeline is strip → embed → retrieve, and the counterfactual pairs become a regression
  test (≥ .90 overlap).
- Coverage is limited to the listed cue types and to English plus basic Spanish. Spanish adjective agreement isn't handled.
- An independent held-out set (written without seeing the rules) is still needed before any user-facing claim.
- If E7b fails, the next step is option 2 (NER) as E7c, with a new pre-registration.

## Evidence
`research/findings/e7_free_text_matching.md` (Verdict, Implications 4), `research/findings/e7_posthoc_counterfactual.json`,
`research/findings/e7b_cue_stripping.md` (pre-registration), `tests/test_text_cues.py`.
