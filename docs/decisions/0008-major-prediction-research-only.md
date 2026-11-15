# 0008 — Field-of-study prediction (E6) stays research-only
Date: 2026-11-15 *(backfilled)*        Status: Accepted

## Context
E6's multinomial LR on item answers predicts the major family at top-3 .565 (vs majority .40), which passes its bar.
However, it over-predicts Psychology about twofold, small fields are nearly invisible, it amplifies gender gaps (STEM-core ×1.11,
Psychology ×1.65), and the items predict gender (AUC .84).

## Options
1. Show field-of-study suggestions in v1.
2. **Keep it research-only for now** and re-scope it for v3.

## Decision
Option 2: no user-facing field-of-study suggestions in v1. For v3, re-scope it as "people with similar interests often
studied…", shown next to career families, after a de-amplification step and a re-audit. Demographics are never used as inputs.

## Evidence
`research/findings/e6_major_prediction.md` (Verdict, Implications).
