"""E2 — Factor structure, hexagon fit, invariance and interest archetypes.

Run:  .venv/Scripts/python -I research/feasibility/e2_structure.py [--seed 42] [--quick]

Pre-registration and results: research/findings/e2_structure.md
Outputs: research/findings/e2_structure.json and research/findings/e2_*.png
"""
from __future__ import annotations

import argparse
import itertools
import json
import time
import warnings
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import factor_analyzer.factor_analyzer as _fa_mod
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from factor_analyzer import FactorAnalyzer
from scipy.optimize import linear_sum_assignment, minimize
from sklearn.manifold import MDS
from sklearn.metrics import adjusted_rand_score
from sklearn.mixture import GaussianMixture
from sklearn.utils import check_array as _sk_check_array


def _check_array_compat(*args, force_all_finite=None, **kw):
    """factor_analyzer 0.5.1 passes `force_all_finite`, renamed `ensure_all_finite` in scikit-learn >= 1.6."""
    if force_all_finite is not None:
        kw["ensure_all_finite"] = force_all_finite
    return _sk_check_array(*args, **kw)


_fa_mod.check_array = _check_array_compat  # runtime shim only; no package files are modified

warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning)

ROOT = Path(__file__).resolve().parents[2]
FINDINGS = ROOT / "research" / "findings"
DATA_MAIN = ROOT / "data" / "processed" / "riasec_people.parquet"
DATA_INCL = ROOT / "data" / "processed" / "riasec_people_incl_shared_network.parquet"

SCALES = list("RIASEC")
ITEMS = [f"{s}{i}" for s in SCALES for i in range(1, 9)]
ITEM_SCALE = np.repeat(np.arange(6), 8)
ANGLES = np.deg2rad(np.arange(6) * 60.0)  # R=0, I=60, A=120, S=180, E=240, C=300
SU2009_D = {"R": 0.84, "I": 0.26, "A": -0.35, "S": -0.68, "E": None, "C": -0.33, "things_people": 0.93}
AGE_BANDS = {"13-17": (13, 17), "18-24": (18, 24), "25+": (25, 200)}


def rnd(x, k=3):
    if isinstance(x, dict):
        return {kk: rnd(v, k) for kk, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [rnd(v, k) for v in x]
    if isinstance(x, (np.floating, float)):
        return None if not np.isfinite(x) else round(float(x), k)
    if isinstance(x, np.integer):
        return int(x)
    if isinstance(x, np.ndarray):
        return rnd(x.tolist(), k)
    return x


# --------------------------------------------------------------------------- data
def load(path: Path) -> pd.DataFrame:
    df = pd.read_parquet(path)
    df[ITEMS] = df[ITEMS].replace(0, np.nan).astype(float)
    df["elevation"] = df[SCALES].mean(axis=1)
    df["differentiation"] = df[SCALES].max(axis=1) - df[SCALES].min(axis=1)
    cen = df[SCALES].to_numpy() - df["elevation"].to_numpy()[:, None]
    df["prediger_x"] = cen @ np.cos(ANGLES)  # Things (+) vs People (-)
    df["prediger_y"] = cen @ np.sin(ANGLES)  # Ideas (+) vs Data (-)
    # vendor (Strong supplement, note 01) secondary comparison, on raw scale means
    s = {k: df[k] for k in SCALES}
    df["vendor_pt"] = 2 * s["R"] + s["I"] - s["A"] - 2 * s["S"] - s["E"] + s["C"]
    df["vendor_di"] = 1.73 * s["E"] + 1.73 * s["C"] - 1.73 * s["I"] - 1.73 * s["A"]
    df["age_band"] = pd.cut(df["age"], [12, 17, 24, 200], labels=list(AGE_BANDS))
    df["sex"] = df["gender"].map({1.0: "male", 2.0: "female"})
    return df


def item_corr(df: pd.DataFrame) -> np.ndarray:
    return df[ITEMS].corr().to_numpy()


# --------------------------------------------------------------------------- factor retention
def parallel_analysis(n: int, p: int, R: np.ndarray, iters: int, rng) -> dict:
    obs_pca = np.sort(np.linalg.eigvalsh(R))[::-1]
    smc = 1 - 1 / np.diag(np.linalg.inv(R))
    Rr = R.copy()
    np.fill_diagonal(Rr, smc)
    obs_fa = np.sort(np.linalg.eigvalsh(Rr))[::-1]
    rand_pca, rand_fa = [], []
    for _ in range(iters):
        Z = rng.standard_normal((n, p)).astype(np.float32)
        Rz = np.corrcoef(Z, rowvar=False)
        rand_pca.append(np.sort(np.linalg.eigvalsh(Rz))[::-1])
        smc_z = 1 - 1 / np.diag(np.linalg.inv(Rz))
        np.fill_diagonal(Rz, smc_z)
        rand_fa.append(np.sort(np.linalg.eigvalsh(Rz))[::-1])
    p95_pca = np.percentile(rand_pca, 95, axis=0)
    p95_fa = np.percentile(rand_fa, 95, axis=0)

    def n_retained(obs, ref):
        k = 0
        while k < len(obs) and obs[k] > ref[k]:
            k += 1
        return k

    return {
        "obs_pca": obs_pca, "rand95_pca": p95_pca, "obs_fa": obs_fa, "rand95_fa": p95_fa,
        "n_pca": n_retained(obs_pca, p95_pca), "n_fa": n_retained(obs_fa, p95_fa),
        "n_kaiser": int((obs_pca > 1).sum()),
    }


def velicer_map(R: np.ndarray, max_m: int = 12) -> dict:
    p = R.shape[0]
    vals, vecs = np.linalg.eigh(R)
    order = np.argsort(vals)[::-1]
    vals, vecs = vals[order], vecs[:, order]
    loads = vecs * np.sqrt(np.clip(vals, 0, None))
    off = ~np.eye(p, dtype=bool)
    out = [np.mean(R[off] ** 2)]
    for m in range(1, max_m + 1):
        A = loads[:, :m]
        C = R - A @ A.T
        d = np.sqrt(np.diag(C))
        P = C / np.outer(d, d)
        out.append(np.mean(P[off] ** 2))
    return {"map": out, "n_map": int(np.argmin(out))}


# --------------------------------------------------------------------------- EFA
def efa(R: np.ndarray, n_factors: int, rotation: str):
    fa = FactorAnalyzer(n_factors=n_factors, rotation=rotation, method="minres", is_corr_matrix=True)
    fa.fit(R)
    L = fa.loadings_.copy()
    phi = getattr(fa, "phi_", None)
    phi = np.eye(n_factors) if phi is None else phi.copy()
    if n_factors == 6:
        # match factors to scales (Hungarian on mean loading of each scale's items)
        M = np.array([[L[ITEM_SCALE == s, f].mean() for f in range(6)] for s in range(6)])
        rows, cols = linear_sum_assignment(-np.abs(M))
        perm = cols[np.argsort(rows)]
        sign = np.sign(M[np.arange(6), perm])
        sign[sign == 0] = 1
        L = L[:, perm] * sign
        phi = phi[np.ix_(perm, perm)] * np.outer(sign, sign)
    return L, phi


def item_table(L: np.ndarray) -> tuple[list[dict], int]:
    rows, n_ok = [], 0
    for i, it in enumerate(ITEMS):
        s = ITEM_SCALE[i]
        absl = np.abs(L[i])
        top = int(np.argmax(absl))
        ok = (top == s) and (L[i, s] >= 0.40)
        n_ok += ok
        other = np.delete(absl, s)
        cross = [SCALES[j] for j in range(6) if j != s and absl[j] >= 0.30]
        rows.append({"item": it, "intended": SCALES[s], "loading_intended": L[i, s],
                     "primary_factor": SCALES[top], "max_other_abs": other.max(),
                     "cross_loadings_ge_.30": cross, "loads_correctly": bool(ok)})
    return rows, int(n_ok)


def tucker(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    return (a * b).sum(0) / np.sqrt((a**2).sum(0) * (b**2).sum(0))


# --------------------------------------------------------------------------- reliability
def reliability(df: pd.DataFrame) -> dict:
    out = {}
    for s in SCALES:
        cols = [f"{s}{i}" for i in range(1, 9)]
        X = df[cols].dropna().to_numpy()
        k = X.shape[1]
        alpha = k / (k - 1) * (1 - X.var(0, ddof=1).sum() / X.sum(1).var(ddof=1))
        R = np.corrcoef(X, rowvar=False)
        fa = FactorAnalyzer(n_factors=1, rotation=None, method="minres", is_corr_matrix=True).fit(R)
        lam = np.abs(fa.loadings_[:, 0])
        omega = lam.sum() ** 2 / (lam.sum() ** 2 + (1 - lam**2).sum())
        tot = X.sum(1)
        irr, aid = {}, {}
        for j, c in enumerate(cols):
            rest = tot - X[:, j]
            irr[c] = np.corrcoef(X[:, j], rest)[0, 1]
            Xd = np.delete(X, j, axis=1)
            aid[c] = (k - 1) / (k - 2) * (1 - Xd.var(0, ddof=1).sum() / Xd.sum(1).var(ddof=1))
        out[s] = {"n": len(X), "alpha": alpha, "omega_total": omega, "item_rest_r": irr,
                  "alpha_if_deleted": aid, "one_factor_loadings": dict(zip(cols, lam))}
    return out


# --------------------------------------------------------------------------- CFA (ML, numpy)
class MultiGroupCFA:
    """Independent-clusters CFA, 6 correlated factors, ML on covariance (+ mean) structure.

    level: 'configural' | 'metric' | 'scalar'. Group 0 is the reference (factor variances 1, means 0).
    """

    def __init__(self, covs, means, ns, level):
        self.S, self.m, self.n = [np.asarray(c) for c in covs], [np.asarray(x) for x in means], np.asarray(ns, float)
        self.G, self.p, self.level = len(covs), covs[0].shape[0], level
        self.w = self.n / self.n.sum()
        p, G = self.p, self.G
        k = 0

        def take(shape):
            nonlocal k
            idx = np.arange(k, k + int(np.prod(shape))).reshape(shape)
            k += int(np.prod(shape))
            return idx

        self.lam = [take((p,))] * G if level in ("metric", "scalar") else [take((p,)) for _ in range(G)]
        self.psi = [take((p,)) for _ in range(G)]
        tri = [(i, j) for i in range(6) for j in range(i + 1, 6)]
        self.tri = tri
        self.phi_off = [take((15,)) for _ in range(G)]
        self.phi_var = [None] + [take((6,)) if level != "configural" else None for _ in range(G - 1)]
        if level == "scalar":
            self.tau = [take((p,))] * G
            self.kap = [None] + [take((6,)) for _ in range(G - 1)]
        else:
            self.tau, self.kap = None, None
        self.k = k

    def start(self, lam0, psi0, phi0):
        th = np.zeros(self.k)
        for g in range(self.G):
            th[self.lam[g]] = lam0[g]
            th[self.psi[g]] = np.log(np.clip(psi0[g], 1e-3, None))
            th[self.phi_off[g]] = [phi0[g][i, j] for i, j in self.tri]
            if self.phi_var[g] is not None:
                th[self.phi_var[g]] = np.log(1.0)
        if self.tau is not None:
            th[self.tau[0]] = np.average(np.array(self.m), axis=0, weights=self.w)
        return th

    def unpack(self, th, g):
        L = np.zeros((self.p, 6))
        L[np.arange(self.p), ITEM_SCALE] = th[self.lam[g]]
        psi = np.exp(th[self.psi[g]])
        Phi = np.eye(6)
        if self.phi_var[g] is not None:
            sd = np.exp(0.5 * th[self.phi_var[g]])
        else:
            sd = np.ones(6)
        for v, (i, j) in zip(th[self.phi_off[g]], self.tri):
            Phi[i, j] = Phi[j, i] = v
        Phi = Phi * np.outer(sd, sd)  # off-diagonal params are correlations
        mu = None
        if self.tau is not None:
            kap = np.zeros(6) if self.kap[g] is None else th[self.kap[g]]
            mu = th[self.tau[g]] + L @ kap
        return L, psi, Phi, sd, mu

    def f_and_grad(self, th):
        F, grad = 0.0, np.zeros_like(th)
        for g in range(self.G):
            L, psi, Phi, sd, mu = self.unpack(th, g)
            Sig = L @ Phi @ L.T + np.diag(psi)
            try:
                cf = np.linalg.cholesky(Sig)
            except np.linalg.LinAlgError:
                return 1e10, np.zeros_like(th)
            Si = np.linalg.inv(Sig)
            W = self.S[g].copy()
            d = None
            if mu is not None:
                d = self.m[g] - mu
                W = W + np.outer(d, d)
            logdet = 2 * np.log(np.diag(cf)).sum()
            Fg = logdet + np.trace(W @ Si) - self.logdetS(g) - self.p
            Gm = Si - Si @ W @ Si
            wg = self.w[g]
            F += wg * Fg
            gL = 2 * Gm @ L @ Phi
            if d is not None:
                v = -2 * Si @ d
                kap = np.zeros(6) if self.kap[g] is None else th[self.kap[g]]
                gL = gL + np.outer(v, kap)
                np.add.at(grad, self.tau[g], wg * v)
                if self.kap[g] is not None:
                    np.add.at(grad, self.kap[g], wg * (L.T @ v))
            np.add.at(grad, self.lam[g], wg * gL[np.arange(self.p), ITEM_SCALE])
            np.add.at(grad, self.psi[g], wg * np.diag(Gm) * psi)
            gPhi = L.T @ Gm @ L
            offv = np.array([2 * gPhi[i, j] * sd[i] * sd[j] for i, j in self.tri])
            np.add.at(grad, self.phi_off[g], wg * offv)
            if self.phi_var[g] is not None:
                # d Phi_ij / d log var_i = 0.5 Phi_ij (i != j), Phi_ii (i == j)
                gv = np.array([gPhi[i, i] * Phi[i, i] + sum(gPhi[i, j] * Phi[i, j] for j in range(6) if j != i)
                               for i in range(6)])
                np.add.at(grad, self.phi_var[g], wg * gv)
        return F, grad

    def logdetS(self, g):
        if not hasattr(self, "_lds"):
            self._lds = [np.linalg.slogdet(s)[1] for s in self.S]
        return self._lds[g]

    def fit(self, th0):
        res = minimize(self.f_and_grad, th0, jac=True, method="L-BFGS-B",
                       options={"maxiter": 5000, "maxfun": 20000, "ftol": 1e-12, "gtol": 1e-7})
        self.th, self.res = res.x, res
        return self

    def fit_indices(self):
        N = self.n.sum()
        moments = self.G * self.p * (self.p + 1) / 2 + (self.G * self.p if self.level == "scalar" else 0)
        n_par = self.k  # all free parameters; scalar adds shared intercepts (p) and latent means (6 per non-ref group)
        df = moments - n_par
        chi2 = N * self.res.fun
        chi2_0 = sum(n * (np.log(np.diag(S)).sum() - self.logdetS(g)) for g, (n, S) in enumerate(zip(self.n, self.S)))
        df_0 = self.G * self.p * (self.p - 1) / 2
        rmsea = np.sqrt(self.G) * np.sqrt(max(0.0, (chi2 - df) / (df * N)))
        cfi = 1 - max(chi2 - df, 0) / max(chi2_0 - df_0, chi2 - df, 1e-9)
        srmr = []
        for g in range(self.G):
            L, psi, Phi, sd, mu = self.unpack(self.th, g)
            Sig = L @ Phi @ L.T + np.diag(psi)
            s = np.sqrt(np.diag(self.S[g]))
            Rres = (self.S[g] - Sig) / np.outer(s, s)
            iu = np.triu_indices(self.p)
            srmr.append(np.sqrt(np.mean(Rres[iu] ** 2)))
        return {"chi2": chi2, "df": int(df), "cfi": cfi, "rmsea": rmsea,
                "srmr": float(np.average(srmr, weights=self.w)), "converged": bool(self.res.success),
                "n_params": int(self.k)}

    def std_solution(self, g):
        L, psi, Phi, sd, mu = self.unpack(self.th, g)
        Sig = L @ Phi @ L.T + np.diag(psi)
        lam_std = L[np.arange(self.p), ITEM_SCALE] * sd[ITEM_SCALE] / np.sqrt(np.diag(Sig))
        D = np.diag(1 / sd)
        return lam_std, D @ Phi @ D

    def latent_means(self):
        if self.level != "scalar":
            return None
        return [np.zeros(6)] + [self.th[self.kap[g]] for g in range(1, self.G)]


def cfa_start(dfs):
    lam0, psi0, phi0 = [], [], []
    for d in dfs:
        S = d[ITEMS].cov().to_numpy()
        sds = np.sqrt(np.diag(S))
        lam = np.zeros(48)
        for s in range(6):
            idx = np.where(ITEM_SCALE == s)[0]
            R = np.corrcoef(d[[ITEMS[i] for i in idx]].dropna().to_numpy(), rowvar=False)
            fa = FactorAnalyzer(n_factors=1, rotation=None, method="minres", is_corr_matrix=True).fit(R)
            lam[idx] = np.abs(fa.loadings_[:, 0]) * sds[idx]
        lam0.append(lam)
        psi0.append(np.diag(S) - lam**2)
        phi0.append(np.clip(d[SCALES].corr().to_numpy() * 1.15, -0.95, 0.95))  # rough disattenuation as start
    return lam0, psi0, phi0


def run_cfa_ladder(dfs: list[pd.DataFrame], names: list[str]) -> dict:
    covs = [d[ITEMS].cov().to_numpy() for d in dfs]
    means = [d[ITEMS].mean().to_numpy() for d in dfs]
    ns = [len(d) for d in dfs]
    lam0, psi0, phi0 = cfa_start(dfs)
    out, prev = {}, None
    for level in ("configural", "metric", "scalar"):
        m = MultiGroupCFA(covs, means, ns, level)
        if level == "configural":
            th0 = m.start(lam0, psi0, phi0)
        else:
            # warm start from the previous level: average loadings over groups
            th0 = m.start([np.mean(lam0, 0)] * len(dfs), psi0, phi0)
            for g in range(len(dfs)):
                Lp, psip, Phip, sdp, _ = prev.unpack(prev.th, g)
                th0[m.psi[g]] = np.log(psip)
            th0[m.lam[0]] = np.mean([prev.unpack(prev.th, g)[0][np.arange(48), ITEM_SCALE] for g in range(len(dfs))], 0)
        t = time.time()
        m.fit(th0)
        fi = m.fit_indices()
        fi["seconds"] = round(time.time() - t, 1)
        if level != "configural":
            fi["delta_cfi"] = fi["cfi"] - out[prev.level]["cfi"]
            fi["delta_rmsea"] = fi["rmsea"] - out[prev.level]["rmsea"]
            fi["step_acceptable"] = bool(fi["delta_cfi"] >= -0.010 and fi["delta_rmsea"] <= 0.015)
        if level == "configural":
            fi["std_loadings_by_group"] = {n: dict(zip(ITEMS, m.std_solution(g)[0])) for g, n in enumerate(names)}
            fi["factor_corr_by_group"] = {n: m.std_solution(g)[1] for g, n in enumerate(names)}
        if level == "scalar":
            lm = m.latent_means()
            fi["latent_means_vs_" + names[0]] = {n: dict(zip(SCALES, lm[g] / m.unpack(m.th, 0)[3]))
                                                 for g, n in enumerate(names)}
            fi["latent_means_note"] = "in reference-group latent SD units (unstandardised kappa / ref sd = 1)"
        out[level] = fi
        prev = m
    return out


def item_dif(df: pd.DataFrame, group_col: str, focal, ref) -> dict:
    """Uniform DIF: item ~ rest score (+ rest^2) + group; coefficient / item SD. Positive = focal higher."""
    d = df[df[group_col].isin([focal, ref])]
    out = {}
    for i, it in enumerate(ITEMS):
        cols = [f"{SCALES[ITEM_SCALE[i]]}{k}" for k in range(1, 9) if f"{SCALES[ITEM_SCALE[i]]}{k}" != it]
        sub = d[[it] + cols + [group_col]].dropna()
        rest = sub[cols].sum(1).to_numpy()
        rest = (rest - rest.mean()) / rest.std()
        gvar = (sub[group_col] == focal).astype(float).to_numpy()
        X = np.column_stack([np.ones(len(sub)), rest, rest**2, gvar])
        y = sub[it].to_numpy()
        beta = np.linalg.lstsq(X, y, rcond=None)[0]
        out[it] = beta[3] / y.std()
    return out


# --------------------------------------------------------------------------- hexagon
def circ_dist(i, j):
    d = abs(i - j)
    return min(d, 6 - d)


PAIRS = [(i, j) for i in range(6) for j in range(i + 1, 6)]
PAIR_CLASS = np.array([circ_dist(i, j) for i, j in PAIRS])
PRED = [(a, b) for a in range(15) for b in range(15) if PAIR_CLASS[a] < PAIR_CLASS[b]]  # 72


def rtor_ci(C: np.ndarray) -> float:
    r = np.array([C[i, j] for i, j in PAIRS])
    diff = np.array([r[a] - r[b] for a, b in PRED])
    return float(((diff > 0).sum() - (diff < 0).sum()) / len(PRED))


def rtor(C: np.ndarray) -> dict:
    ci = rtor_ci(C)
    perms = list(itertools.permutations(range(6)))
    cis = np.array([rtor_ci(C[np.ix_(p, p)]) for p in perms])
    return {"ci": ci, "p": float((cis >= ci - 1e-12).mean()), "n_predictions": len(PRED),
            "min_attainable_p": 12 / 720}


def dist_means(C):
    r = np.array([C[i, j] for i, j in PAIRS])
    return {"adjacent": r[PAIR_CLASS == 1].mean(), "alternate": r[PAIR_CLASS == 2].mean(),
            "opposite": r[PAIR_CLASS == 3].mean()}


def circular_order_ok(xy: np.ndarray) -> tuple[bool, str]:
    xy = xy - xy.mean(0)
    ang = np.arctan2(xy[:, 1], xy[:, 0])
    order = list(np.argsort(ang))
    seq = "".join(SCALES[i] for i in order)
    ref = "RIASEC"
    rots = {ref[k:] + ref[:k] for k in range(6)}
    rots |= {r[::-1] for r in rots}
    return seq in rots, seq


def procrustes_to_hex(xy: np.ndarray):
    target = np.column_stack([np.cos(ANGLES), np.sin(ANGLES)])
    X = xy - xy.mean(0)
    U, _, Vt = np.linalg.svd(X.T @ target)
    Rm = U @ Vt
    Y = X @ Rm
    Y = Y / np.sqrt((Y**2).sum(1)).mean()
    return Y


def hexagon(df: pd.DataFrame, seed: int, n_boot: int) -> dict:
    C = df[SCALES].corr().to_numpy()
    res = {"corr": C, "dist_means": dist_means(C), "rtor": rtor(C)}
    dm = res["dist_means"]
    res["mean_order_ok"] = bool(dm["adjacent"] > dm["alternate"] > dm["opposite"])
    mds = MDS(n_components=2, metric="precomputed", metric_mds=True, init="random", random_state=seed, n_init=8,
              normalized_stress=True)
    xy = mds.fit_transform(1 - C)
    res["mds_xy"] = procrustes_to_hex(xy)
    res["mds_order_ok"], res["mds_seq"] = circular_order_ok(xy)
    res["mds_stress"] = float(mds.stress_)
    # PCA of person-centred scale scores
    X = df[SCALES].to_numpy()
    Xc = X - X.mean(1, keepdims=True)
    Xc = Xc - Xc.mean(0)
    vals, vecs = np.linalg.eigh(np.cov(Xc, rowvar=False))
    o = np.argsort(vals)[::-1]
    load = vecs[:, o[:2]] * np.sqrt(vals[o[:2]])
    res["pca_xy"] = procrustes_to_hex(load)
    res["pca_order_ok"], res["pca_seq"] = circular_order_ok(load)
    res["pca_var_explained_2"] = float(vals[o[:2]].sum() / vals.sum())
    ang = np.rad2deg(np.arctan2(res["mds_xy"][:, 1], res["mds_xy"][:, 0])) % 360
    res["mds_angles_deg"] = dict(zip(SCALES, ang))
    if n_boot:
        rng = np.random.default_rng(seed)
        Xs = df[SCALES].to_numpy()
        bs = []
        for _ in range(n_boot):
            idx = rng.integers(0, len(Xs), len(Xs))
            bs.append(rtor_ci(np.corrcoef(Xs[idx], rowvar=False)))
        res["rtor"]["ci_boot95"] = [float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))]
    res["hexagon_ok"] = bool(res["mean_order_ok"] and res["rtor"]["p"] <= 0.05 + 1e-9 and res["mds_order_ok"])
    return res


# --------------------------------------------------------------------------- group effects
def cohen_d(a: np.ndarray, b: np.ndarray) -> dict:
    a, b = a[~np.isnan(a)], b[~np.isnan(b)]
    n1, n2 = len(a), len(b)
    sp = np.sqrt(((n1 - 1) * a.var(ddof=1) + (n2 - 1) * b.var(ddof=1)) / (n1 + n2 - 2))
    d = (a.mean() - b.mean()) / sp
    se = np.sqrt((n1 + n2) / (n1 * n2) + d**2 / (2 * (n1 + n2)))
    return {"d": d, "ci95": [d - 1.96 * se, d + 1.96 * se], "n_male": n1, "n_female": n2}


def gender_d(df: pd.DataFrame) -> dict:
    m, f = df[df.sex == "male"], df[df.sex == "female"]
    out = {s: cohen_d(m[s].to_numpy(), f[s].to_numpy()) for s in SCALES}
    out["things_people"] = cohen_d(m.prediger_x.to_numpy(), f.prediger_x.to_numpy())
    out["ideas_data"] = cohen_d(m.prediger_y.to_numpy(), f.prediger_y.to_numpy())
    out["elevation"] = cohen_d(m.elevation.to_numpy(), f.elevation.to_numpy())
    out["differentiation"] = cohen_d(m.differentiation.to_numpy(), f.differentiation.to_numpy())
    out["vendor_people_things"] = cohen_d(m.vendor_pt.to_numpy(), f.vendor_pt.to_numpy())
    # Mahalanobis D over the six scales (pooled covariance)
    Xm, Xf = m[SCALES].to_numpy(), f[SCALES].to_numpy()
    Sp = ((len(Xm) - 1) * np.cov(Xm, rowvar=False) + (len(Xf) - 1) * np.cov(Xf, rowvar=False)) / (len(Xm) + len(Xf) - 2)
    diff = Xm.mean(0) - Xf.mean(0)
    out["mahalanobis_D"] = float(np.sqrt(diff @ np.linalg.solve(Sp, diff)))
    return out


# --------------------------------------------------------------------------- archetypes
def helmert_basis() -> np.ndarray:
    """6x5 orthonormal basis of the sum-to-zero subspace."""
    H = np.zeros((6, 5))
    for k in range(1, 6):
        H[:k, k - 1] = 1
        H[k, k - 1] = -k
        H[:, k - 1] /= np.linalg.norm(H[:, k - 1])
    return H


def features(df: pd.DataFrame, variant: str, zscore: bool, ref: pd.DataFrame | None = None) -> np.ndarray:
    X = df[SCALES].to_numpy()
    if zscore:
        r = df if ref is None else ref
        X = (X - r[SCALES].mean().to_numpy()) / r[SCALES].std().to_numpy()
    elev = X.mean(1, keepdims=True)
    shape = (X - elev) @ helmert_basis()
    return shape if variant == "shape" else np.column_stack([shape, elev])


def fit_gmm(F, k, seed, n_init=1):
    return GaussianMixture(n_components=k, covariance_type="full", random_state=seed, n_init=n_init,
                           max_iter=500, reg_covar=1e-5).fit(F)


def choose_k(bic: dict) -> dict:
    ks = sorted(bic)
    k2 = [k for k in ks if k >= 2]
    kmin = min(k2, key=lambda k: bic[k])
    rule = "argmin"
    k_sel = kmin
    if kmin >= 13:
        gain12 = bic[1] - bic[2]
        rule = "elbow"
        k_sel = max(k2)
        for k in k2[:-1]:
            if bic[k] - bic[k + 1] < 0.10 * gain12:
                k_sel = k
                break
    return {"k_argmin": kmin, "k_rule": rule, "k_from_bic_rule": k_sel}


def describe_k(df: pd.DataFrame, F: np.ndarray, k: int, seed: int, n_stab: int, full_report: bool) -> dict:
    raw = df[SCALES].to_numpy()
    raw_c = raw - raw.mean(1, keepdims=True)
    gm = fit_gmm(F, k, seed, n_init=3)
    lab = gm.predict(F)
    res = {"k": k}
    labs = [fit_gmm(F, k, seed + 1000 + s).predict(F) for s in range(n_stab)]
    aris = [adjusted_rand_score(a, b) for a, b in itertools.combinations(labs, 2)]
    res["seed_ari_mean"], res["seed_ari_min"] = float(np.mean(aris)), float(np.min(aris))
    rng = np.random.default_rng(seed)
    sh = []
    for s in range(n_stab):
        perm = rng.permutation(len(F))
        A, B = perm[: len(F) // 2], perm[len(F) // 2:]
        la = fit_gmm(F[A], k, seed + s).predict(F)
        lb = fit_gmm(F[B], k, seed + 2000 + s).predict(F)
        sh.append(adjusted_rand_score(la, lb))
    res["split_half_ari_mean"], res["split_half_ari_min"] = float(np.mean(sh)), float(np.min(sh))
    post = gm.predict_proba(F)
    res["mean_max_posterior"] = float(post.max(1).mean())
    if not full_report:
        return res
    pop_c = raw_c.mean(0)
    sd_c = raw_c.std(0)
    flat = (df["differentiation"] < 1.0).to_numpy()
    low = (df["elevation"] < 2.0).to_numpy()
    sex = df["sex"].to_numpy()
    base_f = np.mean(sex[pd.notna(sex)] == "female")
    clusters = []
    for c in np.argsort(-np.bincount(lab, minlength=k)):
        mask = lab == c
        cent = raw[mask].mean(0)
        cen_c = raw_c[mask].mean(0)
        rel = (cen_c - pop_c) / sd_c
        sx = sex[mask]
        sx = sx[pd.notna(sx)]
        f_share = float(np.mean(sx == "female")) if len(sx) else np.nan
        rr_f, rr_m = f_share / base_f, (1 - f_share) / (1 - base_f)
        flag = bool(max(f_share, 1 - f_share) >= 0.80 or rr_f >= 1.5 or rr_f <= 0.67 or rr_m >= 1.5 or rr_m <= 0.67)
        raw_code = "".join(SCALES[i] for i in np.argsort(-cent)[:3])
        rel_code = "".join(SCALES[i] for i in np.argsort(-rel)[:3] if rel[i] > 0.25) or "-"
        clusters.append({
            "cluster": int(c), "n": int(mask.sum()), "share": float(mask.mean()),
            "raw_means": dict(zip(SCALES, cent)), "centred": dict(zip(SCALES, cen_c)),
            "rel_to_population_sd": dict(zip(SCALES, rel)), "raw_top3": raw_code,
            "relative_code": rel_code, "elevation_mean": float(df["elevation"].to_numpy()[mask].mean()),
            "differentiation_mean": float(df["differentiation"].to_numpy()[mask].mean()),
            "flat_share": float(flat[mask].mean()), "low_elevation_share": float(low[mask].mean()),
            "female_share_mf": f_share, "rep_ratio_female": rr_f, "rep_ratio_male": rr_m,
            "gender_flag": flag, "minor_share": float(df["minor_13_17"].to_numpy()[mask].mean()),
            "median_age": float(np.median(df["age"].to_numpy()[mask])),
            "mean_max_posterior": float(post[mask].max(1).mean()),
        })
    res["clusters"] = clusters
    res["flat_share_overall"] = float(flat.mean())
    res["low_elevation_share_overall"] = float(low.mean())
    res["female_share_sample_mf"] = float(base_f)
    res["_labels"] = lab
    return res


def archetype_variant(df: pd.DataFrame, variant: str, zscore: bool, ks, seed: int, n_stab: int,
                      full_report: bool) -> dict:
    F = features(df, variant, zscore)
    bic = {}
    t = time.time()
    for k in ks:
        bic[k] = fit_gmm(F, k, seed, n_init=3).bic(F)
    sel = choose_k(bic)
    k = sel["k_from_bic_rule"]
    raw = df[SCALES].to_numpy()
    raw_c = raw - raw.mean(1, keepdims=True)
    notes = []
    while True:
        lab = fit_gmm(F, k, seed, n_init=3).predict(F)
        sizes = np.bincount(lab, minlength=k) / len(lab)
        cents = np.array([raw_c[lab == c].mean(0) for c in range(k)])
        cc = np.corrcoef(cents)
        np.fill_diagonal(cc, 0)
        if (sizes.min() >= 0.03 and cc.max() <= 0.90) or k <= 2:
            break
        notes.append(f"k={k}: min size {sizes.min():.3f}, max centred-centroid r {cc.max():.2f} -> step down")
        k -= 1
    res = {"variant": variant, "zscored": zscore, "bic": bic, "selection": sel, "k_chosen": k,
           "interpretability_steps": notes, "seconds_bic": round(time.time() - t, 1)}
    res.update(describe_k(df, F, k, seed, n_stab, full_report))
    if sel["k_from_bic_rule"] != k:
        # POST HOC (not pre-registered): the BIC-rule solution without the interpretability step-down
        res["posthoc_k_bic"] = describe_k(df, F, sel["k_from_bic_rule"], seed, n_stab, full_report)
    return res


# --------------------------------------------------------------------------- plots
def plot_pa(pa, mp, n, path):
    fig, ax = plt.subplots(1, 2, figsize=(11, 4.2))
    x = np.arange(1, 16)
    ax[0].plot(x, pa["obs_pca"][:15], "o-", label="observed (PCA)")
    ax[0].plot(x, pa["rand95_pca"][:15], "s--", label="random 95th pct (PCA)")
    ax[0].plot(x, pa["obs_fa"][:15], "o-", alpha=.6, label="observed (reduced, SMC)")
    ax[0].plot(x, pa["rand95_fa"][:15], "s--", alpha=.6, label="random 95th pct (reduced)")
    ax[0].axvline(6, color="grey", lw=.8)
    ax[0].set_xlabel("component / factor")
    ax[0].set_ylabel("eigenvalue")
    ax[0].set_title(f"Parallel analysis, half A (n = {n:,})\nretain PCA: {pa['n_pca']}, reduced: {pa['n_fa']}")
    ax[0].legend(fontsize=8)
    ax[1].plot(range(len(mp["map"])), mp["map"], "o-")
    ax[1].set_xlabel("components partialled out")
    ax[1].set_ylabel("mean squared partial r")
    ax[1].set_title(f"Velicer MAP (min at {mp['n_map']})")
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


def plot_loadings(L, phi, n, path):
    fig, ax = plt.subplots(1, 2, figsize=(11, 9), gridspec_kw={"width_ratios": [1.1, 1]})
    im = ax[0].imshow(L, cmap="RdBu_r", vmin=-1, vmax=1, aspect="auto")
    ax[0].set_yticks(range(48))
    ax[0].set_yticklabels(ITEMS, fontsize=7)
    ax[0].set_xticks(range(6))
    ax[0].set_xticklabels([f"F{s}" for s in SCALES])
    for i in range(48):
        for j in range(6):
            if abs(L[i, j]) >= .30:
                ax[0].text(j, i, f"{L[i, j]:.2f}", ha="center", va="center", fontsize=6)
    ax[0].set_title(f"EFA oblimin loadings, half A (n = {n:,})")
    fig.colorbar(im, ax=ax[0], shrink=.5)
    ax[1].imshow(phi, cmap="RdBu_r", vmin=-1, vmax=1)
    for i in range(6):
        for j in range(6):
            ax[1].text(j, i, f"{phi[i, j]:.2f}", ha="center", va="center", fontsize=9)
    ax[1].set_xticks(range(6))
    ax[1].set_xticklabels(SCALES)
    ax[1].set_yticks(range(6))
    ax[1].set_yticklabels(SCALES)
    ax[1].set_title("Factor correlations (oblimin)")
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


def _hex_axes(ax, title):
    t = np.linspace(0, 2 * np.pi, 7)
    ax.plot(np.cos(t), np.sin(t), color="lightgrey", lw=.8)
    ax.axhline(0, color="tab:orange", lw=1, ls="--")
    ax.axvline(0, color="tab:green", lw=1, ls="--")
    ax.text(1.45, -0.1, "Things", color="tab:orange", ha="right", fontsize=8)
    ax.text(-1.45, -0.1, "People", color="tab:orange", fontsize=8)
    ax.text(0.04, 1.32, "Ideas", color="tab:green", fontsize=8)
    ax.text(0.04, -1.40, "Data", color="tab:green", fontsize=8)
    ax.set_xlim(-1.5, 1.5)
    ax.set_ylim(-1.5, 1.5)
    ax.set_aspect("equal")
    ax.set_title(title, fontsize=9)
    ax.set_xticks([])
    ax.set_yticks([])


def _hex_points(ax, xy, color="tab:blue"):
    ideal = np.column_stack([np.cos(ANGLES), np.sin(ANGLES)])
    ax.scatter(ideal[:, 0], ideal[:, 1], marker="x", color="lightgrey")
    ax.plot(np.r_[xy[:, 0], xy[0, 0]], np.r_[xy[:, 1], xy[0, 1]], "-", color=color, alpha=.5)
    ax.scatter(xy[:, 0], xy[:, 1], color=color, zorder=3)
    for k, s in enumerate(SCALES):
        ax.text(xy[k, 0] * 1.13, xy[k, 1] * 1.13, s, ha="center", va="center", fontsize=10, weight="bold")


def plot_hexagon(hx, n, path):
    fig, ax = plt.subplots(1, 3, figsize=(14, 4.8))
    _hex_axes(ax[0], f"Metric MDS on 1 - r (Procrustes to ideal hexagon)\norder {hx['mds_seq']}, stress {hx['mds_stress']:.3f}, n = {n:,}")
    _hex_points(ax[0], hx["mds_xy"])
    _hex_axes(ax[1], f"PCA of person-centred scales, PC1-2\norder {hx['pca_seq']}, {100 * hx['pca_var_explained_2']:.0f}% of centred variance")
    _hex_points(ax[1], hx["pca_xy"], "tab:purple")
    C = hx["corr"]
    im = ax[2].imshow(C, cmap="RdBu_r", vmin=-1, vmax=1)
    for i in range(6):
        for j in range(6):
            ax[2].text(j, i, f"{C[i, j]:.2f}", ha="center", va="center", fontsize=9)
    ax[2].set_xticks(range(6))
    ax[2].set_xticklabels(SCALES)
    ax[2].set_yticks(range(6))
    ax[2].set_yticklabels(SCALES)
    r = hx["rtor"]
    ax[2].set_title(f"Scale correlations; RTOR CI = {r['ci']:.2f}, p = {r['p']:.3f}", fontsize=9)
    fig.colorbar(im, ax=ax[2], shrink=.7)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


def plot_groups_hex(groups, path):
    fig, ax = plt.subplots(1, len(groups), figsize=(3.3 * len(groups), 3.6))
    for a, (name, (hx, n)) in zip(ax, groups.items()):
        _hex_axes(a, f"{name} (n = {n:,})\nMDS {hx['mds_seq']}, CI {hx['rtor']['ci']:.2f}, p {hx['rtor']['p']:.3f}")
        _hex_points(a, hx["mds_xy"])
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


def plot_gender_d(gd, path, n_m, n_f):
    keys = SCALES + ["things_people", "ideas_data"]
    ours = [gd[k]["d"] for k in keys]
    err = np.array([[gd[k]["d"] - gd[k]["ci95"][0], gd[k]["ci95"][1] - gd[k]["d"]] for k in keys]).T
    su = [SU2009_D.get(k) for k in keys]
    x = np.arange(len(keys))
    fig, ax = plt.subplots(figsize=(9, 4.2))
    ax.bar(x - .18, ours, .36, yerr=err, label="E2 (OpenPsychometrics)", color="tab:blue")
    ax.bar(x + .18, [v if v is not None else 0 for v in su], .36, label="Su, Rounds & Armstrong 2009", color="tab:grey")
    for xi, v in zip(x, su):
        if v is None:
            ax.text(xi + .18, 0.02, "n/a", ha="center", fontsize=7)
    ax.axhline(0, color="k", lw=.8)
    ax.set_xticks(x)
    ax.set_xticklabels(["R", "I", "A", "S", "E", "C", "Things-\nPeople", "Ideas-\nData"])
    ax.set_ylabel("Cohen's d (male - female)")
    ax.set_title(f"Gender differences (n male = {n_m:,}, n female = {n_f:,}); 95% CI shown")
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


def plot_bic(variants, path, n):
    fig, ax = plt.subplots(figsize=(8, 4.2))
    for name, v in variants.items():
        ks = sorted(v["bic"])
        b = np.array([v["bic"][k] for k in ks])
        ax.plot(ks, (b - b[0]) / 1000, "o-", label=f"{name} (chosen k = {v['k_chosen']})")
    ax.set_xlabel("k (GMM components)")
    ax.set_ylabel("BIC - BIC(k=1), thousands")
    ax.set_title(f"GMM BIC curves (n = {n:,})")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


def plot_archetypes(v, path, n, title):
    cl = v["clusters"]
    k = len(cl)
    cols = 4
    rows = int(np.ceil(k / cols))
    fig, ax = plt.subplots(rows, cols, figsize=(3.2 * cols, 2.6 * rows), squeeze=False)
    for a, c in zip(ax.flat, cl):
        vals = [c["raw_means"][s] for s in SCALES]
        a.bar(SCALES, vals, color=["tab:brown", "tab:blue", "tab:purple", "tab:green", "tab:red", "tab:grey"])
        a.set_ylim(1, 5)
        a.axhline(np.mean(vals), color="k", lw=.7, ls=":")
        a.set_title(f"{c['relative_code']} | {100 * c['share']:.1f}% | F {100 * c['female_share_mf']:.0f}%"
                    + (" *" if c["gender_flag"] else ""), fontsize=8)
    for a in list(ax.flat)[k:]:
        a.axis("off")
    fig.suptitle(f"{title} (n = {n:,}). Bars = raw scale means 1-5; dotted = elevation; * = gender flag", fontsize=9)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


# --------------------------------------------------------------------------- main
def headline(df: pd.DataFrame, seed: int, quick: bool, k_arch: dict | None) -> dict:
    """Subset used for the robustness re-run."""
    rng = np.random.default_rng(seed)
    perm = rng.permutation(len(df))
    A, B = df.iloc[perm[: len(df) // 2]], df.iloc[perm[len(df) // 2:]]
    RA, RB = item_corr(A), item_corr(B)
    pa = parallel_analysis(len(A), 48, RA, 5 if quick else 20, rng)
    LA, phiA = efa(RA, 6, "oblimin")
    LB, _ = efa(RB, 6, "oblimin")
    _, n_ok = item_table(LA)
    hx = hexagon(df, seed, 0)
    gd = gender_d(df)
    out = {"n": len(df), "pa_n_pca": pa["n_pca"], "pa_n_fa": pa["n_fa"], "items_correct_A": n_ok,
           "items_correct_B": item_table(LB)[1], "tucker_A_vs_B": dict(zip(SCALES, tucker(LA, LB))),
           "factor_corr_A": phiA, "hexagon": {k: hx[k] for k in ("dist_means", "rtor", "mds_seq", "hexagon_ok")},
           "scale_corr": hx["corr"], "gender_d": {k: v["d"] if isinstance(v, dict) else v for k, v in gd.items()}}
    # group-level structure (added after the E1 audit: the shared-network filter removes many minors)
    groups = {"male": df[df.sex == "male"], "female": df[df.sex == "female"]}
    for b in AGE_BANDS:
        groups[b] = df[df.age_band == b]
    gL = {g: efa(item_corr(d), 6, "oblimin")[0] for g, d in groups.items()}
    ghx = {g: hexagon(d, seed, 0) for g, d in groups.items()}
    cong = {}
    for fam in (["male", "female"], list(AGE_BANDS)):
        for a, b in itertools.combinations(fam, 2):
            cong[f"{a}_vs_{b}"] = dict(zip(SCALES, tucker(gL[a], gL[b])))
    out["groups"] = {
        "n": {g: len(d) for g, d in groups.items()},
        "tucker": cong,
        "items_correct_by_group": {g: item_table(gL[g])[1] for g in groups},
        "hexagon_by_group": {g: {k: ghx[g][k] for k in ("dist_means", "rtor", "mds_seq", "hexagon_ok")} for g in groups},
        "gender_d_by_age_band": {b: {k: v["d"] if isinstance(v, dict) else v
                                     for k, v in gender_d(df[df.age_band == b]).items()} for b in AGE_BANDS},
    }
    if "shared_network" in df and df["shared_network"].any():
        sn = df[df.shared_network]
        sn_min, kept_min = sn[sn.age_band == "13-17"], df[(~df.shared_network) & (df.age_band == "13-17")]
        out["minors_shared_vs_kept"] = {
            "n_shared_13_17": len(sn_min), "n_kept_13_17": len(kept_min),
            "share_minors_in_shared": float((sn.age_band == "13-17").mean()),
            "tucker_13_17_shared_vs_kept": dict(zip(SCALES, tucker(efa(item_corr(sn_min), 6, "oblimin")[0],
                                                                   efa(item_corr(kept_min), 6, "oblimin")[0]))),
            "hexagon_13_17_shared": {k: v for k, v in hexagon(sn_min, seed, 0).items()
                                     if k in ("dist_means", "rtor", "mds_seq", "hexagon_ok")},
            "scale_means_13_17_shared": sn_min[SCALES].mean().to_dict(),
            "scale_means_13_17_kept": kept_min[SCALES].mean().to_dict(),
        }
    if k_arch:
        out["archetypes"] = {}
        for name, (variant, k) in k_arch.items():
            F = features(df, variant, False)
            labs = [fit_gmm(F, k, seed + 1000 + s).predict(F) for s in range(3 if quick else 5)]
            out["archetypes"][name] = {"k": k, "seed_ari_mean": float(np.mean(
                [adjusted_rand_score(a, b) for a, b in itertools.combinations(labs, 2)]))}
    return out


def main(seed: int, quick: bool) -> dict:
    t0 = time.time()
    rng = np.random.default_rng(seed)
    df = load(DATA_MAIN)
    if quick:
        df = df.sample(n=12000, random_state=seed).reset_index(drop=True)
    res = {"meta": {"seed": seed, "quick": quick, "n": len(df), "data": str(DATA_MAIN.relative_to(ROOT)),
                    "item_missing_cells": int(df[ITEMS].isna().sum().sum())}}
    perm = rng.permutation(len(df))
    A, B = df.iloc[perm[: len(df) // 2]], df.iloc[perm[len(df) // 2:]]
    res["meta"]["n_half_A"], res["meta"]["n_half_B"] = len(A), len(B)
    print(f"[{time.time() - t0:.0f}s] loaded n={len(df)}")

    # ---- (a) factors
    RA, RB = item_corr(A), item_corr(B)
    pa = parallel_analysis(len(A), 48, RA, 5 if quick else 20, rng)
    mp = velicer_map(RA)
    plot_pa(pa, mp, len(A), FINDINGS / "e2_parallel_analysis.png")
    LA, phiA = efa(RA, 6, "oblimin")
    LB, phiB = efa(RB, 6, "oblimin")
    LAp, phiAp = efa(RA, 6, "promax")
    tabA, okA = item_table(LA)
    tabB, okB = item_table(LB)
    tabP, okP = item_table(LAp)
    plot_loadings(LA, phiA, len(A), FINDINGS / "e2_efa_loadings.png")
    # extra factors: what does a 7/8-factor solution split off?
    extra = {}
    for nf in (7, 8):
        fa = FactorAnalyzer(n_factors=nf, rotation="oblimin", method="minres", is_corr_matrix=True).fit(RA)
        L7 = fa.loadings_
        extra[nf] = [{"factor": f, "items_ge_.40": [ITEMS[i] for i in np.where(L7[:, f] >= .40)[0]]} for f in range(nf)]
    res["factors"] = {
        "parallel_analysis": {"n_retain_pca": pa["n_pca"], "n_retain_reduced": pa["n_fa"], "n_kaiser": pa["n_kaiser"],
                              "obs_pca_first10": pa["obs_pca"][:10], "rand95_pca_first10": pa["rand95_pca"][:10],
                              "obs_reduced_first10": pa["obs_fa"][:10], "rand95_reduced_first10": pa["rand95_fa"][:10]},
        "velicer_map": {"n_map": mp["n_map"], "map_values": mp["map"]},
        "efa_oblimin_A": {"items_correct": okA, "items": tabA, "factor_corr": phiA},
        "efa_oblimin_B": {"items_correct": okB, "factor_corr": phiB,
                          "items_failing": [r["item"] for r in tabB if not r["loads_correctly"]]},
        "efa_promax_A": {"items_correct": okP, "factor_corr": phiAp,
                         "items_failing": [r["item"] for r in tabP if not r["loads_correctly"]]},
        "tucker_A_vs_B": dict(zip(SCALES, tucker(LA, LB))),
        "tucker_oblimin_vs_promax_A": dict(zip(SCALES, tucker(LA, LAp))),
        "loadings_A": {it: dict(zip(SCALES, LA[i])) for i, it in enumerate(ITEMS)},
        "extra_factor_solutions": extra,
    }
    res["reliability"] = reliability(df)
    print(f"[{time.time() - t0:.0f}s] EFA done: PA={pa['n_pca']}/{pa['n_fa']} MAP={mp['n_map']} okA={okA} okB={okB}")

    # CFA on half B (confirmation), single group
    cfaB = run_cfa_ladder([B], ["half_B"])["configural"]
    res["cfa_half_B"] = cfaB
    print(f"[{time.time() - t0:.0f}s] CFA B: CFI={cfaB['cfi']:.3f} RMSEA={cfaB['rmsea']:.3f}")

    # ---- (b) hexagon
    hx = hexagon(df, seed, 50 if quick else 200)
    plot_hexagon(hx, len(df), FINDINGS / "e2_hexagon_mds.png")
    pred = df[["prediger_x", "prediger_y", "vendor_pt", "vendor_di"]].corr()
    res["hexagon"] = {k: hx[k] for k in hx}
    res["hexagon"]["halfA_rtor"] = rtor(A[SCALES].corr().to_numpy())
    res["hexagon"]["halfB_rtor"] = rtor(B[SCALES].corr().to_numpy())
    res["prediger"] = {
        "r_angle_x_vs_vendor_people_things": pred.loc["prediger_x", "vendor_pt"],
        "r_angle_y_vs_vendor_data_ideas": pred.loc["prediger_y", "vendor_di"],
        "r_x_y": pred.loc["prediger_x", "prediger_y"],
        "mean_x": df.prediger_x.mean(), "sd_x": df.prediger_x.std(),
        "mean_y": df.prediger_y.mean(), "sd_y": df.prediger_y.std(),
        "note": "x = Things(+)/People(-), y = Ideas(+)/Data(-); angle-based on person-centred raw scale means",
    }
    print(f"[{time.time() - t0:.0f}s] hexagon CI={hx['rtor']['ci']:.2f} p={hx['rtor']['p']:.3f} mds={hx['mds_seq']}")

    # ---- (c) groups
    groups = {"male": df[df.sex == "male"], "female": df[df.sex == "female"]}
    for b in AGE_BANDS:
        groups[b] = df[df.age_band == b]
    gL, ghx = {}, {}
    for g, d in groups.items():
        gL[g] = efa(item_corr(d), 6, "oblimin")
        ghx[g] = hexagon(d, seed, 0)
    cong = {}
    for fam in (["male", "female"], list(AGE_BANDS)):
        for a, b in itertools.combinations(fam, 2):
            cong[f"{a}_vs_{b}"] = dict(zip(SCALES, tucker(gL[a][0], gL[b][0])))
    plot_groups_hex({g: (ghx[g], len(groups[g])) for g in groups}, FINDINGS / "e2_group_hexagons.png")
    gd = gender_d(df)
    gd_age = {b: gender_d(df[df.age_band == b]) for b in AGE_BANDS}
    plot_gender_d(gd, FINDINGS / "e2_gender_d.png", len(groups["male"]), len(groups["female"]))
    res["groups"] = {
        "n": {g: len(d) for g, d in groups.items()},
        "tucker": cong,
        "items_correct_by_group": {g: item_table(gL[g][0])[1] for g in groups},
        "items_failing_by_group": {g: [r["item"] for r in item_table(gL[g][0])[0] if not r["loads_correctly"]] for g in groups},
        "factor_corr_by_group": {g: gL[g][1] for g in groups},
        "hexagon_by_group": {g: {k: ghx[g][k] for k in ("dist_means", "rtor", "mean_order_ok", "mds_seq", "mds_order_ok",
                                                         "pca_seq", "pca_order_ok", "hexagon_ok", "corr")} for g in groups},
        "gender_d": gd,
        "gender_d_su2009": SU2009_D,
        "gender_d_by_age_band": {b: {k: v["d"] if isinstance(v, dict) else v for k, v in x.items()} for b, x in gd_age.items()},
        "scale_means_by_group": {g: d[SCALES + ["elevation", "differentiation"]].mean().to_dict() for g, d in groups.items()},
        "prediger_means_by_group": {g: {"x": d.prediger_x.mean(), "y": d.prediger_y.mean()} for g, d in groups.items()},
        "item_dif_gender_female_minus_male_sd": item_dif(df, "sex", "female", "male"),
        "item_d_gender_male_minus_female": {it: cohen_d(groups["male"][it].to_numpy(), groups["female"][it].to_numpy())["d"] for it in ITEMS},
        "item_dif_age_13_17_minus_25plus_sd": item_dif(df.assign(ab=df.age_band.astype(str)), "ab", "13-17", "25+"),
    }
    print(f"[{time.time() - t0:.0f}s] groups done; running multi-group CFA")
    res["mgcfa"] = {
        "gender": run_cfa_ladder([groups["male"], groups["female"]], ["male", "female"]),
        "age": run_cfa_ladder([groups[b] for b in AGE_BANDS], list(AGE_BANDS)),
    }
    for k, v in res["mgcfa"].items():
        print(f"   MGCFA {k}: " + ", ".join(f"{lv} CFI={v[lv]['cfi']:.3f} RMSEA={v[lv]['rmsea']:.3f}" for lv in v))

    # ---- (d) archetypes
    ks = list(range(1, 9 if quick else 16))
    n_stab = 3 if quick else 10
    arch = {}
    for name, variant, z in (("shape", "shape", False), ("shape_plus_elevation", "shape_elev", False),
                             ("shape_z", "shape", True), ("shape_plus_elevation_z", "shape_elev", True)):
        arch[name] = archetype_variant(df, variant, z, ks, seed, n_stab, full_report=not z)
        a = arch[name]
        print(f"[{time.time() - t0:.0f}s] GMM {name}: k={a['k_chosen']} seedARI={a['seed_ari_mean']:.2f} "
              f"splitARI={a['split_half_ari_mean']:.2f}"
              + (f" | posthoc k={a['posthoc_k_bic']['k']} seedARI={a['posthoc_k_bic']['seed_ari_mean']:.2f} "
                 f"splitARI={a['posthoc_k_bic']['split_half_ari_mean']:.2f}" if "posthoc_k_bic" in a else ""))
    plot_bic(arch, FINDINGS / "e2_gmm_bic.png", len(df))
    for name, fn, title in (("shape", "e2_archetypes_shape.png", "GMM archetypes, shape only"),
                            ("shape_plus_elevation", "e2_archetypes_shape_elev.png", "GMM archetypes, shape + elevation")):
        plot_archetypes(arch[name], FINDINGS / fn, len(df), f"{title}, k = {arch[name]['k_chosen']} (pre-registered rule)")
        if "posthoc_k_bic" in arch[name]:
            ph = arch[name]["posthoc_k_bic"]
            plot_archetypes(ph, FINDINGS / fn.replace(".png", "_posthoc_kbic.png"), len(df),
                            f"{title}, k = {ph['k']} (BIC rule, POST HOC, no interpretability step)")
    # agreement between the two variants
    ls, le = arch["shape"].pop("_labels"), arch["shape_plus_elevation"].pop("_labels")
    res["archetype_variant_ari"] = adjusted_rand_score(ls, le)
    for a in arch.values():
        a.pop("_labels", None)
        if "posthoc_k_bic" in a:
            a["posthoc_k_bic"].pop("_labels", None)
    res["archetypes"] = arch

    # ---- robustness
    print(f"[{time.time() - t0:.0f}s] robustness re-run on incl-shared-network table")
    dfi = load(DATA_INCL)
    if quick:
        dfi = dfi.sample(n=12000, random_state=seed).reset_index(drop=True)
    k_arch = {"shape": ("shape", arch["shape"]["k_chosen"]),
              "shape_plus_elevation": ("shape_elev", arch["shape_plus_elevation"]["k_chosen"])}
    res["robustness_incl_shared_network"] = headline(dfi, seed, quick, k_arch)
    res["robustness_incl_shared_network"]["shared_network_only"] = {
        "n": int(dfi.shared_network.sum()),
        "hexagon_rtor": rtor(dfi[dfi.shared_network][SCALES].corr().to_numpy()),
        "scale_means": dfi[dfi.shared_network][SCALES].mean().to_dict(),
        "minor_share": float(dfi[dfi.shared_network]["minor_13_17"].mean()),
    }
    res["meta"]["seconds"] = round(time.time() - t0, 1)
    return res


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--quick", action="store_true", help="subsample (12k rows) for a fast smoke run")
    ap.add_argument("--robust-only", action="store_true",
                    help="recompute only the incl-shared-network robustness block and merge it into the existing JSON")
    a = ap.parse_args()
    FINDINGS.mkdir(parents=True, exist_ok=True)
    name = "e2_structure_quick.json" if a.quick else "e2_structure.json"
    if a.robust_only:
        prev = json.loads((FINDINGS / name).read_text())
        dfi = load(DATA_INCL)
        if a.quick:
            dfi = dfi.sample(n=12000, random_state=a.seed).reset_index(drop=True)
        k_arch = {"shape": ("shape", prev["archetypes"]["shape"]["k_chosen"]),
                  "shape_plus_elevation": ("shape_elev", prev["archetypes"]["shape_plus_elevation"]["k_chosen"])}
        rob = headline(dfi, a.seed, a.quick, k_arch)
        rob["shared_network_only"] = prev["robustness_incl_shared_network"].get("shared_network_only")
        prev["robustness_incl_shared_network"] = rnd(rob, 4)
        (FINDINGS / name).write_text(json.dumps(prev, indent=2))
        print("updated robustness block in", FINDINGS / name)
        raise SystemExit(0)
    out = rnd(main(a.seed, a.quick), 4)
    (FINDINGS / name).write_text(json.dumps(out, indent=2))
    print("wrote", FINDINGS / name)
