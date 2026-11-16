# 03 - ML and data-driven career / major recommenders

Researched Nov 2026. Levels: A meta/official, B large study, C small/thesis/conference, D press/blog/vendor/community, E own experiments.
Method note: the PNAS paper (Kern et al. 2019) is open access but PMC, PNAS and CORE were blocked for the fetch tool (403/bot check). I could verify the sample sizes from the author repository and a university abstract page, but NOT the paper's own accuracy table. Accuracy figures for Vocation Compass below are therefore press-level (D) and flagged.

## Question
How accurate are data-driven career/major recommenders and interest-inventory predictions, what do they use as inputs, and how do they fail? What does that mean for a RIASEC-to-O*NET recommender?

## Key findings

### Vocation Compass (Kern et al., PNAS 2019)
- Reference: Kern, McCarthy, Chakrabarty & Rizoiu (2019), "Social media-predicted personality traits and values can help match people to their ideal jobs", PNAS 116(52), 26459-26464. (B) [UTS Open Research abstract page](https://opus.lib.uts.edu.au/handle/10453/137868)
- Sample: 128,279 Twitter users across 3,513 occupations; personality profiles of users are automatically inferred from language; occupations show distinct psychological profiles; similar occupations cluster; some clusters contradict existing classifications. (B) same source.
- Repository facts (author code, README): user-level files (128,278 users) are not public (Twitter/IBM Watson terms); the occupation-prediction file is `10_professions_data` with Big Five + 10 value features for **38,073 users**; classifiers include XGBoost; metrics (precision, recall, F1, accuracy, confusion matrix) are only in plots. So the supervised "match" was evaluated over **10 professions**, not all 3,513. (D/C: community repo, but authored by the paper team) [VocationMap repo](https://github.com/behavioral-ds/VocationMap)
- Press releases state the recommender hit "over 70%" accuracy (UNSW; one outlet said 73%); errors "often close in skill sets". A later write-up cites a smaller clustering set (101,152 users, 1,227 occupations) and 20 clusters. (D) [UNSW press](https://www.unsw.edu.au/newsroom/news/2019/12/new-map-reveals-the-hidden-personality-profiles-of-jobs) , [Medical Xpress PDF](https://medicalxpress.com/news/2019-12-unveiling-reveals-hidden-personalities-jobs.pdf)
- **Not verified from the paper:** the exact accuracy definition (top-1? top-k?), baseline, per-class confusion, and the accuracy of the personality inference. `[UNVERIFIED]` The skill file's "about 70% accuracy" should be treated as a press figure for a 10-class task on Twitter-inferred personality, not as evidence that a career recommender reaches 70% over hundreds of occupations. (Our interpretation, flagged.)
- Failure modes (our reading, consistent with the above): inputs are inferred traits from a self-selected platform population; occupation labels come from self-description in Twitter bios; high-base-rate classes dominate; no outcome (satisfaction/performance) validation.

### Interest inventories predict career choice, moderately
- Hanna & Rounds (2020, Psychological Bulletin; DOI 10.1037/bul0000269): binomial-normal meta-analytic model gives overall hit rate **50.8%** for predicting career choice from measured interests (thesis version: 50.3%); moderators include inventory, scale type, outcome type, year, hit-rate calculation; the authors stress base rates (comparing hit rates with employment rates in the interest categories). Study/sample counts not retrieved `[UNVERIFIED]`. (A) [Illinois IDEALS record](https://www.ideals.illinois.edu/items/109885) via search summary.
- Interpretation: "50% hit" refers to a small set of broad categories (Holland categories) with chance far below 50%; always compare to base rates.

### Machine-learning-augmented interest scoring
- Song, Shin, Tang, Hanna & Behrend (2024, Personnel Psychology 77(2), 295-319): N = 81,267 employed and unemployed participants; ML-augmented scoring beat traditional profile matching in overall accuracy for occupational membership (employed) and vocational aspirations (unemployed); strongest for high-base-rate job categories, **underpredicted low-base-rate categories**. (B) [record](https://www.econbiz.de/Record/investigating-machine-learning-s-capacity-to-enhance-the-prediction-of-career-choices/10014535947) (abstract only; model type and accuracy numbers not retrieved `[UNVERIFIED]`).
- O*NET Center "Using Machine Learning to Develop Occupational Interest Profiles and High-Point Codes for the O*NET System": supervised models trained on human RIASEC ratings, using information already in the O*NET database as inputs, produce RIASEC occupational interest profiles for 923 data-level O*NET-SOC occupations. Accuracy metrics not on the HTML page `[UNVERIFIED]`. (A, official) [O*NET ML_OIPs](https://www.onetcenter.org/reports/ML_OIPs.html) This is the occupation side of our matching: RIASEC profiles of occupations are themselves ML estimates.
- Chatbot-inferred interests (Auburn master's thesis, 2023): training n = 229, test n = 88; machine-inferred interest scores had good internal consistency, split-half reliability, factorial and convergent/discriminant validity but failed criterion-related and incremental validity. (C) [Auburn ETD](https://etd.auburn.edu/handle/10415/8815)

### Predicting majors from interests/other predictors (small, non-comparable)
- Conference abstract (University of South Florida, APS 2020): cross-validated Random Forest hit rate 45% for predicting major from career interests (number of classes not stated). (C) [APS](https://www.psychologicalscience.org/conventions/archive/2020annual/paper/30635/)
- University of Jordan engineering-fields study: balanced bagging accuracy 91.3, 87.7, 82.7, 77.7, 72.9, 65.0% for 2-, 3-, 4-, 5-, 6-, 7-way major classification: accuracy falls with the number of classes. (C, search summary) `[UNVERIFIED: not opened]`
- A 2023 STEM-major study found academic variables (calculus credits, science identity, STEM credits, math achievement) dominated major choice, not interests (search summary, C) `[UNVERIFIED]`.
- Several Random Forest "career guidance" projects report 90%+ accuracy on personality datasets (e.g. a Nepali project: RF 91.14% vs decision tree 78.25%); these are typically tiny or synthetic and in-sample (D). Treat as non-evidence.

### Recommender-system families and their problems
- Freire & de Castro (2020, Knowledge and Information Systems): e-recruitment recommenders 2012-2020: content-based about 27%, collaborative about 6%, knowledge-based about 13%, hybrid about 21% of reviewed papers; hybrid/non-traditional methods rising. (A, review; search summary) [datalearner record](https://datalearner.com/academic/journal-papers/0219-1377/volumes-and-issues/63/paper-detail/17348)
- Ertugrul & Bitirim (2025, Journal of Big Data): systematic review of 57 articles 2010-2023; collaborative, content-based, hybrid and knowledge-based all represented; evaluation mostly classification metrics (precision, recall, F1). (A) [DOAJ](https://doaj.org/article/b4d45185a8284f9e872f7cacdb654396)
- Imankulova et al. (2024, J Emerging Technologies and Computing): career guidance recommenders; cold start named as key limitation. (C) [JETC](https://jetc.sdu.edu.kz/index.php/jetc/article/view/12)
- Mashayekhi et al. (2022, arXiv 2209.05112): data sparsity, multilingual support, explainability and multi-stakeholder objectives central. (B/C) [arXiv](https://bohrium.dp.tech/paper/arxiv/2209.05112)
- Spoladore et al. (2026, Eng Applications of AI): knowledge-based job recommenders often lack ontology-engineering rigour (search summary). `[UNVERIFIED]`
- Job-recommender literature is about job seekers with interaction histories (clicks/applications), a different problem from a first-time, no-history teenager. Collaborative filtering has no usable data for us at v1 (cold start); we have O*NET content plus our own questionnaire.

## Evidence table
| Source | Level | n | Key number |
|---|---|---|---|
| Kern et al. 2019 (PNAS) | B | 128,279 users; 3,513 occupations; 38,073 users x 10 professions in repo | press: "over 70%" for a 10-class task `[UNVERIFIED in paper]` |
| Hanna & Rounds 2020 | A | k not retrieved | hit rate 50.8% (50.3% thesis) |
| Song et al. 2024 | B | 81,267 | ML > profile matching; underpredicts rare occupations |
| O*NET ML OIPs | A | 923 occupations | supervised ML RIASEC profiles |
| USF RF major prediction | C | n/a | 45% hit rate |
| Jordan engineering fields | C | n/a | 91.3% (2 classes) to 65.0% (7 classes) |
| Auburn chatbot thesis | C | 229 + 88 | no criterion validity |

## Gaps / conflicts
- Accuracy of any recommender depends on number of classes and base rates; headline numbers (45-91%) are incomparable.
- No study found that validated a career recommender against longer-term satisfaction/persistence outcomes.
- Press (70%) vs paper details unverified for Vocation Compass; the repo suggests a 10-profession evaluation.
- ML scoring helps common occupations and hurts rare ones (Song et al.), which conflicts with the goal of showing less obvious careers.

## Implications for Career Compass
- v1 architecture: content-based/knowledge-based matching (user RIASEC posterior vs O*NET occupation interest profiles, i.e. the OIPs) with explanations per dimension. No collaborative filtering until real, consented interaction data exist (also GDPR; see note 06).
- Evaluate with metrics that account for base rates and class count (Hanna & Rounds): report lift over base rate, top-k, and stability (E5), not a single "accuracy". Avoid quoting "70%".
- Use ML only where it adds value and test that it does not collapse recommendations into high-base-rate jobs (diversity/coverage metric; rare-occupation recall).
- Treat occupation RIASEC profiles as estimates with uncertainty (they are ML-derived by O*NET); propagate that uncertainty into rankings.
- Major prediction (v3) should include academic variables, not interests alone; expect modest accuracy.

## Open questions
1. Read the PNAS paper: accuracy metric, baseline, Big Five/value inference accuracy. 2. Hanna & Rounds k and moderators. 3. Song et al. model and metrics. 4. O*NET ML report PDF metrics.

## Sources
- Kern, M. L., McCarthy, P. X., Chakrabarty, D., & Rizoiu, M.-A. (2019). PNAS 116(52), 26459-26464. https://opus.lib.uts.edu.au/handle/10453/137868 ; code https://github.com/behavioral-ds/VocationMap
- UNSW Newsroom (2019). New map reveals the hidden personality profiles of jobs. https://www.unsw.edu.au/newsroom/news/2019/12/new-map-reveals-the-hidden-personality-profiles-of-jobs (press, D)
- Hanna, G., & Rounds, J. (2020). How accurate are interest inventories? Psychological Bulletin. https://www.ideals.illinois.edu/items/109885
- Song, Q. C., Shin, Y., Tang, C., Hanna, G., & Behrend, T. (2024). Investigating machine learning's capacity to enhance the prediction of career choices. Personnel Psychology 77(2), 295-319. https://www.econbiz.de/Record/investigating-machine-learning-s-capacity-to-enhance-the-prediction-of-career-choices/10014535947
- O*NET Center. Using machine learning to develop occupational interest profiles and high-point codes. https://www.onetcenter.org/reports/ML_OIPs.html
- Auburn University thesis (2023). Predicting vocational interests through an AI-based chatbot. https://etd.auburn.edu/handle/10415/8815
- APS 2020 convention paper, predicting college major from career interests. https://www.psychologicalscience.org/conventions/archive/2020annual/paper/30635/
- Freire & de Castro (2020). e-Recruitment recommender systems: a systematic review. Knowledge and Information Systems. https://datalearner.com/academic/journal-papers/0219-1377/volumes-and-issues/63/paper-detail/17348
- Ertugrul & Bitirim (2025). Job recommender systems: a systematic literature review. Journal of Big Data. https://doaj.org/article/b4d45185a8284f9e872f7cacdb654396
- Imankulova et al. (2024). Review of approaches/challenges in career recommendation systems. https://jetc.sdu.edu.kz/index.php/jetc/article/view/12
- Mashayekhi et al. (2022). A challenge-based survey of e-recruitment recommendation systems. arXiv 2209.05112. https://bohrium.dp.tech/paper/arxiv/2209.05112
