"""Codebook verification for the OpenPsychometrics RIASEC file (read-only). Usage: python -I script --raw DIR"""
import argparse
from pathlib import Path
import pandas as pd

ap = argparse.ArgumentParser(); ap.add_argument("--raw", required=True)
p = Path(ap.parse_args().raw) / "RIASEC_data12Dec2018" / "data.csv"
df = pd.read_csv(p, sep="\t", dtype=str, keep_default_na=False)
print(df.shape); print(list(df.columns))
items = [f"{t}{i}" for t in "RIASEC" for i in range(1, 9)]
print("item value counts:\n", pd.concat([df[c] for c in items]).value_counts().head(10))
for c in ["education","urban","gender","engnat","hand","religion","orientation","race","voted","married","uniqueNetworkLocation","source"]:
    print(c, df[c].value_counts().head(15).to_dict())
a = pd.to_numeric(df["age"], errors="coerce"); print(a.describe(), (a<13).sum(), (a>90).sum(), (a>1000).sum())
print("familysize", pd.to_numeric(df.familysize,errors='coerce').describe())
for c in ["TIPI1","VCL1","VCL6","VCL9","VCL12"]: print(c, df[c].value_counts().to_dict())
print("country top", df.country.value_counts().head(10).to_dict(), df.country.nunique())
m = df["major"].str.strip()
print("major nonblank:", (m!="").sum(), (m!="").mean())
print(m.str.lower().value_counts().head(40))
print("elapse", [pd.to_numeric(df[c],errors='coerce').describe()[["min","50%","max"]].to_dict() for c in ["introelapse","testelapse","surveyelapse"]])
