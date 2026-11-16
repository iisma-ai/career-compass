# 0017 — Adopt name rules v2; don't use rule-based negation; negated free text triggers a follow-up question
Date: 2026-11-16        Status: Accepted

## Context
E7c (`research/findings/e7c_names_negation.md`) was NOT VIABLE as pre-registered.
- **Criterion 1 passed:** name and gender invariance on a set written blind to the rules was .929, and names alone
  .906. Name traps scored 1.00. Quality and rejection were unchanged.
- **The negation criteria failed:**
  - the negated letter was pushed below zero in 4 of 12 held-out statements (5 of 6 on the development set);
  - negation traps scored .375, because idioms such as "nothing beats…" were read as rejection.

## Options
1. Drop both modules.
2. Tune the negation rules on the held-out failures. Rejected: the held-out set would become development data, and
   rules have already shown they overfit.
3. **Adopt names v2 in the research free-text pipeline. Use no negation module. When a statement contains a negation
   cue, show no free-text-based results and ask "What would you rather do?".**

## Decision
Option 3.
- `text_cues.py` v2 replaces v1 in the free-text pipeline. ADR 0012's "strip before embedding" stays in force.
- `negation.py` stays in the repo as a research artefact. It isn't called by any pipeline; it can serve as a cue
  detector for the follow-up design.
- A learned approach (NLI or a polarity classifier) becomes a new experiment (E7d). It needs its own pre-registration
  and a new held-out set written by humans.
- Free text stays research-only (ADR 0012). A human-written held-out set is still required (ROADMAP 2.4).

## Consequences
- MODELS L5, ROADMAP 2.4, RESEARCH §5 and CLAUDE.md are updated.
- Known bug: Devanagari combining marks are left behind (GN12). The fix is part of the next name experiment; nothing
  is fixed in place.
- The selection of options 1–3 was made after seeing the E7c results (post-hoc). It rests on the separate criteria
  that were pre-registered.

## Evidence
`research/findings/e7c_names_negation.md`, `e7c_names_negation.json`, `e7c_heldout.csv`; ADRs 0012, 0016.
