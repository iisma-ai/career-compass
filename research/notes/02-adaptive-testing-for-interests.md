# 02 - Adaptive testing (CAT/IRT) for interest inventories

Researched Nov 2026. Levels: A meta/official, B large study, C small/thesis/conference, D vendor/blog, E own experiments.
Method note: O*NET report PDFs (IP Manual, Mini-IP, IPSF Psychometric) were fetched but the tool could not decode their compressed text; only the HTML landing pages were readable. Reliability coefficients and item-selection details for the O*NET forms are therefore `[UNVERIFIED]` and must be read by hand (or by E1 on the O*NET files) before use.

## Question
How many items do we need to estimate a RIASEC profile well, what adaptive machinery (IRT model, estimator, item selection, stopping rule) is supported by evidence, and what do O*NET Interest Profiler forms tell us about short-form accuracy?

## Key findings

### O*NET Interest Profiler family (official docs, level A)
- Forms (O*NET Resource Center page): Mini-IP = 30 questions, web-based, English and Spanish, mobile design, free via My Next Move / Mi Proximo Paso; IP Short Form = 60 questions, paper-and-pencil, English; "completion time approximately 10-20 minutes"; Creative Commons licensed (CC BY 4.0 page; Career Exploration Tools License allows redistribution and building other assessments). Reports on both forms are linked; the page itself gives no coefficients. [O*NET IP](https://www.onetcenter.org/IP.html)
- Parent instrument: 180-item self-scoring Interest Profiler (Lewis & Rivkin, 1999). Short Form (Rounds, Su, Lewis & Rivkin, 2010) has 60 items derived from it for counseling/consulting use; the summary page says research indicates "acceptable levels of reliability and convergent and discriminant validity" and that item selection "successfully increased the endorsement rate for the Enterprising scale". No numbers on the page. [IPSF Psychometric summary](https://www.onetcenter.org/reports/IPSF_Psychometric.html)
- Development method of the Short Form: one secondary summary says it used iterative multidimensional scaling and item evaluation by trained judges; **I found no evidence that IRT was used in selecting the Short-Form items** (the premise "IRT item selection" in the brief is unsupported). A later IRT analysis of the IP exists (Rounds, Hoff & Lewis, 2021) but was not retrieved. `[UNVERIFIED]` Sample sizes (secondary): development n = 1,061 and validation n = 132 for the Short Form (a review); the Mini-IP report is described as using two samples of 1,061 and 575 (search summary of the O*NET report). `[UNVERIFIED]`
- Mini-IP: 30 items = 5 per RIASEC scale taken from the 60-item Short Form, in pairs in RIASEC order; the report says scale reduction brings "an inherent decrease in scale reliability and accuracy of measurement", with "acceptable internal consistencies" and "highly correlated" equivalent scales between Short and Mini forms (search summary of the O*NET report). Numeric alpha values not retrieved. A vendor page (JobCannon) quotes alpha .78-.85; not verified, treat as D `[UNVERIFIED]`.
- Earlier O*NET IP reliability/validity report (Rounds, Walker, Day, Hubert, Lewis, Rivkin, 1999): HTML page gives only metadata; numbers in PDF `[UNVERIFIED]`. [IP_RVS](https://www.onetcenter.org/reports/IP_RVS.html)
- Cross-inventory caution: Chu, Russell, Hoff, Phan & Rounds (2022, J Career Assessment 30(4), 776-801) compared SDS, O*NET IP, ACT Interest Inventory and Strong: RIASEC scores were highly correlated across inventories but "often gave respondents different high-point codes"; item content differed. (B) [Illinois experts](https://experts.illinois.edu/en/publications/what-do-interest-inventories-measure-the-convergence-and-content-/) This means top-letter agreement between ANY two forms (including short vs full) will be imperfect, and the "true" code is itself unstable.
- O*NET occupation-code agreement is also low: mean pairwise agreement of first/second/third Holland-code letters across code sources was 12.56% with three-way agreement 2.62% (CDC/NIOSH study of O*NET Holland code classifications, search summary). Concerns occupations, not people. (B/secondary) [stacks.cdc.gov](https://stacks.cdc.gov/view/cdc/197381)

### Interest-inventory CATs (IRT)
- Simsek & Tavsancil (Turkish interest inventory, E-POD 2022): polytomous IRT CAT; 1,449 high school students for calibration/simulation (45% female); equivalence study n = 81; item bank 164 items over 17 factors; EAP estimation; stopping at SE < .50; about 4 items per interest area; live CAT estimates "strongly positively correlated" with paper-pencil (coefficient not reported on the page). IRT model name not on the page. (C) [DergiPark](http://dergipark.org.tr/en/doi/10.21031/epod.1148313)
- Alkan & Deniz (Occupational Field Interest Inventory CAT, 2023): 1,425 high school students for post-hoc simulation; Generalised Partial Credit Model; MFI item selection; stopping SE = .40; average 59 items administered; correlations paper score vs simulated theta .91-.97; live CAT with 150 students vs paper form .73-.91. (C) [DergiPark](https://dergipark.org.tr/en/pub/epod/issue/76343/1153713)
- Aybek (doctoral thesis, Turkish self-assessment inventory): simulations used a mean of 113 items vs 230 on the paper form; correlations .90-.96 across 23 factors (from a search summary, D/C) `[UNVERIFIED, not opened]`.
- Pattern (our interpretation): simulations on already-collected full-form data overstate live performance (.91-.97 in simulation vs .73-.91 live in the same study). Plan for the live gap in E4 validation.
- No RIASEC-specific IRT CAT study with public item bank was found in this search (search summary). Open question.

### Multidimensional and Bayesian CAT
- Segall (1996, Psychometrika 61, 331-354): Bayesian and ML item selection/scoring for multidimensional adaptive tests; selection by maximising the determinant of the (posterior) information/covariance matrix with a multivariate-normal prior; simulation showed equal or higher reliabilities than unidimensional testing. (A/methodological; abstract and secondary summaries) `[UNVERIFIED: full text]` [Psychometrika record via search](https://springerlink.bibliotecabuap.elogim.com/content/pdf/10.1007/BF02294343.pdf)
- Mulder & van der Linden (2009, Psychometrika) review optimal-design criteria (D-, A-optimality) for multidimensional adaptive testing. [Springer](https://link.springer.com/doi/10.1007/s11336-008-9097-5)
- Personality MCAT: a 16PF-5 multidimensional adaptive thesis reports that cutting test length by up to 50% still gave trait estimates correlating .70-.86 with full-form scores; real-data demonstration, not peer-reviewed Monte Carlo (C). [UGA thesis](https://openscholar.uga.edu/record/5851/files/mcmillan_jeremiah_t_201912_phd.pdf) A Spanish FFM CAT study found facets measurable with about a third of a 480-item pool (search summary, unopened). `[UNVERIFIED]`
- Gains shrink at short lengths: ideal-point forced-choice work reports CAT at about half the length of non-adaptive to reach equal true-score correlations, but at short lengths CAT had no notable advantage over optimal static tests (search summary). (C) `[UNVERIFIED]`
- Bayesian questionnaire / EIG: AdaptQuest (arXiv 2112.14476) picks next question by information gain on a Bayesian network and stops when posterior entropy falls below a threshold; BED-LLM selects queries by expected information gain. (C, method papers; no interest-inventory validation) [AdaptQuest](https://arxiv.org/pdf/2112.14476)
- Caveat on Fisher information: assumes item parameters known (calibrated); calibration error propagates (Stanford MLHP course text, D). [mlhp.stanford.edu](https://mlhp.stanford.edu/src/chap3.html)

### Stopping rules
- PROMIS-style default: stop when SE(theta) < .30 (about 3 T-score points, reliability about .90-.91) with minimum 4 and maximum 12 items per domain; SE .32 equated to reliability .90 in a 2025 PMC review. (A/B, health measurement) [PMC12681468](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC12681468/) ; [PROMIS guide](https://casrai.org/guides/promis-physical-function)
- A 2018 simulation (Behavior Research Methods, DOI 10.3758/s13428-018-1068-x) comparing SE, minimum-information and change-in-theta rules under GPCM found SE rule best, especially with a maximum-item cap; tested SE .35 and .30. Authors not confirmed. (B/C) [Springer PDF](https://link.springer.com/content/pdf/10.3758/s13428-018-1068-x.pdf)
- Predicted-standard-error-reduction rules may beat plain SE for poorly targeted respondents (PubMed 32982603, search summary). `[UNVERIFIED]`

## Evidence table
| Source | Level | n | Key number |
|---|---|---|---|
| O*NET IP page (Mini-IP 30, Short Form 60, CC BY) | A | n/a | forms, free, 10-20 min |
| O*NET Short Form / Mini-IP reports | A | 1,061; 575; 132 (secondary) | "acceptable" reliability; numbers `[UNVERIFIED]` |
| Chu et al. 2022 | B | 4 inventories | scores correlate highly; high-point codes often differ |
| Simsek & Tavsancil 2022 | C | 1,449; live 81 | EAP, SE<.50, about 4 items/area, 164-item bank |
| Alkan & Deniz 2023 | C | 1,425; live 150 | 59 items avg, GPCM, SE .40; r .91-.97 sim, .73-.91 live |
| Segall 1996 | A (method) | simulation | det-based Bayesian MCAT >= unidim. reliability |
| 16PF MCAT thesis | C | n/a | 50% shorter, r .70-.86 |
| PROMIS stopping rule | A/B | n/a | SE<.30; 4-12 items/domain |

## Gaps / conflicts
- No published RIASEC MCAT with open calibration; no verified short-vs-full Holland-code agreement rate. We must measure it ourselves (E4) on the 145,828-respondent OpenPsychometrics dataset (skill file) and O*NET item content.
- Mini-IP says scale reduction lowers reliability; Turkish CATs say about 4 items per area suffice at SE .50. SE .50 corresponds to reliability about .75 (1 - SE^2 under unit-variance theta; our arithmetic), which is low for a three-letter code.
- Simulation-vs-live gap (.91-.97 vs .73-.91).
- Interest inventories disagree with each other on high-point codes (Chu et al. 2022), so "accuracy vs full form" is bounded by test-retest/inter-form agreement; use test-retest ceiling as the benchmark, not 1.0.

## Implications for Career Compass (recommendations; our interpretation, to be tested in E4)
1. **Item bank:** start from the CC BY O*NET IP (180 items; Short Form 60) and/or the 48-item OpenPsychometrics RIASEC set, calibrate a multidimensional GRM (6 correlated traits; use graded responses, Strongly dislike-Strongly like, plus "Not sure"). Check licence per item before reuse.
2. **Length:** target median about 24-30 items (about 4-5 per dimension), hard cap about 40, floor about 12. Rationale: Mini-IP is 30 items (5/scale), Turkish CATs reached usable precision at about 4/area (SE .50) and about 59 items for 17+ areas; MCAT borrows strength across correlated dimensions. Test candidate rules in E4 against full-bank scores and against retest-bounded targets.
3. **Estimator:** EAP (multivariate normal prior using the empirical RIASEC correlation matrix) for scoring; it is stable at short lengths and gives posterior covariance for free. MAP/WLE are alternatives; compare in E4.
4. **Item selection:** first 6-12 items fixed or content-balanced (at least 1-2 per RIASEC type) to avoid cold-start; then D-optimal (maximise determinant of the posterior information matrix, Segall) or expected-posterior-variance reduction on the quantity we care about: the ranking of top-k occupations, not just trait SE. Add content balancing and exposure limits.
5. **Stopping rule:** combine (a) posterior SD < about .35-.45 on the top 3 dimensions (or a 95% credible region that separates the top 3 from the rest) with (b) stability of the top-10 occupation list across the last 3 items (our E5 metric) and (c) a max-item cap. PROMIS-style SE<.30 with min/max is the best-documented template; SE .50 is probably too loose for 3-letter codes.
6. **"Lost user" mode:** allow "don't know / never tried" responses and treat them as missing-not-at-random; use more activity-based (concrete) items, since indecisive users may lack experience. No evidence found on this specifically; flag as a design hypothesis.
7. **Validation:** report simulation AND live-gap, and agreement bounded by retest reliability; never claim "equivalent to the full inventory" without E4/E5 evidence.

## Open questions
O*NET Short Form/Mini-IP alpha and agreement figures (read PDFs); whether any IRT calibration of the IP exists (Rounds, Hoff & Lewis 2021); verification of Aybek thesis, Spanish FFM CAT and 16PF thesis numbers; authors of the 2018 BRM stopping-rule paper.

## Sources
- O*NET Center. Interest Profiler. https://www.onetcenter.org/IP.html
- Rounds, J., Su, R., Lewis, P., & Rivkin, D. (2010). O*NET Interest Profiler Short Form Psychometric Characteristics: Summary. https://www.onetcenter.org/reports/IPSF_Psychometric.html (PDF: https://www.onetcenter.org/dl_files/IPSF_Psychometric.pdf, not decoded)
- Mini-IP report. https://www.onetcenter.org/dl_files/Mini-IP.pdf (not decoded)
- Rounds, Walker, Day, Hubert, Lewis & Rivkin (1999). O*NET Interest Profiler: Reliability, Validity, and Self-Scoring. https://www.onetcenter.org/reports/IP_RVS.html
- Chu, Russell, Hoff, Phan & Rounds (2022). What do interest inventories measure? J Career Assessment 30(4), 776-801. https://experts.illinois.edu/en/publications/what-do-interest-inventories-measure-the-convergence-and-content-/
- Simsek, A. S., & Tavsancil, E. (2022). Polytomous IRT-based CAT for measuring psychological traits. Egitimde ve Psikolojide Olcme ve Degerlendirme Dergisi. http://dergipark.org.tr/en/doi/10.21031/epod.1148313
- Alkan, V., & Deniz, K. Z. (2023). Developing a CAT form of the Occupational Field Interest Inventory. https://dergipark.org.tr/en/pub/epod/issue/76343/1153713
- Segall, D. O. (1996). Multidimensional adaptive testing. Psychometrika 61, 331-354. https://springerlink.bibliotecabuap.elogim.com/content/pdf/10.1007/BF02294343.pdf
- Mulder, J., & van der Linden, W. J. (2009). Multidimensional adaptive testing with optimal design criteria for item selection. Psychometrika. https://link.springer.com/doi/10.1007/s11336-008-9097-5
- McMillan, J. T. (2019). Multidimensional adaptive personality assessment (16PF5), PhD thesis, UGA. https://openscholar.uga.edu/record/5851/files/mcmillan_jeremiah_t_201912_phd.pdf
- AdaptQuest (2021). arXiv 2112.14476. https://arxiv.org/pdf/2112.14476
- PROMIS CAT stopping rules review. https://www.ncbi.nlm.nih.gov/pmc/articles/PMC12681468/ ; https://casrai.org/guides/promis-physical-function
- Stopping rule simulation, Behavior Research Methods 2018. https://link.springer.com/content/pdf/10.3758/s13428-018-1068-x.pdf
- CDC/NIOSH. Convergent validity of O*NET Holland code classifications. https://stacks.cdc.gov/view/cdc/197381
