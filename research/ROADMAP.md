# Carrier_helper — Roadmap (v0 → v3)

Assembled 2026-11-16. Phases follow CLAUDE.md:
- v1 covers careers only.
- Universities and degrees come in v3.

Every success criterion below is a **proposed bar**. Each one has to be pre-registered in its own commit before the
experiment or study that tests it (ADR 0003). The "today" numbers come from `research/findings/` (level E). Targets are
our choices, not evidence.

## Overview
| Phase | Goal | Exit gate |
|---|---|---|
| **v0** Research and feasibility | Evidence-backed dossier and blueprint | Dossier complete and cross-checked; E1–E7b reported (almost done) |
| **v1** Careers MVP (closed pilot) | 24-item questionnaire → career families with explanations, in English, with no data stored | All release blockers cleared; pilot criteria met |
| **v2** Own data, wider reach | Own licensed item bank and calibration, Spanish, EU catalogue, optional free text | Calibration and invariance on our own sample; Spanish parity |
| **v3** Study paths | "People with similar interests studied…" alongside careers | Fairness audit passes after de-amplification |

---

## v0 — Research and feasibility (current)
| Milestone | Status |
|---|---|
| Literature notes 01–06 | Done |
| E1–E7 feasibility experiments, plus E7b | Done ([RESEARCH.md §5](RESEARCH.md)) |
| DATA_SOURCES, RESEARCH, MODELS, ROADMAP | Done, as of 2026-11-16 |
| Ethics review of the dossier | To do (ethics-reviewer, read-only) |
| Primary-source checks of the `[UNVERIFIED]` items in RESEARCH.md §10 | To do |

**Exit criteria:**
- No uncited numbers in the four docs.
- The ethics review finds no overclaiming.
- The blocker list is agreed.

## v1 — Careers MVP (closed pilot)
**Scope:**
- Fixed 24-item form with an optional refine step to 30 items.
- GRM-EAP profile.
- Lost-user gate and flow.
- Pearson matching into r ≥ .80 families with a job-zone filter.
- About 3 unordered families, each with 2–3 example jobs and an explanation.
- A printable summary for a counsellor.
- No free text, no accounts, no stored answers (processing in memory).

The full specification is in [MODELS.md](MODELS.md).

**Release blockers** (all must be cleared before anyone outside the team uses it; from the ethics review, CLAUDE.md):
1. Privacy/legal design and a DPIA, reviewed by a lawyer or DPO. This includes the consent age: 16 by default in the EU
   (minimum 13), 14 in Spain ([GDPR Art. 8](https://gdpr-info.eu/art-8-gdpr/); [LOPDGDD Art. 7](https://www.boe.es/buscar/act.php?id=BOE-A-2018-16673)).
2. Item parameters that may legally ship: either permission from OpenPsychometrics, or items we are allowed to use
   (O\*NET IP, CC BY 4.0) calibrated on a consented pilot sample (ADR 0002).
3. Replacement items for the 8 flagged items, and a **re-audited DIF** on the final item set.
4. A validated lost-user flow.
5. O\*NET attribution on the site (text in the README; done).

**Milestones:**
| # | Milestone | Proposed success criterion | Today |
|---|---|---|---|
| 1.1 | Write and DIF-screen new items (non-biology I, non-sales E, counter-stereotypic R/S) | Every retained item has \|DIF\| below the E2 flag threshold for gender and age | 8 of 48 items flagged (E2) |
| 1.2 | Calibrate the final form on a consented pilot sample | Per-scale α ≥ .80; 24-item vs 40-item profile r ≥ .95 | α .83–.90; r .965–.968 in replay (E1, E4) |
| 1.3 | Live vs simulated check | Live top-3 family agreement no more than .05 below the replay value | .63–.64 in replay (E4) |
| 1.4 | Family labels and explanations | Counsellor review: ≥ 80% of family labels judged accurate | Not done |
| 1.5 | Lost-user flow | A pilot with gated users shows an increase in career decision self-efficacy vs a ranked-list control (pre-registered effect size) | Design only |
| 1.6 | Fairness audit of outputs | Per-group family agreement within .05 across gender and age; exposure of R/S families reported by gender and reviewed by the ethics reviewer | Boys 13–17 top-10 .46 vs .55 overall (E5); R-top share 1.7% vs 8.9% (E3) |
| 1.7 | Usability pilot (n set by a power analysis) | Median completion ≤ 6 min; ≥ 70% find at least one family "worth exploring" | Not done |

**Not in v1:** CAT, free text, field-of-study suggestions, accounts, feedback learning.

## v2 — Own data and wider reach
| # | Milestone | Proposed success criterion | Today |
|---|---|---|---|
| 2.1 | Grow the item bank to 15–20 calibrated items per scale; re-run E4 | CAT beats the best fixed form by ≥ .03 r or 5 points of top-3 family agreement at equal length (E4's secondary bar) | CAT ≤ +.005 r with 8 items per scale (E4) |
| 2.2 | Spanish version | Configural and metric invariance ES vs EN; family agreement within .05 | Untested; hexagon fit varies by culture (Rounds & Tracey 1996, A) |
| 2.3 | EU catalogue (ESCO crosswalk), finer A/S/I occupations | Exposure Gini below .77; A-top pool at least doubled | Gini .77; 28 A-top occupations (E3) |
| 2.4 | Free text as optional evidence (E7c → product) | Negation handled (negated letter < 0 in ≥ 5 of 6 pairs); counterfactual overlap ≥ .90 on an **independent** held-out set; name subset ≥ .90 | Negation 1 of 6; overlap .922, names .838, not independent (E7, E7b) |
| 2.5 | Opt-in feedback (after a DPIA) | Consent rate and data minimisation reviewed; no demographic inputs to models | Not started |
| 2.6 | Outcome study design | Pre-registered follow-up (e.g. 12 months) on exploration actions and satisfaction | Not started |

## v3 — Study paths (universities and degrees)
| # | Milestone | Proposed success criterion | Today |
|---|---|---|---|
| 3.1 | Field-of-study layer as "people with similar interests often studied…" | Top-3 beats majority and centroid baselines with non-overlapping CIs on our own data | .565 vs .40 / .32 on OpenPsychometrics (E6) |
| 3.2 | De-amplification | Predicted gender share gap ≤ actual gap for every field (ratio ≤ 1.0); women's STEM top-3 hit within .05 of men's | Psychology ×1.65, STEM-core ×1.11; STEM top-3 hit 52% vs 80% (E6) |
| 3.3 | Regulatory check | AI Act high-risk assessment completed (education steering, Annex III point 3, cited in E6) | Not done |
| 3.4 | University catalogue data | A licensed source per country, documented in DATA_SOURCES.md | Not started |

---

## Standing rules for every phase
- Pre-register, commit, then run (ADR 0003). Log every decision and step in `docs/` (CLAUDE.md rule 8).
- Never present match r or similarity scores as accuracy. Show families, not ranks (ADR 0006).
- No demographic inputs. Run fairness checks before any user-facing release (CLAUDE.md rule 7).
- No user data until the privacy design exists (CLAUDE.md rule 5).

## Sources
- GDPR Art. 8. https://gdpr-info.eu/art-8-gdpr/
- LOPDGDD Art. 7. https://www.boe.es/buscar/act.php?id=BOE-A-2018-16673
- Rounds, J., & Tracey, T. J. G. (1996). https://experts.illinois.edu/en/publications/cross-cultural-structural-equivalence-of-riasec-models-and-measur/
- Own experiments: `research/findings/e1_data_audit.md` … `e7b_cue_stripping.md`; decisions in `docs/decisions/`.
