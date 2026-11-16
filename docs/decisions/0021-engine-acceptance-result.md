# 0021 — v1 engine acceptance: the pre-set bar failed on a mis-benchmarked metric; the engine reproduces E4
Date: 2026-11-16        Status: Accepted

## Context
ADR 0020 set an acceptance bar before the first engine run: mean per-person r between the 24-item predicted profile
and the full-test scale means ≥ .95 on 5,000 adults. The result was **.940, so the bar failed.**

Diagnosis after the run:
- I benchmarked the bar against E4's ".965–.968", which is **r_theta**: a per-scale correlation of θ across people.
- The test measured a per-person correlation across the six scales. That is a different and lower-scoring metric.
- E4 never reported the per-person metric, so the bar had no valid anchor.

## Options
1. Lower the bar to make the test pass. Rejected: that moves a bar after seeing the result.
2. **Keep the failed test as a record, and add a separate check that the engine reproduces E4 on E4's own metric
   (chosen).** The tolerance for that check was chosen after the first run, and this ADR discloses it.

## Decision
- `test_replay_on_real_answers` stays as written, marked `xfail(strict=True)`. If the engine ever passes .95, the test
  goes red and someone must review it.
- New `test_engine_reproduces_e4_metric`, on the same 5,000 adults:
  - E4's replay form scored through the engine gives r_raw .944, against .945 reported by E4 (tolerance ±.01, post-hoc);
  - the v1 balanced form must not be worse than E4's form by more than .005.
- One-off diagnostic, not a test, on the same sample:

  | Form | r_theta | r_raw | Top-3 families (r80) | Per-person profile r |
  |---|---|---|---|---|
  | v1 balanced | .972 | .949 | .647 | .940 |
  | E4 replay form | .971 | .944 | .636 | .936 |

  E4 reported .964 / .945 / .628. The balanced v1 form is slightly better on every metric.
- The engine is accepted as a correct implementation of MODELS L2–L4. Its quality is the E4 quality, not better.

## Consequences
- MODELS L1 records the exact v1 form; E9's findings note that its proxy form included E1.
- Lesson for future bars: name the metric's exact definition and source cell when anchoring a threshold.

## Evidence
`tests/test_engine.py`; `research/findings/e4_cat_simulation.json` (`curves["reduced:best_corr"]["24"]`); ADR 0020.
