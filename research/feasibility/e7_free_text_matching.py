"""E7 — Free-text interests -> O*NET occupations with sentence embeddings (retrieval only).

Run:   .venv/Scripts/python -I research/feasibility/e7_free_text_matching.py [--seed 42] [--quick]
Blind: .venv/Scripts/python -I research/feasibility/e7_free_text_matching.py --score-blind
       (after research/findings/e7_blind_ratings.csv has been filled in from e7_blind_sheet.csv)

Pre-registration and results: research/findings/e7_free_text_matching.md
Inputs:  research/findings/e7_test_statements.csv, e7_offtopic_inputs.csv, e3_families.csv,
         data/processed/onet_occupations.parquet, data/raw/onet_31_0/db_31_0_csv/*.csv (read only).
Outputs: research/findings/e7_free_text_matching.json, e7_per_statement.csv, e7_blind_sheet.csv,
         e7_blind_key.json, e7_*.png
Everything runs locally; the only network access is the one-time Hugging Face model download.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))  # python -I does not add the script dir or PYTHONPATH
from career_compass import matching as M  # noqa: E402

FINDINGS = ROOT / "research" / "findings"
RAW = ROOT / "data" / "raw" / "onet_31_0" / "db_31_0_csv"
OCC_PATH = ROOT / "data" / "processed" / "onet_occupations.parquet"
OUT_JSON = FINDINGS / "e7_free_text_matching.json"

SCALES = M.SCALES
MODELS = {
    "minilm": "sentence-transformers/all-MiniLM-L6-v2",
    "mml12": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
}
VARIANTS = ["a", "b", "c", "d"]
K = 10
FIRST_MEMBERS = {"female", "name_female", "name_a", "young", "nat_a"}
CORE_CATS = {"pure", "mixed", "hobby", "negation", "negation_twin"}
GATED_PAIR_TYPES = {"gender_pair", "name_pair"}
ADDENDUM_CATS = {"pronoun_pair", "nationality_pair"}
PAIR_TYPES = ["gender_pair", "name_pair", "pronoun_pair", "nationality_pair", "age_pair"]


def rnd(x, k=4):
    if isinstance(x, dict):
        return {str(kk): rnd(v, k) for kk, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [rnd(v, k) for v in x]
    if isinstance(x, (np.floating, float)):
        return None if not np.isfinite(x) else round(float(x), k)
    if isinstance(x, (np.integer, np.bool_)):
        return int(x)
    if isinstance(x, np.ndarray):
        return rnd(x.tolist(), k)
    return x


# ----------------------------------------------------------------------------- data
def load_catalogue():
    occ = pd.read_parquet(OCC_PATH).rename(columns={"onet_soc_code": "code"})
    occ = occ.sort_values("code").reset_index(drop=True)
    fam = pd.read_csv(FINDINGS / "e3_families.csv", dtype={"code": str}).set_index("code")
    occ["fam80"] = fam.loc[occ.code, "family_r80"].to_numpy()
    occ["fam90"] = fam.loc[occ.code, "family_r90"].to_numpy()
    codes = set(occ.code)

    tasks = pd.read_csv(RAW / "task_statements.csv", encoding="utf-8")
    tasks = tasks[tasks["O*NET-SOC Code"].isin(codes)].copy()
    im = pd.read_csv(RAW / "task_ratings.csv", encoding="utf-8")
    im = im[im["Scale ID"] == "IM"][["O*NET-SOC Code", "Task ID", "Data Value"]]
    tasks = tasks.merge(im, on=["O*NET-SOC Code", "Task ID"], how="left")
    tasks["im"] = tasks["Data Value"].fillna(-1)

    alt = pd.read_csv(RAW / "sample_of_reported_titles.csv", encoding="utf-8")
    alt = alt[alt["O*NET-SOC Code"].isin(codes)]
    alt = alt.assign(mnm=(alt["Shown in My Next Move"] == "Y").astype(int))
    alt = alt.sort_values(["O*NET-SOC Code", "mnm"], ascending=[True, False], kind="stable")

    idx = {c: i for i, c in enumerate(occ.code)}
    tasks["occ_i"] = tasks["O*NET-SOC Code"].map(idx)
    tasks = tasks.sort_values(["occ_i", "Task ID"]).reset_index(drop=True)

    text_a, text_d = [], []
    for r in occ.itertuples():
        text_a.append(f"{r.title}. {r.description}")
        at = [t for t in alt.loc[alt["O*NET-SOC Code"] == r.code, "Reported Job Title"] if t != r.title][:10]
        tt = tasks[tasks.occ_i == idx[r.code]].sort_values("im", ascending=False, kind="stable")["Task"].head(5)
        parts = [f"{r.title}."]
        if at:
            parts.append("Also called: " + ", ".join(at) + ".")
        parts.append(r.description)
        parts.append("Tasks: " + " ".join(tt))
        text_d.append(" ".join(parts))
    return occ, tasks, text_a, text_d


def load_statements():
    t = pd.read_csv(FINDINGS / "e7_test_statements.csv", dtype=str, keep_default_na=False, encoding="utf-8")
    x = pd.read_csv(FINDINGS / "e7_offtopic_inputs.csv", dtype=str, keep_default_na=False, encoding="utf-8")
    return t, x


def target_vec(letters: str) -> np.ndarray:
    t = np.zeros(6)
    for w, L in zip((3, 2, 1), letters):
        t[SCALES.index(L)] = w
    return t


# ----------------------------------------------------------------------------- scoring
def rank_topk(S: np.ndarray, k: int = K) -> np.ndarray:
    return np.argsort(-S, axis=1, kind="stable")[:, :k]


def max_over_groups(S_tasks: np.ndarray, group: np.ndarray, n_groups: int) -> np.ndarray:
    starts = np.r_[0, np.flatnonzero(np.diff(group)) + 1]
    assert len(starts) == n_groups and (group[starts] == np.arange(n_groups)).all()
    return np.maximum.reduceat(S_tasks, starts, axis=1)


def model_license(repo: str) -> str | None:
    try:
        from huggingface_hub import try_to_load_from_cache

        p = try_to_load_from_cache(repo, "README.md")
        if isinstance(p, str):
            m = re.search(r"^license:\s*(\S+)", Path(p).read_text(encoding="utf-8"), re.M)
            return m.group(1) if m else None
    except Exception:  # noqa: BLE001
        return None
    return None


def embed_scores(name, repo, occ, tasks, text_a, text_d, queries, log):
    from sentence_transformers import SentenceTransformer

    t0 = time.time()
    model = SentenceTransformer(repo, device="cpu")
    enc = lambda xs: model.encode(list(xs), batch_size=64, normalize_embeddings=True,  # noqa: E731
                                  convert_to_numpy=True, show_progress_bar=False)
    msl = model.max_seq_length
    tok = model.tokenizer
    trunc = {}
    for lab, tx in (("a", text_a), ("d", text_d), ("tasks", tasks["Task"].tolist())):
        lens = np.array([len(ids) for ids in tok(list(tx), add_special_tokens=True)["input_ids"]])
        trunc[lab] = {"share_truncated": float((lens > msl).mean()), "median_tokens": float(np.median(lens))}
    Ea, Ed, Et = enc(text_a), enc(text_d), enc(tasks["Task"])
    g = tasks["occ_i"].to_numpy()
    Eb = np.zeros((len(occ), Et.shape[1]))
    np.add.at(Eb, g, Et)
    Eb /= np.linalg.norm(Eb, axis=1, keepdims=True)
    Q = enc(queries)
    S = {"a": Q @ Ea.T, "b": Q @ Eb.T, "c": max_over_groups(Q @ Et.T, g, len(occ)), "d": Q @ Ed.T}
    log[name] = {"repo": repo, "max_seq_length": msl, "dim": int(Ea.shape[1]), "truncation": trunc,
                 "license_from_model_card": model_license(repo), "seconds": round(time.time() - t0, 1)}
    return S, Q, enc


def tfidf_scores(index_texts, queries):
    from sklearn.feature_extraction.text import TfidfVectorizer

    v = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), sublinear_tf=True)
    X = v.fit_transform(index_texts)
    return (v.transform(queries) @ X.T).toarray()


def keyword_profiles(queries):
    kw = pd.read_csv(RAW / "career_interest_type_keywords.csv", encoding="utf-8")
    name2l = {"Realistic": "R", "Investigative": "I", "Artistic": "A", "Social": "S",
              "Enterprising": "E", "Conventional": "C"}
    stop = {"with", "like", "to", "of", "and", "the"}
    kws = []
    for r in kw.itertuples():
        words = [w for w in re.findall(r"[a-z]+", r.Keyword.lower()) if w not in stop]
        kws.append((SCALES.index(name2l[r._2]), [w[: max(4, len(w) - 2)] for w in words]))
    P = np.zeros((len(queries), 6))
    for i, q in enumerate(queries):
        toks = re.findall(r"[a-záéíóúñ]+", q.lower())
        for k, stems in kws:
            if stems and all(any(t.startswith(s) for t in toks) for s in stems):
                P[i, k] += 1
    return P


# ----------------------------------------------------------------------------- metrics
def per_statement(top: np.ndarray, sims_top: np.ndarray | None, st: pd.DataFrame, occ: pd.DataFrame):
    """Metrics per statement for one method given its (n, K) top list."""
    code_idx = {c: i for i, c in enumerate(occ.code)}
    prof = occ[SCALES].to_numpy(float)
    cprof = prof - prof.mean(axis=1, keepdims=True)
    f80, f90, jz = occ.fam80.to_numpy(), occ.fam90.to_numpy(), occ.job_zone.to_numpy(float)
    toplet = prof.argmax(axis=1)
    rows = []
    for i, r in enumerate(st.itertuples()):
        tk = top[i]
        sens = [code_idx[c] for c in r.sensible_codes.split(";") if c]
        d = {}
        for k in (5, 10):
            if sens:
                d[f"hit_occ{k}"] = float(np.isin(tk[:k], sens).any())
                d[f"hit_fam80_{k}"] = float(np.isin(f80[tk[:k]], f80[sens]).any())
                d[f"hit_fam90_{k}"] = float(np.isin(f90[tk[:k]], f90[sens]).any())
            else:
                d[f"hit_occ{k}"] = d[f"hit_fam80_{k}"] = d[f"hit_fam90_{k}"] = np.nan
        p = prof[tk].mean(axis=0)
        pc = p - p.mean()
        d["p"] = pc
        d["jz_mean"] = jz[tk].mean()
        d["jz_ge4"] = (jz[tk] >= 4).mean()
        d["letter_share"] = np.bincount(toplet[tk], minlength=6) / len(tk)
        if r.intended_riasec:
            t = target_vec(r.intended_riasec)
            d["riasec_r"] = float(np.corrcoef(p, t)[0, 1])
            d["riasec_top1"] = float(SCALES[int(np.argmax(p))] == r.intended_riasec[0])
            d["riasec_in"] = float(SCALES[int(np.argmax(p))] in r.intended_riasec)
            if sims_top is not None:
                w = np.clip(sims_top[i], 0, None)
                w = w / w.sum() if w.sum() > 0 else np.full(len(tk), 1 / len(tk))
                f = (w[:, None] * cprof[tk]).sum(axis=0)
                d["fusion_r"] = float(np.corrcoef(f, t)[0, 1])
                d["fusion_top1"] = float(SCALES[int(np.argmax(f))] == r.intended_riasec[0])
        rows.append(d)
    return rows


def boot_mean(x, rng, B):
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    if len(x) == 0:
        return {"mean": None, "lo": None, "hi": None, "n": 0}
    bs = rng.choice(x, size=(B, len(x)), replace=True).mean(axis=1)
    return {"mean": float(x.mean()), "lo": float(np.percentile(bs, 2.5)), "hi": float(np.percentile(bs, 97.5)),
            "n": int(len(x))}


def boot_diff(x, y, rng, B):
    x, y = np.asarray(x, float), np.asarray(y, float)
    ok = np.isfinite(x) & np.isfinite(y)
    dlt = x[ok] - y[ok]
    idx = rng.integers(0, len(dlt), size=(B, len(dlt)))
    bs = dlt[idx].mean(axis=1)
    return {"mean": float(dlt.mean()), "lo": float(np.percentile(bs, 2.5)), "hi": float(np.percentile(bs, 97.5)),
            "n": int(ok.sum())}


def youden_threshold(real, off):
    s = np.sort(np.unique(np.r_[real, off]))
    cand = np.r_[s[0] - 1e-6, (s[:-1] + s[1:]) / 2, s[-1] + 1e-6]
    J = np.array([(off < c).mean() - (real < c).mean() for c in cand])
    return float(cand[np.flatnonzero(J == J.max())[0]])


def rejection(real, off, rng, n_splits):
    real, off = np.asarray(real), np.asarray(off)
    frr, trr, thr = [], [], []
    for _ in range(n_splits):
        pr, po = rng.permutation(len(real)), rng.permutation(len(off))
        rc, rh = pr[: len(real) // 2], pr[len(real) // 2:]
        oc, oh = po[: len(off) // 2], po[len(off) // 2:]
        t = youden_threshold(real[rc], off[oc])
        thr.append(t)
        frr.append((real[rh] < t).mean())
        trr.append((off[oh] < t).mean())
    t_all = youden_threshold(real, off)
    return {"heldout_frr": float(np.mean(frr)), "heldout_frr_p90": float(np.percentile(frr, 90)),
            "heldout_offtopic_reject": float(np.mean(trr)), "threshold_split_mean": float(np.mean(thr)),
            "threshold_split_sd": float(np.std(thr)), "threshold_all": t_all,
            "insample_frr": float((real < t_all).mean()), "insample_offtopic_reject": float((off < t_all).mean()),
            "real_median": float(np.median(real)), "off_median": float(np.median(off)),
            "real_min": float(real.min()), "off_max": float(off.max()),
            "auc": float((real[:, None] > off[None, :]).mean() + 0.5 * (real[:, None] == off[None, :]).mean())}


# ----------------------------------------------------------------------------- main
def main(seed: int, quick: bool) -> dict:
    rng = np.random.default_rng(seed)
    B = 200 if quick else 2000
    n_splits = 20 if quick else 200
    t0 = time.time()
    occ, tasks, text_a, text_d = load_catalogue()
    st, off = load_statements()
    print(f"occupations {len(occ)}, tasks {len(tasks)}, statements {len(st)}, off-topic {len(off)}")
    queries = st.text.tolist()
    n = len(st)
    allq = queries + off.text.tolist()

    models = {"minilm": MODELS["minilm"]} if quick else MODELS
    log, scores, protos = {}, {}, {}
    act = pd.read_csv(RAW / "interests_illustrative_activities.csv", encoding="utf-8")
    act = act[act["Interest Type"] == "Career Type"]
    for name, repo in models.items():
        S, Q, enc = embed_scores(name, repo, occ, tasks, text_a, text_d, allq, log)
        for v in VARIANTS:
            scores[f"{name}:{v}"] = S[v]
        P = np.stack([enc(act.loc[act["Element Name"] == nm, "Activity"]).mean(axis=0) for nm in
                      ["Realistic", "Investigative", "Artistic", "Social", "Enterprising", "Conventional"]])
        P /= np.linalg.norm(P, axis=1, keepdims=True)
        protos[name] = Q[:n] @ P.T
        print(f"  {name}: {log[name]['seconds']} s")
    scores["tfidf:a"] = tfidf_scores(text_a, allq)
    scores["tfidf:d"] = tfidf_scores(text_d, allq)
    kp = keyword_profiles(allq)
    scores["keyword"] = M.score_matrix(kp, occ, method="pearson")
    kw_nohit = (kp.sum(axis=1) == 0)

    # ---- per-statement metrics for every method
    per = {}
    tops = {}
    for m, S in scores.items():
        Sq = S[:n]
        top = rank_topk(Sq)
        tops[m] = top
        sims = np.take_along_axis(Sq, top, axis=1)
        per[m] = per_statement(top, sims if not m.startswith(("tfidf", "keyword")) else None, st, occ)
    # random baseline: expected values over draws
    R = 300 if quick else 2000
    rand_rows = [dict() for _ in range(n)]
    acc = {}
    for _ in range(R):
        top = np.stack([rng.choice(len(occ), K, replace=False) for _ in range(n)])
        rows = per_statement(top, None, st, occ)
        for i, d in enumerate(rows):
            for kk, vv in d.items():
                if kk in ("p", "letter_share"):
                    continue
                acc.setdefault((i, kk), []).append(vv)
    for (i, kk), vs in acc.items():
        rand_rows[i][kk] = float(np.nanmean(vs)) if np.isfinite(vs).any() else np.nan
    per["random"] = rand_rows
    random_list_draw = np.stack([rng.choice(len(occ), K, replace=False) for _ in range(n)])

    def col(m, key):
        return np.array([d.get(key, np.nan) for d in per[m]], float)

    cat = st.category.to_numpy()
    lang = st.language.to_numpy()
    member = st.pair_member.to_numpy()
    is_pair_first = np.isin(member, list(FIRST_MEMBERS)) & np.isin(cat, ["gender_pair", "name_pair", "age_pair"])
    en_core = (lang == "en") & (np.isin(cat, list(CORE_CATS)) | is_pair_first)
    sets = {"en_core": en_core, "vague_en": (cat == "vague") & (lang == "en"),
            "spanish": cat == "spanish", "negation": cat == "negation"}
    for c in sorted(set(cat)):
        sets[f"cat:{c}"] = cat == c
    jzc = occ.set_index("code").job_zone
    trades = np.array([(jzc.loc[s.split(";")] <= 3).mean() > 0.5 if s else False for s in st.sensible_codes])
    sets["trades"] = trades & (st.sensible_codes != "").to_numpy()
    sets["non_trades"] = (~trades) & (st.sensible_codes != "").to_numpy()
    print(f"EN-core n = {en_core.sum()}  (pre-registered 57)")

    methods = list(per)
    metric_keys = ["hit_occ5", "hit_occ10", "hit_fam80_5", "hit_fam80_10", "hit_fam90_5", "hit_fam90_10",
                   "riasec_r", "riasec_top1", "riasec_in", "fusion_r", "fusion_top1"]
    table = {}
    for m in methods:
        table[m] = {}
        for sname, mask in sets.items():
            table[m][sname] = {k: boot_mean(col(m, k)[mask], rng, B) for k in metric_keys}

    emb = [m for m in methods if m.split(":")[0] in models]
    order_v = {v: i for i, v in enumerate(VARIANTS)}

    def sel_key(m):
        t = table[m]["en_core"]
        return (-t["hit_fam80_5"]["mean"], -t["hit_occ5"]["mean"], order_v[m.split(":")[1]],
                list(models).index(m.split(":")[0]))

    best = sorted(emb, key=sel_key)[0]
    best_tfidf = max(["tfidf:a", "tfidf:d"], key=lambda m: (table[m]["en_core"]["hit_fam80_5"]["mean"],
                                                           table[m]["en_core"]["hit_occ5"]["mean"]))
    diff = boot_diff(col(best, "hit_fam80_5")[en_core], col(best_tfidf, "hit_fam80_5")[en_core], rng, B)
    diff_occ = boot_diff(col(best, "hit_occ5")[en_core], col(best_tfidf, "hit_occ5")[en_core], rng, B)
    diff_kw = boot_diff(col(best, "hit_fam80_5")[en_core], col("keyword", "hit_fam80_5")[en_core], rng, B)
    print(f"best = {best}, best TF-IDF = {best_tfidf}")

    # ---- rejection
    top1 = {m: S.max(axis=1) for m, S in scores.items()}
    has_set = (st.sensible_codes != "").to_numpy()
    base_rows = ~np.isin(cat, list(ADDENDUM_CATS))
    real_en = has_set & (lang == "en") & base_rows
    off_en = (off.language == "en").to_numpy()
    print(f"rejection real EN n = {real_en.sum()} (pre-registered 76), off-topic EN n = {off_en.sum()}")
    rej = {}
    for m in methods:
        if m == "random":
            continue
        s = top1[m]
        rej[m] = {"en": rejection(s[:n][real_en], s[n:][off_en], rng, n_splits)}
        if m.split(":")[0] == "mml12":
            real_all = has_set & base_rows
            rej[m]["en_es"] = rejection(s[:n][real_all], s[n:], rng, n_splits)
    thr_best = rej[best]["en"]["threshold_all"]
    s_best = top1[best]
    no_match = {
        "threshold": thr_best,
        "vague_empty": {r.id: {"top1": float(s_best[i]), "no_good_match": bool(s_best[i] < thr_best)}
                        for i, r in enumerate(st.itertuples()) if r.category == "vague_empty"},
        "share_no_match_by_category": {c: float((s_best[:n][cat == c] < thr_best).mean()) for c in sorted(set(cat))},
        "offtopic_no_match_by_kind": {k: float((s_best[n:][(off.kind == k).to_numpy()] < thr_best).mean())
                                      for k in sorted(set(off.kind))},
        "offtopic_accepted_ids": [off.id.iloc[j] for j in range(len(off)) if s_best[n + j] >= thr_best],
    }
    if best.split(":")[0] == "minilm" and "mml12" not in models:
        pass

    # ---- negation
    id2i = {r: i for i, r in enumerate(st.id)}

    def ov(m, i, j):
        return len(set(tops[m][i]) & set(tops[m][j])) / K

    core_idx = np.flatnonzero(en_core)
    neg = {}
    for m in emb + [best_tfidf, "keyword"]:
        pairs = []
        for r in st[st.category == "negation"].itertuples():
            tw = st[st.negation_twin_of == r.id].id.iloc[0]
            i, j = id2i[r.id], id2i[tw]
            pi, pj = per[m][i]["p"], per[m][j]["p"]
            li = [SCALES.index(L) for L in r.negated_letters]
            pairs.append({"id": r.id, "twin": tw, "overlap": ov(m, i, j), "neg_letter_score_negated": float(pi[li].mean()),
                          "neg_letter_score_twin": float(pj[li].mean())})
        ref = [ov(m, a, b) for ai, a in enumerate(core_idx) for b in core_idx[ai + 1:]]
        neg[m] = {"pairs": pairs, "mean_overlap": float(np.mean([p["overlap"] for p in pairs])),
                  "reference_overlap_unrelated": float(np.mean(ref)),
                  "mean_neg_letter_negated": float(np.mean([p["neg_letter_score_negated"] for p in pairs])),
                  "mean_neg_letter_twin": float(np.mean([p["neg_letter_score_twin"] for p in pairs])),
                  "share_negated_letter_below_zero": float(np.mean([p["neg_letter_score_negated"] < 0 for p in pairs]))}

    # ---- Spanish vs English
    es = {}
    tr = st[st.category == "spanish"]
    for m in emb + [best_tfidf, "keyword"]:
        ie = [id2i[x] for x in tr.translation_of]
        isp = [id2i[x] for x in tr.id]
        es[m] = {"n_pairs": len(ie),
                 "en_hit_fam80_5": float(np.nanmean(col(m, "hit_fam80_5")[ie])),
                 "es_hit_fam80_5": float(np.nanmean(col(m, "hit_fam80_5")[isp])),
                 "en_hit_occ5": float(np.nanmean(col(m, "hit_occ5")[ie])),
                 "es_hit_occ5": float(np.nanmean(col(m, "hit_occ5")[isp])),
                 "en_riasec_r": float(np.nanmean(col(m, "riasec_r")[ie])),
                 "es_riasec_r": float(np.nanmean(col(m, "riasec_r")[isp])),
                 "crosslingual_top10_overlap": float(np.mean([ov(m, a, b) for a, b in zip(ie, isp)]))}

    # ---- bias pairs
    bias = {}
    for m in emb + [best_tfidf, "keyword"]:
        out = {}
        for ptype in PAIR_TYPES:
            rows = []
            for pid, g in st[st.category == ptype].groupby("pair_id", sort=True):
                a = g[g.pair_member.isin(FIRST_MEMBERS)].iloc[0]
                b = g[~g.pair_member.isin(FIRST_MEMBERS)].iloc[0]
                i, j = id2i[a.id], id2i[b.id]
                di, dj = per[m][i], per[m][j]
                rows.append({"pair": pid, "lang": a.language, "a": a.pair_member, "b": b.pair_member,
                             "overlap10": ov(m, i, j),
                             "overlap5": len(set(tops[m][i][:5]) & set(tops[m][j][:5])) / 5,
                             "profile_shift_l2": float(np.linalg.norm(di["p"] - dj["p"])),
                             "profile_shift_signed": (di["p"] - dj["p"]).tolist(),
                             "jz_mean_shift": float(di["jz_mean"] - dj["jz_mean"]),
                             "jz_ge4_shift": float(di["jz_ge4"] - dj["jz_ge4"]),
                             "letter_share_shift": (di["letter_share"] - dj["letter_share"]).tolist(),
                             "hit_fam80_5_a": di["hit_fam80_5"], "hit_fam80_5_b": dj["hit_fam80_5"],
                             "hit_occ5_a": di["hit_occ5"], "hit_occ5_b": dj["hit_occ5"]})
            df = pd.DataFrame(rows)
            out[ptype] = {"pairs": rows, "mean_overlap10": float(df.overlap10.mean()),
                          "min_overlap10": float(df.overlap10.min()),
                          "mean_profile_shift_l2": float(df.profile_shift_l2.mean()),
                          "mean_signed_shift_a_minus_b": dict(zip(SCALES, np.mean(np.stack(df.profile_shift_signed), axis=0))),
                          "mean_jz_shift": float(df.jz_mean_shift.mean()),
                          "mean_jz_ge4_shift": float(df.jz_ge4_shift.mean()),
                          "mean_letter_share_shift": dict(zip(SCALES, np.mean(np.stack(df.letter_share_shift), axis=0))),
                          "hit_fam80_5_a": float(df.hit_fam80_5_a.mean()), "hit_fam80_5_b": float(df.hit_fam80_5_b.mean()),
                          "hit_occ5_a": float(df.hit_occ5_a.mean()), "hit_occ5_b": float(df.hit_occ5_b.mean())}
        gated = [r["overlap10"] for p in GATED_PAIR_TYPES for r in out[p]["pairs"]]
        out["gated_gender_name_mean_overlap10"] = float(np.mean(gated))
        out["gated_n_pairs"] = len(gated)
        bias[m] = out

    # ---- fusion / prototypes
    fusion = {}
    for name in models:
        G = protos[name] - protos[name].mean(axis=1, keepdims=True)
        rr, t1 = [], []
        for i, r in enumerate(st.itertuples()):
            if r.intended_riasec:
                t = target_vec(r.intended_riasec)
                rr.append(np.corrcoef(G[i], t)[0, 1])
                t1.append(SCALES[int(np.argmax(G[i]))] == r.intended_riasec[0])
            else:
                rr.append(np.nan)
                t1.append(np.nan)
        rr, t1 = np.array(rr, float), np.array(t1, float)
        fusion[f"prototype:{name}"] = {s: {"r": boot_mean(rr[sets[s]], rng, B), "top1": boot_mean(t1[sets[s]], rng, B)}
                                       for s in ("en_core", "vague_en", "spanish")}
    for m in emb:
        fusion[m] = {s: {"r": table[m][s]["fusion_r"], "top1": table[m][s]["fusion_top1"]}
                     for s in ("en_core", "vague_en", "spanish")}

    # ---- blind-rating sheet (best variant 20, best TF-IDF 5, random 5); key kept separate
    brng = np.random.default_rng(seed)
    pool = np.flatnonzero(en_core | sets["vague_en"])
    pick = brng.choice(pool, size=30, replace=False)
    assign = ["best"] * 20 + ["tfidf"] * 5 + ["random"] * 5
    order = brng.permutation(30)
    sheet, key = [], {}
    for pos, o in enumerate(order):
        i, kind = int(pick[o]), assign[o]
        lst = tops[best][i] if kind == "best" else tops[best_tfidf][i] if kind == "tfidf" else random_list_draw[i]
        rid = f"B{pos + 1:02d}"
        sheet.append({"rating_id": rid, "statement": st.text.iloc[i],
                      **{f"title{k + 1}": occ.title.iloc[int(lst[k])] for k in range(5)}})
        key[rid] = {"kind": kind, "method": best if kind == "best" else best_tfidf if kind == "tfidf" else "random",
                    "statement_id": st.id.iloc[i], "codes": [occ.code.iloc[int(c)] for c in lst[:5]]}
    pd.DataFrame(sheet).to_csv(FINDINGS / "e7_blind_sheet.csv", index=False, encoding="utf-8")
    (FINDINGS / "e7_blind_key.json").write_text(json.dumps(key, indent=1), encoding="utf-8")

    # ---- per-statement table (no titles, so the blind rating stays blind)
    ps = st[["id", "language", "category", "difficulty"]].copy()
    ps["trades"] = trades
    for m in (best, best_tfidf, "keyword"):
        for k in ("hit_occ5", "hit_fam80_5", "riasec_r"):
            ps[f"{m}|{k}"] = col(m, k)
        ps[f"{m}|top1_sim"] = top1[m][:n]
    ps["best_no_good_match"] = s_best[:n] < thr_best
    ps.to_csv(FINDINGS / "e7_per_statement.csv", index=False, encoding="utf-8")

    # ---- verdict
    t_best = table[best]["en_core"]["hit_fam80_5"]["mean"]
    d_pts = diff["mean"] * 100
    rb = rej[best]["en"]
    ov_g = bias[best]["gated_gender_name_mean_overlap10"]
    c = {"c1_hit": t_best, "c2_diff_pts": d_pts, "c3_frr": rb["heldout_frr"], "c3_offreject": rb["heldout_offtopic_reject"],
         "c4_overlap": ov_g}
    proven = t_best >= .70 and d_pts >= 10 and rb["heldout_frr"] <= .10 and rb["heldout_offtopic_reject"] >= .80 and ov_g >= .90
    promising = t_best >= .55 and d_pts >= 5 and rb["heldout_frr"] <= .20 and rb["heldout_offtopic_reject"] >= .60 and ov_g >= .80
    c["verdict"] = "proven" if proven else "promising" if promising else "not viable"
    c["pass"] = {"c1": t_best >= .70, "c2": d_pts >= 10, "c3": rb["heldout_frr"] <= .10 and rb["heldout_offtopic_reject"] >= .80,
                 "c4": ov_g >= .90}

    # ---- charts
    charts(table, methods, best, best_tfidf, top1, n, real_en, off_en, st, thr_best, bias, es, emb, sets)

    return {
        "seed": seed, "quick": quick, "runtime_s": round(time.time() - t0, 1), "bootstrap_B": B,
        "rejection_splits": n_splits, "random_draws": R,
        "n": {"occupations": len(occ), "tasks": len(tasks), "statements": n, "offtopic": len(off),
              "en_core": int(en_core.sum()), "rejection_real_en": int(real_en.sum()),
              "rejection_off_en": int(off_en.sum()), "trades_statements": int(sets["trades"].sum()),
              "non_trades_statements": int(sets["non_trades"].sum()),
              "keyword_no_hit_share_en_core": float(kw_nohit[:n][en_core].mean())},
        "models": log, "best_variant": best, "best_tfidf": best_tfidf,
        "table": table, "diff_best_minus_tfidf_fam80_5": diff, "diff_best_minus_tfidf_occ5": diff_occ,
        "diff_best_minus_keyword_fam80_5": diff_kw,
        "rejection": rej, "no_good_match": no_match, "negation": neg, "spanish": es, "bias": bias,
        "fusion": fusion, "verdict": c,
    }


def charts(table, methods, best, best_tfidf, top1, n, real_en, off_en, st, thr, bias, es, emb, sets):
    FINDINGS.mkdir(parents=True, exist_ok=True)
    ms = [m for m in methods]
    fam = [table[m]["en_core"]["hit_fam80_5"] for m in ms]
    occ5 = [table[m]["en_core"]["hit_occ5"] for m in ms]
    x = np.arange(len(ms))
    fig, ax = plt.subplots(figsize=(11, 4.5))
    for off_, vals, lab in ((-0.2, fam, "family Hit@5 (r>=.80)"), (0.2, occ5, "occupation Hit@5")):
        mv = np.array([v["mean"] for v in vals])
        ax.bar(x + off_, mv, 0.4, label=lab,
               yerr=[mv - np.array([v["lo"] for v in vals]), np.array([v["hi"] for v in vals]) - mv], capsize=2)
    ax.axhline(.70, ls="--", c="k", lw=.8)
    ax.set_xticks(x, ms, rotation=40, ha="right")
    ax.set_ylabel("share of statements")
    ax.set_title(f"E7 Hit@5 on EN-core statements (n = {fam[0]['n']}), 95% bootstrap CI; best = {best}")
    ax.legend()
    fig.tight_layout()
    fig.savefig(FINDINGS / "e7_hit_at_k.png", dpi=130)
    plt.close(fig)

    s = top1[best]
    vague_empty = (st.category == "vague_empty").to_numpy()
    fig, ax = plt.subplots(figsize=(7, 4))
    bins = np.linspace(min(s.min(), 0), s.max() + .02, 30)
    ax.hist(s[:n][real_en], bins, alpha=.6, label=f"real EN statements (n={real_en.sum()})")
    ax.hist(s[n:][off_en], bins, alpha=.6, label=f"off-topic EN (n={off_en.sum()})")
    for v in s[:n][vague_empty]:
        ax.axvline(v, c="purple", lw=1, ls=":")
    ax.axvline(thr, c="k", ls="--", label=f"Youden threshold {thr:.3f}")
    ax.set_xlabel(f"top-1 cosine similarity ({best})")
    ax.set_ylabel("count")
    ax.set_title("E7 rejection: real vs off-topic (dotted = vague_empty)")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(FINDINGS / "e7_rejection_hist.png", dpi=130)
    plt.close(fig)

    cats = [k for k in sets if k.startswith("cat:") and k != "cat:vague_empty"]
    fig, ax = plt.subplots(figsize=(11, 4))
    x = np.arange(len(cats))
    for j, m in enumerate([best, best_tfidf, "keyword", "random"]):
        ax.bar(x + (j - 1.5) * 0.2, [table[m][c]["hit_fam80_5"]["mean"] or 0 for c in cats], 0.2, label=m)
    ax.set_xticks(x, [f"{c[4:]}\n(n={table[best][c]['hit_fam80_5']['n']})" for c in cats], fontsize=8)
    ax.set_ylabel("family Hit@5")
    ax.set_title("E7 family Hit@5 by statement category (all languages)")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(FINDINGS / "e7_by_category.png", dpi=130)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(11, 4))
    labs, vals, cols = [], [], []
    palette = dict(zip(PAIR_TYPES, ["C0", "C1", "C2", "C3", "C4"]))
    for p in PAIR_TYPES:
        for r in bias[best][p]["pairs"]:
            labs.append(f"{r['pair']}\n{r['lang']}")
            vals.append(r["overlap10"])
            cols.append(palette[p])
    ax.bar(range(len(vals)), vals, color=cols)
    ax.axhline(.9, ls="--", c="k", lw=.8)
    ax.set_xticks(range(len(vals)), labs, fontsize=7)
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("top-10 overlap within pair")
    handles = [plt.Rectangle((0, 0), 1, 1, color=c) for c in palette.values()]
    ax.legend(handles, PAIR_TYPES, fontsize=7, ncol=5, loc="lower left")
    ax.set_title(f"E7 counterfactual pairs ({best}); n = {len(vals)} pairs")
    fig.tight_layout()
    fig.savefig(FINDINGS / "e7_bias_pairs.png", dpi=130)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(9, 4))
    x = np.arange(len(emb))
    ax.bar(x - .2, [es[m]["en_hit_fam80_5"] for m in emb], .4, label="EN originals")
    ax.bar(x + .2, [es[m]["es_hit_fam80_5"] for m in emb], .4, label="ES translations")
    ax.set_xticks(x, emb, rotation=30, ha="right")
    ax.set_ylabel("family Hit@5")
    ax.set_title(f"E7 Spanish vs English, n = {es[emb[0]]['n_pairs']} translation pairs")
    ax.legend()
    fig.tight_layout()
    fig.savefig(FINDINGS / "e7_spanish.png", dpi=130)
    plt.close(fig)


def score_blind() -> dict:
    res = json.loads(OUT_JSON.read_text(encoding="utf-8"))
    key = json.loads((FINDINGS / "e7_blind_key.json").read_text(encoding="utf-8"))
    rt = pd.read_csv(FINDINGS / "e7_blind_ratings.csv", dtype=str, keep_default_na=False, encoding="utf-8")
    rt["kind"] = rt.rating_id.map(lambda r: key[r]["kind"])
    rt["statement_id"] = rt.rating_id.map(lambda r: key[r]["statement_id"])
    out = {}
    for kind, g in rt.groupby("kind"):
        vc = g.rating.value_counts()
        out[kind] = {"n": int(len(g)), **{lab: int(vc.get(lab, 0)) for lab in ("sensible", "partly", "not")},
                     "share_sensible": float((g.rating == "sensible").mean()),
                     "share_sensible_or_partly": float(g.rating.isin(["sensible", "partly"]).mean())}
    b = out.get("best", {})
    out["secondary_bar_pass"] = bool(b.get("share_sensible", 0) >= .70)
    res["blind_rating"] = out
    OUT_JSON.write_text(json.dumps(rnd(res), indent=2), encoding="utf-8")
    # best-variant top-5 titles are now safe to write (rating done)
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--quick", action="store_true", help="primary model only, fewer bootstrap draws")
    ap.add_argument("--score-blind", action="store_true", help="score e7_blind_ratings.csv into the JSON")
    a = ap.parse_args()
    FINDINGS.mkdir(parents=True, exist_ok=True)
    if a.score_blind:
        print(json.dumps(score_blind(), indent=2))
        sys.exit(0)
    res = rnd(main(a.seed, a.quick))
    out = OUT_JSON if not a.quick else FINDINGS / "e7_free_text_matching_quick.json"
    out.write_text(json.dumps(res, indent=2), encoding="utf-8")
    print(json.dumps({k: res[k] for k in ("n", "best_variant", "best_tfidf", "verdict", "models")}, indent=2))
