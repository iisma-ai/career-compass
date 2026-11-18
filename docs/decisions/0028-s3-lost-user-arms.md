# 0028 — Draft engine and demo arms for the lost-user trial (S3)
Date: 2026-11-18        Status: Accepted

## Context
ROADMAP 1.5 compares two flows for people the gate flags (differentiation < 1.0 or elevation < 2.0, MODELS L3): the
usual broad-families flow and a new flow. The protocol says S3 can't start until the new flow exists and a counsellor
has reviewed it (blockers 4 and 7). Until now the engine returned no families for gated users (ADR 0027), so neither
arm existed.

## Options
1. Wait for a counsellor to design the new flow. Rejected as the only route: a working draft gives the counsellor
   something concrete to review.
2. **Build both arms as research drafts from the MODELS L3 design (chosen).**
3. Also add scenario-based items with a "don't know / never tried" option. Deferred: new items have no GRM
   calibration, so they can't be scored until a pilot like S1 calibrates them.

## Decision
- **Engine:** `assess(..., lost_arm=None | "usual" | "explore")`.
  - **Default (None):** unchanged, so gated users get no families.
  - **"usual" (arm A):** the 3 families from `recommend`, with the "several directions" notice, as a mixed profile gets.
  - **"explore" (arm B, draft):** `explore_families`, which takes 5 families in score order but only one per leading
    interest type, then fills any remaining places in score order.
  - **Ordering and scope:** both arms are unordered and deterministic. The arm is ignored for users who aren't gated.
  - **Assignment:** the study assigns the arm at random, never from answers or personal characteristics (ADR 0015).
- **Demo:** the lost page shows a reviewer-only choice of arm.
  - **Arm B page:**
    - explicit uncertainty wording;
    - one draft "something to try" per group, chosen by the group's leading type;
    - a plain-text summary to take to a counsellor;
    - no numbers.
  - **Status of the copy:** all of it is draft, pending counsellor review.
- **Not in the draft:** scenario items, the "don't know" option, localised help links.

## Consequences
- S3 now has two concrete arms to review. Counsellor review (blocker 7) and the trial itself (blocker 4) are still
  needed. The pre-registered effect size and the career decision self-efficacy instrument are still `[TO DECIDE]`.
- **Seen when checking three flat profiles (descriptive, not an experiment):**
  - arm B never included an Artistic-led group, because the catalogue has few of them (E3);
  - most examples needed considerable or extensive preparation (the E3 skew);
  - for a nearly flat profile, the Pearson ranking is driven by small differences, so family choice there is close
    to arbitrary.

  This is one reason arm B leans on try-outs rather than on the specific families. The counsellor review should
  decide whether arm B should guarantee one group per type, picked by hand.

## Evidence
MODELS L3, L4; ROADMAP 1.5; protocol §2 (S3); ADRs 0006, 0015, 0027; [e3](../../research/findings/e3_occupation_space.md);
`tests/test_demo.py` (S3 arm tests).
