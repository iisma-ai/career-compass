"""E7b — Demographic-cue stripping before free-text matching (pre-registered in research/findings/e7b_cue_stripping.md).

Run: uv run python -I research/feasibility/e7b_cue_stripping.py --seed 42     (smoke: --quick)

Fixed configuration from E7 (no reselection): all-MiniLM-L6-v2, index variant (d), cosine, top-10. Every query goes
through carrier_helper.text_cues.strip_demographic_cues() before embedding; "raw" is the E7 behaviour, computed in
the same run. Reuses E7's loaders, metrics and rejection procedure unchanged.
Output: research/findings/e7b_cue_stripping.json and e7b_*.png
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

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "research" / "feasibility"))  # python -I drops the script dir
sys.path.insert(0, str(ROOT / "src"))
import e7_free_text_matching as E

from carrier_helper.text_cues import strip_demographic_cues

FINDINGS = ROOT / "research" / "findings"
HELDOUT = FINDINGS / "e7b_heldout_pairs.csv"
OUT_JSON = FINDINGS / "e7b_cue_stripping.json"
DEV_GATED = {"gender_pair", "name_pair"}
DEV_ALL = ["gender_pair", "name_pair", "pronoun_pair", "nationality_pair", "age_pair"]
BAR = {"proven": {"overlap": .90, "fam": .92, "occ": .83, "frr": .10, "off": .80, "trap": .90},
       "promising": {"overlap": .80, "fam": .88, "occ": .78, "frr": .20, "off": .60, "trap": .80}}


def overlap(top, i, j):
    return len(set(top[i]) & set(top[j])) / E.K


def main(seed: int, quick: bool) -> dict:
    rng = np.random.default_rng(seed)
    B = 200 if quick else 2000
    n_splits = 20 if quick else 200
    t0 = time.time()
    occ, tasks, text_a, text_d = E.load_catalogue()
    st, off = E.load_statements()
    ho = pd.read_csv(HELDOUT, dtype=str, keep_default_na=False, encoding="utf-8")

    blocks = {"st": st.text.tolist(), "off": off.text.tolist(), "ho": ho.text.tolist()}
    stripped, cues = {}, {}
    for k, xs in blocks.items():
        res = [strip_demographic_cues(x) for x in xs]
        stripped[k] = [r[0] for r in res]
        cues[k] = [r[1] for r in res]
    # one query list: raw then stripped for each block
    order, queries = [], []
    for k, raw_texts in blocks.items():
        for variant, xs in (("raw", raw_texts), ("strip", stripped[k])):
            order.append((k, variant, len(queries), len(xs)))
            queries += xs
    models = {"minilm": E.MODELS["minilm"]} if quick else E.MODELS
    log, tops, top1 = {}, {}, {}
    for name, repo in models.items():
        S, _, _ = E.embed_scores(name, repo, occ, tasks, text_a, text_d, queries, log)
        Sd = S["d"]
        for k, variant, start, n in order:
            tops[(name, k, variant)] = E.rank_topk(Sd[start:start + n])
            top1[(name, k, variant)] = Sd[start:start + n].max(axis=1)
        print(f"  {name}: {log[name]['seconds']} s")

    out = {"config": {"seed": seed, "quick": quick, "models": list(models), "variant": "d", "k": E.K,
                      "bootstrap_B": B, "rejection_splits": n_splits},
           "models_log": log}

    # ---- M5 cue audit
    cat = st.category.to_numpy()
    cue_free_e7 = ~np.isin(cat, DEV_ALL)
    out["M5_cue_audit"] = {
        "e7_cue_free_statements_changed": int(sum(bool(c) for c, f in zip(cues["st"], cue_free_e7) if f)),
        "e7_cue_free_statements_n": int(cue_free_e7.sum()),
        "offtopic_changed": int(sum(bool(c) for c in cues["off"])),
        "cue_types_e7_pairs": dict(Counter(t for c, f in zip(cues["st"], cue_free_e7) if not f for t, _ in c)),
        "cue_types_heldout": dict(Counter(t for c in cues["ho"] for t, _ in c)),
        "heldout_rows_with_no_cue_found": [ho.id.iloc[i] for i, c in enumerate(cues["ho"])
                                           if not c and ho.member.iloc[i] in ("a", "b")],
    }

    res = {}
    for name in models:
        r = {}
        # ---- M1 counterfactual invariance
        def pair_stats(df, block, sets, name=name):
            id2i = {x: i for i, x in enumerate(df.id)}
            outp = {}
            for sname, mask in sets.items():
                rows = []
                for pid, g in df[mask].groupby("pair_id", sort=True):
                    ga = g[g.member.isin(["a"] + list(E.FIRST_MEMBERS))]
                    gb = g[g.member.isin(["b", "male", "name_male", "name_b", "older", "nat_b"])]
                    gc = g[g.member == "content"]
                    i, j = id2i[ga.id.iloc[0]], id2i[gb.id.iloc[0]]
                    row = {"pair": pid, "lang": ga.language.iloc[0],
                           "raw": overlap(tops[(name, block, "raw")], i, j),
                           "strip": overlap(tops[(name, block, "strip")], i, j),
                           "identical_after_strip": stripped[block][i] == stripped[block][j],
                           "stripped_a": stripped[block][i], "stripped_b": stripped[block][j]}
                    if len(gc):
                        c = id2i[gc.id.iloc[0]]
                        Ts = tops[(name, block, "strip")]
                        row["strip_a_vs_content"] = overlap(Ts, i, c)
                        row["strip_b_vs_content"] = overlap(Ts, j, c)
                        row["raw_a_vs_content"] = overlap(tops[(name, block, "raw")], i, c)
                    if "new_phrasing" in g:
                        row["new_phrasing"] = ga.new_phrasing.iloc[0] == "1"
                    rows.append(row)
                summ = {}
                for key in ("raw", "strip"):
                    summ[key] = E.boot_mean([x[key] for x in rows], rng, B)
                summ["coverage_identical"] = float(np.mean([x["identical_after_strip"] for x in rows]))
                if rows and "strip_a_vs_content" in rows[0]:
                    summ["strip_vs_content_mean"] = float(np.mean([(x["strip_a_vs_content"] + x["strip_b_vs_content"])
                                                                   / 2 for x in rows]))
                    summ["raw_a_vs_content_mean"] = float(np.mean([x["raw_a_vs_content"] for x in rows]))
                if rows and "new_phrasing" in rows[0]:
                    for flag in (True, False):
                        sub = [x["strip"] for x in rows if x["new_phrasing"] == flag]
                        summ[f"strip_new_phrasing_{flag}"] = {"mean": float(np.mean(sub)) if sub else None,
                                                              "n": len(sub)}
                outp[sname] = {"summary": summ, "pairs": rows}
            return outp

        hs = ho.set.to_numpy()
        r["M1_heldout"] = pair_stats(ho, "ho", {
            "gated": np.isin(hs, ["gated_gender", "gated_name"]), "gender": hs == "gated_gender",
            "name": hs == "gated_name", "age": hs == "age", "origin": hs == "origin"})
        r["M1_dev_e7"] = pair_stats(st.rename(columns={"pair_member": "member"}), "st", {
            "gated_dev": np.isin(cat, list(DEV_GATED)), "pronoun": cat == "pronoun_pair",
            "nationality": cat == "nationality_pair", "age": cat == "age_pair"})

        # ---- M2 retrieval quality on E7 sets
        lang = st.language.to_numpy()
        member = st.pair_member.to_numpy()
        is_first = np.isin(member, list(E.FIRST_MEMBERS)) & np.isin(cat, ["gender_pair", "name_pair", "age_pair"])
        en_core = (lang == "en") & (np.isin(cat, list(E.CORE_CATS)) | is_first)
        sets = {"en_core": en_core, "vague_en": (cat == "vague") & (lang == "en"), "spanish": cat == "spanish"}
        per = {v: E.per_statement(tops[(name, "st", v)], None, st, occ) for v in ("raw", "strip")}

        def col(v, key, per=per):
            return np.array([d.get(key, np.nan) for d in per[v]], float)

        m2 = {"n_en_core": int(en_core.sum())}
        for sname, mask in sets.items():
            m2[sname] = {}
            for key in ("hit_fam80_5", "hit_occ5", "hit_fam90_5", "riasec_r"):
                m2[sname][key] = {"raw": E.boot_mean(col("raw", key)[mask], rng, B),
                                  "strip": E.boot_mean(col("strip", key)[mask], rng, B),
                                  "diff_strip_minus_raw": E.boot_diff(col("strip", key)[mask], col("raw", key)[mask],
                                                                      rng, B)}
        r["M2_quality"] = m2

        # ---- M3 rejection (same sets as E7: 76 real EN vs 27 off-topic EN)
        has_set = (st.sensible_codes != "").to_numpy()
        real_en = has_set & (lang == "en") & ~np.isin(cat, list(E.ADDENDUM_CATS))
        off_en = (off.language == "en").to_numpy()
        r["M3_rejection"] = {"n_real": int(real_en.sum()), "n_off": int(off_en.sum())}
        for v in ("raw", "strip"):
            r["M3_rejection"][v] = E.rejection(top1[(name, "st", v)][real_en], top1[(name, "off", v)][off_en],
                                               np.random.default_rng(seed), n_splits)

        # ---- M4 content preservation (traps)
        trap = np.flatnonzero(hs == "trap")
        Tr, Ts = tops[(name, "ho", "raw")], tops[(name, "ho", "strip")]
        r["M4_traps"] = {"n": len(trap),
                         "unchanged_share": float(np.mean([stripped["ho"][i] == blocks["ho"][i] for i in trap])),
                         "mean_top10_overlap_raw_vs_strip": float(np.mean([len(set(Tr[i]) & set(Ts[i])) / E.K
                                                                           for i in trap])),
                         "changed": {ho.id.iloc[i]: stripped["ho"][i] for i in trap
                                     if stripped["ho"][i] != blocks["ho"][i]}}
        res[name] = r
    out["results"] = res

    # ---- verdict (primary model only)
    p = res["minilm"]
    vals = {"overlap": p["M1_heldout"]["gated"]["summary"]["strip"]["mean"],
            "fam": p["M2_quality"]["en_core"]["hit_fam80_5"]["strip"]["mean"],
            "occ": p["M2_quality"]["en_core"]["hit_occ5"]["strip"]["mean"],
            "frr": p["M3_rejection"]["strip"]["heldout_frr"],
            "off": p["M3_rejection"]["strip"]["heldout_offtopic_reject"],
            "trap": p["M4_traps"]["mean_top10_overlap_raw_vs_strip"]}

    def passes(b):
        return {"(1) overlap": vals["overlap"] >= b["overlap"],
                "(2) quality": vals["fam"] >= b["fam"] and vals["occ"] >= b["occ"],
                "(3) rejection": vals["frr"] <= b["frr"] and vals["off"] >= b["off"],
                "(4) traps": vals["trap"] >= b["trap"]}

    pv, pm = passes(BAR["proven"]), passes(BAR["promising"])
    verdict = "PROVEN" if all(pv.values()) else "PROMISING" if all(pm.values()) else "NOT VIABLE"
    out["verdict"] = {"values": vals, "proven_criteria": pv, "promising_criteria": pm, "verdict": verdict}
    out["seconds_total"] = round(time.time() - t0, 1)
    charts(res, quick)
    return out


def charts(res, quick):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    r = res["minilm"]
    rows = r["M1_heldout"]["gated"]["pairs"] + r["M1_heldout"]["age"]["pairs"] + r["M1_heldout"]["origin"]["pairs"]
    fig, ax = plt.subplots(figsize=(10, 4.2))
    x = np.arange(len(rows))
    ax.bar(x - .2, [q["raw"] for q in rows], .4, label="raw (E7 behaviour)", color="#9aa5b1")
    ax.bar(x + .2, [q["strip"] for q in rows], .4, label="cue-stripped", color="#2b6cb0")
    ax.axhline(.90, ls="--", c="k", lw=1)
    ax.text(len(rows) - .5, .91, "bar .90 (gated pairs only)", ha="right", fontsize=8)
    ax.set_xticks(x, [q["pair"] for q in rows], rotation=60, fontsize=8)
    ax.set_ylabel("top-10 overlap, member A vs B")
    ax.set_ylim(0, 1.05)
    ax.set_title(f"E7b held-out counterfactual pairs, minilm:d (gated n = 18, age 4, origin 4){' [quick]' * quick}")
    ax.legend(fontsize=8, loc="lower left")
    fig.tight_layout()
    fig.savefig(FINDINGS / "e7b_heldout_overlap.png", dpi=130)
    plt.close(fig)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--quick", action="store_true", help="primary model only, fewer bootstrap draws")
    a = ap.parse_args()
    result = E.rnd(main(a.seed, a.quick))
    target = OUT_JSON.with_name("e7b_cue_stripping_quick.json") if a.quick else OUT_JSON
    target.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(result["verdict"], indent=2))
    print(json.dumps(result["M5_cue_audit"], indent=2, ensure_ascii=False))
