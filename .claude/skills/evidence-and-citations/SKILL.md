---
name: evidence-and-citations
description: Rules for citing sources, grading evidence strength and avoiding fabricated claims in all research docs (RESEARCH.md, DATA_SOURCES.md, MODELS.md, ROADMAP.md, notes, findings). Use whenever writing or reviewing research text, literature notes, or any factual claim.
---

# Evidence and citations

## Rules
1. Every factual or numeric claim gets a citation: a URL, a paper reference with DOI/URL, or a
   path like `research/findings/e4_cat_simulation.md`.
2. Never invent papers, authors, numbers, dataset fields or URLs. If you can't verify it, write
   `[UNVERIFIED]` and add it to the doc's **Open questions** list.
3. Report numbers the way the source states them (r vs ρ, corrected vs uncorrected, n).
4. Separate **what the evidence says** from **our interpretation** ("This suggests…").
5. Prefer primary sources. Secondary or blog sources must be labelled as such.

## Citation format
Inline: `... correlates r ≈ .32 with performance [Nye et al., 2017](URL).`
Each doc ends with a **Sources** list: `- Author(s) (Year). Title. Venue. URL`

## Evidence-strength ladder (state it for key claims)
| Level | Type |
|---|---|
| A | Meta-analysis / systematic review / official dataset documentation |
| B | Peer-reviewed study with large sample |
| C | Small or single-sample study, thesis, conference paper |
| D | Press release, blog, vendor claim, community project |
| E | Our own experiments (cite the findings file; note sample and caveats) |

## Sources already collected (verified via search, Nov 2026)
- O*NET Interests dictionary (30.2), RIASEC element IDs, scales: https://www.onetcenter.org/dictionary/30.2/excel/interests.html
- O*NET 31.0 CSV dictionary: https://www.onetcenter.org/dictionary/31.0/csv/
- O*NET content updates (Work Values frozen at 30.2, Work Styles 30.1): https://www.onetcenter.org/dictionary/30.3/text/appendix_updates.html
- O*NET Interest Profiler: https://onetcenter.org/IP.html · Services: https://services.onetcenter.org/ip
- Mini-IP / IP Manual: https://www.onetcenter.org/dl_files/Mini-IP.pdf , https://www.onetcenter.org/dl_files/IP_Manual.pdf
- OpenPsychometrics mirror (RIASEC 2018, 145,828 respondents, 48 items): https://github.com/haghish/openpsychometrics
- ESCO downloads and API: https://esco.ec.europa.eu/en/structure-esco-downloadable-datasets , https://esco.ec.europa.eu/en/use-esco
- Nye, Su, Rounds & Drasgow (2012), interests and performance (A): https://journals.sagepub.com/doi/10.1177/1745691612449021
- Nye et al. (2017) revisit: 92 studies; congruence r = .32, interest scores alone .16 (A): https://experts.illinois.edu/en/publications/interest-congruence-and-performance-revisiting-recent-meta-analyt/
- Congruence and satisfaction: weak (ρ ≈ .08–.20) (A/B): https://journals.sagepub.com/doi/pdf/10.1177/08948453211033903
- Interest CAT (EAP, SE < .50, about 4 items per area) (C): https://dx.doi.org/10.21031/epod.1148313
- Vocation Compass (Kern et al., PNAS 2019): 128,279 Twitter users, 3,513 occupations. The "over 70% accuracy" is a **press figure only (D)**; the author repo suggests the supervised task used 10 professions (38,073 users). Paper not read. https://www.unsw.edu.au/newsroom/news/2019/12/new-map-reveals-the-hidden-personality-profiles-of-jobs
- Morris (2016), Strong sample N = 1,283,110, sex difference D = 1.61 (B; a correction notice exists, so check which numbers changed): https://hk.themyersbriggs.com/content/Research%20and%20White%20Papers/Strong/Morris_2016_Vocational_Interests_in_the_United_States_JCounselingPsych.pdf
- Extracting O*NET features from the NLx corpus (JAAT toolkit; the abstract does not name "TaskMatch") (C): https://arxiv.org/abs/2510.01470

Added from the literature review (2026-11-14; full detail in `research/notes/01–06`):
- Low, Yoon, Roberts & Rounds (2005), stability of interests (A): https://doi.org/10.1037/0033-2909.131.5.713
- Rounds & Tracey (1996), hexagon fails cross-culturally (A): https://experts.illinois.edu/en/publications/cross-cultural-structural-equivalence-of-riasec-models-and-measur/
- Van Iddekinge et al. (2011), interests → performance .14, turnover −.15 (A): https://digitalcommons.memphis.edu/facpubs/11916
- Mount et al. (2005), Big Five ↔ RIASEC (A): https://iro.uiowa.edu/esploro/outputs/journalArticle/Higher-order-dimensions-of-the-Big-Five/9984963096602771
- Hoff et al. (2020), interest fit → satisfaction, modest (A; exact ρ unverified): https://sciencedaily.com/releases/2020/11/201111144353.htm
- Hanna & Rounds (2020), inventory hit rate about 50.8% (A): https://www.ideals.illinois.edu/items/109885
- Song et al. (2024), ML-augmented scoring (n = 81,267), underpredicts low-base-rate careers (B): https://www.econbiz.de/Record/investigating-machine-learning-s-capacity-to-enhance-the-prediction-of-career-choices/10014535947
- Chu et al. (2022), inventories disagree on high-point codes (B): https://experts.illinois.edu/en/publications/what-do-interest-inventories-measure-the-convergence-and-content-/
- Su, Rounds & Armstrong (2009), gender differences, Things–People d = 0.93 (A): https://iro.uiowa.edu/esploro/outputs/journalArticle/Men-and-things-women-and-people/9984380502202771
- Su & Rounds (2015), STEM interest gender gaps (B): https://frontiersin.org/articles/10.3389/fpsyg.2015.00189/full
- Alkan & Deniz (2023), live vs simulated CAT gap (C): https://dergipark.org.tr/en/pub/epod/issue/76343/1153713
- Mulder & van der Linden (2009), multidimensional CAT item selection (B): https://link.springer.com/doi/10.1007/s11336-008-9097-5
- O*NET ML occupational interest profiles report (A): https://www.onetcenter.org/reports/ML_OIPs.html
- LLM career-advice bias: Nghiem et al. 2024 https://arxiv.org/abs/2406.12232 ; Forcada Rodriguez et al. 2025 https://arxiv.org/abs/2505.02456 ; Salinas et al. 2023 https://arxiv.org/abs/2308.02053 (C)
- Udayar et al. (2020), career indecision meta-analysis (A): https://serval.unil.ch/fr/notice/serval:BIB_AF059FD4623A
- GDPR Art. 8 (default 16, min 13): https://gdpr-info.eu/art-8-gdpr/ · Spain LOPDGDD Art. 7 (14): https://www.boe.es/buscar/act.php?id=BOE-A-2018-16673

**PDFs still to be read by a human** (machine fetch failed): O*NET Short Form/Mini-IP reports, Kern et al. 2019,
Low et al. 2005, Prediger 1982 weights, Tracey & Rounds 1993, Morris 2016 correction, Brown 2003 / Whiston 2017.

Add new verified sources to this list as research proceeds.
