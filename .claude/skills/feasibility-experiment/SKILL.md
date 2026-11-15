---
name: feasibility-experiment
description: Template and rules for designing, running and reporting a reproducible feasibility experiment (E1–E7) or any model evaluation in this project. Use when writing or running a script in research/feasibility/ or writing a research/findings/ file.
---

# Feasibility experiment protocol

## Before running: pre-register
Write the top of `research/findings/eN_<slug>.md` **before** running the code:
```
# EN — <title>
Question:      <one sentence>
Hypothesis:    <what we expect and why, with citation if from literature>
Data:          <data/processed/... or data/raw/<source>/..., n rows after filters>
Method:        <models / analyses>
Baselines:     <at least one trivial baseline + the O*NET-style Pearson baseline where relevant>
Metrics:       <exact metrics>
Success bar:   <threshold for "proven" / "promising" / "not viable">
```
Don't change the success bar after seeing results. If it was wrong, say so in the
discussion and keep the original.

## Script skeleton: `research/feasibility/eN_<slug>.py`
```python
"""EN — <title>. Run: uv run python -I research/feasibility/eN_<slug>.py"""
import argparse, json
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
FINDINGS = ROOT / "research" / "findings"

def main(seed: int, quick: bool) -> dict:
    rng = np.random.default_rng(seed)
    # 1. load (data/processed preferred)   2. filter (log counts)
    # 3. analyse                           4. compare to baselines
    results = {}
    return results

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--quick", action="store_true", help="subsample for a fast smoke run")
    a = ap.parse_args()
    res = main(a.seed, a.quick)
    FINDINGS.mkdir(parents=True, exist_ok=True)
    (FINDINGS / "eN_<slug>.json").write_text(json.dumps(res, indent=2))
    print(json.dumps(res, indent=2))
```
Charts go to `research/findings/eN_<slug>_*.png` (matplotlib, labelled axes, n in title).
Use held-out splits (train/test, or k-fold) for anything predictive. Report CIs (bootstrap)
for headline numbers.

## After running: report
Append to the findings file: **Results** (table + charts), **Verdict** (proven / promising /
not viable vs. the success bar), **Caveats**, **Implications for the product**.

## The experiment list
| ID | Question | Success bar (initial proposal; confirm before running) |
|---|---|---|
| E1 | Is the OpenPsychometrics data usable? (quality, demographics, `major` field) | ≥ 50k clean rows; codebook fields confirmed |
| E2 | Do the 48 items recover 6 RIASEC factors and the hexagon? Are there stable archetypes? | Clear 6-factor solution; hexagon order in MDS; clusters stable (ARI ≥ .7 across seeds) |
| E3 | How differentiated are O*NET occupations in RIASEC space? | Report effective resolution: how many distinct groups exist |
| **E4** | **How many adaptive questions reproduce the full-test profile and top-10 careers?** | r ≥ .90 with full scores and ≥ 70% top-10 overlap within ≤ 20 items |
| E5 | How stable are top-10 recommendations under answer noise? | Mean bootstrap top-10 overlap reported; sets the ceiling for E4 |
| E6 | Can answers predict university major family better than RIASEC similarity? | Top-3 accuracy beats both baselines with non-overlapping CIs |
| E7 | Does free text match sensible O*NET occupations via embeddings? | ≥ 70% of 30 hand-written statements get a "sensible" top-5 (blind rating) |

Use the `irt-cat-simulation` skill for E4 and `riasec-scoring` for all data cleaning.
