"""E4 - Adaptive questionnaire (CAT) simulation: how few questions do we need?

Run (repo root):
    .venv/Scripts/python -I research/feasibility/e4_cat_simulation.py --seed 42
    .venv/Scripts/python -I research/feasibility/e4_cat_simulation.py --quick            # smoke run
    .venv/Scripts/python -I research/feasibility/e4_cat_simulation.py --table incl_shared  # robustness

Pre-registration and results: research/findings/e4_cat_simulation.md

Design (see the findings file for the full pre-registration):
  * 70/30 split stratified by gender x age band; calibration people are never simulated.
  * One logistic GRM per RIASEC scale (girth 0.8.0 grm_mml, MML), P(X>=k) = expit(a(theta-b_k)).
  * 6x6 latent correlation matrix by pairwise ML given the fixed item parameters (prior for engine B).
  * EAP on a 1-D grid per scale; the correlated prior uses a Gaussian (EP-style) site approximation,
    and the reported estimate is the exact grid posterior of each scale under its Gaussian cavity.
  * Engines: A (max Fisher info, independent prior, round-robin), B (correlated prior, max expected
    reduction in total posterior variance), C (B + top-10 stability stopping), baselines random-k,
    best-k by discrimination, Mini-IP-like 5/scale, full 48.
  * Each simulation person's real recorded answers are replayed. Missing answers remove the item from that
    person's pool (not counted as administered).
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import minimize_scalar
from scipy.special import expit
from scipy.stats import norm

ROOT = Path(__file__).resolve().parents[2]
FINDINGS = ROOT / "research" / "findings"
sys.path.insert(0, str(ROOT / "src"))  # -I drops the script dir; matching.py lives in src/

import girth

try:
    from career_compass import matching as M

    HAVE_MATCHING = True
except Exception:  # pragma: no cover - fallback documented in the findings
    M = None
    HAVE_MATCHING = False

SCALES = list("RIASEC")
ITEMS = [f"{s}{i}" for s in SCALES for i in range(1, 9)]
SCALE_OF = np.repeat(np.arange(6), 8)
FLAGGED = ["R1", "A7", "S4", "E4", "R3", "I8", "R4", "E1"]  # E2: weak (R1, A7, S4) + gender DIF
GRID = np.linspace(-5, 5, 81)
LOGPRIOR0 = norm.logpdf(GRID)
K_CURVE = list(range(6, 49, 2))
K_HEAD = [12, 20, 30]
SE_THRESH = [0.30, 0.40, 0.50]
CAPS = [20, 30, 40, 48]
TABLES = {
    "main": ROOT / "data" / "processed" / "riasec_people.parquet",
    "incl_shared": ROOT / "data" / "processed" / "riasec_people_incl_shared_network.parquet",
}
OCC_PATH = ROOT / "data" / "processed" / "onet_occupations.parquet"


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


# ============================================================================ data
def load_people(table: str, quick: bool, seed: int):
    df = pd.read_parquet(TABLES[table])
    if quick:
        df = df.sample(8000, random_state=seed).reset_index(drop=True)
    X = df[ITEMS].to_numpy(dtype=float)
    resp = np.where(np.isnan(X), -1, X - 1).astype(np.int8)  # 0..4, -1 missing
    g = df["gender"].map({1.0: "male", 2.0: "female"}).fillna("other").to_numpy()
    age = df["age"].to_numpy()
    band = np.where(age < 18, "13-17", np.where(age < 25, "18-24", "25+"))
    raw_full = df[SCALES].to_numpy(dtype=float)  # observed scale means (>= 6 of 8 answered)
    return df, resp, g, band, raw_full


def strat_split(g, band, seed, frac_cal=0.7):
    rng = np.random.default_rng(seed)
    strata = pd.Series(g + "|" + band)
    cal = np.zeros(len(g), bool)
    for idx in strata.groupby(strata).groups.values():
        idx = np.asarray(idx)
        rng.shuffle(idx)
        cal[idx[: int(round(frac_cal * len(idx)))]] = True
    return cal


# ============================================================================ GRM
def cat_probs(a, b, grid=GRID):
    """Category probabilities (J, Q, 5) for logistic GRM."""
    cum = expit(a[:, None, None] * (grid[None, :, None] - b[:, None, :]))  # J,Q,4
    ones = np.ones_like(cum[:, :, :1])
    zeros = np.zeros_like(cum[:, :, :1])
    return np.clip(np.concatenate([ones, cum], 2) - np.concatenate([cum, zeros], 2), 1e-12, 1)


def fisher_info(a, b, grid=GRID):
    cum = expit(a[:, None, None] * (grid[None, :, None] - b[:, None, :]))
    d = a[:, None, None] * cum * (1 - cum)  # derivative of P*_k
    z = np.zeros_like(d[:, :, :1])
    dP = np.concatenate([z, d], 2) - np.concatenate([d, z], 2)
    return (dP**2 / cat_probs(a, b, grid)).sum(2)  # J,Q


def scale_loglik(resp_s, P_s):
    """Per-person log-likelihood on the grid for one scale. resp_s (n, 8) 0..4/-1; P_s (8, Q, 5)."""
    L = np.zeros((resp_s.shape[0], P_s.shape[1]))
    logP = np.log(P_s)
    for j in range(resp_s.shape[1]):
        m = resp_s[:, j] >= 0
        L[m] += logP[j][:, resp_s[m, j]].T
    return L


def marginal_ll(resp_s, a, b):
    L = scale_loglik(resp_s, cat_probs(a, b)) + LOGPRIOR0
    mx = L.max(1, keepdims=True)
    return float((mx[:, 0] + np.log(np.exp(L - mx).sum(1) * (GRID[1] - GRID[0]))).sum())


def _pack(a, b):
    return np.concatenate([[np.log(a)], [b[0]], np.log(np.diff(b))])


def _unpack(x):
    return np.exp(x[0]), x[1] + np.concatenate([[0], np.cumsum(np.exp(x[2:]))])


def em_polish(R, a, b, max_iter=200, tol=1e-3):
    """Bock-Aitkin EM for the GRM (exact MML on the 81-point grid), started from girth's solution.

    E-step: expected counts W[j, k, q] of category k of item j at node q. M-step: per item, maximise
    sum_kq W log P_jk(q) over (log a, b1, log threshold gaps), which keeps thresholds ordered.
    """
    from scipy.optimize import minimize

    a, b = a.copy(), b.copy()
    J = R.shape[1]
    onehot = [(R[:, j][:, None] == np.arange(5)[None, :]).astype(float) for j in range(J)]  # missing -> all 0
    ll_hist = []
    for it in range(max_iter):
        L = scale_loglik(R, cat_probs(a, b)) + LOGPRIOR0
        mx = L.max(1, keepdims=True)
        post = np.exp(L - mx)
        ssum = post.sum(1, keepdims=True)
        ll_hist.append(float((mx[:, 0] + np.log(ssum[:, 0] * (GRID[1] - GRID[0]))).sum()))
        if it > 0 and ll_hist[-1] - ll_hist[-2] < tol:
            break
        post /= ssum
        for j in range(J):
            W = onehot[j].T @ post  # (5, Q)

            def f(x, W=W):
                aj, bj = _unpack(x)
                return -(W.T * np.log(cat_probs(np.array([aj]), bj[None, :])[0])).sum()

            res = minimize(f, _pack(a[j], b[j]), method="L-BFGS-B")
            a[j], b[j] = _unpack(res.x)
    return a, b, ll_hist


def calibrate(resp_cal):
    """Six girth GRMs, then an own Bock-Aitkin EM polish (final estimates). Returns a, b, diagnostics."""
    a = np.zeros(48)
    b = np.zeros((48, 4))
    a_g = np.zeros(48)
    b_g = np.zeros((48, 4))
    diag = {}
    for s in range(6):
        cols = np.arange(8 * s, 8 * s + 8)
        R = resp_cal[:, cols].astype(int)
        D = np.where(R < 0, girth.INVALID_RESPONSE, R + 1).T
        t0 = time.time()
        res = girth.grm_mml(D, {"use_LUT": False, "max_iteration": 200})
        a_s, b_s = np.asarray(res["Discrimination"], float), np.asarray(res["Difficulty"], float)
        assert b_s.shape == (8, 4), b_s.shape
        t1 = time.time()
        a_p, b_p, hist = em_polish(R, a_s, b_s)
        a_g[cols], b_g[cols] = a_s, b_s
        a[cols], b[cols] = a_p, b_p
        diag[SCALES[s]] = {
            "girth_seconds": round(t1 - t0, 1), "em_seconds": round(time.time() - t1, 1),
            "ll_girth": round(hist[0], 2), "ll_em_final": round(hist[-1], 2), "em_iterations": len(hist) - 1,
            "max_abs_da_girth_vs_em": round(float(np.abs(a_s - a_p).max()), 4),
            "max_abs_db_girth_vs_em": round(float(np.abs(b_s - b_p).max()), 4),
            "thresholds_ordered": bool((np.diff(b_p, axis=1) > 0).all()),
        }
        log(f"GRM {SCALES[s]}: a girth {np.round(a_s, 2)} em {np.round(a_p, 2)}", diag[SCALES[s]])
    return a, b, diag, a_g, b_g


def eap_indep(loglik):
    """loglik (n, 6, Q) -> posterior (n,6,Q), mean, var under N(0,1) per scale."""
    lp = loglik + LOGPRIOR0
    lp = lp - lp.max(-1, keepdims=True)
    post = np.exp(lp)
    post /= post.sum(-1, keepdims=True)
    mu = post @ GRID
    var = np.clip(post @ GRID**2 - mu**2, 1e-8, None)
    return post, mu, var


def eap_corr(loglik, mu0, v0, Phi_inv):
    """Correlated-prior EAP via Gaussian sites + exact 1-D cavity posteriors.

    mu0, v0: per-scale posterior mean/var under N(0,1) (n, 6). Returns post (n,6,Q), mean, var,
    and the Gaussian 6x6 posterior covariance C (n,6,6).
    """
    tau = np.clip(1.0 / v0 - 1.0, 0, None)
    h = np.where(tau > 0, mu0 / v0, 0.0)
    P = Phi_inv[None] + tau[:, :, None] * np.eye(6)[None]
    C = np.linalg.inv(P)
    m = np.einsum("nij,nj->ni", C, h)
    Css = np.einsum("nii->ni", C)
    w = Css / (1 - tau * Css)
    c = w * (m / Css - h)
    lp = loglik - 0.5 * (GRID[None, None, :] - c[:, :, None]) ** 2 / w[:, :, None]
    lp = lp - lp.max(-1, keepdims=True)
    post = np.exp(lp)
    post /= post.sum(-1, keepdims=True)
    mu = post @ GRID
    var = np.clip(post @ GRID**2 - mu**2, 1e-8, None)
    return post, mu, var, C


def latent_corr(resp_cal, P):
    """Pairwise ML latent correlation given fixed item parameters (41-point grid)."""
    sub = slice(None, None, 2)
    g = GRID[sub]
    dq = g[1] - g[0]
    Ls = []
    for s in range(6):
        L = scale_loglik(resp_cal[:, 8 * s: 8 * s + 8], P[8 * s: 8 * s + 8][:, sub, :])
        Ls.append(np.exp(L - L.max(1, keepdims=True)))
    Phi = np.eye(6)
    q1, q2 = np.meshgrid(g, g, indexing="ij")
    for s in range(6):
        for t in range(s + 1, 6):
            def nll(r):
                k = np.exp(-(q1**2 - 2 * r * q1 * q2 + q2**2) / (2 * (1 - r**2))) / (2 * np.pi * np.sqrt(1 - r**2))
                v = ((Ls[s] @ (k * dq * dq)) * Ls[t]).sum(1)
                return -np.log(v).sum()
            Phi[s, t] = Phi[t, s] = minimize_scalar(nll, bounds=(-0.95, 0.95), method="bounded",
                                                    options={"xatol": 1e-4}).x
    return Phi


def q3_matrix(resp_cal, P, mu_full):
    """Yen's Q3 residual correlations within each scale (EAP theta, independent prior)."""
    escore = (P * np.arange(5)[None, None, :]).sum(2)  # J,Q
    out = {}
    for s in range(6):
        cols = list(range(8 * s, 8 * s + 8))
        E = np.stack([np.interp(mu_full[:, s], GRID, escore[j]) for j in cols], 1)
        R = resp_cal[:, cols].astype(float)
        R[R < 0] = np.nan
        res = pd.DataFrame(R - E, columns=[ITEMS[j] for j in cols])
        out[SCALES[s]] = res.corr()
    return out


# ============================================================================ simulation engine
class Engine:
    """Vectorised CAT replay. Records the state after every administered item (k = 1..48)."""

    def __init__(self, resp, P, info_grid, Phi, pool_mask, kind, order_priority=None,
                 se_stop=None, nmax=48):
        self.resp, self.P, self.info, self.kind = resp, P, info_grid, kind
        self.Phi_inv = np.linalg.inv(Phi)
        self.n = resp.shape[0]
        self.avail = (resp >= 0) & pool_mask[None, :]
        self.admin = np.zeros_like(self.avail)
        self.loglik = np.zeros((self.n, 6, GRID.size))
        self.logP = np.log(P)
        self.prio = order_priority  # (n, 48) or (48,) for fixed orders (higher = earlier)
        self.se_stop = se_stop  # engine A variable-length: skip scales already below SE
        self.nmax = nmax
        self.last_scale = np.full(self.n, -1)
        Ps = P.reshape(6, 8, GRID.size, 5)
        self.Ps_r = [Ps[s].transpose(1, 0, 2).reshape(GRID.size, 40) for s in range(6)]
        self.i0 = np.array([np.argmax(np.where(pool_mask[8 * s: 8 * s + 8], info_grid[8 * s: 8 * s + 8, 40], -1))
                            for s in range(6)])  # most informative at theta = 0 (grid index 40)

    def state(self):
        post0, mu0, v0 = eap_indep(self.loglik)
        postc, muc, vc, C = eap_corr(self.loglik, mu0, v0, self.Phi_inv)
        return post0, mu0, v0, postc, muc, vc, C

    def _round_robin_scale(self, open_scale):
        """Next open scale after last_scale in R..C cyclic order; -1 if none."""
        nxt = np.full(self.n, -1)
        for off in range(1, 7):
            cand = (self.last_scale + off) % 6
            ok = (nxt < 0) & open_scale[np.arange(self.n), cand]
            nxt[ok] = cand[ok]
        return nxt

    def select(self, step, st):
        post0, mu0, v0, postc, muc, vc, C = st
        ok = self.avail & ~self.admin
        has_scale = np.stack([ok[:, 8 * s: 8 * s + 8].any(1) for s in range(6)], 1)
        if self.kind in ("fixed", "random"):
            pr = np.broadcast_to(self.prio, ok.shape)
            score = np.where(ok, pr, -np.inf)
        elif self.kind == "A" or (self.kind == "B" and step < 6):
            open_scale = has_scale.copy()
            if self.se_stop is not None:
                open_scale &= np.sqrt(v0) >= self.se_stop
            if self.kind == "B":  # starter: one item per scale, most informative at theta = 0
                open_scale = has_scale & np.eye(6, dtype=bool)[step][None, :]
                tgt = np.where(open_scale[:, step], step, -1)
                th = np.zeros((self.n, 6))
            else:
                tgt = self._round_robin_scale(open_scale)
                th = mu0
            idx = np.clip((th - GRID[0]) / (GRID[1] - GRID[0]), 0, GRID.size - 1)
            lo = np.floor(idx).astype(int).clip(0, GRID.size - 2)
            fr = idx - lo
            th_item = lo[:, SCALE_OF], fr[:, SCALE_OF]
            inf = self.info[np.arange(48)[None, :], th_item[0]] * (1 - th_item[1]) + \
                self.info[np.arange(48)[None, :], th_item[0] + 1] * th_item[1]
            score = np.where(ok & (SCALE_OF[None, :] == tgt[:, None]), inf, -np.inf)
        elif self.kind == "B":
            g = (C**2).sum(1) / np.einsum("nii->ni", C) ** 2  # (n, 6): 1 + sum beta^2
            score = np.full(ok.shape, -np.inf)
            for s in range(6):
                ps = postc[:, s, :]
                pk = (ps @ self.Ps_r[s]).reshape(self.n, 8, 5)
                m1 = ((ps * GRID) @ self.Ps_r[s]).reshape(self.n, 8, 5)
                delta = (m1**2 / pk).sum(2) - muc[:, s: s + 1] ** 2  # var - E[var | x]
                score[:, 8 * s: 8 * s + 8] = np.where(ok[:, 8 * s: 8 * s + 8], delta * g[:, s: s + 1], -np.inf)
        else:
            raise ValueError(self.kind)
        j = score.argmax(1)
        active = np.isfinite(score[np.arange(self.n), j])
        return j, active

    def run(self, record_corr=True):
        n = self.n
        T = self.nmax
        rec = {k: np.zeros((T + 1, n, 6), np.float32) for k in ("mu0", "se0", "muc", "sec", "raw0", "rawc")}
        rec["nadm"] = np.zeros((T + 1, n), np.int16)
        rec["order"] = np.full((n, T), -1, np.int16)
        escore = (self.P * np.arange(5)[None, None, :]).sum(2)  # J,Q (0..4)
        st = self.state()
        self._record(rec, 0, st, escore)
        for t in range(T):
            j, active = self.select(t, st)
            rows = np.where(active)[0]
            jj = j[rows]
            x = self.resp[rows, jj]
            self.loglik[rows, SCALE_OF[jj], :] += self.logP[jj, :, x]
            self.admin[rows, jj] = True
            self.last_scale[rows] = SCALE_OF[jj]
            rec["order"][rows, t] = jj
            st = self.state()
            self._record(rec, t + 1, st, escore)
            if not active.any():
                for k in rec:
                    if k != "order":
                        rec[k][t + 2:] = rec[k][t + 1]
                break
        return rec

    def _record(self, rec, t, st, escore):
        post0, mu0, v0, postc, muc, vc, C = st
        rec["mu0"][t], rec["se0"][t] = mu0, np.sqrt(v0)
        rec["muc"][t], rec["sec"][t] = muc, np.sqrt(vc)
        obs = np.where(self.admin, self.resp, 0).astype(float)
        for key, post in (("raw0", post0), ("rawc", postc)):
            E = np.einsum("nsq,sjq->nsj", post, escore.reshape(6, 8, -1)).reshape(self.n, 48)
            full = np.where(self.admin, obs, E) + 1.0
            rec[key][t] = full.reshape(self.n, 6, 8).mean(2)
        rec["nadm"][t] = self.admin.sum(1)


# ============================================================================ metrics
class Ranker:
    def __init__(self, occ, method, fams=None):
        self.occ, self.method, self.fams = occ, method, fams or {}

    def fam_top(self, prof, fl, k=3):
        """Top-k families per person; a family's score is its best member's score (as in E5)."""
        S = M.score_matrix(prof, self.occ, self.method)
        order = np.argsort(fl, kind="stable")
        starts = np.r_[0, np.flatnonzero(np.diff(fl[order])) + 1]
        F = np.maximum.reduceat(S[:, order], starts, axis=1)
        part = np.argpartition(-F, k - 1, 1)[:, :k]
        return np.take_along_axis(part, np.argsort(-np.take_along_axis(F, part, 1), 1), 1)

    def top(self, prof, k=10):
        if HAVE_MATCHING:
            return M.top_k_indices(prof, self.occ, k=k, method=self.method)
        o = self.occ[SCALES].to_numpy(float)  # fallback: Pearson only
        pc = prof - prof.mean(1, keepdims=True)
        pc /= np.linalg.norm(pc, axis=1, keepdims=True) + 1e-12
        oc = o - o.mean(1, keepdims=True)
        oc /= np.linalg.norm(oc, axis=1, keepdims=True)
        s = pc @ oc.T
        part = np.argpartition(-s, k - 1, 1)[:, :k]
        return np.take_along_axis(part, np.argsort(-np.take_along_axis(s, part, 1), 1), 1)


def overlap(A, B):
    return (A[:, :, None] == B[:, None, :]).any(2).mean(1)


def holland(prof_cat, prof_ref):
    o_c = np.argsort(-prof_cat, axis=1, kind="stable")
    o_r = np.argsort(-prof_ref, axis=1, kind="stable")
    tie_top = np.isclose(prof_ref, prof_ref.max(1, keepdims=True), atol=1e-9)
    first = tie_top[np.arange(len(prof_cat)), o_c[:, 0]]
    set3 = (np.sort(o_c[:, :3], 1) == np.sort(o_r[:, :3], 1)).all(1)
    code3 = (o_c[:, :3] == o_r[:, :3]).all(1)
    return first, set3, code3


def corr_cols(x, y):
    xc, yc = x - x.mean(0), y - y.mean(0)
    return (xc * yc).sum(0) / np.sqrt((xc**2).sum(0) * (yc**2).sum(0))


def evaluate(theta, raw, ref, rankers, mask=None):
    """theta/raw: (n,6) estimates; ref: dict with theta_full, raw_full, top10/top3 per method."""
    sel = slice(None) if mask is None else mask
    r_th = corr_cols(theta[sel], ref["theta_full"][sel])
    r_raw = corr_cols(raw[sel], ref["raw_full"][sel])
    out = {"r_theta": r_th.mean(), "r_raw": r_raw.mean(),
           "r_theta_by_scale": dict(zip(SCALES, np.round(r_th, 4))),
           "r_raw_by_scale": dict(zip(SCALES, np.round(r_raw, 4)))}
    pp = {}
    for name, rk in rankers.items():
        t10 = rk.top(raw[sel], 10)
        pp[f"top10_{name}"] = overlap(t10, ref[f"top10_{name}"][sel])
        pp[f"top3_{name}"] = overlap(t10[:, :3], ref[f"top10_{name}"][sel][:, :3])
        if getattr(rk, "fams", None):  # E3/E5 family level: symmetric hit rate + top-3 families (best member)
            for fname, fl in rk.fams.items():
                fa, fb = fl[t10], fl[ref[f"top10_{name}"][sel]]
                pp[f"fam10_{fname}"] = 0.5 * (overlap(fa, fb) + overlap(fb, fa))
                pp[f"top3fam_{fname}"] = overlap(rk.fam_top(raw[sel], fl, 3), ref[f"top3fam_{fname}"][sel])
    f, s3, c3 = holland(raw[sel], ref["raw_full"][sel])
    pp.update(first_letter=f, code3_set=s3, code3_exact=c3)
    for k, v in pp.items():
        out[k] = float(np.mean(v))
    return {k: (float(v) if isinstance(v, (np.floating, float)) else v) for k, v in out.items()}, pp


def bootstrap(theta, raw, ref, pp, B, seed, theta2=None, raw2=None, pp2=None):
    """Percentile CIs for mean r_theta, r_raw and per-person metrics; optional paired difference."""
    rng = np.random.default_rng(seed)
    n = len(theta)
    keys = list(pp)
    stats = {k: [] for k in ["r_theta", "r_raw", *keys]}
    dstats = {k: [] for k in stats} if theta2 is not None else None
    for _ in range(B):
        w = rng.multinomial(n, np.full(n, 1 / n)).astype(float)

        def wcorr(x, y):
            mx, my = (w @ x) / n, (w @ y) / n
            cov = w @ ((x - mx) * (y - my))
            return (cov / np.sqrt((w @ (x - mx) ** 2) * (w @ (y - my) ** 2))).mean()

        vals = {"r_theta": wcorr(theta, ref["theta_full"]), "r_raw": wcorr(raw, ref["raw_full"])}
        for k in keys:
            vals[k] = (w @ pp[k]) / n
        for k, v in vals.items():
            stats[k].append(v)
        if dstats is not None:
            v2 = {"r_theta": wcorr(theta2, ref["theta_full"]), "r_raw": wcorr(raw2, ref["raw_full"])}
            for k in keys:
                v2[k] = (w @ pp2[k]) / n
            for k in v2:
                dstats[k].append(vals[k] - v2[k])

    def ci(v):
        return [round(float(np.percentile(v, 2.5)), 4), round(float(np.percentile(v, 97.5)), 4)]

    out = {k: ci(v) for k, v in stats.items()}
    if dstats is not None:
        out["diff_vs_comparator"] = {k: {"mean": round(float(np.mean(v)), 4), "ci": ci(v)} for k, v in dstats.items()}
    return out


def at_k(rec, k, scoring):
    """Estimates after k administered items (index by step; step == items for non-exhausted people)."""
    th = rec["mu0" if scoring == "indep" else "muc"][k]
    raw = rec["raw0" if scoring == "indep" else "rawc"][k]
    return th.astype(float), raw.astype(float)


def at_stop(rec, kstop, scoring):
    idx = np.arange(rec["nadm"].shape[1])
    th = rec["mu0" if scoring == "indep" else "muc"][kstop, idx]
    raw = rec["raw0" if scoring == "indep" else "rawc"][kstop, idx]
    return th.astype(float), raw.astype(float), rec["nadm"][kstop, idx].astype(int)


def first_true(cond, kmin, kmax):
    """cond (T+1, n) bool; first step k in [kmin, kmax] where cond holds, else kmax."""
    c = cond.copy()
    c[:kmin] = False
    c[kmax + 1:] = False
    c[kmax] = True
    return c.argmax(0)


def items_summary(nused):
    return {"mean": round(float(nused.mean()), 2), "median": float(np.median(nused)),
            "p10": float(np.percentile(nused, 10)), "p90": float(np.percentile(nused, 90)),
            "min": int(nused.min()), "max": int(nused.max())}


# ============================================================================ main
def main(seed: int, quick: bool, table: str) -> dict:
    t_start = time.time()
    out = {"meta": {"seed": seed, "quick": quick, "table": table, "girth": girth.__version__ if hasattr(girth, "__version__") else "0.8.0",
                    "numpy": np.__version__, "pandas": pd.__version__, "matching_py": HAVE_MATCHING}}
    df, resp, g, band, raw_full = load_people(table, quick, seed)
    cal = strat_split(g, band, seed)
    sim = ~cal
    out["meta"].update(n=len(df), n_cal=int(cal.sum()), n_sim=int(sim.sum()),
                       missing_cells_sim=int((resp[sim] < 0).sum()))
    log("n", len(df), "cal", cal.sum(), "sim", sim.sum())
    headline_only = table != "main"
    B_boot = 200 if quick else 1000

    # ---------------- calibration
    a, b, diag, a_g, b_g = calibrate(resp[cal])
    P = cat_probs(a, b)
    info = fisher_info(a, b)
    out["calibration"] = {
        "convergence": diag,
        "items": {ITEMS[j]: {"a": round(float(a[j]), 3), "b": [round(float(x), 3) for x in b[j]],
                             "a_girth": round(float(a_g[j]), 3), "b_girth": [round(float(x), 3) for x in b_g[j]],
                             "low_a_flag": bool(a[j] < 0.65), "e2_flag": ITEMS[j] in FLAGGED,
                             "max_info": round(float(info[j].max()), 3),
                             "theta_at_max_info": float(GRID[info[j].argmax()])} for j in range(48)},
    }
    for s in range(6):
        cols = range(8 * s, 8 * s + 8)
        out["calibration"].setdefault("scale_info_at", {})[SCALES[s]] = {
            str(t): round(float(info[list(cols)][:, int(np.argmin(np.abs(GRID - t)))].sum()), 2) for t in (-2, -1, 0, 1, 2)}
    Phi = latent_corr(resp[cal], P)
    out["calibration"]["latent_corr"] = np.round(Phi, 4).tolist()
    log("latent corr\n", np.round(Phi, 2))
    try:
        e2 = json.loads((FINDINGS / "e2_structure.json").read_text())
        phi_e2 = np.array(e2["cfa_half_B"]["factor_corr_by_group"]["half_B"])
        iu = np.triu_indices(6, 1)
        out["calibration"]["latent_corr_vs_e2_cfa"] = {
            "max_abs_diff": round(float(np.abs(Phi - phi_e2)[iu].max()), 4),
            "corr_of_offdiag": round(float(np.corrcoef(Phi[iu], phi_e2[iu])[0, 1]), 4)}
    except Exception as e:  # pragma: no cover
        out["calibration"]["latent_corr_vs_e2_cfa"] = str(e)

    # full-test EAP on calibration (Q3) and reference on simulation
    L_cal = np.stack([scale_loglik(resp[cal][:, 8 * s: 8 * s + 8], P[8 * s: 8 * s + 8]) for s in range(6)], 1)
    _, mu_cal, v_cal = eap_indep(L_cal)
    out["calibration"]["empirical_reliability_full"] = dict(zip(SCALES, np.round(1 - v_cal.mean(0), 4).tolist()))
    if not headline_only:
        q3 = q3_matrix(resp[cal], P, mu_cal)
        q3_out = {}
        for s, Q in q3.items():
            v = Q.to_numpy()
            iu = np.triu_indices(8, 1)
            mean_q3 = v[iu].mean()
            flags = [(Q.index[i], Q.columns[j], round(float(v[i, j]), 3)) for i, j in zip(*iu) if v[i, j] - mean_q3 > 0.20]
            q3_out[s] = {"mean_q3": round(float(mean_q3), 3), "max_q3": round(float(v[iu].max()), 3), "flags": flags,
                         "matrix": np.round(v, 3).tolist()}
        out["calibration"]["q3"] = q3_out
    del L_cal

    # ---------------- simulation reference
    rs = resp[sim]
    n_sim = rs.shape[0]
    L_sim = np.stack([scale_loglik(rs[:, 8 * s: 8 * s + 8], P[8 * s: 8 * s + 8]) for s in range(6)], 1)
    _, theta_full, v_full = eap_indep(L_sim)
    raw_sim = raw_full[sim]
    occ = M.load_occupations() if HAVE_MATCHING else pd.read_parquet(OCC_PATH).rename(columns={"onet_soc_code": "code"})
    methods = ["pearson", "cosine_centered"] if HAVE_MATCHING else ["pearson"]
    fams = {}
    if HAVE_MATCHING:  # E3 families (research/findings/e3_families.csv), joined by O*NET-SOC code
        fcsv = pd.read_csv(FINDINGS / "e3_families.csv").set_index("code")
        for r in ("r80", "r90"):
            fams[r] = fcsv.loc[occ["code"], f"family_{r}"].to_numpy().astype(int)
        out["meta"]["n_families"] = {r: len(np.unique(v)) for r, v in fams.items()}
    rankers = {m: Ranker(occ, m, fams if m == "pearson" else None) for m in methods}
    ref = {"theta_full": theta_full, "raw_full": raw_sim}
    for m, rk in rankers.items():
        ref[f"top10_{m}"] = rk.top(raw_sim, 10)
    for fname, fl in fams.items():
        ref[f"top3fam_{fname}"] = rankers["pearson"].fam_top(raw_sim, fl, 3)
    # theta-metric ranking reference (secondary)
    ref_theta_top10 = rankers["pearson"].top(theta_full, 10)
    gs, bs = g[sim], band[sim]
    diff = raw_sim.max(1) - raw_sim.min(1)
    groups = {f"{gg} {bb}": (gs == gg) & (bs == bb) for gg in ("female", "male") for bb in ("13-17", "18-24", "25+")}
    groups["flat (<1.0)"] = diff < 1.0
    groups["differentiated (>=1.0)"] = diff >= 1.0
    out["groups_n"] = {k: int(v.sum()) for k, v in groups.items()}
    pool_full = np.ones(48, bool)
    pool_red = np.array([it not in FLAGGED for it in ITEMS])
    rng = np.random.default_rng(seed + 1)

    # fixed orders
    def rr_order(rank_within):  # rank_within: (.., 48) rank of each item inside its scale (0 = first)
        return -(rank_within * 6 + SCALE_OF)  # higher = earlier; round-robin R, I, A, S, E, C
    rank_a = np.zeros(48, int)
    for s in range(6):
        cols = np.arange(8 * s, 8 * s + 8)
        rank_a[cols[np.argsort(-a[cols])]] = np.arange(8)
    prio_best = rr_order(rank_a).astype(float)
    rnd = rng.random((n_sim, 48))
    rank_rnd = np.zeros((n_sim, 48), int)
    for s in range(6):
        cols = np.arange(8 * s, 8 * s + 8)
        rank_rnd[:, cols] = np.argsort(np.argsort(rnd[:, cols], 1), 1)
    prio_rand = rr_order(rank_rnd).astype(float)
    out["best_fixed_order"] = [ITEMS[j] for j in np.argsort(-prio_best)]

    def run(kind, pool, prio=None, se_stop=None, resp_=rs, Phi_=Phi):
        t0 = time.time()
        if prio is not None and prio.ndim == 1 and not pool.all():
            prio = np.where(pool, prio, -1e9)
        eng = Engine(resp_, P, info, Phi_, pool, kind, prio, se_stop)
        rec = eng.run()
        drop = {"A": ("muc", "sec", "rawc"), "B": ("mu0", "se0", "raw0")}.get(kind, ())
        for k in drop:  # memory: keep only the scoring the engine uses
            del rec[k]
        log(f"run {kind} pool={int(pool.sum())} se_stop={se_stop}: {time.time() - t0:.0f}s")
        return rec

    variants = {"full": pool_full} if headline_only else {"full": pool_full, "reduced": pool_red}
    curves, head, recs = {}, {}, {}
    pp_store = {}
    for vname, pool in variants.items():
        recs[vname] = {
            "A": run("A", pool), "B": run("B", pool),
            "best": run("fixed", pool, prio_best), "random": run("random", pool, prio_rand),
        }
        cfgs = {"A": ("A", "indep"), "B": ("B", "corr"),
                "best_corr": ("best", "corr"), "best_indep": ("best", "indep"),
                "random_corr": ("random", "corr"), "random_indep": ("random", "indep")}
        kmax = int(pool.sum())
        for cname, (rname, scoring) in cfgs.items():
            cv = {}
            for k in [k for k in K_CURVE if k <= kmax]:
                m, _ = evaluate(*at_k(recs[vname][rname], k, scoring), ref, rankers)
                cv[k] = {kk: vv for kk, vv in m.items() if not kk.endswith("by_scale")}
            curves[f"{vname}:{cname}"] = cv
            log(f"curve {vname}:{cname} k=20:", {kk: round(vv, 3) for kk, vv in cv.get(20, {}).items()})
        for k in K_HEAD:
            for cname, (rname, scoring) in cfgs.items():
                th, raw = at_k(recs[vname][rname], k, scoring)
                m, pp = evaluate(th, raw, ref, rankers)
                t10 = rankers["pearson"].top(th, 10)
                m["top10_pearson_theta_metric"] = float(overlap(t10, ref_theta_top10).mean())
                head[f"{vname}:{cname}:k{k}"] = m
                pp_store[(vname, cname, k)] = (th, raw, pp)
        # Mini-IP-like (5 highest-a per scale, 30 items) scored by raw item means (no IRT)
        if pool.all():
            mini = rank_a < 5  # the 5 highest-a items of each scale
            out["mini_ip_like_items"] = [ITEMS[j] for j in np.where(mini)[0]]
            X = np.where(mini[None, :] & (rs >= 0), rs + 1.0, np.nan)
            raw_mini = np.stack([np.nanmean(X[:, 8 * s: 8 * s + 8], 1) for s in range(6)], 1)
            m, pp = evaluate(raw_mini, raw_mini, ref, rankers)
            head[f"{vname}:miniIP_raw:k30"] = m
            pp_store[(vname, "miniIP_raw", 30)] = (raw_mini, raw_mini, pp)
        del recs[vname]["random"]

    # reduced bank vs a 40-item reference
    if not headline_only:
        L40 = np.stack([scale_loglik(np.where(pool_red[8 * s: 8 * s + 8], rs[:, 8 * s: 8 * s + 8], -1),
                                     P[8 * s: 8 * s + 8]) for s in range(6)], 1)
        _, th40, _ = eap_indep(L40)
        X = np.where(pool_red[None, :] & (rs >= 0), rs + 1.0, np.nan)
        raw40 = np.stack([np.nanmean(X[:, 8 * s: 8 * s + 8], 1) for s in range(6)], 1)
        ref40 = {"theta_full": th40, "raw_full": raw40}
        for mth, rk in rankers.items():
            ref40[f"top10_{mth}"] = rk.top(raw40, 10)
        for fname, fl in fams.items():
            ref40[f"top3fam_{fname}"] = rankers["pearson"].fam_top(raw40, fl, 3)
        out["reduced_bank_vs_40item_reference"] = {}
        for k in K_HEAD:
            for cname, (rname, scoring) in {"A": ("A", "indep"), "B": ("B", "corr"), "best_corr": ("best", "corr")}.items():
                m, _ = evaluate(*at_k(recs["reduced"][rname], k, scoring), ref40, rankers)
                out["reduced_bank_vs_40item_reference"][f"{cname}:k{k}"] = {kk: vv for kk, vv in m.items() if not kk.endswith("by_scale")}
        m40, _ = evaluate(th40, raw40, ref, rankers)
        out["full40_vs_full48"] = {kk: vv for kk, vv in m40.items()}
        del L40
    out["curves"] = curves
    out["fixed_length"] = head

    # ---------------- variable length
    var = {}
    var_store = {}
    for vname in variants:
        recB = recs[vname]["B"]
        kmax = int(variants[vname].sum())
        for t in SE_THRESH:
            cond = (recB["sec"].max(2) < t)
            for cap in CAPS:
                cap_ = min(cap, kmax)
                ks = first_true(cond, 6, cap_)
                th, raw, nu = at_stop(recB, ks, "corr")
                m, pp = evaluate(th, raw, ref, rankers)
                m["items"] = items_summary(nu)
                key = f"{vname}:B_se{t:.2f}_cap{cap}"
                var[key] = m
                var_store[key] = (th, raw, pp, nu)
        # C: top-10 stability (Pearson, on the engine's own predicted raw profile)
        T = recB["rawc"].shape[0] - 1
        tops = np.stack([np.sort(rankers["pearson"].top(recB["rawc"][k].astype(float), 10), 1) for k in range(T + 1)])
        same = np.zeros((T + 1, n_sim), bool)
        same[1:] = (tops[1:] == tops[:-1]).all(2)
        stable3 = np.zeros_like(same)
        stable3[3:] = same[3:] & same[2:-1] & same[1:-2]
        for cap in [20, 30, 40, 48]:
            cap_ = min(cap, kmax)
            ks = first_true(stable3, 12, cap_)
            th, raw, nu = at_stop(recB, ks, "corr")
            m, pp = evaluate(th, raw, ref, rankers)
            m["items"] = items_summary(nu)
            key = f"{vname}:C_stab_cap{cap}"
            var[key] = m
            var_store[key] = (th, raw, pp, nu)
        top3sd = np.take_along_axis(recB["sec"], np.argsort(-recB["rawc"], 2)[:, :, :3], 2).max(2)
        for sd in (0.40, 0.45):
            ks = first_true(stable3 & (top3sd < sd), 12, min(40, kmax))
            th, raw, nu = at_stop(recB, ks, "corr")
            m, pp = evaluate(th, raw, ref, rankers)
            m["items"] = items_summary(nu)
            key = f"{vname}:C_lit_sd{sd:.2f}_cap40"
            var[key] = m
            var_store[key] = (th, raw, pp, nu)
        del tops
        # engine A with per-scale SE stopping (separate runs: selection depends on the threshold)
        if vname == "full" and not headline_only:
            for t in SE_THRESH:
                recA = run("A", variants[vname], se_stop=t)
                done = np.zeros((recA["nadm"].shape[0], n_sim), bool)
                done[1:] = recA["nadm"][1:] == recA["nadm"][:-1]  # no item added -> stopped
                for cap in CAPS:
                    ks = first_true(np.vstack([done[1:], done[-1:]]), 6, cap)
                    th, raw, nu = at_stop(recA, ks, "indep")
                    m, pp = evaluate(th, raw, ref, rankers)
                    m["items"] = items_summary(nu)
                    key = f"{vname}:A_se{t:.2f}_cap{cap}"
                    var[key] = m
                    var_store[key] = (th, raw, pp, nu)
                    if cap == 48:
                        var_store[key + ":order"] = recA["order"]
                del recA
    out["variable_length"] = var
    log("variable-length done")

    # ---------------- secondary bar: CAT vs best fixed (paired bootstrap)
    sec = {}
    for vname in variants:
        for k in K_HEAD:
            best_name = max(["best_corr", "best_indep"], key=lambda c: head[f"{vname}:{c}:k{k}"]["r_theta"])
            thb, rawb, ppb = pp_store[(vname, best_name, k)]
            for cname in ("A", "B"):
                th, raw, pp = pp_store[(vname, cname, k)]
                bt = bootstrap(th, raw, ref, pp, B_boot, seed, thb, rawb, ppb)
                sec[f"{vname}:{cname}:k{k}_vs_{best_name}"] = bt["diff_vs_comparator"]
                if k == 20:
                    head[f"{vname}:{cname}:k{k}"]["ci"] = {kk: vv for kk, vv in bt.items() if kk != "diff_vs_comparator"}
            head[f"{vname}:{best_name}:k{k}"]["ci"] = {kk: vv for kk, vv in bootstrap(thb, rawb, ref, ppb, B_boot, seed).items()}
        for key in [kk for kk in var if kk.startswith(vname)]:
            th, raw, pp, nu = var_store[key]
            kk = int(round(nu.mean()))
            kk = min(max(kk, 6), 48 if vname == "full" else 40)
            best_rec = recs[vname]["best"]
            thb, rawb = at_k(best_rec, kk, "corr")
            _, ppb = evaluate(thb, rawb, ref, rankers)
            bt = bootstrap(th, raw, ref, pp, B_boot // 2, seed, thb, rawb, ppb)
            var[key]["ci"] = {k2: v2 for k2, v2 in bt.items() if k2 != "diff_vs_comparator"}
            var[key]["vs_best_fixed_same_mean_length"] = {"k": kk, **{k2: bt["diff_vs_comparator"][k2] for k2 in
                                                                       ("r_theta", "top10_pearson", "top3_pearson")}}
    out["secondary_bar"] = sec
    log("bootstrap done")

    # ---------------- group breakdowns
    grp = {}
    for key, (rname, scoring, k) in {"B:k20": ("B", "corr", 20), "A:k20": ("A", "indep", 20),
                                     "best_corr:k20": ("best", "corr", 20), "B:k12": ("B", "corr", 12),
                                     "B:k30": ("B", "corr", 30)}.items():
        th, raw = at_k(recs["full"][rname], k, scoring)
        grp[key] = {gname: {kk: vv for kk, vv in evaluate(th, raw, ref, rankers, mask)[0].items() if not kk.endswith("by_scale")}
                    for gname, mask in groups.items()}
    for key in [kk for kk in var if kk.startswith("full:") and ("C_lit_sd0.40" in kk or "B_se0.40_cap30" in kk or "C_stab_cap20" in kk)]:
        th, raw, pp, nu = var_store[key]
        grp[key.replace("full:", "")] = {gname: {**{kk: vv for kk, vv in evaluate(th, raw, ref, rankers, mask)[0].items()
                                                    if not kk.endswith("by_scale")}, "items_mean": float(nu[mask].mean())}
                                         for gname, mask in groups.items()}
    grp["curves_B_top10"] = {gname: {k: float(evaluate(*at_k(recs["full"]["B"], k, "corr"), ref, {"pearson": rankers["pearson"]}, mask)[0]["top10_pearson"])
                                     for k in (6, 12, 18, 24, 30, 36, 42, 48)} for gname, mask in groups.items()}
    grp["curves_B_rtheta"] = {gname: {k: float(evaluate(*at_k(recs["full"]["B"], k, "corr"), ref, {}, mask)[0]["r_theta"])
                                      for k in (6, 12, 18, 24, 30, 36, 42, 48)} for gname, mask in groups.items()}
    out["groups"] = grp

    # full-test SE and lost-user indicators
    se_full = np.sqrt(v_full)
    out["full_test_se"] = {"mean_by_scale": dict(zip(SCALES, np.round(se_full.mean(0), 3).tolist())),
                           "share_max_se_ge_0.40": round(float((se_full.max(1) >= 0.40).mean()), 4),
                           "share_max_se_ge_0.30": round(float((se_full.max(1) >= 0.30).mean()), 4)}
    recB = recs["full"]["B"]
    lost = {}
    for k in (12, 20):
        th, raw = at_k(recB, k, "corr")
        dk = raw.max(1) - raw.min(1)
        maxse = recB["sec"][k].max(1)
        flat_pred = dk < 1.0
        _, ppk = evaluate(th, raw, ref, rankers)
        lost[f"k{k}"] = {
            "pred_flat_share": round(float(flat_pred.mean()), 4),
            "sens_for_full_flat": round(float(flat_pred[groups["flat (<1.0)"]].mean()), 4),
            "ppv": round(float(groups["flat (<1.0)"][flat_pred].mean()), 4) if flat_pred.any() else None,
            "top10_if_pred_flat": round(float(ppk["top10_pearson"][flat_pred].mean()), 4),
            "top10_if_not_pred_flat": round(float(ppk["top10_pearson"][~flat_pred].mean()), 4),
            "corr_top10_with_pred_diff": round(float(np.corrcoef(ppk["top10_pearson"], dk)[0, 1]), 4),
            "corr_top10_with_maxse": round(float(np.corrcoef(ppk["top10_pearson"], maxse)[0, 1]), 4),
            "top10_by_pred_diff_quintile": [round(float(ppk["top10_pearson"][(dk >= lo) & (dk <= hi)].mean()), 4)
                                            for lo, hi in zip(np.percentile(dk, [0, 20, 40, 60, 80]), np.percentile(dk, [20, 40, 60, 80, 100]))],
            "pred_diff_quintile_edges": np.round(np.percentile(dk, [0, 20, 40, 60, 80, 100]), 3).tolist(),
        }
    # full-test flat: how often top-10 agrees at k=20 and full; already in groups
    out["lost_user"] = lost

    # item usage
    usage = {}
    for key, ordr, k in [("B_first20", recs["full"]["B"]["order"], 20), ("A_first20", recs["full"]["A"]["order"], 20),
                         ("B_first12", recs["full"]["B"]["order"], 12)]:
        o = ordr[:, :k]
        usage[key] = {ITEMS[j]: round(float((o == j).any(1).mean()), 4) for j in range(48)}
    for key in [kk for kk in var_store if kk.startswith("full:C_lit_sd0.40") and not kk.endswith(":order")]:
        nu = var_store[key][3]
        ks = nu  # number administered; B order is shared
        o = recs["full"]["B"]["order"]
        mask = np.arange(48)[None, :] < ks[:, None]
        usage["C_lit_sd0.40_cap40"] = {ITEMS[j]: round(float(((o == j) & mask).any(1).mean()), 4) for j in range(48)}
    usage["B_first_item_after_starters"] = pd.Series(recs["full"]["B"]["order"][:, 6]).map(lambda j: ITEMS[j] if j >= 0 else None).value_counts(normalize=True).round(4).head(10).to_dict()
    out["item_usage"] = usage
    out["B_scale_allocation_first20"] = dict(zip(SCALES, np.round(np.stack([np.isin(recs["full"]["B"]["order"][:, :20], np.arange(8 * s, 8 * s + 8)).sum(1) for s in range(6)], 1).mean(0), 2).tolist()))
    out["B_scale_allocation_by_group_first20"] = {gname: dict(zip(SCALES, np.round(np.stack([np.isin(recs["full"]["B"]["order"][mask, :20], np.arange(8 * s, 8 * s + 8)).sum(1) for s in range(6)], 1).mean(0), 2).tolist()))
                                                  for gname, mask in groups.items()}

    # ---------------- synthetic check (known theta)
    if not headline_only:
        n_syn = 3000 if quick else 10000
        rng2 = np.random.default_rng(seed + 7)
        th_true = rng2.multivariate_normal(np.zeros(6), Phi, n_syn)
        cum = expit(a[None, :, None] * (th_true[:, SCALE_OF][:, :, None] - b[None, :, :]))
        u = rng2.random((n_syn, 48))
        syn = (u[:, :, None] < cum).sum(2).astype(np.int8)
        Ls = np.stack([scale_loglik(syn[:, 8 * s: 8 * s + 8], P[8 * s: 8 * s + 8]) for s in range(6)], 1)
        _, th_full_syn, _ = eap_indep(Ls)
        raw_full_syn = (syn + 1.0).reshape(n_syn, 6, 8).mean(2)
        escore = (P * np.arange(1, 6)[None, None, :]).sum(2)
        raw_true = np.stack([np.stack([np.interp(th_true[:, s], GRID, escore[j]) for j in range(8 * s, 8 * s + 8)], 1).mean(1) for s in range(6)], 1)
        ref_syn = {"theta_full": th_full_syn, "raw_full": raw_full_syn}
        ref_true = {"theta_full": th_true, "raw_full": raw_true}
        for mth, rk in rankers.items():
            ref_syn[f"top10_{mth}"] = rk.top(raw_full_syn, 10)
            ref_true[f"top10_{mth}"] = rk.top(raw_true, 10)
        for fname, fl in fams.items():
            ref_syn[f"top3fam_{fname}"] = rankers["pearson"].fam_top(raw_full_syn, fl, 3)
            ref_true[f"top3fam_{fname}"] = rankers["pearson"].fam_top(raw_true, fl, 3)
        rnd2 = rng2.random((n_syn, 48))
        rank2 = np.zeros((n_syn, 48), int)
        for s in range(6):
            cols = np.arange(8 * s, 8 * s + 8)
            rank2[:, cols] = np.argsort(np.argsort(rnd2[:, cols], 1), 1)
        synres = {}
        srec = {"A": run("A", pool_full, resp_=syn), "B": run("B", pool_full, resp_=syn),
                "best": run("fixed", pool_full, prio_best, resp_=syn),
                "random": run("random", pool_full, rr_order(rank2).astype(float), resp_=syn)}
        for cname, (rname, scoring) in {"A": ("A", "indep"), "B": ("B", "corr"), "best_corr": ("best", "corr"),
                                        "random_corr": ("random", "corr")}.items():
            for k in (6, 12, 20, 30, 48):
                th, raw = at_k(srec[rname], k, scoring)
                m_full, _ = evaluate(th, raw, ref_syn, rankers)
                m_true, _ = evaluate(th, raw, ref_true, rankers)
                synres[f"{cname}:k{k}"] = {
                    "vs_full": {kk: vv for kk, vv in m_full.items() if not kk.endswith("by_scale")},
                    "vs_true": {kk: vv for kk, vv in m_true.items() if not kk.endswith("by_scale")}}
        m, _ = evaluate(th_full_syn, raw_full_syn, ref_true, rankers)
        synres["full48_vs_true"] = {kk: vv for kk, vv in m.items() if not kk.endswith("by_scale")}
        out["synthetic"] = synres
        out["synthetic_curves"] = {cname: {k: evaluate(*at_k(srec[rname], k, scoring), ref_syn, {"pearson": rankers["pearson"]})[0]
                                           for k in K_CURVE} for cname, (rname, scoring) in
                                   {"A": ("A", "indep"), "B": ("B", "corr"), "best_corr": ("best", "corr"),
                                    "random_corr": ("random", "corr")}.items()}
        for c in out["synthetic_curves"].values():
            for k in c:
                c[k] = {kk: vv for kk, vv in c[k].items() if not kk.endswith("by_scale")}
        log("synthetic done")

    # ---------------- plots
    if not headline_only:
        make_plots(out, recs, var_store, n_sim, quick)
    out["meta"]["seconds"] = round(time.time() - t_start, 1)
    return out


# ============================================================================ plots
def make_plots(out, recs, var_store, n_sim, quick):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    sfx = "_quick" if quick else ""
    curves = out["curves"]
    style = {"full:A": ("A: max-info, indep.", "C0", "-"), "full:B": ("B: corr. prior, var-reduction", "C3", "-"),
             "full:best_corr": ("best fixed k (by a)", "C2", "--"), "full:random_corr": ("random fixed k", "C7", ":"),
             "reduced:B": ("B, bank w/o 8 flagged", "C1", "-."), "reduced:best_corr": ("best fixed, w/o flagged", "C8", "-.")}
    for metric, fname, ylab, bar in [("r_theta", "e4_items_vs_r.png", "mean r(theta_short, theta_full) over 6 scales", 0.90),
                                     ("top10_pearson", "e4_items_vs_top10.png", "mean top-10 overlap with full test (Pearson)", 0.70),
                                     ("top3fam_r80", "e4_items_vs_top3families.png",
                                      "top-3 family overlap with full test (E3 r>=.80 families; dashed = E5 ceiling .60)", 0.60)]:
        fig, ax = plt.subplots(figsize=(7.5, 5))
        for key, (lab, col, ls) in style.items():
            cv = curves[key]
            ks = sorted(cv)
            ax.plot(ks, [cv[k][metric] for k in ks], ls, color=col, label=lab, marker="o", ms=3)
        mini = out["fixed_length"].get("full:miniIP_raw:k30")
        if mini:
            ax.plot([30], [mini[metric]], "k*", ms=12, label="Mini-IP-like 30, raw means")
        ax.axhline(bar, color="k", lw=0.8, ls="--")
        ax.axvline(20, color="k", lw=0.8, ls=":")
        ax.set_xlabel("items administered (k)")
        ax.set_ylabel(ylab)
        ax.set_title(f"E4: items vs {metric} (simulation set n = {n_sim:,}, real answers)")
        ax.legend(fontsize=8)
        ax.grid(alpha=0.3)
        fig.tight_layout()
        fig.savefig(FINDINGS / fname.replace(".png", f"{sfx}.png"), dpi=130)
        plt.close(fig)

    # histograms of items used
    keys = ["full:B_se0.30_cap48", "full:B_se0.40_cap48", "full:B_se0.50_cap48", "full:A_se0.40_cap48",
            "full:C_stab_cap30", "full:C_lit_sd0.40_cap40"]
    keys = [k for k in keys if k in var_store]
    fig, axes = plt.subplots(2, 3, figsize=(12, 6.5), sharex=True)
    for ax, k in zip(axes.ravel(), keys):
        nu = var_store[k][3]
        ax.hist(nu, bins=np.arange(5.5, 49.5, 1), color="C0")
        m = out["variable_length"][k]
        ax.set_title(f"{k.replace('full:', '')}\nmedian {np.median(nu):.0f}, top-10 {m['top10_pearson']:.2f}, r {m['r_theta']:.3f}", fontsize=9)
        ax.set_xlabel("items used")
    fig.suptitle(f"E4: items used per stopping rule (n = {n_sim:,})")
    fig.tight_layout()
    fig.savefig(FINDINGS / f"e4_items_used_hist{sfx}.png", dpi=130)
    plt.close(fig)

    # per-group curves
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.8))
    for ax, key, ylab in [(axes[0], "curves_B_rtheta", "mean r(theta, theta_full)"), (axes[1], "curves_B_top10", "top-10 overlap")]:
        for i, (gname, cv) in enumerate(out["groups"][key].items()):
            ks = sorted(cv, key=int)
            ax.plot([int(k) for k in ks], [cv[k] for k in ks], marker="o", ms=3,
                    ls="--" if "flat" in gname or "differ" in gname else "-", label=f"{gname} (n={out['groups_n'][gname]:,})")
        ax.set_xlabel("items administered (engine B)")
        ax.set_ylabel(ylab)
        ax.grid(alpha=0.3)
    axes[1].legend(fontsize=7)
    fig.suptitle("E4: engine B by gender x age band and profile flatness (r is within-group, so range-restricted)")
    fig.tight_layout()
    fig.savefig(FINDINGS / f"e4_group_curves{sfx}.png", dpi=130)
    plt.close(fig)

    # item usage
    us = out["item_usage"]
    fig, ax = plt.subplots(figsize=(13, 4.5))
    x = np.arange(48)
    w = 0.27
    for i, (k, col) in enumerate([("A_first20", "C0"), ("B_first20", "C3"), ("C_lit_sd0.40_cap40", "C1")]):
        if k in us:
            ax.bar(x + (i - 1) * w, [us[k][it] for it in ITEMS], w, color=col, label=k)
    ax.set_xticks(x)
    ax.set_xticklabels(ITEMS, rotation=90, fontsize=7)
    for j, it in enumerate(ITEMS):
        if it in FLAGGED:
            ax.get_xticklabels()[j].set_color("red")
    ax.set_ylabel("share of simulees administered")
    ax.set_title(f"E4: item usage frequency (red = E2-flagged items; n = {n_sim:,})")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(FINDINGS / f"e4_item_usage{sfx}.png", dpi=130)
    plt.close(fig)

    # synthetic vs real
    if "synthetic_curves" in out:
        fig, axes = plt.subplots(1, 2, figsize=(12, 4.8))
        for ax, metric in zip(axes, ["r_theta", "top10_pearson"]):
            for cname, col in [("A", "C0"), ("B", "C3"), ("best_corr", "C2"), ("random_corr", "C7")]:
                cv = out["synthetic_curves"][cname]
                ks = sorted(cv)
                ax.plot(ks, [cv[k][metric] for k in ks], "--", color=col, label=f"{cname} synthetic")
                rc = out["curves"][f"full:{cname}"]
                ax.plot(sorted(rc), [rc[k][metric] for k in sorted(rc)], "-", color=col, label=f"{cname} real")
            ax.set_xlabel("items administered")
            ax.set_ylabel(metric + " vs own full test")
            ax.grid(alpha=0.3)
        axes[0].legend(fontsize=7)
        fig.suptitle("E4: model-generated (synthetic, dashed) vs real replayed answers (solid)")
        fig.tight_layout()
        fig.savefig(FINDINGS / f"e4_synthetic_vs_real{sfx}.png", dpi=130)
        plt.close(fig)


def _jsonable(o):
    if isinstance(o, dict):
        return {str(k): _jsonable(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_jsonable(v) for v in o]
    if isinstance(o, (np.floating,)):
        return round(float(o), 5)
    if isinstance(o, float):
        return round(o, 5)
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, np.bool_):
        return bool(o)
    if isinstance(o, np.ndarray):
        return _jsonable(o.tolist())
    return o


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--quick", action="store_true", help="subsample 8,000 people for a smoke run")
    ap.add_argument("--table", choices=list(TABLES), default="main")
    args = ap.parse_args()
    res = _jsonable(main(args.seed, args.quick, args.table))
    FINDINGS.mkdir(parents=True, exist_ok=True)
    name = "e4_cat_simulation" + ("" if args.table == "main" else f"_{args.table}") + ("_quick" if args.quick else "")
    (FINDINGS / f"{name}.json").write_text(json.dumps(res, indent=1))
    log(f"wrote {name}.json")
