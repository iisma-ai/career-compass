"""E6 — Supervised prediction of university major family from interest answers.

Run:   python -I research/feasibility/e6_major_prediction.py            (full run)
       python -I research/feasibility/e6_major_prediction.py --quick    (smoke run: subsample, small B)
Pre-registration and results: research/findings/e6_major_prediction.md
Outputs: research/findings/e6_major_prediction.json, e6_*.png
Reads data/processed/riasec_people.parquet and riasec_people_incl_shared_network.parquet only.
The major-family mapping is imported unchanged from research/feasibility/e1_data_audit.py.
"""
import argparse
import importlib.util
import json
import time
import warnings
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from scipy.stats import spearmanr
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import log_loss, roc_auc_score
from sklearn.model_selection import StratifiedKFold, train_test_split
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning)

ROOT = Path(__file__).resolve().parents[2]
FINDINGS = ROOT / "research" / "findings"
PROC = ROOT / "data" / "processed"

_spec = importlib.util.spec_from_file_location("e1_audit", ROOT / "research" / "feasibility" / "e1_data_audit.py")
e1 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(e1)

TYPES = list("RIASEC")
ITEMS = [f"{t}{i}" for t in TYPES for i in range(1, 9)]
TIPI = [f"TIPI{i}" for i in range(1, 11)]
EXCLUDED_TARGETS = ("Undecided/General studies", "Unmapped")
MIN_CLASS_N = 300
LR_C_GRID = (0.001, 0.01, 0.1, 1.0, 10.0)
HGB_GRID = [{"learning_rate": lr, "max_leaf_nodes": m} for lr in (0.05, 0.1) for m in (15, 31)]
FOCUS = ["Engineering", "CS/IT", "Math/Statistics", "Physical/Earth/Environmental sciences",
         "Psychology", "Health/Nursing/Allied health", "Education", "Social work/Counselling"]
STEM_CORE = ["Engineering", "CS/IT", "Math/Statistics", "Physical/Earth/Environmental sciences"]
STEM_SETS = {"stem_core": STEM_CORE, "stem_broad": STEM_CORE + ["Biology/Life sciences"]}
# Item texts from data/raw/openpsych_riasec_2018/RIASEC_data12Dec2018/codebook.txt (copied, not read at runtime)
ITEM_TEXT = dict(zip(ITEMS, [
    "Test the quality of parts before shipment", "Lay brick or tile", "Work on an offshore oil-drilling rig",
    "Assemble electronic parts", "Operate a grinding machine in a factory", "Fix a broken faucet",
    "Assemble products in a factory", "Install flooring in houses",
    "Study the structure of the human body", "Study animal behavior", "Do research on plants or animals",
    "Develop a new medical treatment or procedure", "Conduct biological research",
    "Study whales and other types of marine life", "Work in a biology lab", "Make a map of the bottom of an ocean",
    "Conduct a musical choir", "Direct a play", "Design artwork for magazines", "Write a song",
    "Write books or plays", "Play a musical instrument", "Perform stunts for a movie or television show",
    "Design sets for plays",
    "Give career guidance to people", "Do volunteer work at a non-profit organization",
    "Help people who have problems with drugs or alcohol", "Teach an individual an exercise routine",
    "Help people with family-related problems", "Supervise the activities of children at a camp",
    "Teach children how to read", "Help elderly people with their daily activities",
    "Sell restaurant franchises to individuals", "Sell merchandise at a department store",
    "Manage the operations of a hotel", "Operate a beauty salon or barber shop",
    "Manage a department within a large company", "Manage a clothing store", "Sell houses", "Run a toy store",
    "Generate the monthly payroll checks for an office", "Inventory supplies using a hand-held computer",
    "Use a computer program to generate customer bills", "Maintain employee records",
    "Compute and record statistical and other numerical data", "Operate a calculator",
    "Handle customers' bank transactions", "Keep shipping and receiving records"]))


# ----------------------------------------------------------------------------- data
def major_family(major: pd.Series) -> pd.Series:
    norm = major.map(lambda v: e1.normalise_major(v) if isinstance(v, str) and v.strip() else None)
    valid = norm.where(norm.notna() & ~norm.fillna("").map(e1.is_junk))
    return valid.map(lambda s: e1.map_family(s) if isinstance(s, str) else None)


def load(path: Path, log: dict, classes=None) -> pd.DataFrame:
    d = pd.read_parquet(path)
    log["rows"] = len(d)
    d = d.assign(family=major_family(d["major"]))
    d = d[d.age >= 18]
    log["age_ge_18"] = len(d)
    d = d[d.family.notna()]
    log["valid_major"] = len(d)
    log["excluded_target_sizes"] = {k: int((d.family == k).sum()) for k in EXCLUDED_TARGETS}
    d = d[~d.family.isin(EXCLUDED_TARGETS)]
    counts = d.family.value_counts()
    if classes is None:
        dropped = counts[counts < MIN_CLASS_N]
        log["dropped_small_classes"] = {k: int(v) for k, v in dropped.items()}
        d = d[~d.family.isin(dropped.index)]
    else:
        log["rows_outside_classes"] = int((~d.family.isin(classes)).sum())
        d = d[d.family.isin(classes)]
    log["analysis_rows"] = len(d)
    log["class_counts"] = {k: int(v) for k, v in d.family.value_counts().items()}
    log["gender_counts"] = {str(k): int(v) for k, v in d.gender.value_counts(dropna=False).items()}
    return d.reset_index(drop=True)


def big5(d: pd.DataFrame) -> np.ndarray:
    t = d[TIPI].astype(float).where(d[TIPI] > 0)  # 0 = missing
    r = lambda c: 8 - t[c]
    cols = [(t.TIPI1 + r("TIPI6")) / 2, (r("TIPI2") + t.TIPI7) / 2, (t.TIPI3 + r("TIPI8")) / 2,
            (r("TIPI4") + t.TIPI9) / 2, (t.TIPI5 + r("TIPI10")) / 2]
    return np.column_stack(cols)


def features(d: pd.DataFrame, fs: str) -> np.ndarray:
    items = d[ITEMS].to_numpy(float)
    if fs == "F1":
        return items
    if fs == "F2":
        sc = d[TYPES].to_numpy(float)
        return np.column_stack([sc, sc.mean(1), sc.max(1) - sc.min(1)])
    if fs == "F3":
        return np.column_stack([items, big5(d)])
    if fs == "F4":
        g = d.gender.fillna(0).to_numpy()
        e = d.education.fillna(0).to_numpy()
        demo = [d.age.to_numpy(float)] + [(g == k).astype(float) for k in (1, 2, 3)] + \
               [(e == k).astype(float) for k in (1, 2, 3, 4)]
        return np.column_stack([items] + demo)
    raise ValueError(fs)


FS_NAMES = {"F1": ITEMS, "F2": TYPES + ["elevation", "differentiation"],
            "F3": ITEMS + ["Extraversion", "Agreeableness", "Conscientiousness", "EmotionalStability", "Openness"],
            "F4": ITEMS + ["age", "male", "female", "other", "edu_lt_hs", "edu_hs", "edu_uni", "edu_grad"]}


# ----------------------------------------------------------------------------- models
class Majority:
    def fit(self, X, y, K):
        self.p = np.bincount(y, minlength=K) / len(y)
        return self

    def scores(self, X):
        return np.tile(self.p, (len(X), 1))


class StratRandom(Majority):
    def __init__(self, seed):
        self.rng = np.random.default_rng(seed)

    def scores(self, X):
        g = self.rng.gumbel(size=(len(X), len(self.p)))
        return np.log(self.p + 1e-12) + g


class Centroid:
    """Family centroid of the 6 scale means on train; rank by Pearson r (shape match)."""

    def fit(self, P, y, K):
        self.C = np.vstack([np.nanmean(P[y == k], 0) for k in range(K)])
        return self

    def scores(self, P):
        a = P - np.nanmean(P, 1, keepdims=True)
        b = self.C - self.C.mean(1, keepdims=True)
        a = a / np.linalg.norm(a, axis=1, keepdims=True).clip(1e-9)
        b = b / np.linalg.norm(b, axis=1, keepdims=True)
        return np.nan_to_num(a) @ b.T


def make_model(kind: str, params: dict, weighted: bool, seed: int):
    cw = "balanced" if weighted else None
    if kind == "lr":
        return make_pipeline(SimpleImputer(strategy="median"), StandardScaler(),
                             LogisticRegression(C=params["C"], max_iter=3000, class_weight=cw))
    if kind == "hgb":
        return HistGradientBoostingClassifier(max_iter=500, early_stopping=True, validation_fraction=0.1,
                                              n_iter_no_change=20, random_state=seed, class_weight=cw, **params)
    if kind == "mlp":
        return make_pipeline(SimpleImputer(strategy="median"), StandardScaler(),
                             MLPClassifier(hidden_layer_sizes=(64,), alpha=1e-3, early_stopping=True,
                                           max_iter=300, random_state=seed))
    raise ValueError(kind)


def proba(model, X, K):
    p = model.predict_proba(X)
    out = np.zeros((len(X), K))
    out[:, model.classes_] = p
    return out


# ----------------------------------------------------------------------------- metrics
def topk_correct(y, S, k):
    top = np.argpartition(-S, kth=min(k, S.shape[1] - 1) - 1, axis=1)[:, :k]
    return (top == y[:, None]).any(1)


def confusion(y, pred, K):
    return np.bincount(y * K + pred, minlength=K * K).reshape(K, K)


def macro_f1_bal(y, pred, K):
    cm = confusion(y, pred, K)
    tp = np.diag(cm).astype(float)
    rec = np.divide(tp, cm.sum(1), out=np.zeros(K), where=cm.sum(1) > 0)
    prec = np.divide(tp, cm.sum(0), out=np.zeros(K), where=cm.sum(0) > 0)
    f1 = np.divide(2 * prec * rec, prec + rec, out=np.zeros(K), where=(prec + rec) > 0)
    present = cm.sum(1) > 0
    return f1.mean(), rec[present].mean()


def ece(y, P, bins=15):
    conf = P.max(1)
    corr = P.argmax(1) == y
    edges = np.linspace(0, 1, bins + 1)
    idx = np.clip(np.digitize(conf, edges[1:-1]), 0, bins - 1)
    e, rel = 0.0, []
    for b in range(bins):
        m = idx == b
        if m.any():
            e += m.mean() * abs(corr[m].mean() - conf[m].mean())
            rel.append([float(conf[m].mean()), float(corr[m].mean()), int(m.sum())])
    return float(e), rel


def evaluate(y, S, K, P=None, boot_idx=None):
    pred = S.argmax(1)
    c = {k: topk_correct(y, S, k) for k in (1, 3, 5)}
    f1, bal = macro_f1_bal(y, pred, K)
    out = {f"top{k}": float(v.mean()) for k, v in c.items()}
    out.update(macro_f1=float(f1), balanced_acc=float(bal), n=len(y))
    if P is not None:
        out["log_loss"] = float(log_loss(y, np.clip(P, 1e-12, 1), labels=np.arange(K)))
        out["ece"], out["reliability"] = ece(y, P)
    if boot_idx is not None:
        for k, v in c.items():
            bs = v[boot_idx].mean(1)
            out[f"top{k}_ci"] = [float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))]
        fb = np.array([macro_f1_bal(y[i], pred[i], K) for i in boot_idx])
        out["macro_f1_ci"] = np.percentile(fb[:, 0], [2.5, 97.5]).tolist()
        out["balanced_acc_ci"] = np.percentile(fb[:, 1], [2.5, 97.5]).tolist()
    return out, c


def per_class(y, S, K, names, prior_test):
    pred = S.argmax(1)
    cm = confusion(y, pred, K)
    t3 = topk_correct(y, S, 3)
    rows = {}
    for k in range(K):
        n_true, n_pred = cm[k].sum(), cm[:, k].sum()
        prec = cm[k, k] / n_pred if n_pred else 0.0
        rows[names[k]] = {"n_test": int(n_true), "base_rate": float(prior_test[k]),
                          "recall_top1": float(cm[k, k] / n_true), "precision_top1": float(prec),
                          "lift_top1": float(prec / prior_test[k]), "recall_top3": float(t3[y == k].mean()),
                          "pred_share_top1": float(n_pred / len(y))}
    return rows, cm


# ----------------------------------------------------------------------------- CV tuning
def _cv_fold(kind, params, weighted, X, y, tr, va, K, seed):
    m = make_model(kind, params, weighted, seed).fit(X[tr], y[tr])
    P = proba(m, X[va], K)
    return topk_correct(y[va], P, 3).mean(), log_loss(y[va], np.clip(P, 1e-12, 1), labels=np.arange(K))


def cv_score(kind, params, weighted, X, y, K, folds, seed, n_jobs):
    res = Parallel(n_jobs=n_jobs)(delayed(_cv_fold)(kind, params, weighted, X, y, tr, va, K, seed)
                                  for tr, va in folds)
    r = np.array(res)
    return {"cv_top3": float(r[:, 0].mean()), "cv_top3_sd": float(r[:, 0].std()), "cv_log_loss": float(r[:, 1].mean())}


def pick(cands):
    return sorted(cands, key=lambda c: (-round(c["cv_top3"], 4), c["cv_log_loss"]))[0]


# ----------------------------------------------------------------------------- fairness
def gender_block(y, S, gender, K, names):
    out = {}
    pred = S.argmax(1)
    in3 = np.argsort(-S, 1)[:, :3]
    for g, lab in ((1, "male"), (2, "female")):
        m = gender == g
        ev, _ = evaluate(y[m], S[m], K)
        act = np.bincount(y[m], minlength=K) / m.sum()
        prd = np.bincount(pred[m], minlength=K) / m.sum()
        cm = confusion(y[m], pred[m], K)
        rec = np.divide(np.diag(cm), cm.sum(1), out=np.full(K, np.nan), where=cm.sum(1) > 0)
        rec3 = np.array([topk_correct(y[m][y[m] == k], S[m][y[m] == k], 3).mean() if (y[m] == k).any() else np.nan
                         for k in range(K)])
        incl3 = np.array([(in3[m] == k).any(1).mean() for k in range(K)])
        out[lab] = {"n": int(m.sum()), **{k: ev[k] for k in ("top1", "top3", "top5", "macro_f1", "balanced_acc")},
                    "families": {names[k]: {"actual_share": float(act[k]), "pred_share_top1": float(prd[k]),
                                            "in_top3_rate": float(incl3[k]), "recall_top1": float(rec[k]),
                                            "recall_top3": float(rec3[k])} for k in range(K)}}
    fam = {}
    num, den = 0.0, 0.0
    for k in range(K):
        a_gap = out["female"]["families"][names[k]]["actual_share"] - out["male"]["families"][names[k]]["actual_share"]
        p_gap = out["female"]["families"][names[k]]["pred_share_top1"] - out["male"]["families"][names[k]]["pred_share_top1"]
        fam[names[k]] = {"actual_gap_F_minus_M": float(a_gap), "pred_gap_F_minus_M": float(p_gap),
                         "amplification": float(p_gap / a_gap) if abs(a_gap) > 0.005 else None}
        num += abs(p_gap)
        den += abs(a_gap)
    out["gap"] = fam
    out["total_abs_gap_ratio_pred_over_actual"] = float(num / den)
    stem = {}
    for sname, fams in STEM_SETS.items():
        ks = [names.index(f) for f in fams if f in names]
        row = {}
        for g, lab in ((1, "male"), (2, "female")):
            m = gender == g
            row[lab] = {"actual_share": float(np.isin(y[m], ks).mean()),
                        "pred_share_top1": float(np.isin(pred[m], ks).mean()),
                        "any_in_top3_rate": float(np.isin(in3[m], ks).any(1).mean()),
                        "recall_top3_of_actual_stem": float(np.isin(in3[m][np.isin(y[m], ks)], ks).any(1).mean())}
        row["actual_gap_M_minus_F"] = row["male"]["actual_share"] - row["female"]["actual_share"]
        row["pred_gap_M_minus_F"] = row["male"]["pred_share_top1"] - row["female"]["pred_share_top1"]
        row["amplification"] = row["pred_gap_M_minus_F"] / row["actual_gap_M_minus_F"]
        stem[sname] = row
    out["stem"] = stem
    return out


# ----------------------------------------------------------------------------- main
def main(seed: int, quick: bool) -> dict:
    t0 = time.time()
    rng = np.random.default_rng(seed)
    res = {"seed": seed, "quick": quick}
    log = {}
    d = load(PROC / "riasec_people.parquet", log)
    if quick:
        d = d.groupby("family", group_keys=False).sample(frac=0.15, random_state=seed).reset_index(drop=True)
        log["quick_subsample_rows"] = len(d)
    res["sample"] = log
    names = d.family.value_counts().index.tolist()  # class order = frequency
    K = len(names)
    y_all = d.family.map({n: i for i, n in enumerate(names)}).to_numpy()
    idx_tr, idx_te = train_test_split(np.arange(len(d)), test_size=0.2, stratify=y_all, random_state=seed)
    ytr, yte = y_all[idx_tr], y_all[idx_te]
    res["split"] = {"train": len(idx_tr), "test": len(idx_te), "classes": names}
    prior_te = np.bincount(yte, minlength=K) / len(yte)
    X = {fs: features(d, fs) for fs in ("F1", "F2", "F3", "F4")}
    P6 = d[TYPES].to_numpy(float)
    folds = list(StratifiedKFold(5, shuffle=True, random_state=seed).split(idx_tr, ytr))
    B = 200 if quick else 1000
    boot_idx = rng.integers(0, len(yte), size=(B, len(yte)))
    n_jobs = 2

    # ---- baselines
    base_models = {"B0_majority": Majority().fit(None, ytr, K),
                   "B1_stratified_random": StratRandom(seed).fit(None, ytr, K),
                   "B2_centroid_pearson": Centroid().fit(P6[idx_tr], ytr, K)}
    test_scores, test_probs, correct = {}, {}, {}
    table = {}
    for nm, m in base_models.items():
        S = m.scores(P6[idx_te])
        ev, c = evaluate(yte, S, K, P=S if nm == "B0_majority" else None, boot_idx=boot_idx)
        cv = []
        for tr, va in folds:
            mm = (Centroid().fit(P6[idx_tr][tr], ytr[tr], K) if nm.startswith("B2") else
                  type(m)(seed).fit(None, ytr[tr], K) if nm.startswith("B1") else Majority().fit(None, ytr[tr], K))
            cv.append(topk_correct(ytr[va], mm.scores(P6[idx_tr][va]), 3).mean())
        ev["cv_top3"] = float(np.mean(cv))
        table[nm] = ev
        test_scores[nm], correct[nm] = S, c
        print(f"{nm}: top3 {ev['top3']:.3f}  ({time.time() - t0:.0f}s)", flush=True)
    test_probs["B0_majority"] = test_scores["B0_majority"]

    # ---- tuning
    tuning = {}
    for fs in ("F1", "F2", "F3", "F4"):
        Xtr = X[fs][idx_tr]
        for w in (False, True):
            cands = []
            for C in LR_C_GRID:
                r = cv_score("lr", {"C": C}, w, Xtr, ytr, K, folds, seed, n_jobs)
                cands.append({"params": {"C": C}, **r})
            tuning[f"lr_{'bal' if w else 'unw'}_{fs}"] = {"grid": cands, "best": pick(cands)}
            print(f"tuned lr {fs} w={w}: {pick(cands)}  ({time.time() - t0:.0f}s)", flush=True)
    for w in (False, True):
        cands = []
        for p in HGB_GRID:
            r = cv_score("hgb", p, w, X["F1"][idx_tr], ytr, K, folds, seed, 1)
            cands.append({"params": p, **r})
            print(f"  hgb {p} w={w}: {r}  ({time.time() - t0:.0f}s)", flush=True)
        best = pick(cands)
        tuning[f"hgb_{'bal' if w else 'unw'}_F1"] = {"grid": cands, "best": best}
        for fs in ("F2", "F3", "F4"):
            r = cv_score("hgb", best["params"], w, X[fs][idx_tr], ytr, K, folds, seed, 1)
            tuning[f"hgb_{'bal' if w else 'unw'}_{fs}"] = {"grid": [{"params": best["params"], **r}],
                                                           "best": {"params": best["params"], **r},
                                                           "note": "params reused from F1 tuning"}
            print(f"  hgb {fs} w={w}: {r}  ({time.time() - t0:.0f}s)", flush=True)
    for fs in ("F1", "F3"):
        r = cv_score("mlp", {}, False, X[fs][idx_tr], ytr, K, folds, seed, n_jobs)
        tuning[f"mlp_unw_{fs}"] = {"grid": [{"params": {}, **r}], "best": {"params": {}, **r}}
        print(f"  mlp {fs}: {r}  ({time.time() - t0:.0f}s)", flush=True)
    res["tuning"] = tuning

    # ---- selection on CV (interest-only feature sets)
    interest = {k: v["best"]["cv_top3"] for k, v in tuning.items() if not k.endswith("F4")}
    best_name = max(interest, key=interest.get)
    res["selection"] = {"best_interest_only": best_name, "cv_top3": interest[best_name],
                        "cv_top3_all": dict(sorted(interest.items(), key=lambda kv: -kv[1]))}
    print("selected:", best_name, flush=True)

    # ---- final fits on full train, evaluate on test
    fitted = {}
    for key, tv in tuning.items():
        kind, wt, fs = key.split("_")
        m = make_model(kind, tv["best"]["params"], wt == "bal", seed).fit(X[fs][idx_tr], ytr)
        P = proba(m, X[fs][idx_te], K)
        ev, c = evaluate(yte, P, K, P=P, boot_idx=boot_idx)
        ev["cv_top3"] = tv["best"]["cv_top3"]
        ev["params"] = tv["best"]["params"]
        table[key] = ev
        test_scores[key], test_probs[key], correct[key], fitted[key] = P, P, c, m
        print(f"test {key}: top1 {ev['top1']:.3f} top3 {ev['top3']:.3f} ({time.time() - t0:.0f}s)", flush=True)
    res["results"] = table

    # paired differences on top-3
    cb = correct[best_name][3]
    res["paired_top3_diff"] = {}
    for b in ("B0_majority", "B2_centroid_pearson", "lr_unw_F1", "lr_unw_F2"):
        diff = (cb[boot_idx].astype(float) - correct[b][3][boot_idx]).mean(1)
        res["paired_top3_diff"][b] = {"diff": float(cb.mean() - correct[b][3].mean()),
                                      "ci": np.percentile(diff, [2.5, 97.5]).tolist()}

    # ---- verdict
    bt, b0, b2 = table[best_name], table["B0_majority"], table["B2_centroid_pearson"]
    beats = bt["top3_ci"][0] > b0["top3_ci"][1] and bt["top3_ci"][0] > b2["top3_ci"][1]
    verdict = ("PROVEN" if beats and bt["top3"] >= 0.50 else "PROMISING" if beats else "NOT VIABLE")
    res["verdict"] = {"best": best_name, "top3": bt["top3"], "top3_ci": bt["top3_ci"],
                      "majority_top3_ci": b0["top3_ci"], "centroid_top3_ci": b2["top3_ci"],
                      "non_overlapping_vs_both": bool(beats), "verdict": verdict}

    # ---- per-class, confusion, centroid similarity
    pcs = {}
    for nm in ("B2_centroid_pearson", best_name, "lr_unw_F1", "lr_bal_F1", "hgb_unw_F1", "hgb_bal_F1"):
        pcs[nm], cm = per_class(yte, test_scores[nm], K, names, prior_te)
        if nm == best_name:
            cm_best = cm
    res["per_class"] = pcs
    cmn = cm_best / cm_best.sum(1, keepdims=True)
    off = [(cmn[i, j], names[i], names[j]) for i in range(K) for j in range(K) if i != j]
    off.sort(reverse=True)
    cent = base_models["B2_centroid_pearson"].C
    cc = np.corrcoef(cent)
    sym = cmn + cmn.T
    iu = np.triu_indices(K, 1)
    top_pairs = sorted(zip(sym[iu], iu[0], iu[1]), reverse=True)[:10]
    res["confusion"] = {
        "top_off_diagonal": [{"true": t, "pred": p, "rate": float(r)} for r, t, p in off[:15]],
        "spearman_confusion_vs_centroid_r": float(spearmanr(sym[iu], cc[iu]).statistic),
        "mean_centroid_r_top10_confused_pairs": float(np.mean([cc[i, j] for _, i, j in top_pairs])),
        "mean_centroid_r_all_pairs": float(cc[iu].mean())}
    cent_c = cent - cent.mean(1, keepdims=True)
    pop_c = cent_c - (P6[idx_tr] - np.nanmean(P6[idx_tr], 1, keepdims=True)).mean(0)
    res["centroids"] = {names[k]: {"profile": dict(zip(TYPES, np.round(cent[k], 3).tolist())),
                                   "holland_code": "".join(np.array(TYPES)[np.argsort(-cent_c[k])[:3]]),
                                   "distinctive_code_vs_population": "".join(np.array(TYPES)[np.argsort(-pop_c[k])[:3]])}
                        for k in range(K)}

    # ---- coefficients (LR unweighted F1, standardised items)
    lr = fitted["lr_unw_F1"][-1]
    coef = np.zeros((K, len(ITEMS)))
    coef[lr.classes_] = lr.coef_
    res["coefficients"] = {names[k]: {
        "top_positive": [[ITEMS[j], ITEM_TEXT[ITEMS[j]], float(coef[k, j])] for j in np.argsort(-coef[k])[:4]],
        "top_negative": [[ITEMS[j], ITEM_TEXT[ITEMS[j]], float(coef[k, j])] for j in np.argsort(coef[k])[:3]],
        "mean_by_scale": {t: float(coef[k, i * 8:(i + 1) * 8].mean()) for i, t in enumerate(TYPES)}}
        for k in range(K)}
    if best_name.startswith("lr") and best_name != "lr_unw_F1":
        bl = fitted[best_name][-1]
        bcoef = np.zeros((K, bl.coef_.shape[1]))
        bcoef[bl.classes_] = bl.coef_
        fn = FS_NAMES[best_name.split("_")[2]]
        res["coefficients_best_model_extra_features"] = {
            names[k]: {f: float(bcoef[k, j]) for j, f in enumerate(fn) if f not in ITEMS} for k in range(K)}

    # ---- fairness
    dte = d.iloc[idx_te]
    gen = dte.gender.fillna(0).to_numpy()
    fair = {}
    kind, wt, _ = best_name.split("_")
    f4_name = f"{kind}_{wt}_F4" if f"{kind}_{wt}_F4" in test_scores else "lr_unw_F4"
    res["fairness_f4_counterpart"] = f4_name
    for nm in dict.fromkeys([best_name, "lr_unw_F1", "lr_bal_F1", f4_name, "lr_unw_F4", "B2_centroid_pearson",
                             "B0_majority"]):
        fair[nm] = gender_block(yte, test_scores[nm], gen, K, names)
    other = gen == 3
    fair["gender_other_pooled_warning"] = {"n": int(other.sum()),
                                           "top3_best": float(correct[best_name][3][other].mean()) if other.any() else None,
                                           "note": "too few rows for a stable estimate"}
    agb = np.where(dte.age < 25, "18-24", "25+")
    fair["age_bands"] = {b: {nm: {"n": int((agb == b).sum()),
                                  "top1": float(correct[nm][1][agb == b].mean()),
                                  "top3": float(correct[nm][3][agb == b].mean())}
                             for nm in (best_name, "B0_majority", "B2_centroid_pearson")} for b in ("18-24", "25+")}
    # how much gender information the items carry
    gtr = d.gender.fillna(0).to_numpy()[idx_tr]
    mtr, mte = np.isin(gtr, (1, 2)), np.isin(gen, (1, 2))
    gm = make_model("lr", {"C": 1.0}, False, seed).fit(X["F1"][idx_tr][mtr], gtr[mtr] == 2)
    pg = gm.predict_proba(X["F1"][idx_te][mte])[:, 1]
    yg = gen[mte] == 2
    aucs = []
    for i in range(B):
        j = rng.integers(0, len(yg), len(yg))
        aucs.append(roc_auc_score(yg[j], pg[j]))
    fair["gender_from_items_auc"] = {"auc": float(roc_auc_score(yg, pg)),
                                     "ci": np.percentile(aucs, [2.5, 97.5]).tolist(), "n_test": int(mte.sum())}
    res["fairness"] = fair

    # ---- psychology dominance
    psy = names.index("Psychology")
    nonpsy = yte != psy
    psyres = {"psych_share_test_actual": float(prior_te[psy]),
              "psych_share_pred_top1": {nm: float((test_scores[nm].argmax(1) == psy).mean())
                                        for nm in (best_name, "lr_unw_F1", "lr_bal_F1", "hgb_unw_F1", "B2_centroid_pearson")},
              "psych_in_top3_rate": {nm: float((np.argsort(-test_scores[nm], 1)[:, :3] == psy).any(1).mean())
                                     for nm in (best_name, "lr_unw_F1", "lr_bal_F1", "B2_centroid_pearson")},
              "full_model_on_nonpsych_rows": {nm: {f"top{k}": float(correct[nm][k][nonpsy].mean()) for k in (1, 3, 5)}
                                              for nm in (best_name, "B0_majority", "B2_centroid_pearson")}}
    keep = [k for k in range(K) if k != psy]
    remap = {k: i for i, k in enumerate(keep)}
    trm, tem = ytr != psy, yte != psy
    ytr2 = np.array([remap[v] for v in ytr[trm]])
    yte2 = np.array([remap[v] for v in yte[tem]])
    K2 = K - 1
    bidx2 = rng.integers(0, len(yte2), size=(B, len(yte2)))
    fsb = best_name.split("_")[2]
    m2 = make_model(kind, tuning[best_name]["best"]["params"], wt == "bal", seed).fit(X[fsb][idx_tr][trm], ytr2)
    P2 = proba(m2, X[fsb][idx_te][tem], K2)
    psyres["refit_without_psychology"] = {
        "n_test": int(tem.sum()),
        best_name: evaluate(yte2, P2, K2, P=P2, boot_idx=bidx2)[0],
        "B0_majority": evaluate(yte2, Majority().fit(None, ytr2, K2).scores(P6[idx_te][tem]), K2, boot_idx=bidx2)[0],
        "B2_centroid_pearson": evaluate(yte2, Centroid().fit(P6[idx_tr][trm], ytr2, K2).scores(P6[idx_te][tem]), K2,
                                        boot_idx=bidx2)[0]}
    for v in psyres["refit_without_psychology"].values():
        if isinstance(v, dict):
            v.pop("reliability", None)
    res["psychology"] = psyres

    # ---- robustness on the incl-shared table
    rob = {}
    wlog = {}
    w = load(PROC / "riasec_people_incl_shared_network.parquet", wlog, classes=names)
    if quick:
        w = w.sample(frac=0.15, random_state=seed).reset_index(drop=True)
    rob["sample"] = wlog
    yw = w.family.map({n: i for i, n in enumerate(names)}).to_numpy()
    sh = w.shared_network.to_numpy(bool)
    Xw = {fs: features(w, fs) for fs in ("F1", "F2", "F3")}
    P6w = w[TYPES].to_numpy(float)
    bsh = rng.integers(0, sh.sum(), size=(B, sh.sum()))
    rob["a_shared_only_trained_on_main"] = {"n": int(sh.sum())}
    for nm in dict.fromkeys(["B0_majority", "B2_centroid_pearson", "lr_unw_F1", best_name]):
        if nm.startswith("B"):
            S = base_models[nm].scores(P6w[sh])
        else:
            S = proba(fitted[nm], Xw[nm.split("_")[2]][sh], K)
        ev, _ = evaluate(yw[sh], S, K, P=S if not nm.startswith("B2") else None, boot_idx=bsh)
        ev.pop("reliability", None)
        rob["a_shared_only_trained_on_main"][nm] = ev
    itr, ite = train_test_split(np.arange(len(w)), test_size=0.2, stratify=yw, random_state=seed)
    bw = rng.integers(0, len(ite), size=(B, len(ite)))
    rob["b_fresh_split_incl_shared"] = {"train": len(itr), "test": len(ite)}
    sets = {"B0_majority": Majority().fit(None, yw[itr], K).scores(P6w[ite]),
            "B2_centroid_pearson": Centroid().fit(P6w[itr], yw[itr], K).scores(P6w[ite])}
    for nm in dict.fromkeys(["lr_unw_F1", best_name]):
        k_, w_, f_ = nm.split("_")
        m = make_model(k_, tuning[nm]["best"]["params"], w_ == "bal", seed).fit(Xw[f_][itr], yw[itr])
        sets[nm] = proba(m, Xw[f_][ite], K)
    for nm, S in sets.items():
        ev, _ = evaluate(yw[ite], S, K, P=S if not nm.startswith("B2") else None, boot_idx=bw)
        ev.pop("reliability", None)
        rob["b_fresh_split_incl_shared"][nm] = ev
    res["robustness"] = rob
    res["runtime_s"] = round(time.time() - t0, 1)

    charts(res, names, cmn, test_probs, best_name, coef, len(yte))
    return res


# ----------------------------------------------------------------------------- charts
SHORT = {"Business/Management/Marketing": "Business", "Health/Nursing/Allied health": "Health/Nursing",
         "Languages/Literature": "Languages/Lit", "Physical/Earth/Environmental sciences": "Phys/Earth/Env sci",
         "Humanities (history/philosophy/religion)": "Humanities", "Medicine/Dentistry/Pharmacy": "Medicine/Pharm",
         "Communication/Media/Journalism": "Communication", "Arts/Design/Performing arts": "Arts/Design",
         "Social work/Counselling": "Social work/Couns", "Law/Criminal justice": "Law/Crim justice",
         "Biology/Life sciences": "Biology", "Accounting/Finance": "Accounting/Fin",
         "Architecture/Planning": "Architecture", "Math/Statistics": "Math/Stats"}


def charts(res, names, cmn, probs, best, coef, n_test):
    sn = [SHORT.get(n, n) for n in names]
    tab = res["results"]
    # 1 main results: top-1/3/5 with CIs
    order = ["B0_majority", "B1_stratified_random", "B2_centroid_pearson"] + \
            [k for k in tab if not k.startswith("B")]
    fig, ax = plt.subplots(figsize=(12, 5.5))
    x = np.arange(len(order))
    for off, k, col in ((-0.27, 1, "#9ecae1"), (0, 3, "#3182bd"), (0.27, 5, "#08519c")):
        v = [tab[o][f"top{k}"] for o in order]
        e = np.array([[tab[o][f"top{k}"] - tab[o][f"top{k}_ci"][0], tab[o][f"top{k}_ci"][1] - tab[o][f"top{k}"]]
                      for o in order]).T
        ax.bar(x + off, v, 0.27, yerr=e, color=col, label=f"top-{k}", capsize=1.5)
    ax.axhline(tab["B0_majority"]["top3"], ls="--", c="grey", lw=0.8)
    ax.axhline(0.5, ls=":", c="red", lw=0.8, label="top-3 bar .50")
    ax.set_xticks(x, [o + (" *" if o == best else "") for o in order], rotation=70, fontsize=7)
    ax.set_ylabel("Test accuracy (95% bootstrap CI)")
    ax.set_title(f"E6 major-family prediction, 21 families, test n={n_test:,} (* = CV-selected best interest-only)")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(FINDINGS / "e6_results.png", dpi=120)
    plt.close(fig)
    # 2 confusion
    fig, ax = plt.subplots(figsize=(11, 9.5))
    im = ax.imshow(cmn, cmap="Blues", vmin=0, vmax=max(0.5, cmn.max()))
    ax.set_xticks(range(len(names)), sn, rotation=80, fontsize=7)
    ax.set_yticks(range(len(names)), sn, fontsize=7)
    for i in range(len(names)):
        for j in range(len(names)):
            if cmn[i, j] >= 0.08:
                ax.text(j, i, f"{cmn[i, j]:.2f}", ha="center", va="center", fontsize=5.5,
                        color="white" if cmn[i, j] > 0.3 else "black")
    ax.set_xlabel("Predicted (top-1)")
    ax.set_ylabel("True family")
    ax.set_title(f"E6 row-normalised confusion, {best}, test n={n_test:,}")
    fig.colorbar(im, ax=ax, shrink=0.7)
    fig.tight_layout()
    fig.savefig(FINDINGS / "e6_confusion.png", dpi=120)
    plt.close(fig)
    # 3 reliability
    fig, ax = plt.subplots(figsize=(6, 6))
    for nm in dict.fromkeys([best, "lr_unw_F1", "lr_bal_F1", "hgb_unw_F1"]):
        rel = np.array(tab[nm]["reliability"])
        ax.plot(rel[:, 0], rel[:, 1], "o-", ms=3, label=f"{nm} (ECE {tab[nm]['ece']:.3f})")
    ax.plot([0, 1], [0, 1], "k--", lw=0.8)
    ax.set_xlim(0, 0.8)
    ax.set_ylim(0, 0.8)
    ax.set_xlabel("Mean top-1 predicted probability (bin)")
    ax.set_ylabel("Observed top-1 accuracy")
    ax.set_title(f"E6 reliability of top-1 probability, test n={n_test:,}")
    ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(FINDINGS / "e6_reliability.png", dpi=120)
    plt.close(fig)
    # 4 per-class recall vs base rate
    fig, ax = plt.subplots(figsize=(8, 5.5))
    for nm, mk in ((best, "o"), ("lr_bal_F1", "s"), ("B2_centroid_pearson", "^")):
        pc = res["per_class"][nm]
        ax.scatter([pc[n]["base_rate"] for n in names], [pc[n]["recall_top3"] for n in names], marker=mk, label=nm, s=22)
    for n in names:
        pc = res["per_class"][best][n]
        ax.annotate(SHORT.get(n, n), (pc["base_rate"], pc["recall_top3"]), fontsize=6)
    ax.set_xscale("log")
    ax.set_xlabel("Test base rate (log)")
    ax.set_ylabel("Top-3 recall")
    ax.set_title(f"E6 per-family top-3 recall vs base rate, test n={n_test:,}")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(FINDINGS / "e6_per_class_recall.png", dpi=120)
    plt.close(fig)
    # 5 coefficient heatmap
    fig, ax = plt.subplots(figsize=(7, 8))
    M = np.array([[res["coefficients"][n]["mean_by_scale"][t] for t in TYPES] for n in names])
    v = np.abs(M).max()
    im = ax.imshow(M, cmap="RdBu_r", vmin=-v, vmax=v)
    ax.set_xticks(range(6), TYPES)
    ax.set_yticks(range(len(names)), sn, fontsize=7)
    for i in range(len(names)):
        for j in range(6):
            ax.text(j, i, f"{M[i, j]:.2f}", ha="center", va="center", fontsize=6)
    ax.set_title("E6 LR (F1, unweighted) mean standardised coefficient per scale")
    fig.colorbar(im, ax=ax, shrink=0.6)
    fig.tight_layout()
    fig.savefig(FINDINGS / "e6_coefficients.png", dpi=120)
    plt.close(fig)
    # 6 gender: actual vs predicted share, interest-only vs F4
    fair = res["fairness"]
    f4 = res["fairness_f4_counterpart"]
    fig, axes = plt.subplots(1, 2, figsize=(13, 7), sharey=True)
    yy = np.arange(len(names))
    for ax, g in zip(axes, ("female", "male")):
        a = [fair[best][g]["families"][n]["actual_share"] for n in names]
        p1 = [fair[best][g]["families"][n]["pred_share_top1"] for n in names]
        p4 = [fair[f4][g]["families"][n]["pred_share_top1"] for n in names]
        ax.barh(yy - 0.27, a, 0.27, label="actual share", color="#636363")
        ax.barh(yy, p1, 0.27, label=f"predicted top-1, {best}", color="#3182bd")
        ax.barh(yy + 0.27, p4, 0.27, label=f"predicted top-1, {f4} (with demographics)", color="#e6550d")
        ax.set_title(f"{g} (test n={fair[best][g]['n']:,})")
        ax.set_xlabel("Share of test rows")
        ax.invert_yaxis()
    axes[0].set_yticks(yy, sn, fontsize=7)
    axes[0].legend(fontsize=7)
    fig.suptitle("E6 actual vs predicted major-family share by gender")
    fig.tight_layout()
    fig.savefig(FINDINGS / "e6_gender_shares.png", dpi=120)
    plt.close(fig)


def jsonable(o):
    if isinstance(o, dict):
        return {str(k): jsonable(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [jsonable(v) for v in o]
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return None if np.isnan(o) else float(o)
    if isinstance(o, float) and np.isnan(o):
        return None
    if isinstance(o, np.bool_):
        return bool(o)
    return o


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--quick", action="store_true", help="subsample for a fast smoke run")
    a = ap.parse_args()
    out = jsonable(main(a.seed, a.quick))
    FINDINGS.mkdir(parents=True, exist_ok=True)
    name = "e6_major_prediction_quick.json" if a.quick else "e6_major_prediction.json"
    (FINDINGS / name).write_text(json.dumps(out, indent=2))
    print(json.dumps({k: out[k] for k in ("verdict", "selection", "runtime_s")}, indent=2))
