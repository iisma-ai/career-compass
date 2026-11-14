"""E1 — Data audit of the OpenPsychometrics RIASEC dataset.

Run:   python -I research/feasibility/e1_data_audit.py            (full run)
       python -I research/feasibility/e1_data_audit.py --quick    (smoke run, subsample + few bootstraps)
Pre-registration and results: research/findings/e1_data_audit.md
Outputs: research/findings/e1_data_audit.json, e1_*.png, e1_major_families_draft.csv
Reads data/processed/*.parquet and (read-only) data/raw/openpsych_riasec_2018/ for the funnel.
"""
import argparse
import json
import re
import unicodedata
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import factor_analyzer.factor_analyzer as _fa_mod  # noqa: E402
from factor_analyzer import FactorAnalyzer  # noqa: E402

# Compatibility shim: factor_analyzer 0.5.x passes `force_all_finite`, which scikit-learn >= 1.8
# removed (renamed `ensure_all_finite`). Translate the kwarg instead of pinning/installing packages.
_orig_check_array = _fa_mod.check_array


def _check_array_compat(*args, **kw):
    if "force_all_finite" in kw:
        kw["ensure_all_finite"] = kw.pop("force_all_finite")
    return _orig_check_array(*args, **kw)


_fa_mod.check_array = _check_array_compat

ROOT = Path(__file__).resolve().parents[2]
FINDINGS = ROOT / "research" / "findings"
PROC = ROOT / "data" / "processed"
RAW = ROOT / "data" / "raw" / "openpsych_riasec_2018" / "RIASEC_data12Dec2018"

TYPES = list("RIASEC")
ITEMS = {t: [f"{t}{i}" for i in range(1, 9)] for t in TYPES}
ALL_ITEMS = [c for t in TYPES for c in ITEMS[t]]
FAKE = ["VCL6", "VCL9", "VCL12"]
AGE_BANDS = ["13-17", "18-24", "25+"]

# Decoding from data/raw/openpsych_riasec_2018/RIASEC_data12Dec2018/codebook.txt
CODEBOOK = {
    "education": {1: "Less than high school", 2: "High school", 3: "University degree", 4: "Graduate degree"},
    "urban": {1: "Rural", 2: "Suburban", 3: "Urban"},
    "gender": {1: "Male", 2: "Female", 3: "Other"},
    "engnat": {1: "English native", 2: "Not English native"},
    "hand": {1: "Right", 2: "Left", 3: "Both"},
    "religion": {1: "Agnostic", 2: "Atheist", 3: "Buddhist", 4: "Christian (Catholic)", 5: "Christian (Mormon)",
                 6: "Christian (Protestant)", 7: "Christian (Other)", 8: "Hindu", 9: "Jewish", 10: "Muslim",
                 11: "Sikh", 12: "Other"},
    "orientation": {1: "Heterosexual", 2: "Bisexual", 3: "Homosexual", 4: "Asexual", 5: "Other"},
    "race": {1: "Asian", 2: "Arab", 3: "Black", 4: "Indigenous Aus./Native American/White (merged code)",
             5: "Other"},
    "voted": {1: "Yes", 2: "No"},
    "married": {1: "Never married", 2: "Currently married", 3: "Previously married"},
    "source": {0: "Other/undetermined", 1: "Google", 2: "Internal link"},
}
CODEBOOK_FIELDS = (ALL_ITEMS + ["introelapse", "testelapse", "surveyelapse"] + [f"TIPI{i}" for i in range(1, 11)]
                   + [f"VCL{i}" for i in range(1, 17)] + list(CODEBOOK)[:10] + ["age", "familysize", "major",
                   "uniqueNetworkLocation", "country", "source"])
CODED_RANGES = {k: (0, max(v)) for k, v in CODEBOOK.items()}  # 0 = no answer


def age_band(age: pd.Series) -> pd.Series:
    return pd.cut(age, [12, 17, 24, 200], labels=AGE_BANDS)


# ----------------------------------------------------------------------------- statistics helpers
def smd_cont(a: pd.Series, b: pd.Series) -> float:
    a, b = a.dropna(), b.dropna()
    return float((a.mean() - b.mean()) / np.sqrt((a.var() + b.var()) / 2))


def smd_prop(p1: float, p2: float) -> float:
    den = np.sqrt((p1 * (1 - p1) + p2 * (1 - p2)) / 2)
    return float((p1 - p2) / den) if den > 0 else 0.0


def cronbach_alpha(x: np.ndarray) -> float:
    k = x.shape[1]
    cov = np.cov(x, rowvar=False)
    return float(k / (k - 1) * (1 - np.trace(cov) / cov.sum()))


def omega_1f(x: np.ndarray) -> float:
    """McDonald's omega (total) from a 1-factor minres solution on the item correlation matrix."""
    r = np.corrcoef(x, rowvar=False)
    fa = FactorAnalyzer(n_factors=1, rotation=None, method="minres", is_corr_matrix=True)
    fa.fit(r)
    lam = np.abs(fa.loadings_[:, 0])
    s = lam.sum() ** 2
    return float(s / (s + (1 - lam**2).sum()))


def boot_ci(x: np.ndarray, fn, b: int, rng: np.random.Generator) -> list:
    n = len(x)
    vals = [fn(x[rng.integers(0, n, n)]) for _ in range(b)]
    return [float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))]


def prop_ci(mask: np.ndarray, b: int, rng: np.random.Generator) -> list:
    n = len(mask)
    vals = rng.binomial(n, mask.mean(), b) / n  # parametric bootstrap of a proportion
    return [float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))]


# ----------------------------------------------------------------------------- 1. funnel
def recompute_funnel() -> dict:
    df = pd.read_csv(RAW / "data.csv", sep="\t", dtype=str, keep_default_na=False)
    df = df.drop(columns=[c for c in df.columns if c.startswith("Unnamed")])
    header_ok = {f: f in df.columns for f in CODEBOOK_FIELDS}
    num = [c for c in df.columns if c not in ("country", "major")]
    df[num] = df[num].apply(pd.to_numeric, errors="coerce")
    ranges = {}
    for c in ALL_ITEMS:
        ranges.setdefault("items_in_0_5", True)
        ranges["items_in_0_5"] &= bool(df[c].between(0, 5).all())
    ranges["tipi_in_0_7"] = bool(df[[f"TIPI{i}" for i in range(1, 11)]].apply(lambda s: s.between(0, 7)).all().all())
    ranges["vcl_in_0_1"] = bool(df[[f"VCL{i}" for i in range(1, 17)]].isin([0, 1]).all().all())
    for c, (lo, hi) in CODED_RANGES.items():
        ranges[f"{c}_in_{lo}_{hi}"] = bool(df[c].between(lo, hi).all())
    ranges["uniqueNetworkLocation_in_1_2"] = bool(df.uniqueNetworkLocation.isin([1, 2]).all())
    zero_cells = int((df[ALL_ITEMS] == 0).sum().sum())
    it = df[ALL_ITEMS].replace(0, np.nan)
    nmiss = it.isna().sum(axis=1)
    rules = [
        ("any fake VCL word", (df[FAKE] == 1).any(axis=1)),
        ("straight-lining (all 48 answered, same value)", (it.nunique(axis=1) == 1) & (nmiss == 0)),
        (">= 5 of 48 items missing", nmiss >= 5),
        ("age < 13 or > 90", (df.age < 13) | (df.age > 90) | df.age.isna()),
        ("exact duplicate rows", df.duplicated(keep="first")),
    ]
    steps, keep = [{"step": "raw", "rows_after": len(df), "removed": 0}], pd.Series(True, index=df.index)
    for name, m in rules:
        before = int(keep.sum())
        keep &= ~m
        steps.append({"step": name, "rows_after": int(keep.sum()), "removed": before - int(keep.sum())})

    def scale_ok(mask):
        ok = pd.Series(True, index=df.index)
        for t in TYPES:
            ok &= it[ITEMS[t]].notna().sum(axis=1) >= 6
        return mask & ok

    incl = scale_ok(keep.copy())
    before = int(keep.sum())
    keep &= df.uniqueNetworkLocation != 2
    steps.append({"step": "shared network (uniqueNetworkLocation == 2)", "rows_after": int(keep.sum()),
                  "removed": before - int(keep.sum())})
    before = int(keep.sum())
    keep = scale_ok(keep)
    steps.append({"step": "scale with < 6 of 8 answered", "rows_after": int(keep.sum()),
                  "removed": before - int(keep.sum())})
    independent = {name: int(m.sum()) for name, m in rules}
    independent["shared network"] = int((df.uniqueNetworkLocation == 2).sum())
    return {"steps": steps, "independent_hits": independent, "final_main": int(keep.sum()),
            "final_incl_shared": int(incl.sum()), "zero_item_cells_raw": zero_cells,
            "codebook_fields_in_header": all(header_ok.values()),
            "missing_fields": [k for k, v in header_ok.items() if not v],
            "n_raw_columns": int(df.shape[1]), "raw_value_ranges_ok": ranges}


BUILD_LOG = [145828, 116543, 116298, 116042, 115990, 115990, 80096, 80085]  # DATA_SOURCES.md


def main_vs_shared(main: pd.DataFrame, wide: pd.DataFrame) -> dict:
    shared = wide[wide.shared_network]
    out = {"n_main": len(main), "n_shared_only": len(shared), "n_incl_shared": len(wide), "continuous": {}, "categorical": {}}
    for c in TYPES + ["age", "elevation", "differentiation"]:
        out["continuous"][c] = {
            "main_mean": float(main[c].mean()), "main_sd": float(main[c].std()),
            "shared_mean": float(shared[c].mean()), "shared_sd": float(shared[c].std()),
            "incl_mean": float(wide[c].mean()), "incl_sd": float(wide[c].std()),
            "smd_main_vs_shared": smd_cont(main[c], shared[c]),
            "smd_main_vs_incl": smd_cont(main[c], wide[c]),
            "sd_ratio_main_over_shared": float(main[c].std() / shared[c].std()),
        }
    cats = {"female": lambda d: d.gender == 2, "male": lambda d: d.gender == 1, "minor_13_17": lambda d: d.age < 18,
            "US": lambda d: d.country == "US", "English native": lambda d: d.engnat == 1,
            "university degree+": lambda d: d.education >= 3, "major filled": lambda d: d.major_family.notna()}
    for k, f in cats.items():
        p1, p2, p3 = float(f(main).mean()), float(f(shared).mean()), float(f(wide).mean())
        out["categorical"][k] = {"main": p1, "shared": p2, "incl": p3, "smd_main_vs_shared": smd_prop(p1, p2),
                                 "smd_main_vs_incl": smd_prop(p1, p3)}
    top_c = shared.country.value_counts(normalize=True).head(10)
    out["shared_top_countries"] = {k: float(v) for k, v in top_c.items()}
    return out


# ----------------------------------------------------------------------------- 6. major normalisation
JUNK_EXACT = {
    "n/a", "na", "n.a", "n.a.", "no", "none", "nil", "nill", "null", "nothing", "not applicable", "-", "--", "?",
    "idk", "yes", "x", ".", "no major", "none yet", "not yet", "nope", "n", "i don't know", "dont know",
    "don't know", "no university", "did not attend", "didn't attend", "i didn't", "not attended",
    "haven't attended", "have not attended", "not applicable.", "nonw", "non", "nah", "nil.", "0", "a", "-none-",
    "no college", "not in university", "not in college", "never attended", "n/a.", "nan", "no degree",
    "haven't", "have not", "not", "never", "not sure", "unknown", "nothing yet", "still in high school",
    "high school", "highschool", "high school student", "secondary school", "i'm in high school", "student",
    "hs", "none.", "no.", "...", "yet", "not attending", "not applicable to me", "high school diploma",
}
JUNK_PATTERNS = [r"^[^a-z]*$", r"\bhigh ?school\b", r"\bdid ?n['o]?t\b.*\b(attend|go)", r"\bhave ?n['o]?t\b",
                 r"\bnot (yet|applicable|attend|in uni|gone|been)", r"^n/?a\b", r"\bi am (in|a) (high|secondary)",
                 r"\bi'?m (in|a) (high|secondary)", r"\bsecondary school\b", r"^no[ .,!]", r"\bnever (went|attended|been)",
                 r"\bi ?do ?n'?t know", r"^unsure$", r"^not sure"]

# Ordered rules: first match wins. (family, regex). Keep specific patterns before generic ones.
FAMILY_RULES = [
    ("Undecided/General studies", r"undecided|^general$|undeclared|general (studies|education|ed)\b|liberal (arts|studies)|"
                                  r"interdisciplinary|^ge$|^aa$|^as$|^foundation|pre-?u|a-?levels?\b|"
                                  r"matric|^ib$|\bstpm\b|\bspm\b"),
    ("Psychology", r"ps[iy]c|psyh|pysc|psyk|phsyc|phych|physcol|pschy|pshyc|sychol|phycol|pyschol|psycol|"
                   r"^psy$|psychology|psik|pscho|pycho|behavio(u)?ral science|cognitive science|neuroscience|neuro"),
    ("CS/IT", r"comput|software|information tech|information sys|\bit\b|^i\.t|\bcs\b|\bcis\b|\bmis\b|\bict\b|"
              r"programm|data science|cyber|web (design|dev)|informatics|\binformation science|network|"
              r"game (design|dev)|\bbsit\b|\bbscs\b|computing|multimedia|^ece$|electronics and comm|"
              r"information security|comp sci"),
    ("Engineering", r"engin|mechatronic|aerospace|aeronaut|\bmech\b|electrical|electronic|\bece\b|robotic|"
                    r"\beee\b|\bbeng\b|\bb\.?tech\b|mechanic|^civil$|^(land )?surveying$"),
    ("Architecture/Planning", r"architect|urban plan|town plan|interior design|landscape|construction|"
                              r"quantity survey|real estate|built environment|^planning$|^building$"),
    ("Medicine/Dentistry/Pharmacy", r"medic|\bmbbs\b|\bmd\b|pre[- ]?med|dentist|dental|pharma|surgery|"
                                    r"veterin|veter|\bvet\b|optometr|doctor|pediatric|med[e]?cine|medtech"),
    ("Social work/Counselling", r"social work|counsel|\bmsw\b|\bbsw\b|human services|family studies|"
                                r"child development|human development|youth work|social care|social services|"
                                r"human (and social )?service|community"),
    ("Health/Nursing/Allied health", r"nurs|\bbsn\b|\brn\b|health|physio|physical therap|occupational therap|"
                                     r"speech|kinesiol|exercise|sport|nutrition|dietetic|radiograph|radiolog|"
                                     r"midwif|paramedic|\bemt\b|respiratory|athletic train|\bpta\b|public health|"
                                     r"\bmph\b|chiropract|audiolog|massage|fitness|biomedical science|"
                                     r"medical lab|lab science|clinical|dental hyg|disorders|rehab|recreation|therap|"
                                     r"gerontolog|epidemiolog|kinesol"),
    ("Education", r"educat|eduction|teach|pedagog|\bb\.?ed\b|\bm\.ed\b|tesol|tefl|elementary|special ed|"
                  r"montessori|instruction|early childhood"),
    ("Law/Criminal justice", r"\blaws?\b|lawyer|homeland security|legal|\bllb\b|\bjd\b|juris|crimin|justice|forensic|police|paralegal|"
                             r"security stud"),
    ("Accounting/Finance", r"account|accou|financ|bank|actuar|\bcpa\b|audit|tax|insurance|\bacca\b"),
    ("Economics", r"econom|^econ\b"),
    ("Trades/Vocational", r"cosmetolog|weld|automotive|carpent|plumb|electrician|barber|hairdress|beauty|"
                          r"aviation|pilot"),
    ("Business/Management/Marketing", r"business|\bbu[is]{1,3}n[ei]s|leadership|human resour|manag|market|\bmba\b|\bbba\b|\bhr\b|\bhrm\b|human resource|"
                                      r"commerce|entrepreneur|admin|logistic|supply chain|advertis|retail|"
                                      r"hospitality|hotel|tourism|culinary|event|\bbsba\b|\bbcom\b|"
                                      r"public relations|\bpr\b|international business|sales|fashion merch|"
                                      r"office|secretar|aviation|organizational"),
    ("Communication/Media/Journalism", r"communicat|comunica|journalis|\bmedia\b|mass comm|broadcast|film|cinema|"
                                       r"radio|television|\btv\b|public relations"),
    ("Arts/Design/Performing arts", r"\bart\b|\barts\b|fine art|design|music|theat|drama|danc|perform|paint|"
                                    r"photograph|animat|illustrat|graphic|fashion|studio|sculpt|acting|"
                                    r"creative writing|visual|ceramic|art history|\bbfa\b|\bmfa\b|vocal|"
                                    r"piano|guitar|composition|choral|opera|textile"),
    ("Languages/Literature", r"english|literat|litterat|interpret|\basl\b|sign language|linguist|language|spanish|french|german|japanese|chinese|"
                             r"italian|russian|arabic|korean|translat|writing|\btesl\b|comparative lit|"
                             r"classics|latin|greek|philolog|mandarin|portuguese"),
    ("Humanities (history/philosophy/religion)", r"histor|philosoph|theolog|religio|divinity|bible|biblical|"
                                                 r"ministry|humanities|archaeolog|islamic|jewish stud|"
                                                 r"museum|librar|information stud"),
    ("Social sciences", r"sociolog|anthropolog|politic|government|international (relations|studies|affairs)|"
                        r"\bir\b|geograph|social science|gender stud|women'?s stud|ethnic stud|"
                        r"african american|american stud|public (policy|admin)|development stud|area stud|"
                        r"global stud|asian stud|cultur|demograph|urban stud|social stud|european stud|"
                        r"international (development|relation)|global affairs|^development$|social policy|socialog"),
    ("Math/Statistics", r"\bmath|statist|applied math|mathemat"),
    ("Biology/Life sciences", r"biolog|\bbio\b|biochem|microbio|zoolog|botan|genetic|ecolog|marine|"
                              r"life science|molecular|animal science|biotech|physiolog|anatomy|"
                              r"immunolog|wildlife|entomolog|neurobio|cell bio|biomed"),
    ("Physical/Earth/Environmental sciences", r"chemi|physic|geolog|earth science|environment|astronom|"
                                              r"astrophys|meteorolog|atmospher|ocean|material|"
                                              r"natural science|\bscience\b|sciences|agricult|forestry|"
                                              r"horticult|food science|conservation|sustainab|agronom|geoscien|toxicolog"),
    ("Engineering", r"technolog"),  # fallback for e.g. "engineering technology"-like values
]
FAMILY_RE = [(f, re.compile(p)) for f, p in FAMILY_RULES]


def normalise_major(s: str):
    if s is None or (isinstance(s, float) and np.isnan(s)):
        return None
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    s = re.sub(r"\s+", " ", s.strip().lower()).strip(" .,;:!\"'")
    return s or None


def is_junk(s: str) -> bool:
    return s in JUNK_EXACT or any(re.search(p, s) for p in JUNK_PATTERNS)


def map_family(s: str) -> str:
    for fam, rx in FAMILY_RE:
        if rx.search(s):
            return fam
    return "Unmapped"


def major_analysis(main: pd.DataFrame) -> tuple:
    raw = main.major.fillna("").astype(str)
    norm = raw.map(lambda v: normalise_major(v) if v.strip() else None)
    junk = norm.map(lambda v: isinstance(v, str) and is_junk(v))
    valid = norm.where(~junk)
    fam = valid.map(lambda v: map_family(v) if isinstance(v, str) else None)
    main = main.assign(major_norm=valid, major_family=fam)
    filled = valid.notna()
    vc = valid.value_counts()
    tab = pd.DataFrame({"value": vc.index, "count": vc.values})
    tab["family"] = tab.value.map(map_family)
    tab["cum_share_of_filled"] = tab["count"].cumsum() / tab["count"].sum()
    mapped = fam.notna() & (fam != "Unmapped")
    fam_counts = fam[filled].value_counts()
    by_age = {b: {"n": int((main.age_band == b).sum()),
                  "raw_nonblank_pct": float(100 * (raw[main.age_band == b].str.strip() != "").mean()),
                  "valid_filled_pct": float(100 * filled[main.age_band == b].mean())} for b in AGE_BANDS}
    by_edu = {CODEBOOK["education"][k]: float(100 * filled[main.education == k].mean()) for k in [1, 2, 3, 4]}
    by_gender = {CODEBOOK["gender"][k]: float(100 * filled[main.gender == k].mean()) for k in [1, 2, 3]}
    # top family share by gender (fairness: base rates per family differ by gender)
    fam_gender = (pd.crosstab(fam[mapped], main.gender[mapped].map(CODEBOOK["gender"]), normalize="columns") * 100)
    res = {
        "n_unique_raw_values": int(raw[raw.str.strip() != ""].nunique()),
        "n_unique_normalised_valid": int(valid.nunique()),
        "raw_nonblank_rows": int((raw.str.strip() != "").sum()),
        "junk_rows": int(junk.sum()),
        "valid_filled_rows": int(filled.sum()),
        "valid_filled_pct": float(100 * filled.mean()),
        "fill_by_age_band": by_age, "fill_by_education_pct": by_edu, "fill_by_gender_pct": by_gender,
        "top50": [{"value": v, "count": int(c), "family": map_family(v)} for v, c in vc.head(50).items()],
        "top_junk_values": {k: int(v) for k, v in norm[junk].value_counts().head(20).items()},
        "coverage_mapped_pct_of_filled": float(100 * mapped.sum() / filled.sum()),
        "n_families": int(len([f for f in fam_counts.index if f != "Unmapped"])),
        "family_counts": {k: int(v) for k, v in fam_counts.items()},
        "n_values_for_80pct_of_filled": int((tab.cum_share_of_filled < 0.80).sum() + 1),
        "family_share_by_gender_pct": {g: {f: float(v) for f, v in fam_gender[g].items()} for g in fam_gender.columns},
        "top_unmapped": {k: int(v) for k, v in valid[fam == "Unmapped"].value_counts().head(30).items()},
    }
    return main, tab, res


# ----------------------------------------------------------------------------- main
def main(seed: int, quick: bool) -> dict:
    rng = np.random.default_rng(seed)
    b_alpha, b_omega, b_prop = (50, 20, 200) if quick else (1000, 500, 2000)
    res = {"seed": seed, "quick": quick, "bootstrap": {"alpha": b_alpha, "omega": b_omega, "proportions": b_prop}}

    main_df = pd.read_parquet(PROC / "riasec_people.parquet")
    wide = pd.read_parquet(PROC / "riasec_people_incl_shared_network.parquet")
    onet = pd.read_parquet(PROC / "onet_occupations.parquet")
    for d in (main_df, wide):
        d["age_band"] = age_band(d.age)
        d["elevation"] = d[TYPES].mean(axis=1)
        d["differentiation"] = d[TYPES].max(axis=1) - d[TYPES].min(axis=1)
    if quick:
        main_df = main_df.sample(5000, random_state=seed).reset_index(drop=True)
        wide = wide.sample(8000, random_state=seed).reset_index(drop=True)
    n = len(main_df)
    print(f"main n={n}, incl-shared n={len(wide)}, onet n={len(onet)}")

    # 1. funnel ---------------------------------------------------------------
    funnel = recompute_funnel()
    funnel["build_log_rows_after"] = BUILD_LOG
    funnel["matches_build_log"] = [s["rows_after"] for s in funnel["steps"]] == BUILD_LOG
    funnel["processed_main_rows"] = int(pd.read_parquet(PROC / "riasec_people.parquet", columns=["row_id"]).shape[0])
    funnel["processed_incl_rows"] = int(wide.shape[0]) if not quick else None
    res["funnel"] = funnel
    print("funnel matches build log:", funnel["matches_build_log"])

    # 6 first (needed for major-filled comparison in 1) ------------------------
    main_df, major_tab, major_res = major_analysis(main_df)
    wide, _, _ = major_analysis(wide)
    res["major"] = major_res
    res["main_vs_shared"] = main_vs_shared(main_df, wide)

    # 2. item stats -----------------------------------------------------------
    items = {}
    for t in TYPES:
        sub = main_df[ITEMS[t]]
        for c in ITEMS[t]:
            rest = sub.drop(columns=c).mean(axis=1) * 7
            items[c] = {"scale": t, "mean": float(sub[c].mean()), "sd": float(sub[c].std()),
                        "missing_pct": float(100 * sub[c].isna().mean()),
                        "item_rest_r": float(sub[c].corr(rest)),
                        "floor_pct_1": float(100 * (sub[c] == 1).mean() / sub[c].notna().mean()),
                        "ceiling_pct_5": float(100 * (sub[c] == 5).mean() / sub[c].notna().mean())}
    res["items"] = items
    res["max_item_missing_pct"] = max(v["missing_pct"] for v in items.values())

    # 3. reliability ----------------------------------------------------------
    rel = {}
    for t in TYPES:
        x = main_df[ITEMS[t]].dropna().to_numpy()
        perm = np.column_stack([rng.permutation(x[:, j]) for j in range(x.shape[1])])
        rel[t] = {"n_complete": int(len(x)), "alpha": cronbach_alpha(x), "alpha_ci95": boot_ci(x, cronbach_alpha, b_alpha, rng),
                  "omega": omega_1f(x), "omega_ci95": boot_ci(x, omega_1f, b_omega, rng),
                  "alpha_permuted_baseline": cronbach_alpha(perm), "omega_permuted_baseline": omega_1f(perm)}
        print(f"{t}: alpha={rel[t]['alpha']:.3f} omega={rel[t]['omega']:.3f}")
    res["reliability"] = rel
    # robustness: incl shared; subgroups
    res["reliability_incl_shared"] = {t: cronbach_alpha(wide[ITEMS[t]].dropna().to_numpy()) for t in TYPES}
    sub_rel = {}
    for g in [1, 2]:
        for b in AGE_BANDS:
            m = (main_df.gender == g) & (main_df.age_band == b)
            sub_rel[f"{CODEBOOK['gender'][g]} {b}"] = {
                "n": int(m.sum()), **{t: cronbach_alpha(main_df.loc[m, ITEMS[t]].dropna().to_numpy()) for t in TYPES}}
    for k in [1, 2]:
        m = main_df.engnat == k
        sub_rel[CODEBOOK["engnat"][k]] = {"n": int(m.sum()),
                                          **{t: cronbach_alpha(main_df.loc[m, ITEMS[t]].dropna().to_numpy()) for t in TYPES}}
    res["reliability_by_subgroup_alpha"] = sub_rel

    # 4. demographics ---------------------------------------------------------
    demo = {"n": n, "age": {k: float(v) for k, v in main_df.age.describe(percentiles=[.1, .25, .5, .75, .9]).items()},
            "age_band_counts": {b: int((main_df.age_band == b).sum()) for b in AGE_BANDS}}
    for c, cb in CODEBOOK.items():
        vc = main_df[c].map(cb).fillna("No answer").value_counts()
        demo[c] = {k: {"n": int(v), "pct": float(100 * v / n)} for k, v in vc.items()}
    vc = main_df.country.value_counts()
    demo["country_top15"] = {k: {"n": int(v), "pct": float(100 * v / n)} for k, v in vc.head(15).items()}
    demo["n_countries"] = int(main_df.country.nunique())
    grid = pd.crosstab(main_df.gender.map(CODEBOOK["gender"]).fillna("No answer"), main_df.age_band)
    demo["gender_x_ageband"] = {g: {b: int(grid.loc[g, b]) for b in AGE_BANDS} for g in grid.index}
    cells = [grid.loc[g, b] for g in ["Male", "Female"] for b in AGE_BANDS]
    demo["min_cell_male_female_x_age"] = int(min(cells))
    # extra intersections relevant for fairness
    demo["engnat_x_gender"] = {f"{CODEBOOK['engnat'][e]} {CODEBOOK['gender'][g]}": int(((main_df.engnat == e) & (main_df.gender == g)).sum())
                               for e in [1, 2] for g in [1, 2]}
    res["demographics"] = demo

    # subgroup scale means and gender effect sizes (fairness input) ----------
    means = main_df.groupby([main_df.gender.map(CODEBOOK["gender"]), "age_band"], observed=True)[TYPES].mean()
    res["scale_means_by_gender_age"] = {f"{g} {b}": {t: float(means.loc[(g, b), t]) for t in TYPES}
                                       for g, b in means.index if g in ("Male", "Female")}
    male, fem = main_df[main_df.gender == 1], main_df[main_df.gender == 2]
    res["gender_d_male_minus_female"] = {t: smd_cont(male[t], fem[t]) for t in TYPES}
    res["gender_d_male_minus_female_by_age"] = {
        b: {t: smd_cont(male.loc[male.age_band == b, t], fem.loc[fem.age_band == b, t]) for t in TYPES} for b in AGE_BANDS}
    res["literature_gender_d_su2009"] = {"R": 0.84, "I": 0.26, "A": -0.35, "S": -0.68, "C": -0.33,
                                         "source": "Su, Rounds & Armstrong 2009 via research/notes/06 (E not listed there)"}
    res["scale_descriptives"] = {t: {"mean": float(main_df[t].mean()), "sd": float(main_df[t].std())} for t in TYPES}
    res["scale_correlations"] = main_df[TYPES].corr().round(3).to_dict()

    # 5. profile shape --------------------------------------------------------
    dif, elev = main_df.differentiation.to_numpy(), main_df.elevation.to_numpy()
    shape = {"differentiation": {k: float(v) for k, v in main_df.differentiation.describe(percentiles=[.1, .25, .5, .75, .9]).items()},
             "elevation": {k: float(v) for k, v in main_df.elevation.describe(percentiles=[.1, .25, .5, .75, .9]).items()},
             "corr_differentiation_elevation": float(np.corrcoef(dif, elev)[0, 1])}
    for thr in [0.5, 1.0, 1.5]:
        m = dif < thr
        shape[f"flat_lt_{thr}_pct"] = float(100 * m.mean())
        shape[f"flat_lt_{thr}_ci95"] = [100 * v for v in prop_ci(m, b_prop, rng)]
    lowflat = (dif < 1.0) & (elev < 2.0)
    shape["flat_and_low_elevation_lt2_pct"] = float(100 * lowflat.mean())
    shape["flat_and_low_elevation_lt2_ci95"] = [100 * v for v in prop_ci(lowflat, b_prop, rng)]
    shape["flat_and_high_elevation_ge3_pct"] = float(100 * ((dif < 1.0) & (elev >= 3.0)).mean())
    shape["elevation_lt2_pct"] = float(100 * (elev < 2.0).mean())
    top = main_df[TYPES].to_numpy()
    srt = np.sort(top, axis=1)
    shape["tie_top1_pct"] = float(100 * (srt[:, -1] == srt[:, -2]).mean())
    shape["tie_at_3rd_letter_pct"] = float(100 * (srt[:, -3] == srt[:, -4]).mean())
    flat_by = {}
    for g in [1, 2]:
        for b in AGE_BANDS:
            m = ((main_df.gender == g) & (main_df.age_band == b)).to_numpy()
            flat_by[f"{CODEBOOK['gender'][g]} {b}"] = {"n": int(m.sum()), "flat_lt_1_pct": float(100 * (dif[m] < 1).mean()),
                                                     "median_differentiation": float(np.median(dif[m])),
                                                     "median_elevation": float(np.median(elev[m]))}
    flat_by["major filled"] = {"n": int(main_df.major_family.notna().sum()),
                               "flat_lt_1_pct": float(100 * (dif[main_df.major_family.notna().to_numpy()] < 1).mean())}
    flat_by["major not filled"] = {"n": int(main_df.major_family.isna().sum()),
                                   "flat_lt_1_pct": float(100 * (dif[main_df.major_family.isna().to_numpy()] < 1).mean())}
    shape["by_subgroup"] = flat_by
    shape["flat_lt_1_incl_shared_pct"] = float(100 * (wide.differentiation < 1).mean())
    res["profile_shape"] = shape

    # 7. O*NET comparison -----------------------------------------------------
    P = main_df[TYPES].to_numpy()
    O = onet[TYPES].to_numpy()
    pc = (P - P.mean(1, keepdims=True)).mean(0)
    oc = (O - O.mean(1, keepdims=True)).mean(0)
    p_top = pd.Series(np.array(TYPES)[P.argmax(1)]).value_counts(normalize=True) * 100
    o_top = pd.Series(np.array(TYPES)[O.argmax(1)]).value_counts(normalize=True) * 100
    res["onet_comparison"] = {
        "person_mean_raw_1to5": dict(zip(TYPES, P.mean(0).round(3).tolist())),
        "onet_mean_raw_1to7": dict(zip(TYPES, O.mean(0).round(3).tolist())),
        "person_mean_rescaled_to_1to7": dict(zip(TYPES, (1 + (P.mean(0) - 1) * 1.5).round(3).tolist())),
        "person_mean_centred": dict(zip(TYPES, pc.round(3).tolist())),
        "onet_mean_centred": dict(zip(TYPES, oc.round(3).tolist())),
        "pearson_mean_centred_profiles": float(np.corrcoef(pc, oc)[0, 1]),
        "person_top_type_pct": {t: float(p_top.get(t, 0)) for t in TYPES},
        "onet_top_type_pct": {t: float(o_top.get(t, 0)) for t in TYPES},
        "person_elevation_mean": float(P.mean()), "onet_elevation_mean": float(O.mean()),
        "person_differentiation_median": float(np.median(P.max(1) - P.min(1))),
        "onet_differentiation_median": float(np.median(O.max(1) - O.min(1))),
        "note": "Different response scales (people 1-5 Likert 'enjoy'; O*NET OI 1-7 analyst ratings); compare shapes only.",
    }

    # verdict vs pre-registered bar ------------------------------------------
    full_n = funnel["processed_main_rows"]
    alphas = [rel[t]["alpha"] for t in TYPES]
    crit = {"i_rows_ge_50k": full_n >= 50000,
            "ii_items_missing_le_2pct": res["max_item_missing_pct"] <= 2.0,
            "iii_alpha_ge_.80_all": min(alphas) >= 0.80,
            "iv_cells_ge_1000": demo["min_cell_male_female_x_age"] >= 1000}
    if all(crit.values()):
        verdict = "proven"
    elif not crit["i_rows_ge_50k"] or not crit["ii_items_missing_le_2pct"] or min(alphas) < 0.70:
        verdict = "not viable"
    else:
        n_alpha_fail = sum(a < 0.80 for a in alphas)
        n_cell_fail = sum(c < 1000 for c in cells)
        narrow = (n_alpha_fail <= 1 and min(alphas) >= 0.70 and crit["iv_cells_ge_1000"]) or \
                 (crit["iii_alpha_ge_.80_all"] and n_cell_fail <= 2 and min(cells) >= 500)
        verdict = "promising" if narrow else "not viable"
    res["success_bar"] = {"criteria": crit, "verdict": verdict,
                          "secondary": {"funnel_reproduces_build_log": funnel["matches_build_log"],
                                        "codebook_fields_in_header": funnel["codebook_fields_in_header"],
                                        "major_coverage_ge_80pct": major_res["coverage_mapped_pct_of_filled"] >= 80}}
    if quick:
        res["success_bar"]["note"] = "quick mode: reliability/cells computed on a 5,000-row subsample; not for reporting"

    # outputs -----------------------------------------------------------------
    FINDINGS.mkdir(parents=True, exist_ok=True)
    suffix = "_quick" if quick else ""
    keep = major_tab[(major_tab["count"] >= 3) | (major_tab.cum_share_of_filled <= 0.80)]
    keep[["value", "family", "count", "cum_share_of_filled"]].rename(columns={"value": "raw_normalised_value"}).to_csv(
        FINDINGS / f"e1_major_families_draft{suffix}.csv", index=False)
    res["major"]["csv_rows_written"] = int(len(keep))
    res["major"]["csv_cum_share_covered"] = float(keep["count"].sum() / major_tab["count"].sum())
    make_charts(main_df, res, n, suffix)
    return res


# ----------------------------------------------------------------------------- charts
def make_charts(d: pd.DataFrame, res: dict, n: int, suffix: str) -> None:
    # item distributions: stacked response proportions
    fig, ax = plt.subplots(figsize=(14, 5))
    props = np.array([[(d[c] == v).sum() / d[c].notna().sum() for v in range(1, 6)] for c in ALL_ITEMS])
    bottom = np.zeros(len(ALL_ITEMS))
    colors = plt.cm.RdYlGn(np.linspace(0.1, 0.9, 5))
    for v in range(5):
        ax.bar(ALL_ITEMS, props[:, v], bottom=bottom, color=colors[v], label=str(v + 1), width=0.85)
        bottom += props[:, v]
    ax.set_ylabel("Share of answers")
    ax.set_xlabel("Item (8 per scale, R-I-A-S-E-C)")
    ax.set_title(f"E1 response distribution per item (1=Dislike ... 5=Enjoy), n={n:,}")
    ax.legend(title="Answer", ncol=5, loc="upper center", bbox_to_anchor=(0.5, -0.18))
    ax.tick_params(axis="x", rotation=90, labelsize=7)
    fig.tight_layout()
    fig.savefig(FINDINGS / f"e1_item_distributions{suffix}.png", dpi=120)
    plt.close(fig)

    # reliability
    rel = res["reliability"]
    fig, ax = plt.subplots(figsize=(7, 4))
    x = np.arange(6)
    for off, key, lab in [(-0.15, "alpha", "Cronbach alpha"), (0.15, "omega", "McDonald omega")]:
        v = np.array([rel[t][key] for t in TYPES])
        ci = np.array([rel[t][f"{key}_ci95"] for t in TYPES])
        ax.errorbar(x + off, v, yerr=[v - ci[:, 0], ci[:, 1] - v], fmt="o", capsize=3, label=lab)
    ax.axhline(0.80, ls="--", c="grey", lw=1, label="pre-registered bar .80")
    ax.set_xticks(x, TYPES)
    ax.set_ylim(0.75, 1.0)
    ax.set_xlabel("RIASEC scale")
    ax.set_ylabel("Reliability (95% bootstrap CI)")
    ax.set_title(f"E1 scale reliability, n={n:,}")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(FINDINGS / f"e1_reliability{suffix}.png", dpi=120)
    plt.close(fig)

    # demographics
    fig, axs = plt.subplots(2, 2, figsize=(12, 8))
    axs[0, 0].hist(d.age, bins=np.arange(13, 81), color="steelblue")
    axs[0, 0].set_xlabel("Age (years)")
    axs[0, 0].set_ylabel("Respondents")
    axs[0, 0].set_title("Age")
    g = d.gender.map(CODEBOOK["gender"]).fillna("No answer").value_counts()
    axs[0, 1].bar(g.index, g.values, color="slateblue")
    axs[0, 1].set_ylabel("Respondents")
    axs[0, 1].set_title("Gender")
    c = d.country.value_counts().head(15)
    axs[1, 0].barh(c.index[::-1], c.values[::-1], color="seagreen")
    axs[1, 0].set_xlabel("Respondents")
    axs[1, 0].set_title("Country (top 15, network location)")
    e = d.education.map(CODEBOOK["education"]).fillna("No answer").value_counts()
    axs[1, 1].barh(e.index[::-1], e.values[::-1], color="darkorange")
    axs[1, 1].set_xlabel("Respondents")
    axs[1, 1].set_title("Education completed")
    fig.suptitle(f"E1 demographics of the cleaned sample, n={n:,}")
    fig.tight_layout()
    fig.savefig(FINDINGS / f"e1_demographics{suffix}.png", dpi=120)
    plt.close(fig)

    # differentiation / elevation
    fig, axs = plt.subplots(1, 2, figsize=(12, 4))
    axs[0].hist(d.differentiation, bins=np.arange(0, 4.01, 0.125), color="indianred")
    axs[0].axvline(1.0, ls="--", c="k", lw=1)
    axs[0].set_xlabel("Differentiation = max - min scale mean (1-5 scale)")
    axs[0].set_ylabel("Respondents")
    axs[0].set_title(f"Differentiation ({res['profile_shape']['flat_lt_1.0_pct']:.1f}% < 1.0)")
    axs[1].hist(d.elevation, bins=np.arange(1, 5.01, 0.1), color="gray")
    axs[1].set_xlabel("Elevation = mean of the 6 scale means")
    axs[1].set_ylabel("Respondents")
    axs[1].set_title("Elevation")
    fig.suptitle(f"E1 profile shape, n={n:,}")
    fig.tight_layout()
    fig.savefig(FINDINGS / f"e1_differentiation{suffix}.png", dpi=120)
    plt.close(fig)

    # main vs shared SMD
    ms = res["main_vs_shared"]
    labels = list(ms["continuous"]) + list(ms["categorical"])
    vals = [ms["continuous"][k]["smd_main_vs_shared"] for k in ms["continuous"]] + \
           [ms["categorical"][k]["smd_main_vs_shared"] for k in ms["categorical"]]
    fig, ax = plt.subplots(figsize=(7, 5))
    ax.barh(labels[::-1], vals[::-1], color=["firebrick" if abs(v) >= 0.1 else "steelblue" for v in vals[::-1]])
    ax.axvline(0.1, ls="--", c="grey", lw=1)
    ax.axvline(-0.1, ls="--", c="grey", lw=1)
    ax.set_xlabel("Standardised difference (main - shared-network rows)")
    ax.set_title(f"E1 main (n={ms['n_main']:,}) vs shared-network rows (n={ms['n_shared_only']:,})")
    fig.tight_layout()
    fig.savefig(FINDINGS / f"e1_main_vs_shared_smd{suffix}.png", dpi=120)
    plt.close(fig)

    # major families
    fc = pd.Series(res["major"]["family_counts"]).sort_values()
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.barh(fc.index, fc.values, color="teal")
    ax.set_xlabel("Respondents with a valid major")
    ax.set_title(f"E1 draft major families (coverage {res['major']['coverage_mapped_pct_of_filled']:.1f}%), "
                 f"n={res['major']['valid_filled_rows']:,}")
    fig.tight_layout()
    fig.savefig(FINDINGS / f"e1_major_families{suffix}.png", dpi=120)
    plt.close(fig)

    # person vs O*NET centred profile
    oc = res["onet_comparison"]
    fig, ax = plt.subplots(figsize=(7, 4))
    x = np.arange(6)
    ax.bar(x - 0.2, [oc["person_mean_centred"][t] for t in TYPES], 0.4, label=f"People (1-5), n={n:,}")
    ax.bar(x + 0.2, [oc["onet_mean_centred"][t] for t in TYPES], 0.4, label="O*NET occupations (1-7), n=923")
    ax.axhline(0, c="k", lw=0.8)
    ax.set_xticks(x, TYPES)
    ax.set_xlabel("RIASEC scale")
    ax.set_ylabel("Mean of person-centred score")
    ax.set_title("E1 average centred profile: people vs O*NET occupations")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(FINDINGS / f"e1_profile_vs_onet{suffix}.png", dpi=120)
    plt.close(fig)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--quick", action="store_true", help="subsample for a fast smoke run")
    a = ap.parse_args()
    out = main(a.seed, a.quick)
    FINDINGS.mkdir(parents=True, exist_ok=True)
    name = "e1_data_audit_quick.json" if a.quick else "e1_data_audit.json"
    (FINDINGS / name).write_text(json.dumps(out, indent=2, default=str))
    print(json.dumps({k: out[k] for k in ("success_bar", "reliability")}, indent=2, default=str))
