"""E7 post-hoc (NOT pre-registered): is the counterfactual-pair instability gender/name bias or general brittleness?

Run: .venv/Scripts/python -I research/feasibility/e7_posthoc_counterfactual.py

Added after seeing that the gated gender + name pairs reached a mean top-10 overlap of only .73. For the best variant
(minilm:d, index = title + alternate titles + description + top-5 tasks), this compares:
  (1) cross-gender / cross-name swaps (the pre-registered pairs; recomputed),
  (2) same-gender swaps ("girl" -> "young woman", "Maria" -> "Laura") = brittleness control,
  (3) each cue version vs the cue-free content sentence (how far any cue moves the list).
It also runs a sign test on the direction of the R and S shift (female minus male) across gender + pronoun pairs.
Output: research/findings/e7_posthoc_counterfactual.json
"""
from __future__ import annotations

import json
import sys
from math import comb
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "research" / "feasibility"))
sys.path.insert(0, str(ROOT / "src"))
import e7_free_text_matching as E  # noqa: E402

# (content without cue, female/first cue version, male/second cue version, same-gender control of the first)
PAIRS = {
    "G01": ("I love building things.", "As a girl, I love building things.", "As a boy, I love building things.",
            "As a young woman, I love building things."),
    "G02": ("I'm interested in engineering and how machines work.",
            "I'm a woman and I'm interested in engineering and how machines work.",
            "I'm a man and I'm interested in engineering and how machines work.",
            "I'm a lady and I'm interested in engineering and how machines work."),
    "G03": ("I really enjoy looking after young children.", "As a girl, I really enjoy looking after young children.",
            "As a boy, I really enjoy looking after young children.",
            "As a young woman, I really enjoy looking after young children."),
    "G04": ("I want to become a nurse and care for patients.",
            "I'm a woman and I want to become a nurse and care for patients.",
            "I'm a man and I want to become a nurse and care for patients.",
            "I'm a lady and I want to become a nurse and care for patients."),
    "G05": ("I love computers and coding.", "As a girl, I love computers and coding.",
            "As a boy, I love computers and coding.", "As a young woman, I love computers and coding."),
    "G06": ("I love fashion and makeup.", "I'm a girl who loves fashion and makeup.",
            "I'm a guy who loves fashion and makeup.", "I'm a young woman who loves fashion and makeup."),
    "G07": ("Me encanta construir cosas.", "Como chica, me encanta construir cosas.",
            "Como chico, me encanta construir cosas.", "Como mujer, me encanta construir cosas."),
    "P01": ("I like fixing cars.", "My name is Maria and I like fixing cars.", "My name is Juan and I like fixing cars.",
            "My name is Laura and I like fixing cars."),
    "P02": ("I enjoy helping my classmates with their homework.",
            "I'm Maria, I enjoy helping my classmates with their homework.",
            "I'm Juan, I enjoy helping my classmates with their homework.",
            "I'm Laura, I enjoy helping my classmates with their homework."),
    "P03": ("I want to work in finance.", "Hi, I'm Emily and I want to work in finance.",
            "Hi, I'm Jamal and I want to work in finance.", "Hi, I'm Sarah and I want to work in finance."),
    "P04": ("Me gusta la biología.", "Soy Lucía y me gusta la biología.", "Soy Carlos y me gusta la biología.",
            "Soy Elena y me gusta la biología."),
    "P05": ("I love drawing comics.", "My name is Aisha and I love drawing comics.",
            "My name is Connor and I love drawing comics.", "My name is Fatima and I love drawing comics."),
}
PRONOUN = {
    "PR01": ("She loves repairing engines and working in a garage.", "He loves repairing engines and working in a garage."),
    "PR02": ("She enjoys caring for elderly people and helping them every day.",
             "He enjoys caring for elderly people and helping them every day."),
    "PR03": ("My daughter wants to be a pilot and loves airplanes.", "My son wants to be a pilot and loves airplanes."),
}


def sign_test_p(k_neg: int, n: int) -> float:
    """Two-sided exact binomial test against p = .5."""
    k = min(k_neg, n - k_neg)
    return min(1.0, 2 * sum(comb(n, i) for i in range(k + 1)) / 2 ** n)


def main() -> dict:
    occ, tasks, text_a, text_d = E.load_catalogue()
    texts = []
    for v in PAIRS.values():
        texts += list(v)
    for v in PRONOUN.values():
        texts += list(v)
    log = {}
    S, _, _ = E.embed_scores("minilm", E.MODELS["minilm"], occ, tasks, text_a, text_d, texts, log)
    top = E.rank_topk(S["d"])
    prof = occ[E.SCALES].to_numpy(float)

    def cprof(i):
        p = prof[top[i]].mean(axis=0)
        return p - p.mean()

    def ov(i, j):
        return len(set(top[i]) & set(top[j])) / E.K

    rows, j = {}, 0
    for pid in PAIRS:
        i0, iF, iM, iC = j, j + 1, j + 2, j + 3
        rows[pid] = {"cross_swap": ov(iF, iM), "same_gender_swap": ov(iF, iC), "first_vs_nocue": ov(iF, i0),
                     "second_vs_nocue": ov(iM, i0), "R_shift_first_minus_second": float(cprof(iF)[0] - cprof(iM)[0]),
                     "S_shift_first_minus_second": float(cprof(iF)[3] - cprof(iM)[3])}
        j += 4
    for pid in PRONOUN:
        iF, iM = j, j + 1
        rows[pid] = {"cross_swap": ov(iF, iM), "R_shift_first_minus_second": float(cprof(iF)[0] - cprof(iM)[0]),
                     "S_shift_first_minus_second": float(cprof(iF)[3] - cprof(iM)[3])}
        j += 2

    def mean_of(key, ids):
        return float(np.mean([rows[p][key] for p in ids]))

    g = [p for p in PAIRS if p.startswith("G")]
    nm = [p for p in PAIRS if p.startswith("P")]
    gendered = g + list(PRONOUN)
    r_neg = sum(rows[p]["R_shift_first_minus_second"] < 0 for p in gendered)
    s_pos = sum(rows[p]["S_shift_first_minus_second"] > 0 for p in gendered)
    return {
        "note": "POST HOC, not pre-registered. Best variant minilm:d only.",
        "pairs": rows,
        "summary": {
            "gender": {k: mean_of(k, g) for k in ("cross_swap", "same_gender_swap", "first_vs_nocue", "second_vs_nocue")},
            "name": {k: mean_of(k, nm) for k in ("cross_swap", "same_gender_swap", "first_vs_nocue", "second_vs_nocue")},
            "gated_12": {k: mean_of(k, g + nm) for k in ("cross_swap", "same_gender_swap", "first_vs_nocue",
                                                         "second_vs_nocue")},
            "direction_gender_and_pronoun_pairs": {
                "n": len(gendered), "female_lower_R": r_neg, "sign_test_p_R": sign_test_p(r_neg, len(gendered)),
                "female_higher_S": s_pos, "sign_test_p_S": sign_test_p(s_pos, len(gendered)),
                "mean_R_shift": mean_of("R_shift_first_minus_second", gendered),
                "mean_S_shift": mean_of("S_shift_first_minus_second", gendered)},
        },
    }


if __name__ == "__main__":
    res = E.rnd(main())
    (E.FINDINGS / "e7_posthoc_counterfactual.json").write_text(json.dumps(res, indent=2), encoding="utf-8")
    print(json.dumps(res["summary"], indent=2))
