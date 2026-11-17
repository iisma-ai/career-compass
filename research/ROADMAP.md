# Career Compass — Roadmap (v0 → v3)

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
| **v1** Careers MVP (closed pilot) | 24-item questionnaire → career families with explanations, in English. The product stores nothing; pilot studies run as a separate, consented research tier (ADR 0014) | All release blockers cleared; pilot criteria met |
| **v2** Own data, wider reach | Own licensed item bank and calibration, Spanish, EU catalogue, optional free text | Calibration and invariance on our own sample; Spanish parity |
| **v3** Study paths | "People with similar interests studied…" alongside careers | Fairness audit passes after de-amplification |

---

## v0 — Research and feasibility (current)
| Milestone | Status |
|---|---|
| Literature notes 01–06 | Done |
| E1–E7 feasibility experiments, plus E7b | Done ([RESEARCH.md §5](RESEARCH.md)) |
| DATA_SOURCES, RESEARCH, MODELS, ROADMAP | Done, as of 2026-11-16 |
| Ethics review of the dossier | Done 2026-11-16 (fixes applied) |
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
- A printable summary for a counsellor, and human-help signposting on every result page.
- The item order, GRM parameters and families can't ship until blocker 2 clears.

**Two separate data tiers (ADR 0014):**
- **Product mode:** no accounts, no stored answers, no analytics identifiers, and server logs without IP addresses. Answers
  are processed in memory, which is still processing of personal data and is covered by the DPIA.
- **Research mode** (milestones 1.2, 1.3, 1.5, 1.7): a separate, explicitly consented, pseudonymous study with its own
  protocol, DPIA, research-ethics approval, retention limit and deletion route. Participants are **18+** until the DPIA and a
  lawyer or DPO approve minors, with parental consent where GDPR Art. 8 / LOPDGDD Art. 7 require it.

The full specification is in [MODELS.md](MODELS.md).

**Release blockers** (all must be cleared before anyone outside the team uses it; from the ethics review, CLAUDE.md):
1. Privacy/legal design and a DPIA, reviewed by a lawyer or DPO. This includes the consent age: 16 by default in the EU
   (minimum 13), 14 in Spain ([GDPR Art. 8](https://gdpr-info.eu/art-8-gdpr/); [LOPDGDD Art. 7](https://www.boe.es/buscar/act.php?id=BOE-A-2018-16673)).
2. Item parameters that may legally ship: either permission from OpenPsychometrics, or items we are allowed to use
   (O\*NET IP, CC BY 4.0) calibrated on a consented pilot sample (ADR 0002).
3. Replacement items for the 8 flagged items, and a **re-audited DIF** on the final item set.
4. A validated lost-user flow.
5. O\*NET attribution on the site and on derived files (the text is in the README).
6. A legal assessment of EU AI Act Annex III(3) (education and vocational training) for the v1 tool
   `[UNVERIFIED: secondary sources only]`.
7. Human-help signposting content, reviewed by a counsellor.
8. Research-ethics approval before any research-mode study (milestone 1.0).

**Milestones:**
| # | Milestone | Proposed success criterion | Today |
|---|---|---|---|
| 1.0 | Research-ethics approval and study protocol (prerequisite for 1.2, 1.3, 1.5, 1.7) | Approval obtained; protocol, consent forms, retention and deletion route documented | Not started. Item-pilot size set: plan 400 adults per self-reported gender group, floor 300 ([E8](findings/e8_pilot_power.md), ADR 0018) |
| 1.1 | Write and DIF-screen new items (non-biology I, non-sales E, and R/S items with gender-neutral settings, as a DIF-neutral content choice, not to push results) | Every retained item is cleared: 90% CI for gender DIF inside ±.30 (ADR 0018); age DIF 18–24 vs 25+ by the same rule; teen age DIF listed as unscreened | 8 of 48 items flagged (E2); 26 drafts, unscreened |
| 1.2 | Calibrate the final form on a consented pilot sample | Per-scale α ≥ .80; 24-item vs 40-item profile r ≥ .95 | α .83–.90; r .965–.968 in replay (E1, E4) |
| 1.3 | Live vs simulated check | Live top-3 family agreement no more than .05 below the replay value. This is a lenient target: one CAT study saw a drop of up to .18 from simulated to live (note 02, C) | .63–.64 in replay (E4) |
| 1.4 | Family labels and explanations | Counsellor review: ≥ 80% of family labels judged accurate | Not done |
| 1.5 | Lost-user flow | Gated users: the usual broad-families flow vs the new flow. No arm is one already known to be worse (no ranked-list arm for gated users). The new flow increases career decision self-efficacy by a pre-registered effect size | Design only. n = 176 per arm at d = .30; screen ≈ 2,640 adults (gate rate 13.4%) ([E9](findings/e9_study_power.md)) |
| 1.6 | Fairness audit of outputs | Pre-registered: (a) per-group top-10 and family agreement within .05 on the **answer-conditional gap** (groups standardised to the pooled profile-shape mix; raw gap also reported; ADR 0023), with n per cell from a power analysis, and a named mitigation for any gap (e.g. the differentiation gate); (b) R-top and S-top family exposure by gender, reported with CIs; (c) lost-user gate rate by group. (d) gender-blind check (ADR 0015): product inputs contain no demographic field and no code path reads one; any mitigation is gender-blind (item changes, the gate), never gender-conditioned | Boys 13–17 top-10 .46 vs .55 overall (gap .09, E5); R-top share 1.7% vs 8.9% (E3). E9: 2,052 per group by the pre-registered rule (parity tests alone ≈ 580); gender agreement gap .044 is near the .05 bar, so a gender-blind mitigation (E10) comes first (ADR 0019). E10: no length rule reaches ≤ .02 (best .030 at 26.9 items); about 3/4 of the gap is answer composition (exploratory). Owner chose the answer-conditional gap (ADR 0023) and 1,000 per group with S-top precision ±.045 (ADR 0024) |
| 1.7 | Usability pilot (n set by a power analysis) | Median completion ≤ 6 min. Usefulness is judged by the rating gap between real families and a **shuffled-families control** (to guard against the Barnum effect), not by an absolute percentage. Never reported as accuracy | Not done. E9: 90 participants (paired, d_z = .30) |

**Not in v1:** CAT, free text, field-of-study suggestions, accounts, feedback learning.

## v2 — Own data and wider reach
| # | Milestone | Proposed success criterion | Today |
|---|---|---|---|
| 2.1 | Grow the item bank to 15–20 calibrated items per scale; re-run E4 | CAT beats the best fixed form by ≥ .03 r or 5 points of top-3 family agreement at equal length (E4's secondary bar) | CAT ≤ +.005 r with 8 items per scale (E4) |
| 2.2 | Spanish version | Configural and metric invariance ES vs EN; family agreement within .05 | Untested; hexagon fit varies by culture (Rounds & Tracey 1996, A) |
| 2.3 | EU catalogue (ESCO crosswalk), finer A/S/I occupations | Exposure Gini below .77; A-top pool at least doubled | Gini .77; 28 A-top occupations (E3) |
| 2.4 | Free text as optional evidence (E7c → product) | Negation handled (negated letter < 0 in ≥ 5 of 6 pairs); counterfactual overlap ≥ .90 on an **independent** held-out set, written by people who haven't seen the rules and covering lower-case and non-Latin names; name subset ≥ .90 | Negation: rules fail on blind text, 4 of 12 (E7c). Overlap .929, names .906 on a blind but model-written set (E7c) |
| 2.5 | Opt-in feedback (after a DPIA) | Consent rate and data minimisation reviewed; no demographic inputs to models | Not started |
| 2.6 | Outcome study design | Pre-registered follow-up (e.g. 12 months) on exploration actions and satisfaction. Research mode only: it needs contact identifiers, so it requires its own consent, DPIA and ethics approval | Not started |

## v3 — Study paths (universities and degrees)
| # | Milestone | Proposed success criterion | Today |
|---|---|---|---|
| 3.1 | Field-of-study layer as "people with similar interests often studied…" | Top-3 beats majority and centroid baselines with non-overlapping CIs on our own data | .565 vs .40 / .32 on OpenPsychometrics (E6) |
| 3.2 | De-amplification | Predicted gender share gap ≤ actual gap for every field (ratio ≤ 1.0); women's STEM top-3 hit within .05 of men's | Psychology ×1.65, STEM-core ×1.11; STEM top-3 hit 52% vs 80% (E6) |
| 3.3 | Regulatory check | Legal assessment under EU AI Act Annex III(3) (education and vocational training) completed for field-of-study suggestions `[UNVERIFIED: secondary sources only]` | Not done |
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
