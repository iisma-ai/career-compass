---
name: riasec-scoring
description: Scoring, cleaning and comparing RIASEC (Holland) interest profiles, both people's answers (OpenPsychometrics 48-item test, O*NET Interest Profiler) and occupation profiles. Use when computing scale scores, Holland codes, data-quality filters, hexagon metrics, or person-occupation match scores.
---

# RIASEC scoring

## Person data: OpenPsychometrics RIASEC dataset
- Source: openpsychometrics.org/_rawdata/ (`RIASEC_data12Dec2018.zip`), local copy in
  `data/raw/openpsych_riasec_2018/`. `data.csv` is **tab-separated** despite the extension
  (145,828 rows × 93 columns, plus an empty trailing column). Facts verified 2026-11-14.
- **License: none stated** ("dumped for public edification", research consent). Use it for research
  and model training only. Never redistribute person-level rows.
- Items `R1`–`C8` are rated 1 = Dislike … 5 = Enjoy. **`0` = missing** (undocumented; 21,435 cells).
- `TIPI1`–`TIPI10` are rated 1–7 (0 = missing). `VCL1`–`VCL16` are checkboxes; **fake words are VCL6, VCL9 and VCL12**.
- Demographics: `education, urban, gender, engnat, age, hand, religion, orientation, race,
  voted, married, familysize`. Technical fields: `uniqueNetworkLocation` (2 = shared network),
  `country`, `source`, and elapse times (huge outliers).
- **`major` exists** as free text, filled for 64% of raw rows and 70% of cleaned rows. It is messy (psychology
  13.9k, business 3.8k, english 3.2k, plus junk like "n/a"/"no" and near-duplicates), so it needs
  normalisation into major families before E6.
- Sample bias: raw rows have median age 21, 65% female, 55% US. **The cleaned sample** has median age 23, 67.3% female,
  49.2% US, 63% native English; Spain is not in the top 15. Disclose this in every result.
- The shared-network filter removes far more minors (46% of dropped rows vs 17% of kept rows).

## Verified psychometric facts (E1/E2, `research/findings/e1_*`, `e2_*`)
- α per scale .83 (E) – .90 (C); stable (.81–.91) in every gender × age cell.
- Hexagon order **holds** (RTOR CI .97), including within gender and age groups. Loadings are
  invariant (metric), **intercepts are not (scalar fails)**, so never compare raw score levels
  across groups and never use gender-specific norms.
- Floor effect: 12.1% answer "Dislike" to all 8 R items (R3 is at 61% "1").
- Weak or biased items: R1, A7, S4 (weak); E4, R3, I8, R4, E1 (gender DIF); S1 (age DIF).
- Ties for top type: 9.2% of people, so Holland-code displays must handle ties.
- Angle-based Prediger projection = vendor formulas up to scale (×½) and sign, so they're interchangeable.
- factor_analyzer 0.5.x crashes with scikit-learn 1.9 (`force_all_finite`). Use the in-process
  shim from `research/feasibility/e1_data_audit.py` until the environment is pinned.

**Ready-made tables** (built by `src/carrier_helper/data/build_riasec_people.py`):
- `data/processed/riasec_people.parquet`: 80,085 rows (all filters, including the shared-network drop);
  13,882 minors flagged in `minor_13_17`.
- `data/processed/riasec_people_incl_shared_network.parquet`: 115,974 rows with a `shared_network`
  flag. Use it as a robustness check, because the shared-network filter removes 31% of rows (mix of
  retakes and school networks).

## Scale scores
- Raw scale score = mean of the 8 items per type (treat 0/blank as missing; require ≥ 6 of 8 answered).
- Standardise against the cleaned population (z-scores) when comparing people.
- Holland code = top 3 types by score. Report ties explicitly; don't break them silently.
- **Ipsative vs normative:** for matching, centre each person's profile on their own mean so the
  *shape* drives the match. Keep the overall level (elevation) as a separate feature, since low
  elevation everywhere is a signal of being "lost" or undecided.

## Data-quality filters (apply before any analysis; log how many rows each removes)
Counts are from the 2026-11-14 build, applied in order.
1. Claimed any fake word (VCL6, VCL9, VCL12) → drop (−29,285).
2. Straight-lining: all 48 answered with the same value → drop (−245).
3. ≥ 5 of 48 items missing (> 10%) → drop (−256).
4. Age < 13 or > 90 → drop (−52). Keep 13–17 flagged (minors).
5. Exact duplicate rows → drop (−0).
6. `uniqueNetworkLocation` = 2 (shared network) → drop (−35,894). This is aggressive, so always
   re-check key results on the table that includes these rows.
7. Any scale with < 6 of 8 items answered → drop (−11).

## Hexagon and profile indices
- Order: R-I-A-S-E-C (circular). Angle of type k = k · 60°.
- **Differentiation** = max score − min score (low = flat, undecided profile).
- **Consistency** = hexagon distance between the top two types (adjacent = 1, alternate = 2, opposite = 3).
- **Prediger coordinates** (Data/Ideas, People/Things): use the angle-based projection
  x = Σ score_k · cos(θ_k), y = Σ score_k · sin(θ_k) on the centred profile. Prediger (1982)
  published fixed-weight formulas too. If you use them, look up and cite the exact weights
  `[UNVERIFIED until sourced]`, and never mix variants in one analysis.

## Person ↔ occupation match metrics
| Metric | Notes |
|---|---|
| Pearson correlation of the 6-vectors | What O*NET My Next Move uses for matching (verify); shape-only |
| Cosine on mean-centred vectors | ≈ Pearson; easy to vectorise |
| Euclidean on z-scored vectors | Sensitive to elevation, so use with care |
| Hexagon-aware (circular) distance | Uses the hexagon structure; good for explanations |

**Decided by E3/E5:** the default is **Pearson** (median top-1 r .93, most stable), implemented in
`src/carrier_helper/matching.py`. Use the hexagon kernel for explanations only. `euclid_z` is not viable,
since it pushes flat and low-elevation people to R / job-zone-2 jobs. Self-centred cosine is identical to Pearson.
Match r is **not** a confidence measure (flat profiles still get r ≈ .93), so use profile differentiation
instead: < 1.0 → lost-user flow, < 1.5 → broad families only.
Even the full test gives only about 55% top-10 stability, so present **families** (r ≥ .80, 101 families,
`research/findings/e3_families.csv`) with example jobs, not exact occupation ranks.
People data (1–5 Likert) and O*NET data (OI 1–7) are on **different scales**: compare shapes
(correlation or centred cosine), never raw values.
