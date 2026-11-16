# 0004 — Pearson profile correlation is the default matcher
Date: 2026-11-15 *(backfilled)*        Status: Accepted

## Context
E3 compared four person↔occupation matchers on 80,085 profiles × 923 occupations.

## Options
`pearson` (O\*NET-style), `hexagon` kernel, `cosine_centered`, `euclid_z`.

## Decision
**Pearson** is the ranker. It is proven on E3's bar, the simplest to explain, and the field standard. The hexagon is used
only as an explanation device. `euclid_z` and `cosine_centered` are not used as rankers. The implementation lives in
`src/career_compass/matching.py` and must be reused.

## Consequences
- Exposure is concentrated (Gini .77), and A-top users have a tiny pool. Diversity and re-ranking are open problems.
- Match r is **not** accuracy and is never shown as such.

## Evidence
`research/findings/e3_occupation_space.md` (Verdict, Implications 1–3).
