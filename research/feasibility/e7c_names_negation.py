"""E7c — Name coverage v2 and negation handling (pre-registered in research/findings/e7c_names_negation.md).

Run: uv run python -I research/feasibility/e7c_names_negation.py --seed 42     (smoke: --quick)

Fixed configuration (no reselection): all-MiniLM-L6-v2, variant (d), cosine, top-10. Full pipeline =
strip_demographic_cues (v2) -> split_negation -> score = sim(positive) - alpha * max sim(rejected), alpha = 0
(frozen by e7c_dev_tuning.py). "Raw" = E7 behaviour, computed in the same run. alpha = 0.5 is reported only.
Output: research/findings/e7c_names_negation.json and e7c_*.png
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))  # python -I drops the script dir
import e7c_common as C

E = C.E
FINDINGS = C.ROOT / "research" / "findings"
HELDOUT = FINDINGS / "e7c_heldout.csv"
OUT_JSON = FINDINGS / "e7c_names_negation.json"
ALPHA, ALPHA_SECONDARY = 0.0, 0.5
BAR = {"proven": {"overlap": .90, "names": .90, "neg": .83, "dev": 5, "fam": .92, "occ": .83, "frr": .10,
                  "off": .80, "trap": .90},
       "promising": {"overlap": .80, "names": .80, "neg": .67, "dev": 4, "fam": .88, "occ": .78, "frr": .20,
                     "off": .60, "trap": .80}}
E7_PAIR_CATS = ["gender_pair", "name_pair", "pronoun_pair", "nationality_pair", "age_pair"]


def overlap(top, i, j):
    return len(set(top[i]) & set(top[j])) / E.K


def centred_profile(prof, top_row):
    p = prof[top_row].mean(axis=0)
    return p - p.mean()


def main(seed: int, quick: bool) -> dict:
    rng = np.random.default_rng(seed)
    B = 200 if quick else 2000
    n_splits = 20 if quick else 200
    t0 = time.time()
    st, off = E.load_statements()
    ho = pd.read_csv(HELDOUT, dtype=str, keep_default_na=False, encoding="utf-8")
    texts = {"st": st.text.tolist(), "off": off.text.tolist(), "ho": ho.text.tolist()}
    prep = {}
    for k, xs in texts.items():
        prep[(k, "raw")] = C.prepare(xs, strip=False, negation=False)
        prep[(k, "full")] = C.prepare(xs)
    log = {}
    sc = C.Scorer({f"{k}|{v}": p for (k, v), p in prep.items()}, log=log)
    occ = sc.occ
    prof = occ[E.SCALES].to_numpy(float)

    S, T1, FU, TOP = {}, {}, {}, {}
    for (k, v), p in prep.items():
        for name, a in (("raw", 0.0), ("full", ALPHA), ("full_a05", ALPHA_SECONDARY)):
            if (v == "raw") != (name == "raw"):
                continue
            s, t1, fu = sc.matrix(p, a)
            S[(k, name)], T1[(k, name)], FU[(k, name)] = s, t1, fu
            TOP[(k, name)] = E.rank_topk(s)
    variants = ["raw", "full", "full_a05"]
    out = {"config": {"seed": seed, "quick": quick, "model": "minilm", "variant": "d", "k": E.K, "alpha": ALPHA,
                      "alpha_secondary": ALPHA_SECONDARY, "bootstrap_B": B, "rejection_splits": n_splits},
           "models_log": log}

    # ---- N1 name / gender invariance on held-out pairs
    id2i = {x: i for i, x in enumerate(ho.id)}
    hs = ho.set.to_numpy()

    def pair_rows(mask):
        rows = []
        for pid, g in ho[mask].groupby("pair_id", sort=True):
            a, b = g[g.member == "a"], g[g.member == "b"]
            c = g[g.member == "content"]
            i, j = id2i[a.id.iloc[0]], id2i[b.id.iloc[0]]
            row = {"pair": pid, "lang": a.language.iloc[0], "tags": a.tags.iloc[0],
                   "identical_after_strip": prep[("ho", "full")][i]["stripped"] == prep[("ho", "full")][j]["stripped"],
                   "stripped_a": prep[("ho", "full")][i]["stripped"], "stripped_b": prep[("ho", "full")][j]["stripped"]}
            for v in ("raw", "full"):
                row[v] = overlap(TOP[("ho", v)], i, j)
            if len(c):
                k = id2i[c.id.iloc[0]]
                row["full_vs_content"] = (overlap(TOP[("ho", "full")], i, k) + overlap(TOP[("ho", "full")], j, k)) / 2
            rows.append(row)
        return rows

    n1 = {}
    for sname, mask in {"gated": np.isin(hs, ["gated_name", "gated_gender"]), "name": hs == "gated_name",
                        "gender": hs == "gated_gender"}.items():
        rows = pair_rows(mask)
        summ = {v: E.boot_mean([r[v] for r in rows], rng, B) for v in ("raw", "full")}
        summ["coverage_identical"] = float(np.mean([r["identical_after_strip"] for r in rows])) if rows else None
        summ["full_vs_content_mean"] = float(np.mean([r["full_vs_content"] for r in rows if "full_vs_content" in r]))
        if sname == "name":
            for tag in ("lower", "nonlatin", "signoff", "third_person", "intro", "greeting"):
                sub = [r["full"] for r in rows if tag in r["tags"].split(";")]
                summ[f"tag_{tag}"] = {"mean": float(np.mean(sub)) if sub else None, "n": len(sub)}
            sub = [r["full"] for r in rows if r["lang"] == "es"]
            summ["spanish"] = {"mean": float(np.mean(sub)) if sub else None, "n": len(sub)}
        n1[sname] = {"summary": summ, "pairs": rows}
    out["N1_invariance"] = n1

    # ---- N2 negation
    def neg_eval(block, df, rows_idx, letters_col, intended_col):
        res = {}
        for v in variants:
            items = []
            for i in rows_idx:
                pc = centred_profile(prof, TOP[(block, v)][i])
                li = [E.SCALES.index(L) for L in df[letters_col].iloc[i]]
                d = {"id": df.id.iloc[i], "neg_letter_score": float(pc[li].mean()),
                     "followup": bool(FU[(block, v)][i])}
                if intended_col and df[intended_col].iloc[i]:
                    d["intended_top_in"] = E.SCALES[int(np.argmax(pc))] in df[intended_col].iloc[i]
                items.append(d)
            res[v] = {"share_below_zero": float(np.mean([x["neg_letter_score"] < 0 for x in items])),
                      "n_below_zero": int(sum(x["neg_letter_score"] < 0 for x in items)), "n": len(items),
                      "intended_top_in": (float(np.mean([x["intended_top_in"] for x in items if "intended_top_in" in x]))
                                          if any("intended_top_in" in x for x in items) else None),
                      "items": items}
        return res

    mixed = np.flatnonzero(hs == "neg_mixed")
    out["N2_negation"] = {
        "heldout_mixed": neg_eval("ho", ho, mixed, "negated_letters", "intended_riasec"),
        "e7_dev": neg_eval("st", st, np.flatnonzero(st.category.to_numpy() == "negation"), "negated_letters",
                           "intended_riasec"),
        "split_audit_heldout_mixed": [{"id": ho.id.iloc[i], "positive": prep[("ho", "full")][i]["positive"],
                                       "rejected": prep[("ho", "full")][i]["rejected"]} for i in mixed],
    }

    # ---- N3 retrieval quality on E7 EN-core
    cat, lang, member = st.category.to_numpy(), st.language.to_numpy(), st.pair_member.to_numpy()
    is_first = np.isin(member, list(E.FIRST_MEMBERS)) & np.isin(cat, ["gender_pair", "name_pair", "age_pair"])
    en_core = (lang == "en") & (np.isin(cat, list(E.CORE_CATS)) | is_first)
    per = {v: E.per_statement(TOP[("st", v)], None, st, occ) for v in variants}

    def col(v, key):
        return np.array([d.get(key, np.nan) for d in per[v]], float)

    n3 = {"n_en_core": int(en_core.sum())}
    for key in ("hit_fam80_5", "hit_occ5"):
        n3[key] = {v: E.boot_mean(col(v, key)[en_core], rng, B) for v in variants}
        n3[key]["diff_full_minus_raw"] = E.boot_diff(col("full", key)[en_core], col("raw", key)[en_core], rng, B)
    out["N3_quality"] = n3

    # ---- N4 rejection (positive-part top-1; follow-up rows count as rejected = conservative)
    has_set = (st.sensible_codes != "").to_numpy()
    real_en = has_set & (lang == "en") & ~np.isin(cat, list(E.ADDENDUM_CATS))
    off_en = (off.language == "en").to_numpy()
    n4 = {"n_real": int(real_en.sum()), "n_off": int(off_en.sum())}
    for v in ("raw", "full"):
        r1 = np.nan_to_num(T1[("st", v)], nan=-1.0)
        o1 = np.nan_to_num(T1[("off", v)], nan=-1.0)
        n4[v] = E.rejection(r1[real_en], o1[off_en], np.random.default_rng(seed), n_splits)
    out["N4_rejection"] = n4

    # ---- N5 traps
    trap = np.flatnonzero(np.isin(hs, ["neg_trap", "name_trap"]))
    pf = prep[("ho", "full")]
    out["N5_traps"] = {
        "n": len(trap),
        "mean_top10_overlap_full_vs_raw": float(np.mean([overlap_rows(TOP[("ho", "full")], TOP[("ho", "raw")], i)
                                                         for i in trap])),
        "by_set": {s: float(np.mean([overlap_rows(TOP[("ho", "full")], TOP[("ho", "raw")], i)
                                     for i in trap if hs[i] == s])) for s in ("neg_trap", "name_trap")},
        "unchanged_share": float(np.mean([pf[i]["stripped"] == texts["ho"][i] and not pf[i]["rejected"]
                                          for i in trap])),
        "changed": {ho.id.iloc[i]: {"stripped": pf[i]["stripped"], "positive": pf[i]["positive"],
                                    "rejected": pf[i]["rejected"]} for i in trap
                    if pf[i]["stripped"] != texts["ho"][i] or pf[i]["rejected"]},
    }

    # ---- N6 reported only
    only = np.flatnonzero(hs == "neg_only")
    cue_free_e7 = ~np.isin(cat, E7_PAIR_CATS) & (cat != "negation")
    ps = prep[("st", "full")]
    out["N6_reported"] = {
        "neg_only_followup": {ho.id.iloc[i]: bool(FU[("ho", "full")][i]) for i in only},
        "neg_only_followup_rate": float(np.mean([FU[("ho", "full")][i] for i in only])) if len(only) else None,
        "e7_cue_free_rows_changed_by_strip": int(sum(p["stripped"] != x for p, x, f in
                                                     zip(ps, texts["st"], cue_free_e7) if f)),
        "e7_cue_free_rows_negation_triggered": [st.id.iloc[i] for i in np.flatnonzero(cue_free_e7)
                                                if ps[i]["rejected"]],
        "e7_cue_free_n": int(cue_free_e7.sum()),
        "offtopic_changed": int(sum(p["stripped"] != x or bool(p["rejected"])
                                    for p, x in zip(prep[("off", "full")], texts["off"]))),
        "cue_types_heldout": dict(Counter(t for p in pf for t in p["cue_types"])),
        "neg_cues_heldout": dict(Counter(c for p in pf for c in p["neg_cues"])),
        "heldout_pair_rows_no_cue": [ho.id.iloc[i] for i in range(len(ho))
                                     if hs[i] in ("gated_name", "gated_gender") and ho.member.iloc[i] in ("a", "b")
                                     and not pf[i]["cue_types"]],
    }

    # ---- verdict
    vals = {"overlap": n1["gated"]["summary"]["full"]["mean"], "names": n1["name"]["summary"]["full"]["mean"],
            "neg": out["N2_negation"]["heldout_mixed"]["full"]["share_below_zero"],
            "dev": out["N2_negation"]["e7_dev"]["full"]["n_below_zero"],
            "fam": n3["hit_fam80_5"]["full"]["mean"], "occ": n3["hit_occ5"]["full"]["mean"],
            "frr": n4["full"]["heldout_frr"], "off": n4["full"]["heldout_offtopic_reject"],
            "trap": out["N5_traps"]["mean_top10_overlap_full_vs_raw"]}

    def passes(b):
        return {"(1) invariance": vals["overlap"] >= b["overlap"] and vals["names"] >= b["names"],
                "(2) negation": vals["neg"] >= b["neg"] and vals["dev"] >= b["dev"],
                "(3) quality": vals["fam"] >= b["fam"] and vals["occ"] >= b["occ"],
                "(4) rejection": vals["frr"] <= b["frr"] and vals["off"] >= b["off"],
                "(5) traps": vals["trap"] >= b["trap"]}

    pv, pm = passes(BAR["proven"]), passes(BAR["promising"])
    verdict = "PROVEN" if all(pv.values()) else "PROMISING" if all(pm.values()) else "NOT VIABLE"
    out["verdict"] = {"values": vals, "proven_criteria": pv, "promising_criteria": pm, "verdict": verdict}
    out["seconds_total"] = round(time.time() - t0, 1)
    charts(out, quick)
    return out


def overlap_rows(A, Bm, i):
    return len(set(A[i]) & set(Bm[i])) / E.K


def charts(out, quick):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    rows = out["N1_invariance"]["gated"]["pairs"]
    fig, ax = plt.subplots(1, 2, figsize=(13, 4.2), gridspec_kw={"width_ratios": [2.2, 1]})
    x = np.arange(len(rows))
    ax[0].bar(x - .2, [q["raw"] for q in rows], .4, label="raw (E7 behaviour)", color="#9aa5b1")
    ax[0].bar(x + .2, [q["full"] for q in rows], .4, label="E7c pipeline", color="#2b6cb0")
    ax[0].axhline(.90, ls="--", c="k", lw=1)
    ax[0].set_xticks(x, [q["pair"] for q in rows], rotation=60, fontsize=8)
    ax[0].set_ylim(0, 1.05)
    ax[0].set_ylabel("top-10 overlap, member A vs B")
    ax[0].set_title(f"E7c held-out name (GN) and gender (GG) pairs{' [quick]' * quick}")
    ax[0].legend(fontsize=8, loc="lower left")
    neg = out["N2_negation"]["heldout_mixed"]
    ids = [it["id"] for it in neg["raw"]["items"]]
    y = np.arange(len(ids))
    ax[1].barh(y + .2, [it["neg_letter_score"] for it in neg["raw"]["items"]], .4, color="#9aa5b1", label="raw")
    ax[1].barh(y - .2, [it["neg_letter_score"] for it in neg["full"]["items"]], .4, color="#2b6cb0",
               label="E7c (alpha 0)")
    ax[1].axvline(0, c="k", lw=1)
    ax[1].set_yticks(y, ids, fontsize=8)
    ax[1].invert_yaxis()
    ax[1].set_xlabel("negated letter, centred score in top-10 profile")
    ax[1].set_title("Held-out mixed negations (< 0 = rejected type pushed down)", fontsize=9)
    ax[1].legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(FINDINGS / "e7c_heldout.png", dpi=130)
    plt.close(fig)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--quick", action="store_true", help="fewer bootstrap draws and rejection splits")
    a = ap.parse_args()
    result = E.rnd(main(a.seed, a.quick))
    target = OUT_JSON.with_name("e7c_names_negation_quick.json") if a.quick else OUT_JSON
    target.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(result["verdict"], indent=2))
