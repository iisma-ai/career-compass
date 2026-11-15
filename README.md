# Career Compass

Research project toward a website that helps people, including those who don't yet know what
they like, discover **careers worth exploring** from a short interest questionnaire.

**Status: v0 research.** Nothing here is a product, and no results should be used to make decisions
about anyone. See `research/` for the literature notes, data documentation and feasibility experiments (E1–E7).

## How it works (research design)
- Interests are measured on the six Holland **RIASEC** types (Realistic, Investigative, Artistic,
  Social, Enterprising, Conventional).
- Profiles are matched to occupation interest profiles formulated from O\*NET® data.
- Results are meant to be shown as broad **career families** with example jobs. Experiments show that exact
  job rankings are not stable enough to present as precise.

## Important limitations
- Interests indicate what you may enjoy. They predict job satisfaction only modestly and are not a
  measure of ability or future success.
- The occupation data describes **U.S.** occupations, and its interest ratings are largely
  **estimated by a machine-learning model** with expert review.
- The research sample for the questionnaire analyses is self-selected, online, mostly English-speaking,
  young and majority female.
- Teen interests are still developing; any result is a snapshot.

## Data and attribution
No raw or person-level data is stored in this repository. Each dataset is downloaded locally
(see `research/DATA_SOURCES.md`).

**O\*NET® 31.0 Database**
> This page includes information from the O\*NET 31.0 Database by the U.S. Department of Labor,
> Employment and Training Administration (USDOL/ETA). Used under the
> [CC BY 4.0 license](https://creativecommons.org/licenses/by/4.0/). O\*NET® is a trademark of USDOL/ETA.
> The Career Compass project has modified all or some of this information. USDOL/ETA has not approved,
> endorsed, or tested these modifications.

**O\*NET® 30.2 Database** (Work Values file only; Work Values is not included in later releases)
> This page includes information from the O\*NET 30.2 Database by the U.S. Department of Labor,
> Employment and Training Administration (USDOL/ETA). Used under the
> [CC BY 4.0 license](https://creativecommons.org/licenses/by/4.0/). O\*NET® is a trademark of USDOL/ETA.
> The Career Compass project has modified all or some of this information. USDOL/ETA has not approved,
> endorsed, or tested these modifications.

Changes made to O\*NET data, such as derived occupation families, centred profiles and match scores, are
documented in `research/DATA_SOURCES.md` and the scripts in `src/carrier_helper/data/` and
`research/feasibility/`.
License text source: https://www.onetcenter.org/license_db.html

**Open-Source Psychometrics Project, RIASEC test responses (2018)**
Anonymous research data from [openpsychometrics.org/_rawdata](https://openpsychometrics.org/_rawdata/).
No license is stated, so it is used here for **research only**. Only aggregate statistics appear in this
repository, and no model or parameter derived from it is intended for a product without the
data owner's permission.

**Embedding models (experiment E7):** `sentence-transformers/all-MiniLM-L6-v2` and
`sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` (Apache-2.0). They run locally and are not
included in this repository.

## License
Source code: [MIT](LICENSE). Data and data-derived files remain under the terms of their sources above.
