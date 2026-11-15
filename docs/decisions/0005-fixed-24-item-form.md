# 0005 — v1 uses a fixed 24-item form, not an adaptive test
Date: 2026-11-15 *(backfilled)*        Status: Accepted

## Context
E4 simulated CAT against fixed forms using a GRM calibration of the 48-item bank.

## Options
1. Full CAT (max information or variance reduction).
2. **A fixed content-balanced form ordered by discrimination**, behind a CAT-compatible interface.
3. The full 48 items.

## Decision
Option 2. The default is 24 items (4 per scale), with an optional "refine" step to 30 and no SE-based stopping. CAT gave no
gain over the best fixed order with this bank. The pre-registered bar (70% top-10 overlap within 20 items) is unreachable
even for the full test, whose ceiling is about 55% (E5).

## Consequences
- Revisit CAT when the item bank grows (new I/E items, DIF-balanced items from E2).
- The item order is derived from OpenPsychometrics data, so it can't ship without permission (0002).
- The DIF on the final item set must be re-audited before release.

## Evidence
`research/findings/e4_cat_simulation.md` (Verdict, v1 engine table), `research/findings/e5_stability.md`.
