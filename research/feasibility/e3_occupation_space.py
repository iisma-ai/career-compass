"""E3 — Occupation space: distribution, effective resolution and per-person coverage.

Run:  .venv/Scripts/python -I research/feasibility/e3_occupation_space.py [--seed 42] [--quick]

Pre-registration and results: research/findings/e3_occupation_space.md
Outputs: research/findings/e3_occupation_space.json, e3_families.csv and e3_*.png
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
from scipy import stats
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import connected_components

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))  # python -I does not add the script dir or PYTHONPATH
from career_compass import matching as M

FINDINGS = ROOT / "research" / "findings"
DATA_MAIN = ROOT / "data" / "processed" / "riasec_people.parquet"
DATA_INCL = ROOT / "data" / "processed" / "riasec_people_incl_shared_network.parquet"
RELATED = ROOT / "data" / "raw" / "onet_31_0" / "db_31_0_csv" / "related_occupations.csv"

SCALES = M.SCALES
METHODS = list(M.METHODS)
ANGLES = np.deg2rad(np.arange(6) * 60.0)
AGE_BANDS = {"13-17": (13, 17), "18-24": (18, 24), "25+": (25, 200)}
GENDER = {1: "male", 2: "female", 3: "other"}
FAMILY_R = (0.80, 0.85, 0.90, 0.95)
K = 10


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


def gini(counts) -> float:
    x = np.sort(np.asarray(counts, dtype=float))
    n = len(x)
    if x.sum() == 0:
        return float("nan")
    return float((2 * np.arange(1, n + 1) - n - 1).dot(x) / (n * x.sum()))


def prediger(profiles: np.ndarray) -> np.ndarray:
    c = profiles - profiles.mean(1, keepdims=True)
    return np.c_[c @ np.cos(ANGLES), c @ np.sin(ANGLES)]


def boot_median_ci(x, rng, B):
    x = np.asarray(x)
    if len(x) == 0:
        return [float("nan")] * 2
    meds = [np.median(x[rng.integers(0, len(x), len(x))]) for _ in range(B)]
    return [float(np.percentile(meds, 2.5)), float(np.percentile(meds, 97.5))]


def top_type(P: np.ndarray):
    """Unique top type index, or -1 if tied (exact tie at the maximum)."""
    mx = P.max(1, keepdims=True)
    tied = np.isclose(P, mx).sum(1) > 1
    t = P.argmax(1)
    return np.where(tied, -1, t), t  # (unique-or-tied, first-argmax)


def pearson_of_picks(P, O, idx):
    pv = M._unit_rows(M._centre_rows(P))
    ov = M._unit_rows(M._centre_rows(O))
    return np.einsum("nd,nkd->nk", pv, ov[idx])


def pool_sizes(P, occ, thresholds=(0.70, 0.80), chunk=10000):
    out = {t: np.empty(len(P), dtype=np.int32) for t in thresholds}
    for a in range(0, len(P), chunk):
        s = M.score_matrix(P[a:a + chunk], occ, "pearson")
        for t in thresholds:
            out[t][a:a + chunk] = (s >= t).sum(1)
    return out


def exposure_stats(idx, m, n_people):
    cnt = np.bincount(idx.ravel(), minlength=m)
    srt = np.sort(cnt)[::-1]
    return cnt, {
        "reach_ge1": float((cnt >= 1).mean()),
        "reach_ge_0.1pct": float((cnt >= max(1, 0.001 * n_people)).mean()),
        "n_dead": int((cnt == 0).sum()),
        "gini": gini(cnt),
        "share_of_exposure_top_10pct_occ": float(srt[: int(np.ceil(0.1 * m))].sum() / srt.sum()),
    }


def mmr_rerank(cand_idx, cand_rel, simO, lam=0.7, k=K):
    """Maximal marginal relevance over candidate lists (vectorised over people)."""
    n, c = cand_idx.shape
    chosen = np.zeros((n, k), dtype=np.int32)
    taken = np.zeros((n, c), dtype=bool)
    maxsim = np.full((n, c), -np.inf)
    rows = np.arange(n)
    for j in range(k):
        crit = lam * cand_rel - (1 - lam) * np.where(np.isfinite(maxsim), maxsim, 0.0)
        crit[taken] = -np.inf
        pick = crit.argmax(1)
        taken[rows, pick] = True
        chosen[:, j] = cand_idx[rows, pick]
        s_new = simO[cand_idx, chosen[:, j][:, None]]
        maxsim = np.maximum(maxsim, s_new)
    return chosen


def family_cap_rerank(cand_idx, fam, cap=2, k=K):
    n, c = cand_idx.shape
    out = np.empty((n, k), dtype=np.int32)
    for i in range(n):
        seen, sel = {}, []
        for o in cand_idx[i]:
            f = fam[o]
            if seen.get(f, 0) < cap:
                sel.append(o)
                seen[f] = seen.get(f, 0) + 1
                if len(sel) == k:
                    break
        if len(sel) < k:  # fall back to uncapped order
            sel += [o for o in cand_idx[i] if o not in sel][: k - len(sel)]
        out[i] = sel
    return out


def coverage_block(P, occ, O, groups, rng, B_med, B_reach, label):
    """Q3 core: per method top-10s, quality, exposure. Returns (results, per-method top-10 arrays)."""
    m = len(occ)
    n = len(P)
    tt_unique = groups["top_type_unique"]
    res, tops = {}, {}
    occ_top = O.argmax(1)
    for method in METHODS:
        t0 = time.time()
        idx, own = M.top_k_indices(P, occ, K, method, return_scores=True)
        r = pearson_of_picks(P, O, idx)
        cnt, ex = exposure_stats(idx, m, n)
        # Gini: bootstrap CI. Reach (">= 1 person") is not bootstrappable (resampling with replacement
        # drops ~37% of unique people), so report reach as a function of the number of people instead
        # (subsamples without replacement, 5 repeats).
        bs_gini = []
        for _ in range(B_reach):
            sel = rng.integers(0, n, n)
            bs_gini.append(gini(np.bincount(idx[sel].ravel(), minlength=m)))
        ex["gini_ci95"] = [float(np.percentile(bs_gini, 2.5)), float(np.percentile(bs_gini, 97.5))]
        curve = {}
        for nn in (100, 1000, 5000, 20000, 40000):
            if nn < n:
                vals = [(np.bincount(idx[rng.choice(n, nn, replace=False)].ravel(), minlength=m) >= 1).mean()
                        for _ in range(5)]
                curve[nn] = [float(np.min(vals)), float(np.max(vals))]
        curve[n] = [ex["reach_ge1"], ex["reach_ge1"]]
        ex["reach_ge1_vs_n_people_minmax"] = curve
        d = {
            "median_top1_r": float(np.median(r[:, 0])),
            "median_top1_r_ci95": boot_median_ci(r[:, 0], rng, B_med),
            "iqr_top1_r": [float(np.percentile(r[:, 0], 25)), float(np.percentile(r[:, 0], 75))],
            "median_10th_r": float(np.median(r[:, -1])),
            "median_own_score_top1": float(np.median(own[:, 0])),
            "median_own_score_10th": float(np.median(own[:, -1])),
            "median_mean_top10_r": float(np.median(r.mean(1))),
            "share_top1_r_lt_.60": float((r[:, 0] < 0.6).mean()),
            "exposure": ex,
            "exposure_share_by_occ_top_letter": {
                SCALES[j]: float(cnt[occ_top == j].sum() / cnt.sum()) for j in range(6)},
        }
        by_type = {}
        for j, name in list(enumerate(SCALES)) + [(-1, "tied")]:
            msk = tt_unique == j
            if msk.sum() == 0:
                continue
            gi = idx[msk]
            by_type[name] = {
                "n": int(msk.sum()),
                "median_top1_r": float(np.median(r[msk, 0])),
                "median_top1_r_ci95": boot_median_ci(r[msk, 0], rng, max(100, B_med // 5)),
                "median_10th_r": float(np.median(r[msk, -1])),
                "p10_p90_top1_r": [float(np.percentile(r[msk, 0], 10)), float(np.percentile(r[msk, 0], 90))],
                "p10_p90_10th_r": [float(np.percentile(r[msk, -1], 10)), float(np.percentile(r[msk, -1], 90))],
                "group_reach_n_occ": len(np.unique(gi)),
                "share_top10_same_top_letter": float((occ_top[gi] == j).mean()) if j >= 0 else None,
            }
        d["by_top_type"] = by_type
        d["min_group_median_top1_r"] = float(min(v["median_top1_r"] for kk, v in by_type.items() if kk != "tied"))
        sub = {}
        for gname, gmask in groups["subgroups"].items():
            if gmask.sum() < 50:
                continue
            gi = idx[gmask]
            sub[gname] = {
                "n": int(gmask.sum()),
                "median_top1_r": float(np.median(r[gmask, 0])),
                "median_mean_top10_r": float(np.median(r[gmask].mean(1))),
                "share_top10_R_top_occ": float((occ_top[gi] == 0).mean()),
                "share_top10_S_top_occ": float((occ_top[gi] == 3).mean()),
                "share_top10_A_top_occ": float((occ_top[gi] == 2).mean()),
                "mean_job_zone_top10": float(np.nanmean(occ["job_zone"].to_numpy(dtype=float)[gi])),
            }
        d["by_subgroup"] = sub
        d["seconds"] = time.time() - t0
        res[method] = d
        tops[method] = (idx, r, cnt)
        print(f"[{label}] {method}: median top1 r {d['median_top1_r']:.3f}, reach {ex['reach_ge1']:.3f}, "
              f"gini {ex['gini']:.3f}, min group {d['min_group_median_top1_r']:.3f} ({d['seconds']:.1f}s)")
    return res, tops


def baselines(P, O, groups, rng, m, n):
    occ_top = O.argmax(1)
    out = {}
    idx = np.stack([rng.choice(m, K, replace=False) for _ in range(n)])
    r = pearson_of_picks(P, O, idx)
    _, ex = exposure_stats(idx, m, n)
    out["random_top10"] = {"median_top1_r": float(np.median(r[:, 0])),
                           "median_best_of_10_r": float(np.median(r.max(1))),
                           "median_mean_top10_r": float(np.median(r.mean(1))), "exposure": ex}
    # Holland first-letter: 10 random occupations with the person's (first-argmax) top letter
    pools = {j: np.flatnonzero(occ_top == j) for j in range(6)}
    tf = groups["top_type_first"]
    idx = np.empty((n, K), dtype=np.int64)
    for j in range(6):
        msk = np.flatnonzero(tf == j)
        pool = pools[j]
        for i in msk:
            idx[i] = rng.choice(pool, K, replace=len(pool) < K)
    r = pearson_of_picks(P, O, idx)
    _, ex = exposure_stats(idx, m, n)
    out["holland_first_letter_random10"] = {
        "median_best_of_10_r": float(np.median(r.max(1))),
        "median_mean_top10_r": float(np.median(r.mean(1))), "exposure": ex,
        "pool_size_by_letter": {SCALES[j]: len(pools[j]) for j in range(6)}}
    return out


def make_groups(df: pd.DataFrame, P: np.ndarray):
    tu, tf = top_type(P)
    sub = {}
    for code, name in GENDER.items():
        sub[f"gender_{name}"] = (df["gender"] == code).to_numpy()
    for band, (lo, hi) in AGE_BANDS.items():
        sub[f"age_{band}"] = df["age"].between(lo, hi).to_numpy()
    for code, name in ((1, "male"), (2, "female")):
        for band, (lo, hi) in AGE_BANDS.items():
            sub[f"{name}_{band}"] = ((df["gender"] == code) & df["age"].between(lo, hi)).to_numpy()
    diff = P.max(1) - P.min(1)
    sub["flat_diff_lt1"] = diff < 1.0
    sub["differentiated_diff_ge1"] = diff >= 1.0
    sub["low_elevation_lt2"] = P.mean(1) < 2.0
    return {"top_type_unique": tu, "top_type_first": tf, "subgroups": sub}


def main(seed: int, quick: bool) -> dict:
    rng = np.random.default_rng(seed)
    t_start = time.time()
    B_med, B_reach = (50, 20) if quick else (1000, 200)
    occ = M.load_occupations(extra=True)
    O = occ[SCALES].to_numpy(dtype=float)
    m = len(occ)
    res = {"seed": seed, "quick": quick, "n_occupations": m, "methods": METHODS, "hex_weights": M.HEX_WEIGHTS}

    # ------------------------------------------------------------------ Q1 distribution
    mx = O.max(1, keepdims=True)
    tied_top = np.isclose(O, mx).sum(1) > 1
    order = np.argsort(-O, axis=1, kind="stable")
    top1 = np.array(SCALES)[order[:, 0]]
    code2 = np.char.add(np.array(SCALES)[order[:, 0]], np.array(SCALES)[order[:, 1]])
    q1 = {
        "top_letter_counts": pd.Series(top1).value_counts().reindex(SCALES).fillna(0).astype(int).to_dict(),
        "n_tied_top_letter": int(tied_top.sum()),
        "top2_code_counts_top20": pd.Series(code2).value_counts().head(20).to_dict(),
        "n_distinct_top2_codes": len(set(code2)),
        "n_distinct_top3_codes_holland_code_col": int(occ["holland_code"].nunique()),
        "share_values_clipped_1_or_7": float(np.isin(O, [1.0, 7.0]).mean()),
        "share_occ_with_any_clipped": float(np.isin(O, [1.0, 7.0]).any(1).mean()),
        "differentiation_median": float(np.median(O.max(1) - O.min(1))),
    }
    xy_o = prediger(O)
    Oc = O - O.mean(1, keepdims=True)
    ev = np.linalg.eigvalsh(np.cov(Oc.T))[::-1][:5]  # centred profiles live in 5-D
    q1["pca_centred_explained"] = (ev / ev.sum()).tolist()
    q1["pca_participation_ratio"] = float(ev.sum() ** 2 / (ev**2).sum())
    q1["prediger_radius_share_first_harmonic"] = float(
        (np.linalg.norm(xy_o, axis=1) ** 2).sum() / (3 * (Oc**2).sum()))
    res["q1_distribution"] = q1

    # ------------------------------------------------------------------ Q2 resolution
    ov = M._unit_rows(M._centre_rows(O))
    Rmat = ov @ ov.T
    iu = np.triu_indices(m, 1)
    rpairs = Rmat[iu]
    q2 = {"n_pairs": len(rpairs), "pair_r_median": float(np.median(rpairs)),
          "pair_r_quantiles": {q: float(np.quantile(rpairs, q)) for q in (0.05, 0.25, 0.75, 0.95, 0.99)}}
    for thr in (0.95, 0.98):
        A = (Rmat > thr) & ~np.eye(m, dtype=bool)
        ncomp, _ = connected_components(csr_matrix(A), directed=False)
        q2[f"r_gt_{thr}"] = {"n_pairs": int((rpairs > thr).sum()),
                             "n_occ_with_twin": int(A.any(1).sum()),
                             "n_connected_components": int(ncomp)}
    fams = {r: M.occupation_families(occ, r) for r in FAMILY_R}
    fam_curve = {}
    for r_min in np.round(np.arange(0.5, 0.991, 0.01), 2):
        fam_curve[float(r_min)] = int(M.occupation_families(occ, float(r_min)).max() + 1)
    q2["n_families_curve"] = fam_curve
    q2["families"] = {}
    for r, f in fams.items():
        sizes = np.bincount(f)
        q2["families"][str(r)] = {"n_families": len(sizes), "n_singletons": int((sizes == 1).sum()),
                                  "median_size": float(np.median(sizes)), "max_size": int(sizes.max()),
                                  "share_occ_in_families_ge5": float(sizes[f][sizes[f] >= 5].size / m)}
    # family labels: most central member (max mean r to the other members)
    f90 = fams[0.90]
    fam_label, fam_letter = {}, {}
    for fid in range(f90.max() + 1):
        mem = np.flatnonzero(f90 == fid)
        cen = mem[np.argmax(Rmat[np.ix_(mem, mem)].mean(1))]
        fam_label[fid] = occ.title.iloc[cen]
        fam_letter[fid] = SCALES[int(O[mem].mean(0).argmax())]
    sizes = np.bincount(f90)
    big = np.argsort(-sizes, kind="stable")[:15]
    q2["largest_families_r90"] = [{"family": int(b), "size": int(sizes[b]), "central_member": fam_label[b],
                                   "top_letter_of_mean": fam_letter[b]} for b in big]
    q2["families_r90_by_top_letter"] = pd.Series([fam_letter[i] for i in range(len(sizes))]).value_counts().to_dict()
    fam_df = occ[["code", "title"]].copy()
    for r, f in fams.items():
        fam_df[f"family_r{int(round(r * 100))}"] = f
    fam_df["family_r90_label"] = [fam_label[x] for x in f90]
    fam_df.to_csv(FINDINGS / "e3_families.csv", index=False)
    # related occupations (read-only)
    rel = pd.read_csv(RELATED, dtype=str)
    pos = {c: i for i, c in enumerate(occ.code)}
    rel = rel[rel["O*NET-SOC Code"].isin(pos) & rel["Related O*NET-SOC Code"].isin(pos)]
    a = rel["O*NET-SOC Code"].map(pos).to_numpy()
    b = rel["Related O*NET-SOC Code"].map(pos).to_numpy()
    rr = Rmat[a, b]
    chance_same = float(((sizes * (sizes - 1)).sum()) / (m * (m - 1)))
    q2["related_occupations"] = {
        "n_pairs_both_rated": len(rr),
        "tiers": rel["Relatedness Tier"].value_counts().to_dict(),
        "mean_profile_r_related": float(rr.mean()),
        "mean_profile_r_all_pairs": float(rpairs.mean()),
        "mean_r_by_tier": {t: float(rr[(rel["Relatedness Tier"] == t).to_numpy()].mean())
                           for t in rel["Relatedness Tier"].unique()},
        "share_related_same_family_r90": float((f90[a] == f90[b]).mean()),
        "chance_same_family_r90": chance_same,
        "share_related_r_lt_.5": float((rr < 0.5).mean()),
    }
    res["q2_resolution"] = q2
    print(f"Q2: families r>=.90: {f90.max() + 1}; pairs r>.95: {q2['r_gt_0.95']['n_pairs']}")

    # ------------------------------------------------------------------ Q4 correlates
    jz = occ["job_zone"].to_numpy(dtype=float)
    diffO = O.max(1) - O.min(1)
    q4 = {"job_zone_counts": occ["job_zone"].value_counts().sort_index().to_dict(), "kruskal_by_job_zone": {}}
    feats = {s: Oc[:, j] for j, s in enumerate(SCALES)}
    feats["differentiation"] = diffO
    feats["prediger_x_things_people"] = xy_o[:, 0]
    feats["prediger_y_ideas_data"] = xy_o[:, 1]
    for name, v in feats.items():
        gs = [v[jz == z] for z in (2, 3, 4, 5)]
        H, p = stats.kruskal(*gs)
        q4["kruskal_by_job_zone"][name] = {"H": float(H), "p": float(p), "eps2": float(H / (m - 1)),
                                           "median_by_zone": {int(z): float(np.median(g)) for z, g in zip((2, 3, 4, 5), gs)}}
    ct = pd.crosstab(occ["job_zone"], top1)
    chi2, p, dof, _ = stats.chi2_contingency(ct)
    q4["top_letter_x_job_zone"] = {"table": {int(k): v for k, v in ct.T.to_dict().items()}, "chi2": float(chi2),
                                   "p": float(p), "cramers_v": float(np.sqrt(chi2 / (m * (min(ct.shape) - 1))))}
    ml = (occ["oi_domain_source"] == "Machine Learning").to_numpy()
    q4["domain_source"] = {"n_ML_only": int(ml.sum()), "n_ML_expert": int((~ml).sum()), "mannwhitney": {}}
    for name, v in feats.items():
        U, p = stats.mannwhitneyu(v[ml], v[~ml])
        q4["domain_source"]["mannwhitney"][name] = {
            "p": float(p), "rank_biserial": float(2 * U / (ml.sum() * (~ml).sum()) - 1),
            "median_ML": float(np.median(v[ml])), "median_MLexpert": float(np.median(v[~ml]))}
    ct2 = pd.crosstab(ml, top1)
    chi2, p, _, _ = stats.chi2_contingency(ct2)
    q4["domain_source"]["top_letter_chi2"] = {"chi2": float(chi2), "p": float(p),
                                              "cramers_v": float(np.sqrt(chi2 / (m * (min(ct2.shape) - 1)))),
                                              "table": {str(k): v for k, v in ct2.T.to_dict().items()}}
    q4["domain_source"]["ml_only_job_zone_counts"] = occ.loc[ml, "job_zone"].value_counts().sort_index().to_dict()
    q4["domain_source"]["ml_only_examples"] = occ.loc[ml, "title"].head(12).tolist()
    res["q4_correlates"] = q4

    # ------------------------------------------------------------------ Q3 coverage (main)
    df = pd.read_parquet(DATA_MAIN, columns=SCALES + ["gender", "age"])
    if quick:
        df = df.sample(8000, random_state=seed).reset_index(drop=True)
    P = df[SCALES].to_numpy(dtype=float)
    n = len(P)
    groups = make_groups(df, P)
    xy_p = prediger(P)
    q3 = {"n_people": n, "n_exactly_flat_profiles": int(np.isclose(P.max(1), P.min(1)).sum()),
          "people_top_type_unique_counts": {(SCALES[j] if j >= 0 else "tied"): int((groups["top_type_unique"] == j).sum())
                                            for j in list(range(6)) + [-1]}}
    pools = pool_sizes(P, occ)
    q3["pool_size"] = {}
    for t, v in pools.items():
        d = {"median": float(np.median(v)), "share_zero": float((v == 0).mean()), "by_top_type": {}}
        for j, name in list(enumerate(SCALES)) + [(-1, "tied")]:
            msk = groups["top_type_unique"] == j
            d["by_top_type"][name] = {"median": float(np.median(v[msk])), "share_zero": float((v[msk] == 0).mean()),
                                      "p10": float(np.percentile(v[msk], 10))}
        q3["pool_size"][str(t)] = d
    cov, tops = coverage_block(P, occ, O, groups, rng, B_med, B_reach, "main")
    q3["methods"] = cov
    q3["baselines"] = baselines(P, O, groups, rng, m, n)
    # agreement between methods (top-10 overlap with Pearson)
    q3["overlap_with_pearson_top10"] = {mm: float(M.top_k_overlap_rows(tops[mm][0], tops["pearson"][0]).mean())
                                        for mm in METHODS}

    # exploratory re-ranking of Pearson
    cand_idx, cand_rel = M.top_k_indices(P, occ, 50, "pearson", return_scores=True)
    rr_out = {}
    capped = family_cap_rerank(cand_idx, f90, cap=2)
    mmr = np.vstack([mmr_rerank(cand_idx[a:a + 4000], cand_rel[a:a + 4000], Rmat)
                     for a in range(0, n, 4000)])
    for name, idx in (("pearson_family_cap2", capped), ("pearson_mmr_0.7", mmr)):
        r = pearson_of_picks(P, O, idx)
        _, ex = exposure_stats(idx, m, n)
        rr_out[name] = {"median_mean_top10_r": float(np.median(r.mean(1))),
                        "median_top1_r": float(np.median(r[:, 0])), "exposure": ex,
                        "mean_distinct_families_r90_in_top10": float(np.mean([len(set(f90[row])) for row in idx])),
                        "overlap_with_plain_pearson": float(M.top_k_overlap_rows(idx, tops["pearson"][0]).mean())}
    rr_out["pearson_plain"] = {"median_mean_top10_r": cov["pearson"]["median_mean_top10_r"],
                               "mean_distinct_families_r90_in_top10": float(np.mean([len(set(f90[row])) for row in tops["pearson"][0]])),
                               "exposure": cov["pearson"]["exposure"]}
    q3["exploratory_reranking"] = rr_out
    # most-exposed occupations and dead examples (Pearson)
    cntP = tops["pearson"][2]
    q3["pearson_most_exposed"] = [{"title": occ.title.iloc[i], "share_people": float(cntP[i] / n)}
                                  for i in np.argsort(-cntP)[:10]]
    dead = np.flatnonzero(cntP == 0)
    q3["pearson_dead_by_top_letter"] = pd.Series(top1[dead]).value_counts().reindex(SCALES).fillna(0).astype(int).to_dict()
    q3["pearson_dead_by_job_zone"] = occ.loc[dead, "job_zone"].value_counts().sort_index().to_dict()
    q3["pearson_reach_by_occ_top_letter"] = {s: float((cntP[top1 == s] > 0).mean()) for s in SCALES}
    res["q3_coverage"] = q3

    # ------------------------------------------------------------------ success bar
    bar = {}
    for mm in METHODS:
        c = cov[mm]
        a_ = c["median_top1_r"]
        b_ = c["exposure"]["reach_ge1"]
        c_ = c["min_group_median_top1_r"]
        full = [a_ >= .80, b_ >= .60, c_ >= .60]
        margin = [a_ >= .70, b_ >= .40, c_ >= .50]
        promising = sum(full) == 2 and all(margin)
        bar[mm] = {"a_median_top1_r": a_, "b_reach": b_, "c_min_group_median": c_, "meets": full,
                   "verdict": "proven" if all(full) else ("promising" if promising else "not viable")}
    verdicts = [v["verdict"] for v in bar.values()]
    overall = "proven" if "proven" in verdicts else ("promising" if "promising" in verdicts else "not viable")
    res["success_bar"] = {"per_method": bar, "overall": overall}

    # ------------------------------------------------------------------ robustness
    if not quick:
        dfi = pd.read_parquet(DATA_INCL, columns=SCALES + ["gender", "age"])
        Pi = dfi[SCALES].to_numpy(dtype=float)
        gi = make_groups(dfi, Pi)
        covi, _ = coverage_block(Pi, occ, O, gi, rng, 100, 50, "incl_shared")
        rob = {"n_people": len(Pi)}
        for mm in METHODS:
            c = covi[mm]
            rob[mm] = {"median_top1_r": c["median_top1_r"], "reach_ge1": c["exposure"]["reach_ge1"],
                       "reach_ge_0.1pct": c["exposure"]["reach_ge_0.1pct"], "gini": c["exposure"]["gini"],
                       "min_group_median_top1_r": c["min_group_median_top1_r"],
                       "median_top1_by_type": {k: v["median_top1_r"] for k, v in c["by_top_type"].items()},
                       "minors_median_top1_r": c["by_subgroup"]["age_13-17"]["median_top1_r"]}
        res["robustness_incl_shared_network"] = rob

    # ------------------------------------------------------------------ charts
    charts(occ, O, top1, xy_o, xy_p, P, groups, cov, tops, q2, pools, q3, n, m)
    res["seconds_total"] = time.time() - t_start
    return res


def charts(occ, O, top1, xy_o, xy_p, P, groups, cov, tops, q2, pools, q3, n, m):
    tag = f"n = {n:,} people, {m} occupations"
    # Holland distribution
    fig, ax = plt.subplots(figsize=(7, 4))
    occ_share = pd.Series(top1).value_counts(normalize=True).reindex(SCALES).fillna(0) * 100
    tu = groups["top_type_first"]
    ppl_share = pd.Series(np.array(SCALES)[tu]).value_counts(normalize=True).reindex(SCALES) * 100
    x = np.arange(6)
    ax.bar(x - 0.2, occ_share, 0.4, label="O*NET occupations (top letter)")
    ax.bar(x + 0.2, ppl_share, 0.4, label="People (top type, first argmax)")
    ax.set_xticks(x, SCALES)
    ax.set_ylabel("% of group")
    ax.set_title(f"E3: top RIASEC letter, occupations vs people ({tag})", fontsize=9)
    ax.legend()
    fig.tight_layout()
    fig.savefig(FINDINGS / "e3_holland_distribution.png", dpi=130)
    plt.close(fig)

    # Prediger scatter + people density
    fig, axs = plt.subplots(1, 2, figsize=(12, 5.5))
    jz = occ["job_zone"].to_numpy(dtype=float)
    sc = axs[0].scatter(xy_o[:, 0], xy_o[:, 1], c=jz, cmap="viridis", s=10, alpha=0.8)
    plt.colorbar(sc, ax=axs[0], label="Job zone (2-5)")
    axs[0].set_title(f"Occupations ({m}) in the Prediger plane (OI 1-7, centred)", fontsize=9)
    hb = axs[1].hexbin(xy_p[:, 0], xy_p[:, 1], gridsize=45, bins="log", cmap="magma_r", mincnt=1)
    plt.colorbar(hb, ax=axs[1], label="log10 people")
    axs[1].set_title(f"People ({n:,}) in the Prediger plane (1-5, centred)", fontsize=9)
    for ax in axs:
        ax.axhline(0, c="grey", lw=0.5)
        ax.axvline(0, c="grey", lw=0.5)
        ax.set_xlabel("x: Things (+, R) <-> People (-, S)")
        ax.set_ylabel("y: Ideas (+, I/A) <-> Data (-, E/C)")
        lim = np.abs(ax.get_xlim() + ax.get_ylim()).max()
        ax.set_xlim(-lim, lim)
        ax.set_ylim(-lim, lim)
        for j, s in enumerate(SCALES):
            ax.annotate(s, (0.9 * lim * np.cos(ANGLES[j]), 0.9 * lim * np.sin(ANGLES[j])), fontsize=12,
                        color="red", ha="center")
        ax.set_aspect("equal")
    fig.tight_layout()
    fig.savefig(FINDINGS / "e3_prediger_scatter.png", dpi=130)
    plt.close(fig)

    # angular histograms
    fig = plt.figure(figsize=(6, 6))
    ax = fig.add_subplot(projection="polar")
    bins = np.deg2rad(np.arange(-15, 346, 30))
    for xy, lab in ((xy_o, "occupations"), (xy_p, "people")):
        ang = np.mod(np.arctan2(xy[:, 1], xy[:, 0]) + np.deg2rad(15), 2 * np.pi) - np.deg2rad(15)
        h, _ = np.histogram(ang, bins=bins)
        ax.bar(bins[:-1] + np.deg2rad(15), h / h.sum(), width=np.deg2rad(28), alpha=0.5, label=lab)
    ax.set_xticks(ANGLES, SCALES)
    ax.set_title(f"E3: direction of the centred profile (share per 30 deg)\n{tag}", fontsize=9)
    ax.legend(loc="lower left", fontsize=8)
    fig.tight_layout()
    fig.savefig(FINDINGS / "e3_angle_hist.png", dpi=130)
    plt.close(fig)

    # families curve
    fig, axs = plt.subplots(1, 2, figsize=(11, 4))
    cur = q2["n_families_curve"]
    axs[0].plot(list(cur.keys()), list(cur.values()), marker=".")
    axs[0].axvline(0.9, ls="--", c="grey")
    axs[0].set_xlabel("r_min (every within-family pair has profile r >= r_min)")
    axs[0].set_ylabel("number of families (complete linkage)")
    axs[0].set_title(f"Effective resolution of {m} occupation profiles", fontsize=9)
    ov = M._unit_rows(M._centre_rows(O))
    Rm = ov @ ov.T
    axs[1].hist(Rm[np.triu_indices(m, 1)], bins=80, density=True, alpha=0.6, label="all pairs")
    rel = pd.read_csv(RELATED, dtype=str)
    pos = {c: i for i, c in enumerate(occ.code)}
    rel = rel[rel["O*NET-SOC Code"].isin(pos) & rel["Related O*NET-SOC Code"].isin(pos)]
    axs[1].hist(Rm[rel["O*NET-SOC Code"].map(pos), rel["Related O*NET-SOC Code"].map(pos)], bins=80, density=True,
                alpha=0.6, label="O*NET related pairs")
    axs[1].set_xlabel("profile Pearson r between two occupations")
    axs[1].set_ylabel("density")
    axs[1].legend()
    axs[1].set_title("Pairwise occupation profile similarity", fontsize=9)
    fig.tight_layout()
    fig.savefig(FINDINGS / "e3_families_curve.png", dpi=130)
    plt.close(fig)

    # coverage by top type
    fig, axs = plt.subplots(1, len(METHODS), figsize=(15, 4), sharey=True)
    tu = groups["top_type_unique"]
    for ax, mm in zip(axs, METHODS):
        r = tops[mm][1][:, 0]
        data = [r[tu == j] for j in range(6)] + [r[tu == -1]]
        ax.boxplot(data, showfliers=False)
        ax.set_xticks(range(1, 8), SCALES + ["tied"])
        ax.axhline(0.8, ls="--", c="green", lw=0.8)
        ax.axhline(0.6, ls="--", c="red", lw=0.8)
        ax.set_title(f"{mm}: Pearson r of top-1", fontsize=9)
        ax.set_xlabel("person's top type")
    axs[0].set_ylabel("Pearson r (person vs top-1 occupation)")
    fig.suptitle(f"E3: top-1 match quality by person top type ({tag})", fontsize=10)
    fig.tight_layout()
    fig.savefig(FINDINGS / "e3_coverage_by_type.png", dpi=130)
    plt.close(fig)

    # Lorenz curves
    fig, ax = plt.subplots(figsize=(6, 5))
    for mm in METHODS:
        c = np.sort(tops[mm][2])
        ax.plot(np.linspace(0, 1, m + 1), np.r_[0, np.cumsum(c) / c.sum()],
                label=f"{mm} (Gini {cov[mm]['exposure']['gini']:.2f}, reach {cov[mm]['exposure']['reach_ge1']:.0%})")
    ax.plot([0, 1], [0, 1], c="grey", ls="--", label="equal exposure")
    ax.set_xlabel("share of occupations (least exposed first)")
    ax.set_ylabel("share of all top-10 slots")
    ax.set_title(f"E3: exposure concentration ({tag})", fontsize=9)
    ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(FINDINGS / "e3_exposure_lorenz.png", dpi=130)
    plt.close(fig)

    # pool size
    fig, ax = plt.subplots(figsize=(7, 4))
    v = pools[0.8]
    ax.boxplot([v[tu == j] for j in range(6)] + [v[tu == -1]], showfliers=False)
    ax.set_xticks(range(1, 8), SCALES + ["tied"])
    ax.set_ylabel("# occupations with Pearson r >= .80")
    ax.set_xlabel("person's top type")
    ax.set_title(f"E3: size of the good-match pool by top type ({tag})", fontsize=9)
    fig.tight_layout()
    fig.savefig(FINDINGS / "e3_pool_size.png", dpi=130)
    plt.close(fig)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--quick", action="store_true", help="subsample people for a fast smoke run")
    a = ap.parse_args()
    FINDINGS.mkdir(parents=True, exist_ok=True)
    out = rnd(main(a.seed, a.quick))
    name = "e3_occupation_space_quick.json" if a.quick else "e3_occupation_space.json"
    (FINDINGS / name).write_text(json.dumps(out, indent=2))
    print(json.dumps(out["success_bar"], indent=2))
