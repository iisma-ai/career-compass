# 0022 — E10: no length-based fix for the agreement gap; the 1.6(a) gap definition goes to the owner
Date: 2026-11-17        Status: Accepted (the definition question is left open for the owner)

## Context
E10 (`research/findings/e10_gap_mitigation.md`) tested four gender-blind form-length rules and found none viable.
- The gap in top-3 family agreement (F − M, among people shown families) is .042 at 24 items.
- The best rule, extending to 40 items when differentiation < 1.5 (C3, 26.9 items on average), brings it to .030.
- Giving everyone 40 items leaves .040.

Exploratory post-hoc analysis found that reweighting men to women's profile-shape mix (top-2 code × differentiation)
leaves .011. Most of the gap reflects different answer patterns, not different treatment of similar answers.

The ROADMAP 1.6(a) bar ("per-group agreement within .05") is still a proposal. It has not been pre-registered,
because the 1.6 study doesn't exist yet. As proposed it measures the raw gap.

## Options
1. Keep the raw-gap bar and accept that 1.6(a) will most likely fail. The audit would then report the gap and the
   reasons for it.
2. **Bar on the answer-conditional gap** (after reweighting to a common profile-shape mix). The raw gap would still be
   reported with a CI, but it would not be the bar. This tests what a gender-blind engine controls: similar answers,
   similar quality. **Recommended.**
3. Gender-conditioned corrections. **Rejected:** ADR 0015 forbids them.

Separately, form length:
- (a) Keep 24 items.
- (b) Adopt C3 (extend to 40 for flat profiles). It raises agreement for everyone: F +.018, M +.029.

## Decision
- E10 is recorded as **not viable**. No form change is adopted now.
- The choice between options 1 and 2 is the owner's: it decides what "fair" means for the audit. It must be made, and
  pre-registered, before the 1.6 study.
- C3 stays a candidate. It can be adopted only after a pre-registered live test of the extension step, because its
  benefit is replay-based. Adopting it would raise mean length to about 27 items, and to 28 items for people whose
  profiles are flat more often.
- The composition finding is exploratory. Confirm it on independent data (study S2) before relying on it.

## Consequences
- ROADMAP 1.6 notes the open definition question. Release blocker 3 (fairness) is unchanged.
- Teens show a larger gap (.070 raw, .023 after reweighting) that can't be audited in the 18+ tier.

## Evidence
`research/findings/e10_gap_mitigation.md`, `e10_gap_mitigation.json`, `e10_posthoc.json`; ADRs 0015, 0019, 0020.
