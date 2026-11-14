# O*NET loader reference (31.0 CSV release)

The canonical implementation is `src/carrier_helper/data/build_onet_occupations.py`. Reuse it.
The pattern below is for building **other** occupation-level tables (skills, work styles…).

```python
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]          # adjust to repo root
RAW = ROOT / "data" / "raw" / "onet_31_0" / "db_31_0_csv"

RIASEC_IDS = {
    "1.B.1.a": "R", "1.B.1.b": "I", "1.B.1.c": "A",
    "1.B.1.d": "S", "1.B.1.e": "E", "1.B.1.f": "C",
}

def read_onet(stem: str) -> pd.DataFrame:
    """stem = snake_case 31.0 name, e.g. 'career_interest_types', 'job_zones'."""
    return pd.read_csv(RAW / f"{stem}.csv", dtype=str)

def pivot_scale(stem: str, scale_id: str, element_map: dict | None = None) -> pd.DataFrame:
    """Long O*NET rating file -> occupation x element matrix for one scale."""
    df = read_onet(stem)
    df = df[df["Scale ID"] == scale_id].copy()
    if element_map:
        df = df[df["Element ID"].isin(element_map)]
        df["col"] = df["Element ID"].map(element_map)
    else:
        df["col"] = df["Element Name"]
    df["Data Value"] = df["Data Value"].astype(float)
    return df.pivot_table(index="O*NET-SOC Code", columns="col", values="Data Value")

# Example: RIASEC matrix
# riasec = pivot_scale("career_interest_types", "OI", RIASEC_IDS)[list("RIASEC")]
```

Facts confirmed on 2026-11-14 (build checks):
- 923 occupations with OI ratings, no missing R–C, no duplicate codes.
- OI ranges: R, I, A, S, E 1.00–7.00; C 1.61–7.00. Means: R 4.57, I 3.36, A 1.94, S 2.94, E 2.83, C 4.53.
- Job zone counts: 2 → 337, 3 → 208, 4 → 226, 5 → 152.
- Spot checks pass: Biochemists and Biophysicists I = 7; Actors A = 7; Accountants and Auditors C = 7.
