---
name: onet-data
description: How to load, join and use the O*NET occupational database (RIASEC interests, work styles, work values, skills, tasks, job zones, education) for career matching. Use whenever code or docs touch O*NET files, O*NET-SOC codes, occupation profiles, or the O*NET Web Services API.
---

# O*NET data

O*NET is the US Department of Labor's occupational database. It covers about 900 occupations
and is the **career catalogue** for this project. Current release: **31.0** (CSV dictionary at
https://www.onetcenter.org/dictionary/31.0/csv/). License: **CC BY 4.0**, so attribution is required.

## Files that matter
Local copy: `data/raw/onet_31_0/db_31_0_csv/`. **31.0 CSV filenames are snake_case** (verified
2026-11-14). The older text releases (e.g. 30.2) use Title Case `.txt` names instead.

| 31.0 CSV file | Use in this project |
|---|---|
| `occupation_data.csv` | Code, Title, Description: base table (1,016 occupations) |
| `career_interest_types.csv` | **RIASEC profile per occupation** (923 rated; the 93 unrated are "All Other" catch-alls) |
| `specific_interest_areas.csv` (+ `_to_career_interest_types`), `interests_illustrative_activities.csv`, `interests_illustrative_occupations.csv`, `career_interest_type_keywords.csv` | New in 31.x. Finer interest areas and example activities, good for question items and explanations |
| `work_styles.csv` | Reworked taxonomy: 21 elements `1.D.1.a–u`, scales `DR` (0–10) and `WI` (−3…3), AI/Expert-rated |
| Work Values | **Not in 31.0.** Use 30.2 `Work Values.txt` → `data/processed/onet_work_values_30_2.parquet` (874 occupations, 6 `EX` scales 1–7) |
| `job_zones.csv` (+ `job_zone_reference.csv`) | Preparation level. **Values are 2–5 in 31.0** ("Job Zone 1–2" is merged into code 2) |
| `education.csv`, `training_and_experience.csv` (+ `_categories`) | Required education / experience distribution |
| `transferable_skills.csv`, `essential_skills.csv`, `abilities.csv`, `knowledge.csv`, `work_activities.csv`, `work_context.csv` | Secondary re-ranking / explanations |
| `task_statements.csv`, `task_ratings.csv`, `emerging_tasks.csv` | Concrete "what you'd do" text for explanations and free-text matching (E7) |
| `job_titles.csv`, `sample_of_reported_titles.csv` | Search / free-text matching |
| `related_occupations.csv` | "Similar careers" and diversity |
| `scales_reference.csv`, `content_model_reference.csv` | Scale ranges and element IDs (check these before assuming anything) |

Ready-made processed table: `data/processed/onet_occupations.parquet` (923 rows; `onet_soc_code,
title, R, I, A, S, E, C, job_zone, holland_code, oi_domain_source, description`), built by
`src/carrier_helper/data/build_onet_occupations.py`. Use it instead of re-parsing raw files.

Long-format layout shared by most rating files:
`O*NET-SOC Code | Title | Element ID | Element Name | Scale ID | Data Value | ... | Date | Domain Source`

## Interests file specifics
- Element IDs `1.B.1.a`–`1.B.1.f` = Realistic, Investigative, Artistic, Social, Enterprising, Conventional.
- Scale `OI` = occupational interest rating, **1–7** (confirmed in `scales_reference.csv`). Values pile
  up at 1.0 and 7.0 (clipped), so expect ties at the extremes.
- Scale `IH` = high-point codes (first/second/third interest), numeric 1–6 (R=1 … C=6), 0 = none.
  The first IH letter matches argmax(OI) in 99.9% of occupations.
- `Domain Source`: 871 occupations "Machine Learning/Expert", 52 "Machine Learning". **All
  interest ratings are model-estimated** (date 02/2026). Disclose this as a data-quality caveat.
- Exact titles are combined, e.g. "Biochemists and Biophysicists", "Accountants and Auditors".

## Standard pivot (occupation × RIASEC matrix)
Already built (see above). `reference.md` shows the pivot logic for building new tables
from other rating files.

## Joins and crosswalks
- Join key across all O*NET files: `O*NET-SOC Code` (e.g. `15-2051.00`).
- To BLS wages and projections: truncate to the 6-digit SOC (`15-2051`).
- To ESCO (EU, 28 languages): O*NET-SOC → SOC → ISCO-08 crosswalk → ESCO occupation. Many-to-many,
  so document match rates.

## Web Services API
- Free with registration at https://services.onetcenter.org/. Rate-limited; v2 uses separate API keys.
- Serves Interest Profiler questions (Mini-IP 30 items, Short Form 60) and scoring, plus career reports.
- For research, prefer the **bulk downloads** (reproducible, offline). Use the API only for the product.

## Attribution text (put it in README and the website footer)
> This site incorporates information from O*NET OnLine (onetonline.org) by the U.S. Department of
> Labor, Employment and Training Administration (USDOL/ETA). Used under the CC BY 4.0 license.

Check the exact current wording on onetcenter.org before publishing.
