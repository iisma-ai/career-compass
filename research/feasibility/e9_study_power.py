"""E9 — Sample sizes for milestones 1.5, 1.6 and 1.7 (pre-registered in research/findings/e9_study_power.md).

Run: uv run python -I research/feasibility/e9_study_power.py [--quick]
"""

import argparse
import json
import math
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from career_compass.matching import load_occupations, score_matrix

FINDINGS = ROOT / "research" / "findings"
DATA = ROOT / "data" / "processed" / "riasec_people.parquet"
SCALES = list("RIASEC")
ITEMS = [f"{s}{i}" for s in SCALES for i in range(1, 9)]
DELTA = 0.05
HALF_W = 0.03
Z = {q: float(norm.ppf(q)) for q in (0.80, 0.90, 0.95, 0.975)}


def rnd(x, k=4):
    if isinstance(x, dict):
        return {kk: rnd(v, k) for kk, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [rnd(v, k) for v in x]
    if isinstance(x, (np.floating, float)):
        return None if not np.isfinite(x) else round(float(x), k)
    if isinstance(x, np.integer):
        return int(x)
    return x


def topk(S: np.ndarray, k: int) -> np.ndarray:
    m = S.shape[1]
    St = S - np.arange(m) * 1e-12
    part = np.argpartition(-St, k - 1, axis=1)[:, :k]
    order = np.argsort(-np.take_along_axis(St, part, 1), axis=1, kind="stable")
    return np.take_along_axis(part, order, 1)


def family_top(S: np.ndarray, fam: np.ndarray, k: int) -> np.ndarray:
    order = np.argsort(fam, kind="stable")
    starts = np.r_[0, np.flatnonzero(np.diff(fam[order])) + 1]
    F = np.maximum.reduceat(S[:, order], starts, axis=1)
    return topk(F, k)


def overlap(A, B):
    return (A[:, :, None] == B[:, None, :]).any(2).mean(1)


def tost_n(sd: float) -> int:
    return math.ceil(2 * (Z[0.95] + Z[0.90]) ** 2 * sd**2 / DELTA**2)


def tost_sim(x: np.ndarray, y: np.ndarray, n: int, B: int, rng) -> float:
    y = y - y.mean() + x.mean()  # true gap 0
    ok = 0
    for _ in range(B):
        a, b = rng.choice(x, n, replace=False), rng.choice(y, n, replace=False)
        d = a.mean() - b.mean()
        se = math.sqrt(a.var(ddof=1) / n + b.var(ddof=1) / n)
        ok += (d - Z[0.95] * se > -DELTA) and (d + Z[0.95] * se < DELTA)
    return ok / B


def prop_n(p1: float, p2: float) -> int:
    return math.ceil(Z[0.975] ** 2 * (p1 * (1 - p1) + p2 * (1 - p2)) / HALF_W**2)


def main(seed: int, quick: bool) -> dict:
    t0 = time.time()
    rng = np.random.default_rng(seed)
    df = pd.read_parquet(DATA)
    df[ITEMS] = df[ITEMS].replace(0, np.nan).astype(float)
    df = df[(df.age >= 18)].dropna(subset=ITEMS).reset_index(drop=True)
    if quick:
        df = df.sample(5000, random_state=seed).reset_index(drop=True)
    e4 = json.loads((FINDINGS / "e4_cat_simulation.json").read_text(encoding="utf-8"))
    form = e4["best_fixed_order"][:24]
    full = np.column_stack([df[[f"{s}{i}" for i in range(1, 9)]].mean(1) for s in SCALES])
    short = np.column_stack([df[[it for it in form if it[0] == s]].mean(1) for s in SCALES])
    assert all(sum(it[0] == s for it in form) == 4 for s in SCALES)

    occ = load_occupations()
    fams = pd.read_csv(FINDINGS / "e3_families.csv", dtype={"code": str}).set_index("code").loc[occ.code, "family_r80"]
    fam = fams.to_numpy()
    assert sorted(set(fam)) == list(range(fam.max() + 1))
    fam_prof = occ[SCALES].groupby(fam).mean().to_numpy()
    fam_peak = np.array(SCALES)[fam_prof.argmax(1)]

    A3, O10, F_short = [], [], []
    for i in range(0, len(df), 5000):  # chunked to bound memory (5000 x 923 score matrices)
        S_full = score_matrix(full[i : i + 5000], occ, method="pearson")
        S_short = score_matrix(short[i : i + 5000], occ, method="pearson")
        fs = family_top(S_short, fam, 3)
        A3.append(overlap(fs, family_top(S_full, fam, 3)))
        O10.append(overlap(topk(S_short, 10), topk(S_full, 10)))
        F_short.append(fs)
    A3, O10, F_short = np.concatenate(A3), np.concatenate(O10), np.concatenate(F_short)
    r_top = (fam_peak[F_short] == "R").any(1).astype(float)
    s_top = (fam_peak[F_short] == "S").any(1).astype(float)
    elev, diff = short.mean(1), short.max(1) - short.min(1)
    gate = ((diff < 1.0) | (elev < 2.0)).astype(float)

    contrasts = {
        "gender": (df.gender == 2.0).to_numpy(), "gender_ref": (df.gender == 1.0).to_numpy(),
        "age": (df.age <= 24).to_numpy(), "age_ref": (df.age >= 25).to_numpy(),
    }
    labels = {"gender": ("female", "male"), "age": ("18-24", "25+")}
    B = 200 if quick else 1000
    out16 = {}
    for c in ("gender", "age"):
        g1, g0 = contrasts[c], contrasts[c + "_ref"]
        res = {"groups": labels[c], "n_data": [int(g1.sum()), int(g0.sum())]}
        for name, v in (("A3_top3_family_agreement", A3), ("O10_top10_overlap", O10)):
            x, y = v[g1], v[g0]
            sd = math.sqrt((x.var(ddof=1) + y.var(ddof=1)) / 2)
            n = tost_n(sd)
            p = tost_sim(x, y, n, B, rng)
            while p < 0.78:
                n = math.ceil(n * 1.1)
                p = tost_sim(x, y, n, B, rng)
            gap = x.mean() - y.mean()
            se = math.sqrt(x.var(ddof=1) / len(x) + y.var(ddof=1) / len(y))
            res[name] = {"means": [x.mean(), y.mean()], "observed_gap": gap,
                         "observed_gap_ci95": [gap - Z[0.975] * se, gap + Z[0.975] * se],
                         "pooled_sd": sd, "n_per_group": n, "sim_p_cleared": p,
                         "gap_exceeds_delta": abs(gap) > DELTA}
        for name, v in (("R_top_family_shown", r_top), ("S_top_family_shown", s_top), ("gate_rate", gate)):
            p1, p0 = v[g1].mean(), v[g0].mean()
            res[name] = {"shares": [p1, p0], "n_per_group": prop_n(p1, p0)}
        out16[c] = res
    n16 = max(r[k]["n_per_group"] for r in out16.values() for k in r if isinstance(r[k], dict))

    gate_all = gate.mean()
    out15 = {}
    for d in (0.20, 0.30, 0.50):
        n_arm = math.ceil(2 * (Z[0.975] + Z[0.80]) ** 2 / d**2) + 1
        out15[f"d={d}"] = {"n_per_arm": n_arm, "screen_total": math.ceil(2 * n_arm / gate_all)}
    out17 = {f"dz={d}": math.ceil(((Z[0.975] + Z[0.80]) / d) ** 2 + Z[0.975] ** 2 / 2) for d in (0.20, 0.30, 0.50)}

    return rnd({
        "meta": {"seed": seed, "quick": quick, "n_adults": len(df), "B": B, "form": form,
                 "runtime_s": round(time.time() - t0, 1), "delta": DELTA, "half_width": HALF_W},
        "proxy_check": {"mean_r_short_full": float(np.mean([np.corrcoef(a, b)[0, 1] for a, b in
                                                            zip(short[:5000], full[:5000], strict=True)
                                                            if a.std() > 0 and b.std() > 0]))},
        "m16_fairness_audit": out16,
        "m16_recommended_n_per_group": n16,
        "m15_lost_user_trial": {"gate_rate_adults": gate_all, **out15},
        "m17_usability_paired_n": out17,
    })


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--quick", action="store_true", help="5,000 people, B = 200, for a smoke run")
    args = ap.parse_args()
    out = main(args.seed, args.quick)
    name = "e9_study_power_quick.json" if args.quick else "e9_study_power.json"
    (FINDINGS / name).write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps(out, indent=2))
