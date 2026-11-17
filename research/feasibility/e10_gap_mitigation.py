"""E10 — A gender-blind mitigation for the 24-item agreement gap (pre-registered in research/findings/e10_gap_mitigation.md).

Run: uv run python -I research/feasibility/e10_gap_mitigation.py [--quick]

Gender is read ONLY here, for the offline audit (ADR 0015). The engine never sees it.
"""

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
sys.path.insert(0, str(ROOT / "src"))
from career_compass import engine as E
from career_compass.matching import score_matrix

FINDINGS = ROOT / "research" / "findings"
DATA = ROOT / "data" / "processed" / "riasec_people.parquet"
SOFT = 1.5
CHUNK = 4000


def rnd(x, k=4):
    if isinstance(x, dict):
        return {kk: rnd(v, k) for kk, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [rnd(v, k) for v in x]
    if isinstance(x, np.bool_):
        return bool(x)
    if isinstance(x, (np.floating, float)):
        return None if not np.isfinite(x) else round(float(x), k)
    if isinstance(x, np.integer):
        return int(x)
    return x


def mask_for(bank, form):
    return np.isin(np.array(bank.items), form)


def raw_profiles(X, bank, mask):
    out = []
    for i in range(0, len(X), CHUNK):
        x = X[i : i + CHUNK]
        m = mask if mask.ndim == 1 else mask[i : i + CHUNK]
        out.append(E.score_matrix_responses(np.where(m, x, 0), bank)[2])
    return np.concatenate(out)


def top3_families(P, cat):
    fam = cat.family
    order = np.argsort(fam, kind="stable")
    starts = np.r_[0, np.flatnonzero(np.diff(fam[order])) + 1]
    out = []
    for i in range(0, len(P), CHUNK):
        S = score_matrix(P[i : i + CHUNK], cat.occ)
        S = S - np.arange(S.shape[1]) * 1e-12  # ties by catalogue order, as engine.recommend
        F = np.maximum.reduceat(S[:, order], starts, axis=1)
        part = np.argpartition(-F, 2, axis=1)[:, :3]
        out.append(part)
    return np.concatenate(out)


def gated(P):
    return ((P.max(1) - P.min(1)) < E.GATE_DIFFERENTIATION) | (P.mean(1) < E.GATE_ELEVATION)


def gap_ci(a, female, male, rng, B):
    x, y = a[female], a[male]
    g = x.mean() - y.mean()
    bs = np.array([rng.choice(x, len(x)).mean() - rng.choice(y, len(y)).mean() for _ in range(B)])
    return g, [float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))]


def evaluate(df, quick, rng, B):
    bank, cat = E.ItemBank.from_e4(), E.Catalogue.load()
    X = df[list(bank.items)].to_numpy(int)
    female, male = (df.gender == 2.0).to_numpy(), (df.gender == 1.0).to_numpy()
    f24 = E.build_fixed_form(bank, 4)
    f30 = E.build_fixed_form(bank, 5)
    f40 = [it for it in bank.items if it not in E.EXCLUDED_ITEMS]
    assert f30[:24] == f24 and len(f40) == 40 and set(f24) <= set(f40)
    ref = top3_families(raw_profiles(X, bank, np.ones(48, bool)), cat)
    P24 = raw_profiles(X, bank, mask_for(bank, f24))
    ext = (P24.max(1) - P24.min(1)) < SOFT
    m24, m30, m40 = (mask_for(bank, f) for f in (f24, f30, f40))
    P30 = raw_profiles(X, bank, m30)
    P40 = raw_profiles(X, bank, m40)
    conds = {
        "C0": (P24, np.full(len(X), 24)),
        "C1": (P30, np.full(len(X), 30)),
        "C2": (np.where(ext[:, None], P30, P24), np.where(ext, 30, 24)),
        "C3": (np.where(ext[:, None], P40, P24), np.where(ext, 40, 24)),
        "C4": (P40, np.full(len(X), 40)),
    }
    res = {"n": len(X), "n_female": int(female.sum()), "n_male": int(male.sum()),
           "extended_share": {"female": float(ext[female].mean()), "male": float(ext[male].mean())}}
    for name, (P, nitems) in conds.items():
        a3 = (top3_families(P, cat)[:, :, None] == ref[:, None, :]).any(2).mean(1)
        shown = ~gated(P)
        r = {"mean_items": float(nitems.mean()),
             "mean_items_by_group": {"female": float(nitems[female].mean()), "male": float(nitems[male].mean())},
             "gate_rate": {"female": float(gated(P)[female].mean()), "male": float(gated(P)[male].mean())}}
        for pop, sel in (("primary_shown", shown), ("secondary_all", np.ones(len(X), bool))):
            g, ci = gap_ci(a3, female & sel, male & sel, rng, B)
            r[pop] = {"A3": {"female": float(a3[female & sel].mean()), "male": float(a3[male & sel].mean())},
                      "gap": g, "gap_ci95": ci, "n": [int((female & sel).sum()), int((male & sel).sum())]}
        res[name] = r
    return res


def verdict(res):
    base = res["C0"]["primary_shown"]["A3"]
    if abs(res["C0"]["primary_shown"]["gap"]) <= 0.02:
        return {"verdict": "proven (gate already mitigates)", "recommended": "C0", "mitigations": ["C0"]}
    mit = []
    for c in ("C1", "C2", "C3"):
        p = res[c]["primary_shown"]
        if (abs(p["gap"]) <= 0.02 and p["A3"]["female"] >= base["female"] and p["A3"]["male"] >= base["male"]
                and res[c]["mean_items"] <= 30):
            mit.append(c)
    if not mit:
        return {"verdict": "not viable", "recommended": None, "mitigations": []}
    best = min(mit, key=lambda c: (res[c]["mean_items"], abs(res[c]["primary_shown"]["gap"])))
    return {"verdict": "proven", "recommended": best, "mitigations": mit}


def plot(res, path):
    cs = ["C0", "C1", "C2", "C3", "C4"]
    fig, ax = plt.subplots(figsize=(7.5, 4.5))
    for pop, mk in (("primary_shown", "o"), ("secondary_all", "s")):
        g = [res[c][pop]["gap"] for c in cs]
        lo = [g[i] - res[c][pop]["gap_ci95"][0] for i, c in enumerate(cs)]
        hi = [res[c][pop]["gap_ci95"][1] - g[i] for i, c in enumerate(cs)]
        x = [res[c]["mean_items"] for c in cs]
        ax.errorbar(x, g, yerr=[lo, hi], fmt=mk, capsize=3, label=pop.replace("_", " "))
        for xi, gi, c in zip(x, g, cs, strict=True):
            ax.annotate(c, (xi, gi), textcoords="offset points", xytext=(5, 4), fontsize=8)
    ax.axhline(0.02, color="grey", ls="--", lw=0.8)
    ax.axhline(0.05, color="grey", ls=":", lw=0.8)
    ax.axhline(0, color="black", lw=0.5)
    ax.set_xlabel("mean items administered")
    ax.set_ylabel("gender gap in top-3 family agreement (F − M)")
    ax.set_title(f"E10: gap by condition (adults, n = {res['n']:,}); dashed = .02 bar, dotted = .05")
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)


def main(seed, quick):
    t0 = time.time()
    rng = np.random.default_rng(seed)
    bank_items = list(E.ItemBank.from_e4().items)
    df = pd.read_parquet(DATA)
    df[bank_items] = df[bank_items].replace(0, np.nan)
    df = df.dropna(subset=bank_items)
    df[bank_items] = df[bank_items].astype(int)
    adults, teens = df[df.age >= 18], df[(df.age >= 13) & (df.age <= 17)]
    if quick:
        adults, teens = adults.sample(4000, random_state=seed), teens.sample(2000, random_state=seed)
    B = 100 if quick else 1000
    res = {"adults": evaluate(adults.reset_index(drop=True), quick, rng, B)}
    res["adults"]["decision"] = verdict(res["adults"])
    res["teens_secondary"] = evaluate(teens.reset_index(drop=True), quick, rng, B)
    res["meta"] = {"seed": seed, "quick": quick, "B": B, "runtime_s": round(time.time() - t0, 1)}
    plot(res["adults"], FINDINGS / ("e10_gap_mitigation_quick.png" if quick else "e10_gap_mitigation.png"))
    return rnd(res)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--quick", action="store_true", help="4,000 adults + 2,000 teens, B = 100")
    a = ap.parse_args()
    out = main(a.seed, a.quick)
    (FINDINGS / ("e10_gap_mitigation_quick.json" if a.quick else "e10_gap_mitigation.json")).write_text(
        json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps(out["adults"]["decision"]), out["meta"])
