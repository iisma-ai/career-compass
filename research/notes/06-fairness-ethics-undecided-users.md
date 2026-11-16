# 06 - Fairness, ethics, undecided users, GDPR/minors

Researched Nov 2026. Levels: A meta/official law text, B large study, C small/preprint, D secondary/blog, E own experiments.
Method note: GDPR Art. 8 text (gdpr-info.eu) and Spanish LOPDGDD Art. 7 (BOE) were read directly. Morris (2016) and Hoff et al. numbers come from abstracts/search summaries; full PDFs were not decodable. Legal items beyond Art. 8/Art. 7 are general knowledge flagged `[UNVERIFIED]`; this is not legal advice and needs a lawyer/DPO before launch.

## Question
(1) How big are gender/cultural differences in interests and does RIASEC measure the same thing across groups? (2) How do stereotyped recommendations arise and how can we mitigate them? (3) What does research say about career indecision and what helps undecided people? (4) What do GDPR and Spanish law require for minors?

## Key findings

### Gender and group differences in interests
- Su, Rounds & Armstrong (2009, Psychological Bulletin 135(6), 859-884): data from technical manuals of 47 interest inventories, 503,188 respondents. Things-People dimension d = 0.93 (men things, women people). RIASEC: Realistic d = 0.84, Investigative d = 0.26 (men higher); Artistic d = -0.35, Social d = -0.68, Conventional d = -0.33 (women higher); average |d| = .45 (about 69.8% overlap per a search summary). Item-development strategies can substantially reduce differences. (A) [PubMed record via search](https://pubmed.ncbi.nlm.nih.gov/19883140/) ; [Illinois record](https://iro.uiowa.edu/esploro/outputs/journalArticle/Men-and-things-women-and-people/9984380502202771)
- Su & Rounds (2015, Frontiers in Psychology 6:189): 52 samples, 33 inventories (1964-2007), over 400,000 respondents; largest male-favouring gaps in engineering interests (d = 0.83-1.21); women favoured in social sciences and medical services (d = -0.33, -0.40); gender composition of STEM fields tracked people-/things-orientation, not quantitative ability. (A) [Frontiers](https://frontiersin.org/articles/10.3389/fpsyg.2015.00189/full)
- Morris (2016, J Counseling Psychology 63(5), 604-615): Strong Interest Inventory, U.S. residents aged 14-63, N = 1,283,110, 2005-2014; overall sex-difference multivariate effect Mahalanobis D = 1.61 (27% overlap); sex differences larger and interest levels slightly lower in younger samples; sex differences narrowed slightly among 18-22-year-olds in recent cohorts; ethnicity effects generally very small (e.g. higher Investigative and Enterprising for Asian, Indian and Middle Eastern respondents, lower Realistic for Black respondents). A correction notice exists; check the corrected version `[UNVERIFIED which numbers]`. (B) [Morris record](https://bvbvf1.bib-bvb.de/vufind/PrimoRecord/cdi_proquest_miscellaneous_1835405169) ; skill-file PDF [Morris 2016](https://hk.themyersbriggs.com/content/Research%20and%20White%20Papers/Strong/Morris_2016_Vocational_Interests_in_the_United_States_JCounselingPsych.pdf)
- Hoff et al. (interest fit across gender, ethnicity, education; "Can everyone get interesting jobs?"): title confirmed; no numbers retrieved `[UNVERIFIED]`. Hanna et al. (2025, Applied Psychology; over 250,000 American employees): average person-job interest profile correlation .20 (search summary) `[UNVERIFIED]`. "Interested and employed" (Hoff et al., national study of gender differences in basic interests and employment) exists on ResearchGate; not read. [record](https://discovery.fiu.edu/display/pub303370)
- Interpretation: a d of 0.93 on Things-People means ranking occupations on raw RIASEC scores will reproduce gender-segregated recommendations even when the instrument is working as designed.

### Measurement invariance and structure across groups
- Rounds & Tracey (1996): Holland's circular order did not hold in 76 international matrices (18 countries) or 20 U.S. ethnic matrices (see note 01). (A) [record](https://experts.illinois.edu/en/publications/cross-cultural-structural-equivalence-of-riasec-models-and-measur/)
- Invariance studies found by search (summaries only): South African Career Interest Inventory (n = 407): circular model fit both genders, mostly invariant, better fit for women; a Chinese SDS study tested equivalence across gender and Mainland China vs Hong Kong; 18REST (Brazil, 18 items, 3 per RIASEC type) reported gender measurement invariance despite expected mean differences; a CISS dissertation could not test invariance because baseline fit was poor. General pattern (our synthesis of these small studies): configural and metric invariance often hold, scalar often fails. (C) `[UNVERIFIED: not opened]` [18REST](https://new.scielo.br/j/prc/a/j8dnMMQM3VdKW3dSbZTYPMN/?lang=en) ; [Stellenbosch](https://scholar.sun.ac.za/handle/10019.1/2387)
- No invariance study of the O*NET IP or Mini-IP across Spanish vs English or across groups was found (gap).

### Stereotyped recommendations: evidence and mitigation
- LLM job recommendations show gender/nationality/name bias (Salinas et al. 2023; Nghiem et al. 2024: 320 names, over 750,000 prompts, salary gaps up to 5%; Forcada Rodriguez et al. 2025: 25 countries x 4 pronouns, English/Spanish/German) (see note 04). (B/C)
- A 2026 randomized-style study (n = 123 undergraduates, arXiv; search summary) found a gender-biased LLM assistant increased stereotypic occupation suggestions; a neutral configuration produced the lowest rate. `[UNVERIFIED]`
- ML-augmented interest scoring underpredicts low-base-rate occupations (Song et al. 2024, n = 81,267), which can reinforce existing occupational segregation (see note 03). (B)
- Mitigation options (our interpretation, to test in E5/E6): (a) within-gender or gender-neutral norming is debatable: Su et al. note item-development strategy affects gender gaps; (b) show recommendations from both normed and raw rankings, or give users a "broaden" control; (c) audit with matched counterfactual profiles (same latent scores, different gender/language label) and measure distance between lists; (d) never use gender as a model input; (e) report per-group coverage of top-k lists (e.g. share of Realistic occupations shown to women, Social occupations shown to men).

### Career indecision and what helps undecided people
- Udayar, et al. (2020, J Career Assessment): meta-analysis of 86 studies (N = 54,160): process-related career decision self-efficacy showed stronger negative associations with career indecision than generalised or content self-efficacy or self-esteem; a second analysis of 19 studies (N = 7,953) found process self-efficacy strongly and negatively associated with lack of information and inconsistent information. (A) [SERVAL record](https://serval.unil.ch/fr/notice/serval:BIB_AF059FD4623A) (via search summary; authorship beyond Udayar not confirmed).
- Choi, Park & Yang (2012): meta-analysis of 12 studies; career indecision highly correlated with career decision self-efficacy (described in Udayar et al.; coefficient not retrieved) `[UNVERIFIED]`. (A/secondary)
- Brown et al. (2003, JVB 62; 62 studies, 18 components, five critical ingredients: written exercises, individualised interpretation/feedback, world-of-work information, modelling, building support) and Whiston et al. (2017, JVB 100, 175-184), per secondary summaries: repeated interventions beat one-off ones; counsellor-facilitated beat self-directed/computer-only; effects larger on career decision-making self-efficacy. `[UNVERIFIED primary]` (A/secondary) [CDAA](https://cdaa.imiscloud.com/Web/Blog/Posts/What-is-best-practice-in-careers-education--An-outline-of-the-evidence.aspx)
- Chatbot coaching RCT (n = 82; reduced negative affect, increased goal clarity), small trials and a 36-person study (comparable effect to traditional exercise, over-reliance and privacy concerns) (see note 04). (C) `[UNVERIFIED]`
- Interpretation: indecision is multi-causal (lack of information, inconsistent information, low self-efficacy); a test result alone addresses information, not self-efficacy. Process features (clear next steps, exploration activities, written output, optional counsellor hand-off) are evidence-aligned.

### GDPR and minors (EU / Spain)
- GDPR Art. 8(1): where consent is the lawful basis for information-society services offered directly to a child, processing is lawful if the child is at least 16; below that, consent must be given or authorised by the holder of parental responsibility; Member States may lower the age by law but not below 13; Art. 8(2): controller must make reasonable efforts to verify parental consent given available technology. (A, law text) [gdpr-info.eu Art. 8](https://gdpr-info.eu/art-8-gdpr/)
- Spain, LOPDGDD (Ley Organica 3/2018) Art. 7: processing based on a minor's consent is lawful only if the minor is over 14; for under-14s consent of the holder of parental authority is required, within the scope they set. (A, law text) [BOE](https://www.boe.es/buscar/act.php?id=BOE-A-2018-16673)
- Other member states differ (secondary lists: e.g. Austria 14, France 15, Germany 16; not verified) `[UNVERIFIED]`. A proposed "EU Kids Act" may change minimum ages (secondary, Osborne Clarke) `[UNVERIFIED]`. [source](https://www.osborneclarke.com/es/insights/la-eu-kids-act-propone-nuevas-normas-de-proteccion-de-menores-en-linea-que-anticipan)
- Not verified here, general knowledge, ask a DPO: Art. 5 data minimisation; Art. 22 limits on solely automated decisions with significant effects (a recommendation is probably not such a decision, but profiling transparency under Art. 13-15 still applies); DPIA likely for profiling of minors; storing questionnaire answers is personal data; consent for under-14s in Spain needs parental verification; the EU AI Act might classify some education/vocational tools as high-risk. `[UNVERIFIED]`
- CLAUDE.md rule 5 already blocks collecting user data until a privacy design exists.

## Evidence table
| Source | Level | n | Key number |
|---|---|---|---|
| Su, Rounds & Armstrong 2009 | A | 47 inventories, 503,188 | Things-People d = .93; R .84; I .26; A -.35; S -.68; C -.33 |
| Su & Rounds 2015 | A | 52 samples, 33 inventories, over 400,000 | engineering d = .83-1.21 |
| Morris 2016 | B | 1,283,110 | D = 1.61 overall sex difference; ethnicity effects very small |
| Rounds & Tracey 1996 | A | 20 + 76 + 73 matrices | circular order fails cross-culturally |
| Udayar et al. 2020 | A | 86 studies, 54,160 | process self-efficacy strongest vs indecision |
| Brown et al. 2003 | A | 62 studies | 5 critical ingredients (secondary) |
| GDPR Art. 8 / LOPDGDD Art. 7 | A | n/a | 16 default, min 13; Spain 14 |

## Gaps / conflicts
- Morris (2016) has a correction notice; verify which statistics changed.
- Invariance evidence is small-sample and non-Spanish for the most part; the hexagon may not hold in Spanish minority/immigrant groups (Rounds & Tracey).
- Whether gender-differentiated norms improve or harm outcomes is unresolved; differences are real in raw interests (large for Things-People) but their normative status is a values question.
- Evidence for indecision interventions is mostly counselor-led; online self-help effects uncertain.
- Spanish/EU public bodies' policies for minors in online career tools not checked.

## Implications for Career Compass
- Fairness audit before any release (CLAUDE.md rule 7): counterfactual gender/language tests on the pipeline; report per-group coverage of top-k lists; include a "broaden my options" control and show how many recommendations come from each RIASEC type. Do not use demographic inputs.
- Report Prediger axes and let the user see which axis drives gender-typical results; avoid labelling any career as "for men/women".
- Validate hexagon and loadings by gender and language (ES/EN) in E2 (configural/metric/scalar invariance) before comparing scores across groups.
- Undecided/"lost" mode: support information-gathering and self-efficacy (concrete next steps, explore-by-activity, written summary, repeat later) rather than a single answer; design the exit as "talk to a counsellor/teacher".
- Privacy: target users 14+ in Spain for consent (LOPDGDD Art. 7); for under-14 require verifiable parental consent; for other EU countries check national age (13-16). Prefer no account / no persistent storage / local processing for v1; get legal review before collecting any data.

## Open questions
1. Morris 2016 corrected numbers. 2. Primary reading of Brown 2003, Whiston 2017, Choi 2012. 3. Spanish-language invariance studies of RIASEC. 4. DPO review (Art. 22, DPIA, AI Act). 5. National consent ages for target countries.

## Sources
- Su, R., Rounds, J., & Armstrong, P. I. (2009). Men and things, women and people. Psychological Bulletin 135(6), 859-884. https://iro.uiowa.edu/esploro/outputs/journalArticle/Men-and-things-women-and-people/9984380502202771
- Su, R., & Rounds, J. (2015). All STEM fields are not created equal. Frontiers in Psychology 6:189. https://frontiersin.org/articles/10.3389/fpsyg.2015.00189/full
- Morris, M. L. (2016). Vocational interests in the United States: Sex, age, ethnicity, and year effects. J Counseling Psychology 63(5), 604-615. https://hk.themyersbriggs.com/content/Research%20and%20White%20Papers/Strong/Morris_2016_Vocational_Interests_in_the_United_States_JCounselingPsych.pdf
- Rounds, J., & Tracey, T. J. G. (1996). https://experts.illinois.edu/en/publications/cross-cultural-structural-equivalence-of-riasec-models-and-measur/
- Hoff, K. A., et al. Can everyone get interesting jobs? Estimating interest fit across gender, ethnicity, and education. https://discovery.fiu.edu/display/pub303370
- Ambiel et al. (2018). 18REST. Psicologia: Reflexao e Critica. https://new.scielo.br/j/prc/a/j8dnMMQM3VdKW3dSbZTYPMN/?lang=en
- Udayar, S., et al. (2020). Difficulties in career decision making and self-evaluations: a meta-analysis. J Career Assessment. https://serval.unil.ch/fr/notice/serval:BIB_AF059FD4623A
- Brown et al. (2003) / Whiston et al. (2017) summaries. https://cdaa.imiscloud.com/Web/Blog/Posts/What-is-best-practice-in-careers-education--An-outline-of-the-evidence.aspx
- Regulation (EU) 2016/679, Art. 8. https://gdpr-info.eu/art-8-gdpr/
- Ley Organica 3/2018 (LOPDGDD), Art. 7. https://www.boe.es/buscar/act.php?id=BOE-A-2018-16673
- Notes 03 and 04 in this folder for LLM bias sources.
