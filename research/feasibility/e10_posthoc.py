"""E10 post-hoc (EXPLORATORY, run after the pre-registered E10 result; not pre-registered).

Run: uv run python -I research/feasibility/e10_posthoc.py

1. Reference check: is the gap an artefact of the 48-item reference containing the excluded DIF items?
   (24 vs 40-item reference, 24 vs 48, 40 vs 48.)
2. Composition check: reweight men to women's distribution of profile shape (top-2 code, and top-2 code x
   differentiation band) among people shown families, and recompute the gap.
Gender is read only here, for the offline audit (ADR 0015).
"""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import e10_gap_mitigation as M

from career_compass import engine as E

DIFF_BANDS = [0, 1.5, 2, 2.5, 3, 9]


def agree(A, B):
    return (A[:, :, None] == B[:, None, :]).any(2).mean(1)


def main(seed=7):
    rng = np.random.default_rng(seed)
    bank, cat = E.ItemBank.from_e4(), E.Catalogue.load()
    items = list(bank.items)
    df = pd.read_parquet(M.DATA)
    df[items] = df[items].replace(0, np.nan)
    df = df.dropna(subset=items)
    f24 = E.build_fixed_form(bank, 4)
    f40 = [i for i in items if i not in E.EXCLUDED_ITEMS]
    out = {"meta": {"seed": seed, "exploratory": True}}
    for grp, d in (("adults", df[df.age >= 18]), ("teens", df[(df.age >= 13) & (df.age <= 17)])):
        X = d[items].to_numpy(int)
        fem, mal = (d.gender == 2.0).to_numpy(), (d.gender == 1.0).to_numpy()
        P24, P40, P48 = (M.raw_profiles(X, bank, m) for m in
                         (M.mask_for(bank, f24), M.mask_for(bank, f40), np.ones(48, bool)))
        t24, t40, t48 = (M.top3_families(P, cat) for P in (P24, P40, P48))
        shown = ~M.gated(P24)
        ref = {}
        for name, a in (("24_vs_40ref", agree(t24, t40)), ("24_vs_48ref", agree(t24, t48)),
                        ("40_vs_48ref", agree(t40, t48))):
            g, ci = M.gap_ci(a, fem & shown, mal & shown, rng, 500)
            ref[name] = {"F": a[fem & shown].mean(), "M": a[mal & shown].mean(), "gap": g, "gap_ci95": ci}
        a = agree(t24, t48)
        o = np.argsort(-P24, 1)
        code = pd.Series(["RIASEC"[i] + "RIASEC"[j] for i, j in o[:, :2]])
        band = pd.Series(pd.cut(P24.max(1) - P24.min(1), DIFF_BANDS).astype(str))
        comp = {}
        for sname, s in (("top2_code", code), ("top2_code_x_differentiation", code + "|" + band)):
            f = pd.DataFrame({"s": s, "a": a, "F": fem, "M": mal})[shown]
            wF = f[f.F].s.value_counts(normalize=True)
            mM = f[f.M].groupby("s").a.mean()
            common = wF.index.intersection(mM.index)
            m_rew = float((wF[common] * mM[common]).sum() / wF[common].sum())
            fm, mr = float(f[f.F].a.mean()), float(f[f.M].a.mean())
            comp[sname] = {"F": fm, "M_raw": mr, "M_reweighted": m_rew, "gap_raw": fm - mr,
                           "gap_after_reweight": fm - m_rew, "F_mass_covered": float(wF[common].sum())}
        out[grp] = {"reference_check": ref, "composition_check": comp}
    return M.rnd(out)


if __name__ == "__main__":
    res = main()
    (M.FINDINGS / "e10_posthoc.json").write_text(json.dumps(res, indent=2), encoding="utf-8")
    print(json.dumps(res, indent=2))
