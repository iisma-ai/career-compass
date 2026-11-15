# 0012 — Adopt cue stripping in the free-text pipeline; free text is still not user-facing
Date: 2026-11-15        Status: Accepted

## Context
E7b passed its pre-registered bar. Held-out gated overlap went from .74 raw to .92 stripped, with no loss in retrieval
quality or rejection, and the stripper changed none of the content-trap statements. However, coverage of new phrasings is
67%, name pairs alone reach .84, and the held-out set is not independent.

## Options
1. Call free text ready for users. Rejected: negation, privacy design and an independent test are all still missing.
2. **Make `strip_demographic_cues` a mandatory step before any free-text embedding**, keep free text behind the existing
   gates (ADR 0007), and plan E7c for name coverage and an independent held-out set.
3. Wait for E7c before adopting anything. That wastes a result that costs nothing in quality.

## Decision
Option 2. The free-text design is strip → embed (all-MiniLM-L6-v2, variant d) → top-10 → RIASEC evidence. The E7 and E7b
pairs become regression tests. ADR 0007 still applies: free text stays optional and research-only until negation
handling, the privacy design and an independent evaluation exist.

## Consequences
- E7c (pre-register first): NER or broader rules for names, Spanish noun endings, cosmetic artefacts, and a held-out set
  written blind to the rules.
- Any change to `text_cues.py` must re-run E7b and the unit tests.

## Evidence
`research/findings/e7b_cue_stripping.md` (Results, Verdict, Caveats), `research/findings/e7b_cue_stripping.json`.
