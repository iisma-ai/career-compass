"""E11 — Power of the answer-conditional parity test at 1,000 per group (pre-registered in
research/findings/e11_conditional_gap_power.md).

Run: uv run python -I research/feasibility/e11_conditional_gap_power.py [--quick]

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

from career_compass import engine as E
from career_compass.matching import score_matrix

FINDINGS = M.FINDINGS
BANDS = np.array([1.5, 2.0, 2.5, 3.0])  # -> band 0..4
N_GRID = [500, 750, 1000, 1500, 2000]
DELTA, Z90, MIN_CELL = 0.05, 1.6448536269514722, 10


def top10(P, occ):
    out = []
    for i in range(0, len(P), M.CHUNK):
        S = score_matrix(P[i : i + M.CHUNK], occ)
        S = S - np.arange(S.shape[1]) * 1e-12
        out.append(np.argpartition(-S, 9, axis=1)[:, :10])
    return np.concatenate(out)


def stratum_labels(code, band, g):
    """ADR 0023 pooling. Returns an int label per person; -1 code = 'other'."""
    lab = np.empty(len(code), int)
    other = []
    for c in np.unique(code):
        ic = code == c
        cnt = np.zeros((5, 2), int)
        np.add.at(cnt, (band[ic], g[ic].astype(int)), 1)
        groups, cur, cur_cnt = [], [], np.zeros(2, int)
        for b in range(5):
            cur.append(b)
            cur_cnt = cur_cnt + cnt[b]
            if cur_cnt.min() >= MIN_CELL:
                groups.append(cur)
                cur, cur_cnt = [], np.zeros(2, int)
        if cur:  # leftover top bands merge into the lower neighbour
            if groups:
                groups[-1] = groups[-1] + cur
            else:
                groups = [cur]
        if cnt.sum(0).min() < MIN_CELL:
            other.append(c)
            continue
        for k, bs in enumerate(groups):
            lab[ic & np.isin(band, bs)] = c * 10 + k
    lab[np.isin(code, other)] = -1
    return lab


def cond_gap(y, lab, g):
    _, inv = np.unique(lab, return_inverse=True)
    S = inv.max() + 1
    w = np.bincount(inv, minlength=S) / len(inv)
    gap, var = 0.0, 0.0
    for grp, sign in ((1, 1.0), (0, -1.0)):
        m = g == grp
        n = np.bincount(inv[m], minlength=S)
        s1 = np.bincount(inv[m], weights=y[m], minlength=S)
        s2 = np.bincount(inv[m], weights=y[m] ** 2, minlength=S)
        mean = np.divide(s1, n, out=np.zeros(S), where=n > 0)
        v = np.divide(s2 - n * mean**2, n - 1, out=np.zeros(S), where=n > 1)
        gap += sign * (w * mean).sum()
        var += (w**2 * np.divide(v, n, out=np.zeros(S), where=n > 0)).sum()
    return gap, np.sqrt(var)


def raw_gap(y, g):
    return y[g == 1].mean() - y[g == 0].mean()


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
    O10 = (top10(P24, cat.occ)[:, :, None] == top10(P48, cat.occ)[:, None, :]).any(2).mean(1)
    shown = ~M.gated(P24)
    o = np.argsort(-P24, 1, kind="stable")
    code = o[:, 0] * 6 + o[:, 1]
    band = np.searchsorted(BANDS, P24.max(1) - P24.min(1), side="right")

    contrasts = {
        "gender": ((df.gender == 2.0).to_numpy(), (df.gender == 1.0).to_numpy(), ("female", "male")),
        "age": ((df.age <= 24).to_numpy(), (df.age >= 25).to_numpy(), ("18-24", "25+")),
    }
    grid = [500, 1000] if quick else N_GRID
    R = 100 if quick else 1000
    out = {"meta": {"seed": seed, "quick": quick, "R": R, "grid": grid, "n_adults": len(df),
                    "n_shown": int(shown.sum())}}
    for cname, (g1, g0, labels) in contrasts.items():
        i1, i0 = np.flatnonzero(g1 & shown), np.flatnonzero(g0 & shown)
        idx = np.r_[i1, i0]
        g = np.r_[np.ones(len(i1)), np.zeros(len(i0))]
        lab_full = stratum_labels(code[idx], band[idx], g)
        res = {"groups": labels, "n_shown": [len(i1), len(i0)]}
        for mname, y in (("A3", A3), ("O10", O10)):
            yy = y[idx]
            cg, cse = cond_gap(yy, lab_full, g)
            rg = raw_gap(yy, g)
            r = {"full_data": {"raw_gap": rg, "conditional_gap": cg, "conditional_se": cse,
                               "share_explained": 1 - cg / rg if rg != 0 else None,
                               "n_strata": int(len(np.unique(lab_full)))}, "per_n": {}}
            yA = np.where(g == 1, yy - cg, yy)  # scenario A: true conditional gap ~ 0
            for n in grid:
                clrA = clrB = cov = 0
                for _ in range(R):
                    s1 = rng.choice(len(i1), n, replace=False)
                    s0 = len(i1) + rng.choice(len(i0), n, replace=False)
                    s = np.r_[s1, s0]
                    gs = g[s]
                    lab = stratum_labels(code[idx][s], band[idx][s], gs)
                    for scen, ys in (("A", yA[s]), ("B", yy[s])):
                        est, se = cond_gap(ys, lab, gs)
                        ok = (est - Z90 * se > -DELTA) and (est + Z90 * se < DELTA)
                        if scen == "A":
                            clrA += ok
                        else:
                            clrB += ok
                            cov += (est - Z90 * se <= cg <= est + Z90 * se)
                r["per_n"][n] = {"p_cleared_A": clrA / R, "p_cleared_B": clrB / R, "coverage90_B": cov / R}
                print(f"{cname} {mname} n={n}: A {clrA / R:.3f} B {clrB / R:.3f} cov {cov / R:.3f} "
                      f"({time.time() - t0:.0f}s)", flush=True)
            res[mname] = r
        out[cname] = res

    def ok_at(n):
        return all(out[c][m]["per_n"][n]["p_cleared_A"] >= 0.80
                   and 0.85 <= out[c][m]["per_n"][n]["coverage90_B"] <= 0.95
                   for c in contrasts for m in ("A3", "O10"))

    calibrated = all(0.85 <= out[c][m]["per_n"][n]["coverage90_B"] <= 0.95
                     for c in contrasts for m in ("A3", "O10") for n in grid)
    if 1000 in grid and ok_at(1000):
        verdict = "adequate"
    elif not calibrated:
        verdict = "SE not calibrated; not usable"
    else:
        need = next((n for n in grid if ok_at(n)), None)
        verdict = f"not adequate (n needed = {need if need else '> ' + str(grid[-1])})"
    out["verdict"] = verdict
    out["meta"]["runtime_s"] = round(time.time() - t0, 1)
    return M.rnd(out)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--quick", action="store_true", help="n in {500, 1000}, R = 100")
    a = ap.parse_args()
    res = main(a.seed, a.quick)
    name = "e11_conditional_gap_power_quick.json" if a.quick else "e11_conditional_gap_power.json"
    (FINDINGS / name).write_text(json.dumps(res, indent=2), encoding="utf-8")
    print(res["verdict"])
