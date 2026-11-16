# 0020 — v1 engine in `src/career_compass/engine.py`: balanced 4-per-scale form, GRM-EAP, gate, unordered families
Date: 2026-11-16        Status: Accepted

## Context
MODELS L1–L4 specify the v1 pipeline, but the only implementation is E4's research replay code. Building the product
engine now lets the studies (protocol draft) and the UI run on one tested code path.

While specifying the form, I found that E4's replay form isn't balanced. E4's `best_fixed_order` is a round-robin over
all 48 items. E4 ran it with the 8 flagged items removed, which leaves the first 24 items as 5 R and 3 E. ADR 0005 and
MODELS L1 say "4 per scale". E9's proxy took the first 24 of the unfiltered order, which still includes E1, a
gender-DIF item.

## Options
1. Copy E4's filtered order (5 R / 3 E). Rejected: contradicts ADR 0005 and under-measures E.
2. **Build the form as ADR 0005 states (chosen):** per scale, the 4 retained items with the highest discrimination,
   in round-robin order. Compared with E4's form, R2 is out and E7 is in.

## Decision
- **Engine API:** `ItemBank.from_e4`, `build_fixed_form`, `score` / `score_matrix_responses` (GRM, EAP with
  correlated prior, the same maths as E4), `gate`, `Catalogue.load`, `recommend` and `assess`.
- **Gender-blind (ADR 0015):** no function takes a demographic parameter. A test checks every signature.
- **Output:** about 3 families, sorted by family id (not by score, ADR 0006), each with up to 3 examples ordered by
  job zone. Family labels are placeholders (the title of the most central member) until milestone 1.4.
- **Lost users:** a "lost" status returns no families; the lost-user flow is still design only (blocker 4).
- **Research-only:** every result carries `research_only=True` while the parameters come from OpenPsychometrics data
  (blocker 2).
- **Acceptance check, set before the first run:** on 5,000 adults, the mean per-person r between the engine's
  24-item predicted profile and the full 48-item scale means must be ≥ .95. E4's replay form reached .965–.968.
- **Not implemented:**
  - the diversity cap and thin-pool broadening (MODELS L4);
  - the refine-to-30 step;
  - explanation copy (L6 returns structured fields only);
  - any UI.

## Consequences
- The E9 caveat about E1 is noted in its findings file. The size of its effect on E9's variances is unknown, probably small.
- MODELS L1 gets the exact v1 form.

## Evidence
MODELS L1–L4; ADRs 0002, 0005, 0006, 0014, 0015; `research/findings/e4_cat_simulation.json`; `tests/test_engine.py`.
