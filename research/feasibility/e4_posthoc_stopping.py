"""E4 post hoc (NOT pre-registered): is the gain of variable-length stopping rules real or a part-whole artefact?

Agreement with the full test jumps to 1.0 at 48 items because the reference *is* the 48 answers. A rule that sends
hard cases to 40-48 items therefore gains mechanically against a fixed form at the same MEAN length. Two checks:
  (a) Real data: compare each rule with the best fixed form given (i) each person's own stopping length (isolates
      item selection) and (ii) a random permutation of the rule's lengths across people (same length distribution,
      non-adaptive; isolates the value of the adaptive stopping decision beyond the length distribution).
  (b) Synthetic data (known true theta, no part-whole link to the target): each rule vs the fixed form at the
      rule's mean length, both scored against the TRUE-theta ranking.
Run: .venv/Scripts/python -I research/feasibility/e4_posthoc_stopping.py [--quick]
Writes research/findings/e4_posthoc_stopping.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import expit

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import e4_cat_simulation as E


def stable3_mask(rec, ranker, T):
    tops = np.stack([np.sort(ranker.top(rec["rawc"][k].astype(float), 10), 1) for k in range(T + 1)])
    same = np.zeros((T + 1, tops.shape[1]), bool)
    same[1:] = (tops[1:] == tops[:-1]).all(2)
    st = np.zeros_like(same)
    st[3:] = same[3:] & same[2:-1] & same[1:-2]
    return st


def rules(rec, ranker):
    T = rec["rawc"].shape[0] - 1
    st = stable3_mask(rec, ranker, T)
    top3sd = np.take_along_axis(rec["sec"], np.argsort(-rec["rawc"], 2)[:, :, :3], 2).max(2)
    out = {}
    for cap in (30, 40, 48):
        out[f"C_stab_cap{cap}"] = E.first_true(st, 12, cap)
        out[f"B_se0.40_cap{cap}"] = E.first_true(rec["sec"].max(2) < 0.40, 6, cap)
    out["C_lit_sd0.40_cap40"] = E.first_true(st & (top3sd < 0.40), 12, 40)
    return out


def gather(rec, ks, scoring):
    th, raw, nu = E.at_stop(rec, ks, scoring)
    return th, raw, nu


def main(seed, quick):
    df, resp, g, band, raw_full = E.load_people("main", quick, seed)
    cal = E.strat_split(g, band, seed)
    a, b, *_ = E.calibrate(resp[cal])
    P, info = E.cat_probs(a, b), E.fisher_info(a, b)
    Phi = E.latent_corr(resp[cal], P)
    occ = E.M.load_occupations()
    fcsv = pd.read_csv(E.FINDINGS / "e3_families.csv").set_index("code")
    fams = {r: fcsv.loc[occ["code"], f"family_{r}"].to_numpy().astype(int) for r in ("r80", "r90")}
    rk = E.Ranker(occ, "pearson", fams)
    rankers = {"pearson": rk}
    rank_a = np.zeros(48, int)
    for s in range(6):
        cols = np.arange(8 * s, 8 * s + 8)
        rank_a[cols[np.argsort(-a[cols])]] = np.arange(8)
    prio_best = (-(rank_a * 6 + E.SCALE_OF)).astype(float)
    pool = np.ones(48, bool)
    rng = np.random.default_rng(seed + 11)
    res = {}

    # (a) real data
    rs = resp[~cal]
    L = np.stack([E.scale_loglik(rs[:, 8 * s: 8 * s + 8], P[8 * s: 8 * s + 8]) for s in range(6)], 1)
    _, th_full, _ = E.eap_indep(L)
    raw_sim = raw_full[~cal]
    ref = {"theta_full": th_full, "raw_full": raw_sim, "top10_pearson": rk.top(raw_sim, 10)}
    for f, fl in fams.items():
        ref[f"top3fam_{f}"] = rk.fam_top(raw_sim, fl, 3)
    recB = E.Engine(rs, P, info, Phi, pool, "B").run()
    recF = E.Engine(rs, P, info, Phi, pool, "fixed", prio_best).run()
    keys = ("r_theta", "top10_pearson", "top3fam_r80", "fam10_r90", "first_letter")
    for name, ks in rules(recB, rk).items():
        m_rule, _ = E.evaluate(*gather(recB, ks, "corr")[:2], ref, rankers)
        m_own, _ = E.evaluate(*gather(recF, ks, "corr")[:2], ref, rankers)
        m_shuf, _ = E.evaluate(*gather(recF, rng.permutation(ks), "corr")[:2], ref, rankers)
        kmean = int(round(float(recB["nadm"][ks, np.arange(len(ks))].mean())))
        m_mean, _ = E.evaluate(*E.at_k(recF, kmean, "corr"), ref, rankers)
        res[f"real:{name}"] = {"mean_items": kmean,
                               "rule": {k: m_rule[k] for k in keys},
                               "best_fixed_same_mean_length": {k: m_mean[k] for k in keys},
                               "best_fixed_own_length": {k: m_own[k] for k in keys},
                               "best_fixed_shuffled_lengths": {k: m_shuf[k] for k in keys}}
        print(name, res[f"real:{name}"], flush=True)

    # (b) synthetic with known theta
    n_syn = 3000 if quick else 10000
    rng2 = np.random.default_rng(seed + 7)
    th_true = rng2.multivariate_normal(np.zeros(6), Phi, n_syn)
    cum = expit(a[None, :, None] * (th_true[:, E.SCALE_OF][:, :, None] - b[None, :, :]))
    syn = (rng2.random((n_syn, 48))[:, :, None] < cum).sum(2).astype(np.int8)
    escore = (P * np.arange(1, 6)[None, None, :]).sum(2)
    raw_true = np.stack([np.stack([np.interp(th_true[:, s], E.GRID, escore[j]) for j in range(8 * s, 8 * s + 8)], 1).mean(1)
                         for s in range(6)], 1)
    ref_true = {"theta_full": th_true, "raw_full": raw_true, "top10_pearson": rk.top(raw_true, 10)}
    for f, fl in fams.items():
        ref_true[f"top3fam_{f}"] = rk.fam_top(raw_true, fl, 3)
    sB = E.Engine(syn, P, info, Phi, pool, "B").run()
    sF = E.Engine(syn, P, info, Phi, pool, "fixed", prio_best).run()
    m48, _ = E.evaluate(*E.at_k(sF, 48, "corr"), ref_true, rankers)
    res["synthetic:full48_vs_true"] = {k: m48[k] for k in keys}
    for name, ks in rules(sB, rk).items():
        m_rule, _ = E.evaluate(*gather(sB, ks, "corr")[:2], ref_true, rankers)
        kmean = int(round(float(sB["nadm"][ks, np.arange(n_syn)].mean())))
        m_mean, _ = E.evaluate(*E.at_k(sF, kmean, "corr"), ref_true, rankers)
        m_shuf, _ = E.evaluate(*gather(sF, rng.permutation(ks), "corr")[:2], ref_true, rankers)
        res[f"synthetic_vs_true:{name}"] = {"mean_items": kmean, "rule": {k: m_rule[k] for k in keys},
                                            "best_fixed_same_mean_length": {k: m_mean[k] for k in keys},
                                            "best_fixed_shuffled_lengths": {k: m_shuf[k] for k in keys}}
        print(name, res[f"synthetic_vs_true:{name}"], flush=True)
    for k in (12, 20, 30):
        mb, _ = E.evaluate(*E.at_k(sB, k, "corr"), ref_true, rankers)
        mf, _ = E.evaluate(*E.at_k(sF, k, "corr"), ref_true, rankers)
        res[f"synthetic_vs_true:fixed_k{k}"] = {"B": {kk: mb[kk] for kk in keys}, "best_fixed": {kk: mf[kk] for kk in keys}}
    return res


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--quick", action="store_true")
    a = ap.parse_args()
    out = E._jsonable(main(a.seed, a.quick))
    (E.FINDINGS / f"e4_posthoc_stopping{'_quick' if a.quick else ''}.json").write_text(json.dumps(out, indent=1))
