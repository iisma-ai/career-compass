# 0006 — Show an unordered set of career families, not a ranking
Date: 2026-11-15 *(backfilled)*        Status: Accepted

## Context
E5 found that even the full 48-item test reproduces only about 55% of its own top-10 under answer noise. E3 found that the
catalogue resolves into only about 100–170 distinct occupation profiles.

## Options
1. A ranked top-10 of occupations. Beyond the top few, the order is mostly noise.
2. **An unordered set of occupation families, each with 2–3 example occupations.**
3. A Holland code only. Too coarse to act on.

## Decision
Option 2. Results are "career families worth exploring", with no rank numbers and no match percentages.

## Consequences
The UI needs family names and explanations of why each family fits. E3 families (r ≥ .80 / .90) are a starting point,
not final user-facing labels.

## Evidence
`research/findings/e5_stability.md` (Implications 2), `research/findings/e3_occupation_space.md` (Implications 2).
