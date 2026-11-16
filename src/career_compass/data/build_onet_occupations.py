"""Build occupation x RIASEC table (+title, job_zone) from O*NET 31.0 CSV.

Usage: python -I src/career_compass/data/build_onet_occupations.py --raw data/raw/onet_31_0 --out data/processed [--workvalues data/raw/onet_30_2_workvalues]
NOTE: in 31.0 the Interests file is career_interest_types.csv (snake_case CSV names).
"""
import argparse
from pathlib import Path
import pandas as pd

IDS = {"1.B.1.a": "R", "1.B.1.b": "I", "1.B.1.c": "A", "1.B.1.d": "S", "1.B.1.e": "E", "1.B.1.f": "C"}
CODE = "O*NET-SOC Code"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--workvalues")
    a = ap.parse_args()
    raw = Path(a.raw) / "db_31_0_csv"
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)

    cit = pd.read_csv(raw / "career_interest_types.csv", dtype={"Data Value": float})
    print("career_interest_types rows:", len(cit), "scales:", cit["Scale ID"].unique().tolist())
    oi = cit[(cit["Scale ID"] == "OI") & cit["Element ID"].isin(IDS)]
    wide = (oi.assign(dim=oi["Element ID"].map(IDS)).pivot_table(index=CODE, columns="dim", values="Data Value")[list("RIASEC")])
    # IH high-point codes (1-6 = R..C, 0 = none)
    ih = cit[cit["Scale ID"] == "IH"].pivot_table(index=CODE, columns="Element ID", values="Data Value")
    ih.columns = ["ih1", "ih2", "ih3"]
    inv = {i + 1: c for i, c in enumerate("RIASEC")}
    holland = ih.apply(lambda col: col.round().astype(int).map(inv).fillna("")).agg("".join, axis=1).rename("holland_code")
    src = oi.groupby(CODE)["Domain Source"].agg(lambda s: "/".join(sorted(set(s)))).rename("oi_domain_source")

    occ = pd.read_csv(raw / "occupation_data.csv").set_index(CODE)[["Title", "Description"]]
    jz = pd.read_csv(raw / "job_zones.csv", dtype=str).set_index(CODE)[["Job Zone"]]
    print("occupation_data:", len(occ), "| riasec wide:", len(wide), "| job_zones:", len(jz))
    out_df = occ.join(wide, how="inner").join(jz, how="left").join(holland).join(src)
    out_df = out_df.rename(columns={"Title": "title", "Description": "description", "Job Zone": "job_zone"})
    out_df["job_zone"] = pd.to_numeric(out_df["job_zone"]).astype("Int64")
    out_df.insert(0, "onet_soc_code", out_df.index)
    out_df = out_df.reset_index(drop=True)
    cols = ["onet_soc_code", "title", *"RIASEC", "job_zone", "holland_code", "oi_domain_source", "description"]
    out_df = out_df[cols]
    print("unmatched occupation_data codes (no Interests):", len(occ) - len(wide))
    print("interest codes not in occupation_data:", len(set(wide.index) - set(occ.index)))
    print("job_zone missing after join:", int(out_df.job_zone.isna().sum()))
    out_df.to_parquet(out / "onet_occupations.parquet", index=False)

    print("\n== sanity checks ==")
    print("shape", out_df.shape, "| NaN per col:", out_df.isna().sum()[list("RIASEC") + ["job_zone"]].to_dict())
    print(out_df[list("RIASEC")].agg(["min", "max", "mean", "std"]).round(2))
    print("job_zone counts:", out_df.job_zone.value_counts().sort_index().to_dict())
    print("oi_domain_source:", out_df.oi_domain_source.value_counts().to_dict())
    print("holland_code top:", out_df.holland_code.value_counts().head(8).to_dict())
    print("duplicate codes:", int(out_df.onet_soc_code.duplicated().sum()))
    top_ok = (out_df[list("RIASEC")].idxmax(axis=1) == out_df.holland_code.str[0])
    print("argmax(OI) == IH first letter:", round(top_ok.mean(), 3))
    for t, d in [("Biochemists", "I"), ("Actors", "A"), ("Accountants", "C"), ("Registered Nurses", "S"),
                 ("Electricians", "R"), ("Sales Managers", "E")]:
        r = out_df[out_df.title == t]
        if r.empty:
            print(f"  {t}: NOT FOUND"); continue
        r = r.iloc[0]; prof = r[list("RIASEC")].astype(float)
        print(f"  {t} ({r.onet_soc_code}): argmax={prof.idxmax()} expected={d}  {prof.round(2).to_dict()}  jz={r.job_zone}")

    if a.workvalues:
        wv = pd.read_csv(Path(a.workvalues) / "db_30_2_text" / "Work Values.txt", sep="\t")
        ex = wv[wv["Scale ID"] == "EX"].pivot_table(index=CODE, columns="Element Name", values="Data Value")
        ex.to_parquet(out / "onet_work_values_30_2.parquet")
        j = out_df.onet_soc_code.isin(ex.index)
        print("\nWork Values (30.2): occupations", len(ex), "| match to 31.0 occupations:", int(j.sum()), "of", len(out_df),
              "| in WV not in 31.0:", len(set(ex.index) - set(out_df.onet_soc_code)))


if __name__ == "__main__":
    main()
