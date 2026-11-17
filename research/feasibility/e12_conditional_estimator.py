"""E12 — A calibrated estimator for the answer-conditional gap (pre-registered in
research/findings/e12_conditional_estimator.md).

Run: uv run python -I research/feasibility/e12_conditional_estimator.py [--quick]

Gender and age are read only here, for the offline audit (ADR 0015).
"""

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import e10_gap_mitigation as M
import e11_conditional_gap_power as E11

from career_compass import engine as E

FINDINGS = M.FINDINGS
DELTA, Z90 = 0.05, 1.6448536269514722
FIX_BANDS = np.array([1.5, 2.5])


def design(P):
    c = P - P.mean(1, keepdims=True)
    d = P.max(1) - P.min(1)
    return np.column_stack([c[:, :5], c**2, P.mean(1), d, d**2])


def reg_gap(y, g, Z):
    X = np.column_stack([np.ones(len(y)), g, Z])
    XtX_inv = np.linalg.pinv(X.T @ X)
    b = XtX_inv @ (X.T @ y)
    e = y - X @ b
    n, k = X.shape
    cov = XtX_inv @ ((X * (e**2)[:, None]).T @ X) @ XtX_inv * n / (n - k)
    return float(b[1]), float(np.sqrt(cov[1, 1]))


def fix_gap(y, g, strat):
    present = np.intersect1d(np.unique(strat[g == 1]), np.unique(strat[g == 0]))
    keep = np.isin(strat, present)
    dropped = int(len(np.unique(strat)) - len(present))
    gap, se = E11.cond_gap(y[keep], strat[keep], g[keep])
    return gap, se, dropped


def main(seed, quick):
    t0 = time.time()
    rng = np.random.default_rng(seed)
    bank, cat = E.ItemBank.from_e4(), E.Catalogue.load()
    items = list(bank.items)
    df = pd.read_parquet(M.DATA)
    df[items] = df[items].replace(0, np.nan)
    df = df[df.age >= 18].dropna(subset=items).reset_index(drop=True)
    X = df[items].to_numpy(int)
    P24 = M.raw_profiles(X, bank, M.mask_for(bank, E.build_fixed_form(bank, 4)))
    P48 = M.raw_profiles(X, bank, np.ones(48, bool))
    A3 = (M.top3_families(P24, cat)[:, :, None] == M.top3_families(P48, cat)[:, None, :]).any(2).mean(1)
    O10 = (E11.top10(P24, cat.occ)[:, :, None] == E11.top10(P48, cat.occ)[:, None, :]).any(2).mean(1)
    shown = ~M.gated(P24)
    Z = design(P24)
    strat = P24.argmax(1) * 3 + np.searchsorted(FIX_BANDS, P24.max(1) - P24.min(1), side="right")

    contrasts = {
        "gender": ((df.gender == 2.0).to_numpy(), (df.gender == 1.0).to_numpy(), ("female", "male")),
        "age": ((df.age <= 24).to_numpy(), (df.age >= 25).to_numpy(), ("18-24", "25+")),
    }
    grid = [1000] if quick else [500, 1000, 2000]
    R = 100 if quick else 1000
    out = {"meta": {"seed": seed, "quick": quick, "R": R, "grid": grid, "n_shown": int(shown.sum())}}
    for cname, (g1, g0, labels) in contrasts.items():
        i1, i0 = np.flatnonzero(g1 & shown), np.flatnonzero(g0 & shown)
        idx = np.r_[i1, i0]
        g = np.r_[np.ones(len(i1)), np.zeros(len(i0))]
        Zc, Sc = Z[idx], strat[idx]
        res = {"groups": labels, "n_shown": [len(i1), len(i0)]}
        for mname, y in (("A3", A3), ("O10", O10)):
            yy = y[idx]
            raw = float(yy[g == 1].mean() - yy[g == 0].mean())
            tgt = {"REG": reg_gap(yy, g, Zc)[0], "FIX": fix_gap(yy, g, Sc)[0]}
            r = {"raw_gap": raw, "target": tgt,
                 "share_explained": {k: (1 - v / raw) if raw else None for k, v in tgt.items()}, "per_n": {}}
            for n in grid:
                acc = {k: {"clrA": 0, "clrB": 0, "cov": 0, "bias": 0.0, "dropped": 0} for k in tgt}
                for _ in range(R):
                    s = np.r_[rng.choice(len(i1), n, replace=False), len(i1) + rng.choice(len(i0), n, replace=False)]
                    gs, ys = g[s], yy[s]
                    for k in tgt:
                        for scen in ("A", "B"):
                            yv = np.where(gs == 1, ys - tgt[k], ys) if scen == "A" else ys
                            if k == "REG":
                                est, se = reg_gap(yv, gs, Zc[s])
                                drop = 0
                            else:
                                est, se, drop = fix_gap(yv, gs, Sc[s])
                            ok = (est - Z90 * se > -DELTA) and (est + Z90 * se < DELTA)
                            a = acc[k]
                            if scen == "A":
                                a["clrA"] += ok
                            else:
                                a["clrB"] += ok
                                a["cov"] += (est - Z90 * se <= tgt[k] <= est + Z90 * se)
                                a["bias"] += est - tgt[k]
                                a["dropped"] += drop > 0
                r["per_n"][n] = {k: {"p_cleared_A": a["clrA"] / R, "p_cleared_B": a["clrB"] / R,
                                     "coverage90": a["cov"] / R, "mean_bias": a["bias"] / R,
                                     "share_samples_with_dropped_stratum": a["dropped"] / R}
                                 for k, a in acc.items()}
                print(cname, mname, n, {k: (round(v["coverage90"], 3), round(v["p_cleared_A"], 3))
                                        for k, v in r["per_n"][n].items()}, f"{time.time() - t0:.0f}s", flush=True)
            res[mname] = r
        out[cname] = res

    qual = [k for k in ("REG", "FIX")
            if all(0.85 <= out[c][m]["per_n"][1000][k]["coverage90"] <= 0.95
                   and out[c][m]["per_n"][1000][k]["p_cleared_A"] >= 0.80
                   for c in contrasts for m in ("A3", "O10"))]
    share = {k: float(np.mean([out["gender"][m]["share_explained"][k] for m in ("A3", "O10")])) for k in ("REG", "FIX")}
    out["qualifying"] = qual
    out["gender_share_explained_mean"] = share
    out["chosen"] = max(qual, key=lambda k: share[k]) if qual else None
    out["verdict"] = f"chosen: {out['chosen']}" if qual else "none calibrated"
    out["meta"]["runtime_s"] = round(time.time() - t0, 1)
    return M.rnd(out)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--quick", action="store_true", help="n = 1000 only, R = 100")
    a = ap.parse_args()
    res = main(a.seed, a.quick)
    name = "e12_conditional_estimator_quick.json" if a.quick else "e12_conditional_estimator.json"
    (FINDINGS / name).write_text(json.dumps(res, indent=2), encoding="utf-8")
    print(res["verdict"])
