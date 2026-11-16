"""E5 — Recommendation stability under measurement noise (ceiling for the adaptive test, E4).

Run:  .venv/Scripts/python -I research/feasibility/e5_stability.py [--seed 42] [--quick]

Pre-registration and results: research/findings/e5_stability.md
Outputs: research/findings/e5_stability.json and e5_*.png
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))  # python -I does not add the script dir or PYTHONPATH
from career_compass import matching as M

FINDINGS = ROOT / "research" / "findings"
DATA_MAIN = ROOT / "data" / "processed" / "riasec_people.parquet"
DATA_INCL = ROOT / "data" / "processed" / "riasec_people_incl_shared_network.parquet"
E1_JSON = FINDINGS / "e1_data_audit.json"

SCALES = M.SCALES
METHODS = list(M.METHODS)
ITEMS = [f"{s}{i}" for s in SCALES for i in range(1, 9)]
AGE_BANDS = {"13-17": (13, 17), "18-24": (18, 24), "25+": (25, 200)}
DIFF_BINS = [(-np.inf, 1.0, "<1.0"), (1.0, 1.5, "1.0-1.5"), (1.5, 2.0, "1.5-2.0"), (2.0, 2.5, "2.0-2.5"),
             (2.5, np.inf, ">=2.5")]
KMAX = 20
METRICS = ["ov10", "ov5", "ov3", "top1", "tau20", "fam90", "fam90_jacc", "fam80", "holl1", "holl3set", "holl3exact"]


def rnd(x, k=4):
    if isinstance(x, dict):
        return {str(kk): rnd(v, k) for kk, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [rnd(v, k) for v in x]
    if isinstance(x, (np.floating, float)):
        return None if not np.isfinite(x) else round(float(x), k)
    if isinstance(x, np.integer):
        return int(x)
    if isinstance(x, np.ndarray):
        return rnd(x.tolist(), k)
    return x


# ----------------------------------------------------------------------------- helpers
def topk_from_scores(S: np.ndarray, k: int = KMAX) -> np.ndarray:
    m = S.shape[1]
    St = S - np.arange(m) * 1e-12  # same tie rule as matching.top_k_indices
    part = np.argpartition(-St, k - 1, axis=1)[:, :k]
    order = np.argsort(-np.take_along_axis(St, part, 1), axis=1, kind="stable")
    return np.take_along_axis(part, order, 1)


def overlap(A, B):
    return (A[:, :, None] == B[:, None, :]).any(2).mean(1)


def family_metrics(FA, FB):
    """Symmetric family hit rate and Jaccard of distinct-family sets for (n, 10) family-label arrays."""
    hitA = (FA[:, :, None] == FB[:, None, :]).any(2)
    hitB = (FB[:, :, None] == FA[:, None, :]).any(2)
    sym = 0.5 * (hitA.mean(1) + hitB.mean(1))
    k = FA.shape[1]
    low = np.tril(np.ones((k, k), dtype=bool), -1)  # j' < j
    firstA = ~((FA[:, :, None] == FA[:, None, :]) & low[None]).any(2)
    firstB = ~((FB[:, :, None] == FB[:, None, :]) & low[None]).any(2)
    inter = (firstA & hitA).sum(1)
    jac = inter / (firstA.sum(1) + firstB.sum(1) - inter)
    return sym, jac


def kendall_tau_b(x, y):
    i, j = np.triu_indices(x.shape[1], 1)
    sx = np.sign(x[:, i] - x[:, j])
    sy = np.sign(y[:, i] - y[:, j])
    n0 = len(i)
    den = np.sqrt((n0 - (sx == 0).sum(1)) * (n0 - (sy == 0).sum(1)))
    return np.divide((sx * sy).sum(1), den, out=np.full(len(x), np.nan), where=den > 0)


def holland(P):
    return np.argsort(-P, axis=1, kind="stable")[:, :3]  # ties broken in R-I-A-S-E-C order


def holland_agreement(HA, HB):
    return (HA[:, 0] == HB[:, 0]).astype(float), \
        (np.sort(HA, 1) == np.sort(HB, 1)).all(1).astype(float), \
        (HA == HB).all(1).astype(float)


def compare(T0, S0, T1, S1, fam90, fam80, H0, H1):
    """All metrics for one comparison (reference list T0/S0 vs other list T1/S1). Returns dict of (n,) arrays."""
    a10, b10 = T0[:, :10], T1[:, :10]
    sym90, jac90 = family_metrics(fam90[a10], fam90[b10])
    sym80, _ = family_metrics(fam80[a10], fam80[b10])
    t20 = T0[:, :KMAX]
    tau = kendall_tau_b(np.take_along_axis(S0, t20, 1), np.take_along_axis(S1, t20, 1))
    h1, h3s, h3e = holland_agreement(H0, H1)
    return {"ov10": overlap(a10, b10), "ov5": overlap(T0[:, :5], T1[:, :5]), "ov3": overlap(T0[:, :3], T1[:, :3]),
            "top1": (T0[:, 0] == T1[:, 0]).astype(float), "tau20": tau, "fam90": sym90, "fam90_jacc": jac90,
            "fam80": sym80, "holl1": h1, "holl3set": h3s, "holl3exact": h3e}


def item_bootstrap(Xc: np.ndarray, n_ans: np.ndarray, rng) -> np.ndarray:
    """Xc: (n, 6, 8) item values sorted so NaNs are last; n_ans: (n, 6) answered counts."""
    u = rng.random(Xc.shape)
    idx = np.floor(u * n_ans[:, :, None]).astype(int)
    return np.take_along_axis(Xc, idx, 2).mean(2)


def group_masks(df: pd.DataFrame, P: np.ndarray) -> dict:
    diff = P.max(1) - P.min(1)
    g = {"all": np.ones(len(P), bool), "differentiated_ge1.0": diff >= 1.0, "flat_lt1.0": diff < 1.0,
         "differentiated_ge1.5": diff >= 1.5, "low_elevation_lt2.0": P.mean(1) < 2.0}
    for lo, hi, lab in DIFF_BINS:
        g[f"diff_{lab}"] = (diff >= lo) & (diff < hi)
    gen = df["gender"].to_numpy()
    for code, name in ((1, "male"), (2, "female"), (3, "other_pooled_small_n")):
        g[f"gender_{name}"] = gen == code
    for band, (lo, hi) in AGE_BANDS.items():
        g[f"age_{band}"] = df["age"].between(lo, hi).to_numpy()
    for code, name in ((1, "male"), (2, "female")):
        for band, (lo, hi) in AGE_BANDS.items():
            g[f"{name}_{band}"] = (gen == code) & df["age"].between(lo, hi).to_numpy()
    tf = P.argmax(1)
    tied = np.isclose(P, P.max(1, keepdims=True)).sum(1) > 1
    for j, s in enumerate(SCALES):
        g[f"top_{s}"] = (tf == j) & ~tied
    g["top_tied"] = tied
    return g


def boot_mean_ci(x, rng, B):
    x = np.asarray(x)
    x = x[np.isfinite(x)]
    if len(x) < 2:
        return [float("nan"), float("nan")]
    means = x[rng.integers(0, len(x), (B, len(x)))].mean(1) if len(x) * B <= 5e7 else \
        np.array([x[rng.integers(0, len(x), len(x))].mean() for _ in range(B)])
    return [float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))]


def summarise(person_means: dict, groups: dict, rng, B, ci_groups=("all", "differentiated_ge1.0", "flat_lt1.0")):
    out = {}
    for gname, msk in groups.items():
        if msk.sum() == 0:
            continue
        d = {"n": int(msk.sum())}
        for met, v in person_means.items():
            d[met] = float(np.nanmean(v[msk]))
            if gname in ci_groups and met in ("ov10", "ov3", "fam90", "tau20", "holl3exact"):
                d[f"{met}_ci95"] = boot_mean_ci(v[msk], rng, B)
        out[gname] = d
    return out


# ----------------------------------------------------------------------------- core
def run_table(df: pd.DataFrame, sd: np.ndarray, alpha: np.ndarray, occ, fam90, fam80, n_rep: int, rng, B: int,
              label: str, extra_noise: bool = True) -> dict:
    X = df[ITEMS].to_numpy(dtype=float).reshape(len(df), 6, 8)
    P0 = np.nanmean(X, axis=2)
    assert np.allclose(P0, df[SCALES].to_numpy(dtype=float)), "item means do not reproduce scale scores"
    Xc = np.sort(X, axis=2)  # NaN last
    n_ans = (~np.isnan(X)).sum(2)
    sem = sd * np.sqrt(1 - alpha)
    n = len(P0)
    groups = group_masks(df, P0)
    H0 = holland(P0)
    ref = {}
    for mth in METHODS:
        S0 = M.score_matrix(P0, occ, mth)
        ref[mth] = (S0, topk_from_scores(S0))
    noise_models = {"reliability_sem": lambda: P0 + rng.normal(0, 1, P0.shape) * sem,
                    "item_bootstrap": lambda: item_bootstrap(Xc, n_ans, rng)}
    if extra_noise:
        noise_models["reliability_sem_clipped"] = lambda: np.clip(P0 + rng.normal(0, 1, P0.shape) * sem, 1, 5)
    res = {"n_people": n, "n_replicates": n_rep, "sem": dict(zip(SCALES, sem)), "sd": dict(zip(SCALES, sd)),
           "alpha": dict(zip(SCALES, alpha)), "holland_top_tie_rate": float(
               (np.isclose(P0, P0.max(1, keepdims=True)).sum(1) > 1).mean()), "noise": {}}
    person_level = {}
    for nm, gen in noise_models.items():
        reps = n_rep if nm != "reliability_sem_clipped" else max(5, n_rep // 2)
        prim = {mth: {k: np.zeros(n) for k in METRICS} for mth in METHODS}
        sec = {mth: {k: np.zeros(n) for k in METRICS} for mth in METHODS}
        n_sec = 0
        prev = None
        noise_diag = []
        t0 = time.time()
        for r in range(reps):
            Pr = gen()
            noise_diag.append(float(np.mean(np.abs(Pr - P0))))
            Hr = holland(Pr)
            cur = {}
            for mth in METHODS:
                Sr = M.score_matrix(Pr, occ, mth)
                Tr = topk_from_scores(Sr)
                cur[mth] = (Sr, Tr)
                c = compare(ref[mth][1], ref[mth][0], Tr, Sr, fam90, fam80, H0, Hr)
                for k in METRICS:
                    prim[mth][k] += np.nan_to_num(c[k], nan=0.0)
            if r % 2 == 1:
                for mth in METHODS:
                    c = compare(prev[0][mth][1], prev[0][mth][0], cur[mth][1], cur[mth][0], fam90, fam80, prev[1], Hr)
                    for k in METRICS:
                        sec[mth][k] += np.nan_to_num(c[k], nan=0.0)
                n_sec += 1
            prev = (cur, Hr)
        block = {"replicates": reps, "mean_abs_score_change": float(np.mean(noise_diag)),
                 "seconds": time.time() - t0, "primary_orig_vs_perturbed": {}, "secondary_replicate_pairs": {}}
        for mth in METHODS:
            pm = {k: v / reps for k, v in prim[mth].items()}
            sm = {k: v / max(n_sec, 1) for k, v in sec[mth].items()}
            block["primary_orig_vs_perturbed"][mth] = summarise(pm, groups, rng, B)
            block["secondary_replicate_pairs"][mth] = summarise(sm, {k: groups[k] for k in (
                "all", "differentiated_ge1.0", "flat_lt1.0")}, rng, B)
            person_level[(nm, mth)] = pm
        res["noise"][nm] = block
        p = block["primary_orig_vs_perturbed"]
        print(f"[{label}] {nm}: " + ", ".join(
            f"{m_}: ov10 {p[m_]['differentiated_ge1.0']['ov10']:.3f} fam {p[m_]['differentiated_ge1.0']['fam90']:.3f}"
            for m_ in METHODS) + f" ({block['seconds']:.0f}s)")

    # baselines (relative to each method's original top-10)
    base = {}
    m = len(occ)
    for mth in METHODS:
        T0 = ref[mth][1]
        rand_ov, rand_f90, rand_f80 = [], [], []
        for _ in range(10):
            R = np.stack([rng.choice(m, 10, replace=False) for _ in range(n)])
            rand_ov.append(overlap(T0[:, :10], R).mean())
            rand_f90.append(family_metrics(fam90[T0[:, :10]], fam90[R])[0].mean())
            rand_f80.append(family_metrics(fam80[T0[:, :10]], fam80[R])[0].mean())
        perm = rng.permutation(n)
        oth = T0[perm]
        f90o, _ = family_metrics(fam90[T0[:, :10]], fam90[oth[:, :10]])
        h1, h3s, h3e = holland_agreement(H0, H0[perm])
        base[mth] = {"random_top10": {"ov10": float(np.mean(rand_ov)), "fam90": float(np.mean(rand_f90)),
                                      "fam80": float(np.mean(rand_f80))},
                     "random_other_person": {"ov10": float(overlap(T0[:, :10], oth[:, :10]).mean()),
                                             "ov3": float(overlap(T0[:, :3], oth[:, :3]).mean()),
                                             "fam90": float(f90o.mean()), "holl1": float(h1.mean()),
                                             "holl3set": float(h3s.mean()), "holl3exact": float(h3e.mean())}}
    res["baselines"] = base
    res["_person_level"] = person_level
    res["_groups"] = groups
    res["_P0"] = P0
    return res


# ----------------------------------------------------------------------------- post hoc (exploratory)
def family_top_lists(S: np.ndarray, fam: np.ndarray, k: int) -> np.ndarray:
    """Top-k families per person; a family is scored by its best member's score."""
    order = np.argsort(fam, kind="stable")
    starts = np.r_[0, np.flatnonzero(np.diff(fam[order])) + 1]
    F = np.maximum.reduceat(S[:, order], starts, axis=1)  # (n, n_families); column = family id
    return topk_from_scores(F, k)


def posthoc(df, sd, alpha, occ, seed, n_rep, quick):
    """NOT pre-registered (exploratory).

    (1) Noise-scale curve: stability vs noise multiplier c (noise SD = c * SEM), mapped to the per-scale
        correlation between original and perturbed scores. A ceiling guide for E4.
    (2) Family granularity curve with chance levels.
    (3) Stability of a "top-3 families" display.
    """
    rng = np.random.default_rng(seed + 100)  # separate stream: pre-registered results are unaffected
    P0 = df[SCALES].to_numpy(dtype=float)
    diffm = (P0.max(1) - P0.min(1)) >= 1.0
    sem = sd * np.sqrt(1 - alpha)
    n = len(P0)
    out = {"note": "post hoc, exploratory; not part of the pre-registered success bar", "replicates": n_rep}
    r_grid = (0.5, 0.6, 0.7, 0.8, 0.85, 0.9, 0.95)
    fams = {r: M.occupation_families(occ, r) for r in r_grid}
    curve = {}
    for mth in ("pearson", "hexagon"):
        S0 = M.score_matrix(P0, occ, mth)
        T0 = topk_from_scores(S0)[:, :10]
        F0 = {r: family_top_lists(S0, fams[r], 3) for r in (0.8, 0.9)}
        rows = {}
        for c in ((0.5, 1.0) if quick else (0.25, 0.5, 0.75, 1.0, 1.5, 2.0)):
            acc = {"ov10": [], "fam90": [], "top3fam_r90": [], "top3fam_r80": [], "scale_r": [], "profile_r": []}
            for _ in range(n_rep):
                Pr = P0 + rng.normal(0, 1, P0.shape) * sem * c
                Sr = M.score_matrix(Pr, occ, mth)
                Tr = topk_from_scores(Sr)[:, :10]
                acc["ov10"].append(overlap(T0, Tr)[diffm].mean())
                acc["fam90"].append(family_metrics(fams[0.9][T0], fams[0.9][Tr])[0][diffm].mean())
                for r in (0.8, 0.9):
                    acc[f"top3fam_r{int(r * 100)}"].append(
                        overlap(F0[r], family_top_lists(Sr, fams[r], 3))[diffm].mean())
                acc["scale_r"].append(np.mean([np.corrcoef(P0[:, j], Pr[:, j])[0, 1] for j in range(6)]))
                a_, b_ = P0 - P0.mean(1, keepdims=True), Pr - Pr.mean(1, keepdims=True)
                with np.errstate(invalid="ignore", divide="ignore"):
                    pr = (a_ * b_).sum(1) / np.sqrt((a_**2).sum(1) * (b_**2).sum(1))
                acc["profile_r"].append(np.nanmedian(pr))
            rows[c] = {k: float(np.mean(v)) for k, v in acc.items()}
        curve[mth] = rows
    out["noise_scale_curve_differentiated"] = curve
    # family granularity at c = 1 (Pearson)
    S0 = M.score_matrix(P0, occ, "pearson")
    T0 = topk_from_scores(S0)[:, :10]
    gran = {r: {"obs": [], "chance": []} for r in r_grid}
    t3 = {r: {"obs": [], "chance": []} for r in r_grid}
    F0 = {r: family_top_lists(S0, fams[r], 3) for r in r_grid}
    m = len(occ)
    for _ in range(n_rep):
        Pr = P0 + rng.normal(0, 1, P0.shape) * sem
        Sr = M.score_matrix(Pr, occ, "pearson")
        Tr = topk_from_scores(Sr)[:, :10]
        R = np.stack([rng.choice(m, 10, replace=False) for _ in range(n)])
        for r in r_grid:
            f = fams[r]
            gran[r]["obs"].append(family_metrics(f[T0], f[Tr])[0][diffm].mean())
            gran[r]["chance"].append(family_metrics(f[T0], f[R])[0][diffm].mean())
            nf = f.max() + 1
            t3[r]["obs"].append(overlap(F0[r], family_top_lists(Sr, f, 3))[diffm].mean())
            Rf = np.stack([rng.choice(nf, 3, replace=False) for _ in range(n)])
            t3[r]["chance"].append(overlap(F0[r], Rf)[diffm].mean())
    gout = {}
    for r in r_grid:
        obs, ch = float(np.mean(gran[r]["obs"])), float(np.mean(gran[r]["chance"]))
        gout[str(r)] = {"n_families": int(fams[r].max() + 1), "fam_hit_top10": obs, "fam_hit_chance": ch,
                        "fam_hit_chance_corrected": (obs - ch) / (1 - ch),
                        "top3_families_overlap": float(np.mean(t3[r]["obs"])),
                        "top3_families_chance": float(np.mean(t3[r]["chance"]))}
    out["family_granularity_pearson_differentiated"] = gout
    return out


def posthoc_chart(ph, n):
    fig, axs = plt.subplots(1, 2, figsize=(12, 4.5))
    for mth, ls in (("pearson", "-"), ("hexagon", "--")):
        rows = ph["noise_scale_curve_differentiated"][mth]
        cs = list(rows)
        sr = [rows[c]["scale_r"] for c in cs]
        axs[0].plot(sr, [rows[c]["ov10"] for c in cs], "o" + ls, c="C0", label=f"{mth}: top-10 occupations")
        axs[0].plot(sr, [rows[c]["fam90"] for c in cs], "s" + ls, c="C1", label=f"{mth}: family hit (r>=.90)")
        axs[0].plot(sr, [rows[c]["top3fam_r90"] for c in cs], "^" + ls, c="C2",
                    label=f"{mth}: top-3 families (r>=.90)")
        if mth == "pearson":
            for c, x, y in zip(cs, sr, [rows[c]["ov10"] for c in cs]):
                axs[0].annotate(f"{c} x SEM", (x, y), fontsize=7, xytext=(3, -10), textcoords="offset points")
    axs[0].axhline(0.7, c="grey", ls=":", lw=0.8)
    axs[0].set_xlabel("mean per-scale r(original, perturbed) across people")
    axs[0].set_ylabel("mean agreement (differentiated profiles)")
    axs[0].set_title("Stability vs noise size (post hoc; E4 ceiling guide)", fontsize=9)
    axs[0].legend(fontsize=7)
    g = ph["family_granularity_pearson_differentiated"]
    nf = [g[r]["n_families"] for r in g]
    axs[1].plot(nf, [g[r]["fam_hit_top10"] for r in g], "o-", label="family hit rate, top-10")
    axs[1].plot(nf, [g[r]["fam_hit_chance"] for r in g], "o:", label="... chance (random 10)")
    axs[1].plot(nf, [g[r]["top3_families_overlap"] for r in g], "s-", label="top-3 families overlap")
    axs[1].plot(nf, [g[r]["top3_families_chance"] for r in g], "s:", label="... chance")
    for r, x in zip(g, nf):
        axs[1].annotate(f"r>={r}", (x, g[r]["fam_hit_top10"]), fontsize=7, xytext=(3, 3), textcoords="offset points")
    axs[1].set_xscale("log")
    axs[1].set_xlabel("number of families (complete linkage, r_min)")
    axs[1].set_ylabel("agreement, original vs 1 x SEM perturbed")
    axs[1].set_title("Family granularity (Pearson, post hoc)", fontsize=9)
    axs[1].legend(fontsize=7)
    fig.suptitle(f"E5 post hoc: differentiated profiles, n = {n:,} sample", fontsize=9)
    fig.tight_layout()
    fig.savefig(FINDINGS / "e5_posthoc_curves.png", dpi=130)
    plt.close(fig)


def main(seed: int, quick: bool) -> dict:
    rng = np.random.default_rng(seed)
    t_start = time.time()
    n_sample, n_rep, B = (1000, 6, 100) if quick else (5000, 50, 1000)
    occ = M.load_occupations()
    fam90 = M.occupation_families(occ, 0.90)
    fam80 = M.occupation_families(occ, 0.80)
    e1 = json.loads(E1_JSON.read_text())
    alpha_main = np.array([e1["reliability"][s]["alpha"] for s in SCALES])
    alpha_incl = np.array([e1["reliability_incl_shared"][s] for s in SCALES])

    full = pd.read_parquet(DATA_MAIN, columns=ITEMS + SCALES + ["gender", "age"])
    sd_main = full[SCALES].std(ddof=1).to_numpy()
    df = full.sample(n_sample, random_state=seed).reset_index(drop=True)
    out = {"seed": seed, "quick": quick, "n_families_r90": int(fam90.max() + 1), "n_families_r80": int(fam80.max() + 1),
           "methods": METHODS}
    main_res = run_table(df, sd_main, alpha_main, occ, fam90, fam80, n_rep, rng, B, "main")

    # success bar
    bar = {}
    for mth in METHODS:
        d = main_res["noise"]["reliability_sem"]["primary_orig_vs_perturbed"][mth]["differentiated_ge1.0"]
        ov, fh = d["ov10"], d["fam90"]
        v = "proven" if (ov >= .60 or fh >= .80) else ("promising" if (ov >= .45 or fh >= .65) else "not viable")
        bar[mth] = {"ov10": ov, "ov10_ci95": d["ov10_ci95"], "fam90": fh, "fam90_ci95": d["fam90_ci95"], "verdict": v}
    out["success_bar"] = bar

    # correlation of person-level stability with differentiation (pearson, reliability noise)
    P0 = main_res["_P0"]
    diff = P0.max(1) - P0.min(1)
    pl = main_res["_person_level"]
    out["spearman_ov10_vs_differentiation"] = {
        mth: float(pd.Series(pl[("reliability_sem", mth)]["ov10"]).corr(pd.Series(diff), method="spearman"))
        for mth in METHODS}
    charts(main_res, diff, n_sample)
    out["main"] = {k: v for k, v in main_res.items() if not k.startswith("_")}

    if not quick:
        inc = pd.read_parquet(DATA_INCL, columns=ITEMS + SCALES + ["gender", "age"])
        sd_inc = inc[SCALES].std(ddof=1).to_numpy()
        dfi = inc.sample(n_sample, random_state=seed + 1).reset_index(drop=True)
        ri = run_table(dfi, sd_inc, alpha_incl, occ, fam90, fam80, 20, rng, 200, "incl_shared", extra_noise=False)
        rob = {"n_people": ri["n_people"], "replicates": 20}
        for nm in ("reliability_sem", "item_bootstrap"):
            rob[nm] = {mth: {g: {k: ri["noise"][nm]["primary_orig_vs_perturbed"][mth][g][k]
                                 for k in ("n", "ov10", "fam90", "ov3", "holl3exact")}
                             for g in ("all", "differentiated_ge1.0", "flat_lt1.0", "age_13-17")}
                       for mth in METHODS}
        out["robustness_incl_shared_network"] = rob
    ph = posthoc(df, sd_main, alpha_main, occ, seed, 4 if quick else 20, quick)
    posthoc_chart(ph, n_sample)
    out["posthoc_exploratory"] = ph
    out["seconds_total"] = time.time() - t_start
    return out


def charts(res, diff, n):
    blk = res["noise"]["reliability_sem"]["primary_orig_vs_perturbed"]
    base = res["baselines"]
    labs = [b[2] for b in DIFF_BINS]
    fig, axs = plt.subplots(1, 2, figsize=(12, 4.5), sharey=True)
    for ax, met, title in ((axs[0], "ov10", "occupation-level top-10 overlap"),
                           (axs[1], "fam90", "family-level hit rate (r >= .90 families)")):
        for mth in METHODS:
            ax.plot(labs, [blk[mth][f"diff_{lab}"][met] for lab in labs], marker="o", label=mth)
        ax.axhline(np.mean([base[m_]["random_top10"][met] for m_ in METHODS]), c="grey", ls=":",
                   label="random top-10 (chance)")
        ax.axhline(0.60 if met == "ov10" else 0.80, c="green", ls="--", lw=0.8, label="success bar")
        ax.set_xlabel("profile differentiation (max - min scale mean, 1-5)")
        ax.set_title(title, fontsize=9)
        ax.set_ylim(0, 1)
    axs[0].set_ylabel("mean agreement, original vs perturbed")
    axs[1].legend(fontsize=7)
    cnt = [int(res["_groups"][f"diff_{lab}"].sum()) for lab in labs]
    fig.suptitle(f"E5: stability under reliability (SEM) noise, n = {n:,} people x {res['n_replicates']} replicates; "
                 f"bin n = {cnt}", fontsize=9)
    fig.tight_layout()
    fig.savefig(FINDINGS / "e5_overlap_by_differentiation.png", dpi=130)
    plt.close(fig)

    fig, axs = plt.subplots(1, len(METHODS), figsize=(15, 3.6), sharey=True)
    for ax, mth in zip(axs, METHODS):
        for nm, c in (("reliability_sem", "C0"), ("item_bootstrap", "C1")):
            v = res["_person_level"][(nm, mth)]["ov10"]
            ax.hist(v, bins=np.linspace(0, 1, 21), alpha=0.55, color=c, label=nm)
        ax.set_title(mth, fontsize=9)
        ax.set_xlabel("person mean top-10 overlap")
    axs[0].set_ylabel("people")
    axs[0].legend(fontsize=7)
    fig.suptitle(f"E5: distribution of per-person top-10 overlap (original vs perturbed), n = {n:,}", fontsize=9)
    fig.tight_layout()
    fig.savefig(FINDINGS / "e5_overlap_distribution.png", dpi=130)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(9, 4))
    cells = [f"{g}_{b}" for g in ("male", "female") for b in AGE_BANDS]
    x = np.arange(len(cells))
    w = 0.2
    for i, mth in enumerate(METHODS):
        ax.bar(x + (i - 1.5) * w, [blk[mth][c]["ov10"] for c in cells], w, label=mth)
    ax.set_xticks(x, [f"{c}\n(n={blk['pearson'][c]['n']})" for c in cells], fontsize=8)
    ax.set_ylabel("mean top-10 overlap")
    ax.set_ylim(0, 1)
    ax.legend(fontsize=7)
    ax.set_title(f"E5: top-10 stability by gender x age (reliability noise), n = {n:,}", fontsize=9)
    fig.tight_layout()
    fig.savefig(FINDINGS / "e5_subgroups.png", dpi=130)
    plt.close(fig)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--quick", action="store_true", help="1,000 people x 6 replicates smoke run")
    a = ap.parse_args()
    FINDINGS.mkdir(parents=True, exist_ok=True)
    out = rnd(main(a.seed, a.quick))
    name = "e5_stability_quick.json" if a.quick else "e5_stability.json"
    (FINDINGS / name).write_text(json.dumps(out, indent=2))
    print(json.dumps(out["success_bar"], indent=2))
