---
name: irt-cat-simulation
description: Recipe for calibrating RIASEC items with Item Response Theory (graded response model) and simulating a computerized adaptive test (CAT) to find how few questions are needed. Use for experiment E4, for designing the adaptive questionnaire, or whenever item selection, theta estimation or stopping rules come up.
---

# IRT calibration and CAT simulation

Goal: answer **"how many questions do we really need?"** with real data, and design the
adaptive engine for the product.

## 1. Calibrate
- Data: cleaned OpenPsychometrics 48 items (see `riasec-scoring`). Split respondents into
  **calibration (70%)** and **simulation (30%)** sets. Never simulate on calibration people.
- Model: **graded response model (GRM)**, one per RIASEC scale (6 unidimensional models). That's
  simpler and matches the published CAT studies. Optionally try a multidimensional IRT later
  (6 correlated dimensions), which can borrow information across scales.
- Tools: Python `girth` (`grm_mml`), or R `mirt` called via `Rscript` if girth is insufficient.
  Record versions.
- Check: item discrimination (a) and thresholds (b); flag items with low a (< 0.65). Check
  unidimensionality per scale (E2 results) and local dependence if feasible.

## 2. Simulate the adaptive test (per simulated respondent)
```
prior θ ~ N(0, I)  (or the population correlation matrix across the 6 scales)
loop:
    pick next item  = argmax information at current θ estimate
                      (Fisher info; alternative: expected posterior-entropy reduction,
                       or expected change in the top-k occupation ranking)
    "answer"        = respondent's real recorded answer to that item
    update θ        = EAP (quadrature) posterior mean + SE
    stop if         SE < threshold (try .30 / .40 / .50) OR ranking stable OR max items
```
Replay the person's **real answers**, which is better than synthetic responses. Then also run a
synthetic-response check from the calibrated model.

## 3. What to measure
- Items used (mean, distribution) for each stopping rule.
- Correlation of CAT θ with full 48-item scale scores, per scale and overall.
- **Top-10 O*NET occupation overlap** between the CAT profile and the full-test profile (this
  is what users feel), plus Kendall τ / NDCG@10.
- Baselines: (a) fixed random k items, (b) fixed best-k items by discrimination, (c) O*NET
  Mini-IP-like fixed short form. The CAT must beat (b) to justify its complexity.

## 4. Plots (`research/findings/e4_*.png`)
1. Number of items (x) vs. mean correlation with the full test (y), one line per method.
2. Number of items vs. top-10 overlap.
3. Histogram of items used under each stopping rule.

## 5. Literature anchors (cite in the findings)
Full detail: `research/notes/02-adaptive-testing-for-interests.md`.
- O*NET forms: parent 180 items, Short Form 60, Mini-IP 30 (5 per scale, Spanish version exists).
  Whether IRT drove item selection is `[UNVERIFIED]`; one secondary source says multidimensional
  scaling plus judges. Mini-IP.pdf / IP_Manual.pdf could not be machine-read, so a human should read them.
- Simsek & Tavsancil (2022): EAP + SE < .50, about 4 items per area (C): https://dx.doi.org/10.21031/epod.1148313
- Alkan & Deniz (2023): GPCM, SE .40, about 59 items on average. Simulated r with the paper form .91–.97,
  but the **live CAT only reached .73–.91** (C). Expect a simulation-to-live drop.
- PROMIS-style SE < .30 with 4–12 items per domain is the best-documented template. Use an SE rule plus an item cap.
- Chu et al. (2022): major inventories correlate highly but often disagree on high-point codes,
  so agreement with the full form is capped by retest and inter-form reliability.
- Literature-based starting design for E4: multidimensional GRM, EAP with a multivariate-normal
  prior (empirical RIASEC correlations), 6–12 content-balanced starter items, D-optimal or
  posterior-variance selection aimed at the top-k ranking. Stop when SD < .35–.45 on the top
  3 dimensions and the top-10 list is stable over 3 items, cap about 40. Test this, don't assume it.

## Inputs from E2 (`research/findings/e2_structure.json`)
- Use six per-scale GRMs with a **correlated 6-D prior** from the E2 latent correlations (largest:
  E–C .58, R–C .50, S–E .42; most others < .20). Use full MIRT only if it shows a clear gain.
- Parallel analysis found an extra factor splitting Investigative (medical/lab vs nature/animal),
  so check local dependence within I.
- Flag R1, A7 and S4 (weak) and E4, R3, I8, R4, E1 (gender DIF). Run E4 with and without them.
- The R floor (12% all-"Dislike") makes R θ poorly estimated at the low end, so expect larger SE there.

## E4 outcome (`research/findings/e4_cat_simulation.md`)
- With 8 items per scale, **adaptivity does not beat a good fixed form** (best margin +.005 r).
  v1 uses a **fixed 24-item round-robin form** (optional refine to 30, cap 40), behind a pluggable
  selector so CAT can be switched on once the bank has 15–20+ items per scale.
- 12 items give r ≥ .90 for scale scores. 20 items recover about 90% of the full test's top-10 agreement
  with true θ, and 30 items about 97–98%.
- Calibration: girth underestimates a by about 3–5%. Refine with an exact ML/EM step from girth's start.
- SE thresholds are unreachable with 8-item scales (no one reaches SE < .30 on all six), so don't use SE stopping.
- Comparing variable-length rules against the full test inflates results (part-whole effect: overlap jumps to
  1.0 at 48 items). Judge rules against synthetic true θ or matched length.
- Lost-user trigger: predicted differentiation < 1.0 (r .41 with stability), not posterior SE (r .11).

## Product notes
- The "lost user" signal: high posterior SE or a flat θ profile after N items means switching to
  broader / scenario items and showing a wider, more diverse result set.
- Keep the engine deterministic given the answers (reproducible results, easy to debug).
