# 0018 — Clear pilot items by a 90% CI inside ±.30 SD; plan 400 adults per gender group (floor 300)
Date: 2026-11-16        Status: Accepted

## Context
Milestone 1.1 retains a candidate item only if its gender DIF is below the E2 flag of .30 SD. At pilot scale a point
estimate below .30 can occur by chance for a biased item. E8 (`research/findings/e8_pilot_power.md`) simulated the E2
estimator at pilot sizes on adult OpenPsychometrics data. By the pre-registered rule, 300 per gender group is the minimum.
At that n, items with real DIF around .20–.25 are usually inconclusive.

## Options
1. Keep the point-estimate rule (|DIF| < .30). Rejected: at n = 300 the CI half-width is about .11, so items with
   real DIF of .35–.40 would sometimes pass.
2. **Clear an item only when its 90% CI lies inside ±.30 (chosen).** Three outcomes: cleared, flagged (point
   estimate |DIF| ≥ .30) or inconclusive (otherwise).
3. Equivalence with a tighter margin (e.g. ±.20). Rejected for now: E8 shows it would need far more than 1,500 per
   group for many items; it can be revisited with our own data in v2.

Pilot size: 300 per group (the E8 minimum) or 400 (margin). Chose 400 planned, 300 floor.

## Decision
- Retention: **cleared** items are eligible. **Flagged** items are dropped. **Inconclusive** items are not retained,
  unless the scale can't reach 4 items otherwise. In that case the item is named as a limitation in the re-audit
  (release blocker 3), and the smallest point estimate is preferred (ADR 0015).
- Age DIF uses the same rule, but an 18+ pilot can only compare 18–24 vs 25+. Teen age DIF stays unscreened until
  research with minors is approved (ADR 0014); it is listed as an open limitation, not as cleared.
- The pilot protocol (milestone 1.0) plans **400 adults per self-reported gender group**. It doesn't run the DIF screen
  with fewer than 300 per group. Total recruitment allows for respondents who don't report male/female (rate unknown).
- Gender is self-reported, optional, and used only for this offline audit (ADR 0015).

## Consequences
- `research/items/candidate_items_v1.md` retention bar updated; ROADMAP 1.0 and 1.1 updated.
- The final 24-item form may contain fewer "cleared" items than hoped. Extra candidates were drafted for this reason.
- Assumes new items behave like the old 48 (E8 caveat). Re-check the clearance rate after the pilot.

## Evidence
`research/findings/e8_pilot_power.md`, `e8_pilot_power.json`, `e8_pilot_power.png`; E2 DIF; ADRs 0003, 0014, 0015.
