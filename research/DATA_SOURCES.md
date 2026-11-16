# Data sources

Retrieved 2026-11-14. Raw files live in `data/raw/<slug>/` (git-ignored, untrusted) with a `SOURCE.md`
(URL, date, SHA-256, license). Derived tables are in `data/processed/` (git-ignored).
All scripts run with `python -I` from the repo root using the uv environment (`uv run python -I ...`; pandas, pyarrow, numpy).

## 1. openpsych_riasec_2018 - OpenPsychometrics RIASEC test

- **Role:** person-level RIASEC answers (48 items), the training/simulation population for E2, E4, E5 and E6.
- **URL:** https://openpsychometrics.org/_rawdata/RIASEC_data12Dec2018.zip (page: https://openpsychometrics.org/_rawdata/)
- **Version:** 12 Dec 2018 dump (data collected 2015-2018). SHA-256 `d3d76b9b...ead3c08` (full hash in SOURCE.md).
- **License:** none stated. The page says the data is anonymous, published "for general public edification", and that
  respondents agreed their answers could be used for research. Treat as research use; cite openpsychometrics.org;
  clarify terms before redistributing any derived person-level file. Not CC-licensed.
- **Size:** zip 6.1 MB; `data.csv` 29 MB; 145,828 rows x 93 columns (file is TAB-separated and has an empty trailing column).
- **Key fields (verified against codebook.txt and the header):**
  - Items `R1..R8, I1..I8, A1..A8, S1..S8, E1..E8, C1..C8`: 1=Dislike, 3=Neutral, 5=Enjoy. Value `0` also occurs
    (21,435 of 7.0M cells) and is undocumented; treated as missing.
  - Timing (s): `introelapse`, `testelapse`, `surveyelapse` (max values are in the millions, so outliers exist).
  - `TIPI1..TIPI10` (1-7; `0` = missing; TIPI2/4/6/8/10 are reverse-keyed by the TIPI definition).
  - `VCL1..VCL16` (1 = checked). Fake words: **VCL6 (cuivocal), VCL9 (florted), VCL12 (verdid)**.
  - Demographics: `education` (1-4), `urban` (1-3), `gender` (1 male, 2 female, 3 other), `engnat`, `age`, `hand`,
    `religion` (1-12), `orientation` (1-5), `race` (1-5; coding error merges 3 groups into 4), `voted`, `married`,
    `familysize`. For coded fields `0` = no answer.
  - `uniqueNetworkLocation` (1 = unique, 2 = shared network, e.g. schools or retakes), `country` (ISO-2, 189 values, 'NONE' present), `source`.
  - **`major` exists**: free text, "If you attended a university, what was your major". 93,626 of 145,828 non-blank (64.2%).
    The other 52,202 are empty strings. After the cleaning below, 55,715 of 80,085 retained rows have a non-empty major (69.6%).
    Contains junk such as "n/a" (558) and "no" (496).
    Most frequent (lower-cased, raw rows): psychology 13,878; business 3,848; english 3,240; nursing 2,396; biology 2,122;
    education 1,954; engineering 1,504; accounting 1,292; computer science 1,240; law 1,111; civil engineering 1,108; economics 1,092.
    Needs normalisation/grouping before E6 (e.g. "business", "business administration", "business management").
- **Join keys:** none to O*NET directly; person profiles are matched to occupations by RIASEC shape (see riasec-scoring). `major` is free text.
- **Quality issues:**
  - Self-selected website visitors; skews young (median age 21), female (65%), US 55%, then MY, CA, SG, GB, AU, PH. Not representative.
  - 20.1% (29,285) ticked at least one fake word; 31% (45,101) rows are on shared network locations (retakes or schools).
  - Age has 101 values > 90 including 25 absurd values (up to 2,147,483,647); no values < 13 (dropped by publisher).
  - Large elapse-time outliers; `familysize` also has absurd values (set to NaN outside 0-30 in the processed file).
  - 17.3% (13,882) of the kept rows are minors (13-17); privacy and GDPR rules apply to any product use.
  - Test is 48 items at one page, 8 per scale; scale means differ (R lowest ~2.1, S highest ~3.3).
- **Processing script:** `src/career_compass/data/build_riasec_people.py` -> `data/processed/riasec_people.parquet`
  (80,085 rows; shared-network rows dropped as per skill) and `riasec_people_incl_shared_network.parquet` (115,974 rows;
  adds flag `shared_network`). Exploration script: `research/feasibility/explore_openpsych.py`.
  Added columns: `R I A S E C` (mean of 8 items, >= 6 answered), `n_missing_items`, `minor_13_17`, `vcl_real_words_checked`, `major_clean`, `shared_network`, `row_id` (raw row position).

Cleaning log (sequential):

| Step | Rows before | Rows after | Removed |
|---|---|---|---|
| raw | 145,828 | 145,828 | 0 |
| any fake VCL word | 145,828 | 116,543 | 29,285 |
| straight-lining (all 48 answered, same value) | 116,543 | 116,298 | 245 |
| >= 5 of 48 items missing (>10%) | 116,298 | 116,042 | 256 |
| age < 13 or > 90 | 116,042 | 115,990 | 52 |
| exact duplicate rows | 115,990 | 115,990 | 0 |
| shared network (`uniqueNetworkLocation` == 2) | 115,990 | 80,096 | 35,894 |
| scale with < 6 of 8 answered | 80,096 | 80,085 | 11 |

## 2. onet_31_0 - O*NET 31.0 Database (CSV)

- **Role:** the career catalogue and occupation RIASEC profiles; also Job Zones, tasks, education, work styles.
- **URL:** https://www.onetcenter.org/dl_files/database/db_31_0_csv.zip (page: https://www.onetcenter.org/database.html; dictionary https://www.onetcenter.org/dictionary/31.0/csv/)
- **Version:** O*NET 31.0, August 2026 release. SHA-256 `55033fc6...3d987cd`.
- **License:** CC BY 4.0 (https://www.onetcenter.org/license_db.html). Attribution text (include version):
  "This page includes information from the O*NET 31.0 Database by the U.S. Department of Labor, Employment and Training Administration
  (USDOL/ETA). Used under the CC BY 4.0 license. O*NET(R) is a trademark of USDOL/ETA."
  If we modify data, add: "[Name] has modified all or some of this information. USDOL/ETA has not approved, endorsed, or tested these modifications."
- **Size:** zip 13.2 MB, 45 CSV files (comma-separated, header row). 1,016 occupations in `occupation_data.csv`; 923 have ratings.
- **Key files and real names (31.0 uses snake_case):**

| Skill name | Real file in 31.0 | Rows | Occupations | Notes |
|---|---|---|---|---|
| Interests | `career_interest_types.csv` | 8,307 | 923 | Elements 1.B.1.a-f scale `OI` (min 1, max 7 per scales_reference); 1.B.1.g/h/i scale `IH` (0-6; 1=R..6=C, 0=none) |
| Occupation Data | `occupation_data.csv` | 1,016 | 1,016 | Code, Title, Description |
| Job Zones | `job_zones.csv` | 923 | 923 | Values 2-5 only (see issues) |
| Education | `education.csv` | 11,495 | 901 | Element 2.D.1, scale `RL`, Category 1-12, includes N and CI columns |
| Work Styles | `work_styles.csv` | 37,422 | 891 | Reworked taxonomy: 21 elements 1.D.1.a-u, scales `DR` (0-10) and `WI` (-3 to 3), all AI/Expert |
| Task Statements | `task_statements.csv` | 18,838 | 923 | Task ID, Task, Task Type (Core/Supplemental) |
| Specific interest areas | `specific_interest_areas.csv` | 73,063 | - | Elements 1.B.3.*, optional extra |
| Related occupations | `related_occupations.csv` | 18,460 | 923 | |
| Titles | `job_titles.csv`, `sample_of_reported_titles.csv` | 54,269 / 8,189 | 1,016 / 915 | For E7 free-text |

- **Join keys:** `O*NET-SOC Code` (e.g. `11-1011.00`) across files; first 7 chars = 6-digit SOC for BLS.
- **Quality issues:**
  - OI ratings carry Domain Source `Machine Learning/Expert` (871 occupations) or `Machine Learning` (52). Many are model-estimated, not incumbent surveys.
  - 93 occupations in `occupation_data.csv` have no ratings (all are "... , All Other" catch-all codes); excluded from the matching table.
  - Job Zone 1 no longer exists as its own value; zone 2 is labelled "Job Zone 1-2". No occupation has zone 1.
  - OI distribution is very non-uniform: many 1.0 and 7.0 values (rescaled), mean R 4.57, C 4.53 vs A 1.94.
  - US occupations only; no wages (BLS join needed).
- **Processing script:** `src/career_compass/data/build_onet_occupations.py` -> `data/processed/onet_occupations.parquet`
  (923 rows; columns `onet_soc_code, title, R, I, A, S, E, C, job_zone, holland_code (from IH), oi_domain_source, description`).
- **Sanity checks:** no NaN in R-C or job_zone; ranges R/I/A/S/E 1.00-7.00, C 1.61-7.00; no duplicate codes; first letter of IH code equals argmax of OI in 99.9% rows.
  Spot checks: Biochemists and Biophysicists = I (7.0), Actors = A (7.0), Accountants and Auditors = C (7.0), Registered Nurses = S (top), Electricians = R, Sales Managers = E.
  The exact titles "Biochemists" and "Accountants" do not exist; the real titles are "Biochemists and Biophysicists" (19-1021.00) and "Accountants and Auditors" (13-2011.00).
  Job zone counts: 2: 337, 3: 208, 4: 226, 5: 152.

## 3. onet_30_2_workvalues - O*NET 30.2 Work Values

- **Role:** occupation Work Values profile (not in releases after 30.2 per the skill; confirmed there is no work-values file in 31.0).
- **URL:** https://www.onetcenter.org/dl_files/database/db_30_2_text.zip (full archive; only 4 files extracted). Page: https://www.onetcenter.org/db_releases.html
- **Version:** O*NET 30.2, February 2026. SHA-256 `b5479271...a7453741`. License CC BY 4.0, cite as "O*NET 30.2 Database".
- **Size:** zip 13.4 MB; `Work Values.txt` 494 KB, tab-separated, 7,866 rows, 874 occupations.
- **Key fields:** `O*NET-SOC Code, Element ID, Element Name, Scale ID, Data Value, Date, Domain Source`.
  Six values (1.B.2.a Achievement, b Working Conditions, c Recognition, d Relationships, e Support, f Independence) scale `EX` (1-7);
  1.B.2.g/h/i = first/second/third high-point, scale `VH` (0-6).
- **Join key:** `O*NET-SOC Code`: all 874 codes are present in the 31.0 table (49 of 923 occupations have no work values).
- **Quality issues:** ratings dated 2008-2020 (Analyst), so older than the interests data; frozen.
- **Processing:** same script, `--workvalues` option -> `data/processed/onet_work_values_30_2.parquet` (874 x 6, index = O*NET-SOC Code).
- Cross-check: the 30.2 `Interests.txt` has the same 923 occupations and the same OI/IH layout as 31.0 (same element IDs).

## 4. openpsych_bigfive - IPIP Big Five (optional)

Not downloaded in this pass (optional, not needed for v0 RIASEC work; TIPI in source 1 gives a coarse Big Five).
Candidates found on the index page: https://openpsychometrics.org/_rawdata/BIG5.zip (page lists "56 personality items, 30+ demographic variables"; check which file is meant)
and `IPIP-FFM-data-8Nov2018.zip`. Check codebook and license before download.

## Attribution (README and website footer)

> This site incorporates information from the O*NET 31.0 Database by the U.S. Department of Labor, Employment and Training
> Administration (USDOL/ETA). Used under the CC BY 4.0 license. O*NET(R) is a trademark of USDOL/ETA.
