# 0007 — Free text is retrieval-only, optional, and gated on E7b
Date: 2026-11-15 *(backfilled)*        Status: Accepted

## Context
E7 showed strong retrieval from free text (minilm variant d: family Hit@5 .95, occupation .86) and working off-topic
rejection. However, gender/name-swap top-10 overlap was .73, below the pre-registered .90, so the verdict was **not viable**.
Negation is not handled.

## Options
1. Ship free text as a recommender. Rejected because the bias bar failed.
2. **Keep free text as an optional extra input**, converted to RIASEC evidence and fused with the questionnaire. It only
   ranks existing O\*NET records and never generates text. Nothing ships until a new pre-registered run (E7b) passes the
   invariance bar.
3. Drop free text entirely.

## Decision
Option 2. The index is all-MiniLM-L6-v2 on variant (d), with a "no good match" threshold of about 0.26 (to be recalibrated on
real traffic). Text is processed in memory only and never logged (privacy design pending).

## Consequences
E7b must test demographic-cue stripping on a held-out counterfactual set (0011). Negation needs its own fix later.

## Evidence
`research/findings/e7_free_text_matching.md`, `research/findings/e7_posthoc_counterfactual.json`.
