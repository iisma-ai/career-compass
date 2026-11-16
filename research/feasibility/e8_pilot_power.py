"""E8 — Sample size for the item pilot's gender-DIF screen (pre-registered in research/findings/e8_pilot_power.md).

Run: uv run python -I research/feasibility/e8_pilot_power.py [--quick]

Resamples equal-sized male/female groups of adults from the E1 clean data, re-estimates the E2 uniform-DIF statistic
for each of the 48 items with an HC1 90% CI, and finds the smallest n per group at which clean items (true |DIF| <= .15)
are reliably cleared (CI inside +-.30) while flagged items (true |DIF| >= .30) almost never are.
"""

import argparse
import json
import time
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
FINDINGS = ROOT / "research" / "findings"
DATA = ROOT / "data" / "processed" / "riasec_people.parquet"

SCALES = list("RIASEC")
ITEMS = [f"{s}{i}" for s in SCALES for i in range(1, 9)]
FLAG = 0.30
CLEAN = 0.15
Z90 = 1.6448536269514722
N_GRID = [100, 150, 200, 300, 400, 500, 750, 1000, 1500]


def rnd(x, k=3):
    if isinstance(x, dict):
        return {kk: rnd(v, k) for kk, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [rnd(v, k) for v in x]
    if isinstance(x, (np.floating, float)):
        return None if not np.isfinite(x) else round(float(x), k)
    if isinstance(x, np.integer):
        return int(x)
    return x


def load() -> pd.DataFrame:
    df = pd.read_parquet(DATA)
    df[ITEMS] = df[ITEMS].replace(0, np.nan).astype(float)
    df["sex"] = df["gender"].map({1.0: "male", 2.0: "female"})
    return df


def dif_one(y: np.ndarray, rest_raw: np.ndarray, female: np.ndarray) -> tuple[float, float]:
    """E2 estimator for one item, plus an HC1 SE. Both are in item-SD units."""
    rest = (rest_raw - rest_raw.mean()) / rest_raw.std()
    X = np.column_stack([np.ones(len(y)), rest, rest**2, female])
    XtX_inv = np.linalg.inv(X.T @ X)
    beta = XtX_inv @ (X.T @ y)
    e = y - X @ beta
    n, k = X.shape
    meat = (X * (e**2)[:, None]).T @ X
    cov = XtX_inv @ meat @ XtX_inv * n / (n - k)
    sd = y.std()
    return beta[3] / sd, np.sqrt(cov[3, 3]) / sd


def dif_all(arr: np.ndarray, female: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """arr: complete-case (n, 48) item matrix in ITEMS order."""
    est, se = np.empty(48), np.empty(48)
    for s in range(6):
        block = arr[:, s * 8 : (s + 1) * 8]
        tot = block.sum(1)
        for j in range(8):
            est[s * 8 + j], se[s * 8 + j] = dif_one(block[:, j], tot - block[:, j], female)
    return est, se


def e2_check(df: pd.DataFrame) -> dict:
    """Reproduce E2's per-item (pairwise-complete) gender DIF on all ages and compare with the E2 JSON."""
    e2 = json.loads((FINDINGS / "e2_structure.json").read_text(encoding="utf-8"))
    ref = e2["groups"]["item_dif_gender_female_minus_male_sd"]
    d = df[df.sex.isin(["female", "male"])]
    diffs = {}
    for i, it in enumerate(ITEMS):
        s = SCALES[i // 8]
        cols = [f"{s}{k}" for k in range(1, 9) if f"{s}{k}" != it]
        sub = d[[it, *cols, "sex"]].dropna()
        est, _ = dif_one(sub[it].to_numpy(), sub[cols].sum(1).to_numpy(), (sub.sex == "female").to_numpy(float))
        diffs[it] = abs(round(est, 3) - round(ref[it], 3))
    worst = max(diffs.values())
    return {"max_abs_diff_3dp": worst, "ok": worst <= 0.0015}


def alpha(block: np.ndarray) -> float:
    k = block.shape[1]
    return k / (k - 1) * (1 - block.var(0, ddof=1).sum() / block.sum(1).var(ddof=1))


def main(seed: int, quick: bool) -> dict:
    t0 = time.time()
    rng = np.random.default_rng(seed)
    df = load()
    check = e2_check(df)
    print("E2 reproduction check:", check)
    if not check["ok"]:
        raise SystemExit("Estimator does not reproduce E2; stopping as pre-registered.")

    adults = df[(df.age >= 18) & df.sex.isin(["female", "male"])].dropna(subset=ITEMS)
    arr = adults[ITEMS].to_numpy()
    fem = (adults.sex == "female").to_numpy(float)
    idx_f, idx_m = np.flatnonzero(fem == 1), np.flatnonzero(fem == 0)
    true, true_se = dif_all(arr, fem)
    clean = np.abs(true) <= CLEAN
    flagged = np.abs(true) >= FLAG

    grid = [100, 300, 1000] if quick else N_GRID
    B = 30 if quick else 300
    per_n = {}
    for n in grid:
        cleared = np.zeros((B, 48), bool)
        covered = np.zeros((B, 48), bool)
        half = np.zeros((B, 48))
        alphas = np.zeros((B, 6))
        for b in range(B):
            rows = np.concatenate([rng.choice(idx_f, n, replace=False), rng.choice(idx_m, n, replace=False)])
            a, f = arr[rows], fem[rows]
            est, se = dif_all(a, f)
            lo, hi = est - Z90 * se, est + Z90 * se
            cleared[b] = (lo > -FLAG) & (hi < FLAG)
            covered[b] = (lo <= true) & (true <= hi)
            half[b] = Z90 * se
            alphas[b] = [alpha(a[:, s * 8 : (s + 1) * 8]) for s in range(6)]
        p_clear = cleared.mean(0)
        per_n[n] = {
            "M1_share_clean_items_p_cleared_ge_80": float((p_clear[clean] >= 0.80).mean()),
            "M2_max_p_cleared_flagged": float(p_clear[flagged].max()) if flagged.any() else None,
            "M3_ci90_coverage": float(covered.mean()),
            "M4_median_ci90_halfwidth": float(np.median(half)),
            "M5_alpha_95_width_by_scale": {
                s: float(np.percentile(alphas[:, i], 97.5) - np.percentile(alphas[:, i], 2.5)) for i, s in enumerate(SCALES)
            },
            "alpha_median_by_scale": {s: float(np.median(alphas[:, i])) for i, s in enumerate(SCALES)},
            "p_cleared_by_item": dict(zip(ITEMS, p_clear.tolist(), strict=True)),
        }
        print(f"n={n}: M1={per_n[n]['M1_share_clean_items_p_cleared_ge_80']:.3f} "
              f"M2={per_n[n]['M2_max_p_cleared_flagged']:.3f} M3={per_n[n]['M3_ci90_coverage']:.3f} "
              f"M4={per_n[n]['M4_median_ci90_halfwidth']:.3f}  ({time.time() - t0:.0f}s)")

    rec = next(
        (n for n in grid
         if per_n[n]["M1_share_clean_items_p_cleared_ge_80"] >= 0.90 and per_n[n]["M2_max_p_cleared_flagged"] <= 0.05),
        None,
    )
    calibrated = all(0.85 <= per_n[n]["M3_ci90_coverage"] <= 0.95 for n in grid)
    if not calibrated:
        verdict = "CI not calibrated; result not usable"
    elif rec is None:
        verdict = f"not reachable at <= {grid[-1]} per group"
    else:
        verdict = f"recommended n = {rec} per gender group"

    res = {
        "meta": {
            "seed": seed, "quick": quick, "B": B, "grid": grid, "runtime_s": round(time.time() - t0, 1),
            "n_adults_complete": len(adults), "n_female": len(idx_f), "n_male": len(idx_m),
            "clean_threshold": CLEAN, "flag_threshold": FLAG,
        },
        "e2_reproduction_check": check,
        "true_dif_adults": dict(zip(ITEMS, true.tolist(), strict=True)),
        "true_dif_adults_se": dict(zip(ITEMS, true_se.tolist(), strict=True)),
        "clean_items": [it for it, c in zip(ITEMS, clean, strict=True) if c],
        "flagged_items": [it for it, c in zip(ITEMS, flagged, strict=True) if c],
        "near_flag_items": [it for it, c, f in zip(ITEMS, clean, flagged, strict=True) if not c and not f],
        "per_n": per_n,
        "recommended_n_per_group": rec,
        "ci_calibrated": calibrated,
        "verdict": verdict,
    }
    plot(res, quick)
    return rnd(res, 4)


def plot(res: dict, quick: bool) -> None:
    grid = res["meta"]["grid"]
    fig, ax = plt.subplots(figsize=(8, 5))
    for it, t in res["true_dif_adults"].items():
        ys = [res["per_n"][n]["p_cleared_by_item"][it] for n in grid]
        if abs(t) <= CLEAN:
            c, lw = "tab:blue", 0.8
        elif abs(t) >= FLAG:
            c, lw = "tab:red", 1.6
        else:
            c, lw = "tab:orange", 1.0
        ax.plot(grid, ys, color=c, lw=lw, alpha=0.7)
    ax.axhline(0.80, color="grey", ls="--", lw=0.8)
    ax.axhline(0.05, color="grey", ls=":", lw=0.8)
    if res["recommended_n_per_group"]:
        ax.axvline(res["recommended_n_per_group"], color="black", lw=0.8)
    ax.set_xscale("log")
    ax.set_xticks(grid, [str(n) for n in grid])
    ax.set_xlabel("respondents per gender group (log scale)")
    ax.set_ylabel("P(90% CI inside ±.30): item cleared")
    ax.set_title(f"E8: item clearance by pilot size (B = {res['meta']['B']}; adults, OpenPsychometrics)\n"
                 "blue: true |DIF| ≤ .15, orange: .15–.30, red: ≥ .30")
    fig.tight_layout()
    fig.savefig(FINDINGS / ("e8_pilot_power_quick.png" if quick else "e8_pilot_power.png"), dpi=120)
    plt.close(fig)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--quick", action="store_true", help="3 grid points, B = 30, for a smoke run")
    args = ap.parse_args()
    out = main(args.seed, args.quick)
    name = "e8_pilot_power_quick.json" if args.quick else "e8_pilot_power.json"
    (FINDINGS / name).write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(out["verdict"])
