# Career Compass v1 research studies: protocol draft (milestone 1.0)

**Status: DRAFT, prepared 2026-11-16, not approved.** It is written for a research-ethics committee and a DPO. Nothing
here may be run until:
- a research-ethics committee has approved it;
- a DPIA for research mode exists;
- a lawyer or DPO has reviewed it (release blockers 1 and 8; ADR 0014).

Text marked `[TO DECIDE]` needs an owner or committee decision; `[UNVERIFIED]` marks legal points not checked against
primary sources. This is not legal advice.

## 1. Purpose
Career Compass is a website that estimates a person's vocational interests (RIASEC) from a short questionnaire and suggests
career families worth exploring (`research/MODELS.md`). Before any release, the questionnaire and its outputs must be
calibrated, checked for fairness and tested for usefulness on consented participants. That is the job of these studies
(`research/ROADMAP.md`, milestones 1.1–1.7). The product itself stores nothing (ADR 0014); only these studies collect data.

## 2. Studies
| Study | Milestones | Design | Sample (from) |
|---|---|---|---|
| S1 Item pilot | 1.1, 1.2 | Online questionnaire: the 48 current items + 26 candidate items, random order | 400 per self-reported gender group (floor 300), plus others (E8, ADR 0018) |
| S2 Fairness and usability | 1.3, 1.6, 1.7 | The v1 24-item form → career families; ratings of real vs shuffled families (subsample) | 1.6: 1,000 per group (owner decision; S-top precision ±.045; ADR 0024); 1.7: 90 within it (E9) |
| S3 Lost-user trial | 1.5 | Randomised two-arm trial among people the gate flags: usual broad-families flow vs new flow | 176 per arm; about 2,640 screened (E9) |

S2 must not start before E10, the gender-blind mitigation for the agreement gap (ADR 0019). S3 must not start before the
new lost-user flow exists and a counsellor has reviewed its content (blocker 4 and 7). Each study is pre-registered
(hypotheses, metrics and analysis) and committed before data collection starts (ADR 0003).

## 3. Participants
- **Adults only (18+)** (ADR 0014). Minors are excluded until a DPIA and a lawyer or DPO approve their inclusion, with
  parental consent where GDPR Art. 8 / LOPDGDD Art. 7 require it. Age is confirmed by self-declaration
  `[TO DECIDE: whether self-declaration is enough]`.
- Language: English (v1 is English-only).
- Recruitment channels `[TO DECIDE]`: e.g. university participant pools, career services, a paid online panel. Quota
  sampling by self-reported gender is needed for S1/S2 group sizes. That means asking gender at screening, which must stay
  optional and audit-only (ADR 0015).
- Payment `[TO DECIDE]`: set by the channel and the committee.

## 4. What is collected (data minimisation)
| Data | Studies | Why | Notes |
|---|---|---|---|
| Item answers (1–5) | all | calibration, scoring | |
| Self-reported gender (optional; male / female / another answer / prefer not to say) | S1, S2 | DIF and fairness audit only | Never used by the product or any model (ADR 0015) |
| Age band (18–24, 25+) | S1, S2 | age DIF, fairness | Band, not date of birth |
| Ratings of family lists (real vs shuffled) | S2 subset | 1.7 usefulness | |
| Completion time | S2 | 1.7 | Server-side timing, no device fingerprint |
| Career decision self-efficacy scale | S3 | 1.5 outcome | Instrument and licence `[TO DECIDE]`; check licence before use |
| Study ID (random) | all | linking answers within one session | No name, email or IP stored with answers |

**Not collected:** name, contact details (unless a payment channel requires them, then kept separately by the panel or
payment provider), IP address, free text, location below country level `[TO DECIDE: country at all?]`, ethnicity,
health data.

## 5. Consent and information
- Explicit, informed, opt-in consent before any question. The information sheet covers:
  - the purpose;
  - what is collected;
  - that results are exploratory and not advice, ability tests or predictions of satisfaction;
  - voluntariness;
  - withdrawal and deletion;
  - retention;
  - contact details for the researcher and the DPO.
- Legal basis under GDPR `[UNVERIFIED; for the DPO]`: consent (Art. 6(1)(a)), or public-interest or scientific research
  with Art. 89 safeguards. If gender is ever treated as special-category data (it isn't listed in Art. 9 `[UNVERIFIED]`),
  the basis must be reviewed.
- Participants see their own results at the end (the same output as the product), with the standard wording and links to
  human help (MODELS L3, L6).

## 6. Risks and safeguards
| Risk | Safeguard |
|---|---|
| Distress from "flat" or low-interest results | Non-diagnostic wording; human-help links on every results page; "lost" is never shown; content reviewed by a counsellor (blocker 7) |
| Results taken as a verdict | "Careers worth exploring", no scores or ranks (ADR 0006); explanation of what results don't mean (MODELS L6) |
| Stereotyped suggestions | Gender-blind design (ADR 0015); fairness audit is the purpose of S2 |
| Re-identification | No direct identifiers; age bands; groups with fewer than 10 people are suppressed in any report `[TO DECIDE: threshold]` |
| Data breach | Encrypted storage, access limited to named researchers, access log `[TO DECIDE: hosting, EU region]` |
| Withdrawal after submission | Participants get their study ID at the end; deletion on request until anonymisation or aggregation `[TO DECIDE: cut-off]` |

## 7. Retention and deletion
- Raw pseudonymous answers are kept for at most `[TO DECIDE, e.g. 24 months]` after the study ends, then deleted. Aggregate
  item parameters (GRM estimates) and audit tables are kept, since they hold no personal data.
- Retention, deletion and the deletion route are written into the DPIA and the information sheet.

## 8. Analysis (summary; each study is pre-registered in full)
- **S1:**
  - **DIF:** an item is cleared only when the 90% CI of its gender DIF lies inside ±.30 SD. Items are flagged or
    inconclusive otherwise (ADR 0018).
  - **Age DIF:** 18–24 vs 25+.
  - **Calibration:** GRM; per-scale α ≥ .80; 24-item vs 40-item profile r ≥ .95 (milestone 1.2).
- **S2:**
  - **1.6:** group parity tests (TOST ±.05) on the answer-conditional gap (estimated by regression adjustment on profile
    shape, ADR 0026; raw gap and a fixed-strata sensitivity analysis reported alongside; ADR 0023) for top-3 family agreement and top-10 overlap; R-top and S-top exposure
    by gender with CIs; gate rate by group.
  - **1.7:** paired ratings, real vs shuffled families; median completion time with a CI.
  - **1.3:** live vs simulated agreement.
- **S3:** two-arm comparison of career decision self-efficacy, smallest effect of interest d = .30.
- Results are never reported as "accuracy" (CLAUDE.md, RESEARCH §9).

## 9. Known limits to tell the committee
- **Adults only,** while the product's audience includes teens. Results can't be generalised to teens (ADR 0014). Teen age
  DIF stays unscreened.
- **The sample sizes come from simulations** on a self-selected online dataset (E8, E9). Real shares may differ.
- **The item parameters used today come from OpenPsychometrics data** that is research-only (ADR 0002). S1 exists partly to
  replace them with our own calibration.

## 10. Decisions needed before submission
1. Recruitment channels and payment.
2. ~~Whether 1.6 runs at 2,052 per group or about 1,000~~ Decided: 1,000 per group (ADR 0024).
3. Hosting provider and region, retention period, withdrawal cut-off, small-cell suppression threshold.
4. The career decision self-efficacy instrument (licence).
5. Which ethics committee, and the institution that sponsors the research.
6. GDPR legal basis and whether a DPIA per study or one combined DPIA (DPO).

## Sources
- GDPR Art. 8: https://gdpr-info.eu/art-8-gdpr/ · LOPDGDD Art. 7: https://www.boe.es/buscar/act.php?id=BOE-A-2018-16673
- Own planning results: `research/findings/e8_pilot_power.md`, `research/findings/e9_study_power.md`.
- Decisions: ADRs 0002, 0003, 0006, 0014, 0015, 0018, 0019.
