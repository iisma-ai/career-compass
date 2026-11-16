# 0016 — E7c: rule-based name rules v2 and clause-level negation, with a held-out set written blind to the rules
Date: 2026-11-16        Status: Accepted

## Context
E7b passed its bar, but names reached only .838 overlap. Its rules covered only capitalised Latin names in a few
introductions, and its test set was written by the rules' author (ADR 0012). E7 found negation unhandled: the negated
letter fell below zero in only 1 of 6 rows (E7 M4). ROADMAP 2.4 needs both fixed, tested on an independent held-out set.

## Options
1. **Names:**
   - (a) A statistical NER model, such as spaCy. Rejected for now: it adds a dependency and a model download, it's weak
     on lower-case and short informal text, and it's less auditable.
   - (b) **Broader deterministic rules (chosen):** any case and any script after explicit introductions, greetings,
     sign-offs and relation nouns; removal of non-Latin-script tokens; replacement of later mentions.
2. **Negation:**
   - (a) A cross-encoder or NLI model. Rejected: heavier, and it doesn't address the bi-encoder's ranking directly.
   - (b) **A clause split (chosen):** remove rejected clauses from the query, with an optional penalty α. Uncertainty
     phrases ("not sure", "don't know") are not treated as rejection, because they are a lost-user signal.
3. **Independence of the held-out set:**
   - (a) A human writer: preferred, but not available in this session.
   - (b) **A separate agent (chosen)** given only the format spec and told not to open the rules. This is disclosed
     as weaker than (a).

## Decision
Options 1b, 2b and 3b.
- α is chosen on E7 data only, by a rule written before the tuning ran. Result: α = 0.
- Code, pre-registration and tuning are frozen in one commit, before the held-out set exists.

## Consequences
- Free text stays research-only whatever E7c shows (ADR 0012). A human-written held-out set is still needed before
  any user-facing claim (ROADMAP 2.4).
- Statements that only reject things get a follow-up question instead of results (MODELS L5).

## Evidence
`research/findings/e7c_names_negation.md` (pre-registration), `e7c_dev_tuning.json`, E7 M4, E7b; ADRs 0003, 0011, 0012.
