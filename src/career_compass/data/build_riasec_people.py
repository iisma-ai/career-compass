"""Clean the OpenPsychometrics RIASEC data and score the six scales.

Usage: python -I src/career_compass/data/build_riasec_people.py --raw data/raw/openpsych_riasec_2018 --out data/processed
Filters follow .claude/skills/riasec-scoring; every step logs rows removed.
"""
import argparse
from pathlib import Path

import numpy as np
import pandas as pd

TYPES = list("RIASEC")
ITEMS = {t: [f"{t}{i}" for i in range(1, 9)] for t in TYPES}
ALL_ITEMS = [c for t in TYPES for c in ITEMS[t]]
TIPI = [f"TIPI{i}" for i in range(1, 11)]
VCL = [f"VCL{i}" for i in range(1, 17)]
FAKE = ["VCL6", "VCL9", "VCL12"]  # per codebook.txt
DEMO_CODED = ["education", "urban", "gender", "engnat", "hand", "religion", "orientation",
              "race", "voted", "married"]  # 0 = no answer


def log(step, before, after):
    print(f"{step:<55} {before:>8} -> {after:>8}  removed {before - after:>7}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    raw, out = Path(a.raw), Path(a.out)
    out.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(raw / "RIASEC_data12Dec2018" / "data.csv", sep="\t", dtype=str,
                     keep_default_na=False)
    df = df.drop(columns=[c for c in df.columns if c.startswith("Unnamed")])
    df.insert(0, "row_id", np.arange(len(df)))  # position in the raw file
    num = [c for c in df.columns if c not in ("country", "major", "row_id")]
    df[num] = df[num].apply(pd.to_numeric, errors="coerce")
    n0 = len(df)
    print("raw rows:", n0)

    # items: 0 = missing (codebook range is 1-5; 0 occurs 21,435 times)
    df[ALL_ITEMS] = df[ALL_ITEMS].replace(0, np.nan)
    df["n_missing_items"] = df[ALL_ITEMS].isna().sum(axis=1)
    # coded demographics: 0 = no answer
    df[DEMO_CODED] = df[DEMO_CODED].replace(0, np.nan)
    df[TIPI] = df[TIPI].replace(0, np.nan)

    # independent counts (how many rows each rule would hit on its own)
    rules = {
        "fake VCL word checked": (df[FAKE] == 1).any(axis=1),
        "straight-lining (zero variance, all 48 answered)": (df[ALL_ITEMS].nunique(axis=1) == 1) & (df.n_missing_items == 0),
        "> 10% items missing (>= 5 of 48)": df.n_missing_items > 4.8,
        "age < 13 or > 90": (df.age < 13) | (df.age > 90) | df.age.isna(),
        "shared network (uniqueNetworkLocation == 2)": df.uniqueNetworkLocation == 2,
        "exact duplicate of earlier row": df.drop(columns="row_id").duplicated(keep="first"),
    }
    print("\nIndependent hit counts:")
    for k, v in rules.items():
        print(f"  {k:<55} {int(v.sum()):>8}")

    print("\nSequential filtering:")
    cur = df
    names = list(rules)
    for k in names[:4] + names[5:]:  # network rule applied last, separately
        mask = rules[k].loc[cur.index]
        nxt = cur[~mask]
        log(k, len(cur), len(nxt))
        cur = nxt
    incl_shared = cur.copy()
    nxt = cur[cur.uniqueNetworkLocation == 1]
    log("shared network (uniqueNetworkLocation == 2)", len(cur), len(nxt))
    cur = nxt

    def finish(d):
        d = d.copy()
        for t in TYPES:
            ans = d[ITEMS[t]].notna().sum(axis=1)
            d[t] = d[ITEMS[t]].mean(axis=1).where(ans >= 6)  # need >= 6 of 8
        before = len(d)
        d = d.dropna(subset=TYPES)
        log("scale with < 6 of 8 items answered (any scale)", before, len(d))
        d["minor_13_17"] = d.age < 18
        d["vcl_real_words_checked"] = d[[c for c in VCL if c not in FAKE]].sum(axis=1)
        m = d["major"].str.strip().str.lower().replace("", np.nan)
        d["major_clean"] = m
        d["shared_network"] = d.uniqueNetworkLocation == 2
        d["age"] = d.age.astype(int)
        d["familysize"] = d.familysize.where(d.familysize.between(0, 30))
        return d.reset_index(drop=True)

    final = finish(cur)
    wide = finish(incl_shared)
    print("\nFINAL (shared networks dropped):", len(final), " | variant keeping shared networks:", len(wide))
    print("minors 13-17 flagged:", int(final.minor_13_17.sum()))
    print("major_clean non-null:", int(final.major_clean.notna().sum()))
    print(final[TYPES].describe().round(2))
    final.to_parquet(out / "riasec_people.parquet", index=False)
    wide.to_parquet(out / "riasec_people_incl_shared_network.parquet", index=False)


if __name__ == "__main__":
    main()
