# 0024 — Run the 1.6 fairness audit with 1,000 adults per group; S-top exposure precision relaxed to about ±.045
Date: 2026-11-17        Status: Accepted (owner's decision). Resolves option 2 in ADR 0019.

## Context
E9's pre-registered rule gave 2,052 per group. That number was driven only by the ±.03 precision bar on the share of
people shown an S-top family, which is close to .5. The other 1.6 parts need fewer, using E9's observed shares and the
normal approximation:

| Part | E9 n needed | 95% CI half-width at 1,000 per group |
|---|---|---|
| (b) R-top exposure, gender | 716 | ±.025 |
| (b) S-top exposure, gender / age | 2,022 / 2,052 | ±.043 / ±.043 |
| (c) gate rate, gender / age | 991 / 994 | ±.030 / ±.030 |
| (a) agreement parity (raw gap) | 448–581 | — (recomputed for the conditional gap in E11) |

## Decision (owner, 2026-11-17)
- Study S2 / milestone 1.6 recruits **1,000 adults per self-reported gender group**.
- The S-top precision bar becomes **±.045**. All other 1.6 bars are unchanged.
- E11 checks that 1,000 per group is enough for the answer-conditional parity test (ADR 0023). If it isn't, the
  shortfall goes back to the owner rather than being silently raised.

## Consequences
- S2 now needs about 2,000 adults who report male or female, plus everyone who reports otherwise.
- The protocol draft, ROADMAP 1.6 and STATUS are updated.

## Evidence
`research/findings/e9_study_power.md`, `e9_study_power.json`; ADRs 0019, 0023.
