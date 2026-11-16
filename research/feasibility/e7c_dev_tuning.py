"""E7c development tuning: choose the negation penalty alpha on E7's statements ONLY (development data).

Run: uv run python -I research/feasibility/e7c_dev_tuning.py
Rule (written before running): alpha = the smallest value in GRID with E7 negation rows' negated letter < 0 in
>= 5 of 6, and EN-core family Hit@5 >= .92 and occupation Hit@5 >= .83. If none qualifies, the value with the most
negation rows below zero (ties: smaller alpha). Output: research/findings/e7c_dev_tuning.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))  # python -I drops the script dir
import e7c_common as C

E = C.E
GRID = [0.0, 0.25, 0.5, 0.75, 1.0, 1.5]
OUT = C.ROOT / "research" / "findings" / "e7c_dev_tuning.json"


def main():
    st, off = E.load_statements()
    prep = {"st": C.prepare(st.text.tolist())}
    sc = C.Scorer(prep)
    cat, lang, member = st.category.to_numpy(), st.language.to_numpy(), st.pair_member.to_numpy()
    is_first = np.isin(member, list(E.FIRST_MEMBERS)) & np.isin(cat, ["gender_pair", "name_pair", "age_pair"])
    en_core = (lang == "en") & (np.isin(cat, list(E.CORE_CATS)) | is_first)
    neg_rows = np.flatnonzero(cat == "negation")
    res = {}
    for a in GRID:
        S, _, fu = sc.matrix(prep["st"], a)
        per = E.per_statement(E.rank_topk(S), None, st, sc.occ)
        neg = []
        for i in neg_rows:
            li = [E.SCALES.index(L) for L in st.negated_letters.iloc[i]]
            neg.append(float(per[i]["p"][li].mean()))
        res[str(a)] = {
            "neg_letter_scores": neg, "neg_below_zero": int(sum(v < 0 for v in neg)),
            "en_core_fam5": float(np.nanmean([per[i]["hit_fam80_5"] for i in np.flatnonzero(en_core)])),
            "en_core_occ5": float(np.nanmean([per[i]["hit_occ5"] for i in np.flatnonzero(en_core)])),
            "negation_rows_fam5": float(np.nanmean([per[i]["hit_fam80_5"] for i in neg_rows])),
            "followup_rows": [st.id.iloc[i] for i in np.flatnonzero(fu)],
        }
        print(a, res[str(a)]["neg_below_zero"], round(res[str(a)]["en_core_fam5"], 3),
              round(res[str(a)]["en_core_occ5"], 3), round(res[str(a)]["negation_rows_fam5"], 3))
    ok = [a for a in GRID if res[str(a)]["neg_below_zero"] >= 5 and res[str(a)]["en_core_fam5"] >= .92
          and res[str(a)]["en_core_occ5"] >= .83]
    chosen = ok[0] if ok else max(GRID, key=lambda a: (res[str(a)]["neg_below_zero"], -a))
    out = {"grid": GRID, "results": res, "chosen_alpha": chosen, "rule_met": bool(ok),
           "split_audit": [{"id": st.id.iloc[i], "positive": prep["st"][i]["positive"],
                            "rejected": prep["st"][i]["rejected"]} for i in neg_rows],
           "models_log": sc.log}
    OUT.write_text(json.dumps(E.rnd(out), indent=2, ensure_ascii=False), encoding="utf-8")
    print("chosen alpha:", chosen, "rule met:", bool(ok))


if __name__ == "__main__":
    main()
