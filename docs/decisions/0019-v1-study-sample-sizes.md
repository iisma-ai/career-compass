# 0019 — Sample sizes for the v1 research studies (1.5, 1.6, 1.7) and a gender-blind mitigation for the agreement gap
Date: 2026-11-16        Status: Accepted

## Context
E9 (`research/findings/e9_study_power.md`) computed the sample sizes by its pre-registered rules:
- **1.6 fairness audit:** 2,052 adults per group. This number is set by the ±.03 precision bar on the S-top exposure
  share. The parity tests themselves need about 580 per group.
- **1.5 lost-user trial:** 176 per arm, screening about 2,640 adults.
- **1.7 usability study:** 90 participants.

E9 also found a gender gap in how well the 24-item form agrees with the full test: .044 [.039, .049] for top-3 families.
That is close to the .05 parity bar, so the 1.6(a) gender test would almost surely fail at any feasible n.

## Options
1. Run 1.6 at 2,052 per group as pre-registered.
2. Run 1.6 at about 1,000 per group, which covers (a), (b) R-top and (c). The S-top precision bar would be relaxed to
   ±.045 in a new pre-registration. This trade-off is the owner's to decide; it is **not** decided here.
3. Change the 1.6(a) bar to fit the gap. **Rejected:** moving a bar after seeing data breaks ADR 0003.

## Decision
- The protocol (milestone 1.0) uses the E9 numbers as written: 1.6 at 2,052 per group, 1.5 at 176 per arm, 1.7 at 90.
  Studies 1.6 and 1.7 may share participants.
- Option 2 is recorded as an open question for the owner. If it is chosen, it needs its own ADR and a pre-registration
  before the study.
- Before 1.6 runs, test a **gender-blind** mitigation for the agreement gap as its own pre-registered experiment
  (E10). One candidate: when the 24-item profile is flat (low differentiation), extend to the 30-item refine step.
  The mitigation may use only answers, never gender (ADR 0015).

## Consequences
- A full v1 research programme is large: about 4,100 adults for 1.6, plus the item pilot (800, E8) and the 1.5 screening.
  Recruitment and ethics planning must reflect this.
- 13.4% of adults trigger the lost-user gate, so validating that flow (release blocker 4) matters more.

## Evidence
`research/findings/e9_study_power.md`, `e9_study_power.json`; E1, E4, E5; ADRs 0003, 0014, 0015, 0018.
