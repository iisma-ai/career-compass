# 04 - Free-text and LLM matching to O*NET / ESCO

Researched Nov 2026. Levels: A meta/official, B large study, C small/preprint/thesis, D blog/model card/vendor, E own experiments.
Method note: most items here are arXiv preprints read as abstracts only (the TaskMatch/NLx paper PDF could not be decoded). Numbers not on an abstract are `[UNVERIFIED]`. Honest summary: the literature for "free-text interests -> O*NET occupations" specifically is thin; most work is job-ad or job-title normalisation.

## Question
Which embedding/LLM methods can map a user's free-text description of interests (or a job title) to O*NET/ESCO occupations, how accurate are they, and what are the risks of LLM career advice (bias, hallucination, over-reliance)?

## Key findings

### Embedding methods
- Sentence-BERT (Reimers & Gurevych, 2019, arXiv 1908.10084): siamese/triplet BERT networks produce sentence embeddings comparable by cosine similarity; averaging raw BERT outputs or using [CLS] is often worse than averaging GloVe; finding the most similar pair in 10,000 sentences falls from about 65 hours (BERT cross-encoding) to about 5 seconds (SBERT embeddings) plus 0.01 s comparison. (A/foundational; abstract-level) [arXiv](https://arxiv.org/abs/1908.10084)
- ESCO/EQF linking (Saroglou et al., arXiv 2512.03195): compares Sentence Linking vs Entity Linking from vacancy text to ESCO; releases tool and two annotated datasets; explores generative LLMs. Abstract has no numbers. A search summary reported about 0.54 accuracy for title-query retrieval after fine-tuning all-mpnet-base-v2 (about 4% gain) `[UNVERIFIED]`. (C) [arXiv](https://arxiv.org/abs/2512.03195)
- Community model cards (Misbahuddin job-title-normalizer e5-base/e5-small on Hugging Face): fine-tuned for ESCO + O*NET normalisation over 4,055 occupations, trained on ESCO (EN/FR/DE) and O*NET alternate titles; the card recommends a rejection threshold (out-of-taxonomy titles such as "RevOps" scored about 0.31 vs about 0.8 for true matches). (D, community; metric table not retrieved) [model card](https://huggingface.co/Misbahuddin/job-title-normalizer-e5-base)
- Late-2025 SOC classifier (search summary of arXiv 2511.23057): BERT + NN ensemble reports up to 61% accuracy at the 4th SOC tier and 72% at the 3rd tier, from title+description+skills. `[UNVERIFIED: not opened]` (C)
- O*NET/NLx (Meisenbacher, Nestorov & Norlander, arXiv 2510.01470): Job Ad Analysis Toolkit (JAAT) uses O*NET as framework to extract tasks, occupation codes, tools, skills from more than 155 million NLx job ads (more than 10 billion data points, 2015-2025); reports reliability/accuracy in out-of-sample tests and LLM-as-a-judge evaluation. The abstract does not name "TaskMatch" and gives no accuracy numbers; the skill file's label "TaskMatch" is **not confirmed by the abstract** `[UNVERIFIED]`. (C) [arXiv](https://arxiv.org/abs/2510.01470)
- Related approach: JPLink (arXiv 2002.02557) predicts RIASEC profiles/occupation links for jobs from text with learned representations (supervised). (C) [arXiv](https://arxiv.org/pdf/2002.02557)
- LLM-assisted occupation coding (survey data): LLM4Jobs (arXiv 2309.09708) for occupation extraction/standardisation; Rossow et al. (IGC working papers 2025) pair LLMs with retrieval for ISCO/ISIC coding in Zambia and report substantial accuracy gains at low cost; OccCANINE reports 93.5% on HISCO (historical codes); a Chinese-job-title study reports 98.4% on 500 manual cases with unclear scheme. (C) All via search summaries `[UNVERIFIED numbers]`. [LLM4Jobs](https://arxiv.org/html/2309.09708v2) ; [OccCANINE](https://www.arxiv.org/pdf/2402.13604) ; [IGC](https://www.theigc.org/sites/default/files/2025-10/Rossow-et-al-Working-Paper-October-2025.pdf)
- Chatbot-inferred interests: Auburn master's thesis (n = 229 train, n = 88 test) found machine-inferred RIASEC scores had acceptable reliability/factorial/convergent validity but no criterion or incremental validity (C). [Auburn ETD](https://etd.auburn.edu/handle/10415/8815)

### Do LLMs "have" interests / do they judge interests well?
- Hua, Cheng & Zhu (2024, arXiv 2407.08564): gave LLMs the O*NET Interest Profiler short form; LLMs lean toward Social and Artistic; interests do not match occupations where models perform best; patterns vary by language (English vs Chinese). This studies model self-reports, not their ability to infer a user's interests. (C) [arXiv](https://arxiv.org/abs/2407.08564)
- No peer-reviewed study retrieved that tests zero-shot LLM inference of a person's RIASEC profile from free text against a validated inventory. This is a genuine gap and an E7 candidate. (Search summary.)

### Risks of LLM advice
- Salinas et al. (2023, arXiv 2308.02053): job recommendations from ChatGPT and LLaMA show demographic bias, e.g. secretarial roles suggested for women and consistently low-paying jobs for Mexican workers. (C/B) [arXiv](https://arxiv.org/abs/2308.02053)
- Nghiem, Prindle, Zhao & Daume (2024, arXiv 2406.12232): 320 first names, more than 750,000 prompts, GPT-3.5-Turbo and Llama 3-70B; models favoured White female-sounding names in 40 occupations; salary recommendations differed by up to 5% across subgroups with identical qualifications. (B/C) [arXiv](https://arxiv.org/abs/2406.12232)
- Forcada Rodriguez et al. (2025, arXiv 2505.02456): prompts in English, Spanish, German; 25 countries x 4 pronoun sets; 5 Llama-based models; substantial gender and country biases; intersectional bias persists even when single-axis bias looks fair; prompt language matters; instruction-tuned models least biased. Relevant to Spanish users. (C) [arXiv](https://arxiv.org/abs/2505.02456)
- Auditing LLM career advice for Indian students (NeurIPS 2026 listing; search summary): four models agreed on a stream for only 12.8% of matched profiles; income/first-generation status shifted recommendations toward vocational study. `[UNVERIFIED]` [listing](https://neurips.cc/virtual/2026/162727)
- 2026 arXiv study (n = 123 undergraduates): a gender-biased LLM assistant led to more gender-stereotypic occupation suggestions than control; a neutral configuration produced the fewest (search summary; not opened). `[UNVERIFIED]`
- Effectiveness evidence is thin: a randomized waitlist trial of a solution-focused chatbot coach (n = 82, JVB, 2026 listing) found less negative affect and more goal clarity; a tiny thesis (n = 30) found self-efficacy gains; a within-subject study (n = 36) found comparable effectiveness and over-reliance/privacy concerns. All from search summaries. (C) `[UNVERIFIED]` [JVB listing](https://cris.fau.de/publications/365286850?lang=de_DE) ; [arXiv 2502.18881](https://arxiv.org/pdf/2502.18881)
- Pilot RAG career assistant for high schools: 100 queries, GPT-4 as automatic evaluator plus 25 student raters; RAG beat baseline, especially empathy; hallucination/factual drift noted as risk. (C) [NHSJS](https://nhsjs.com/?p=26125)
- Benchmarks/frameworks for LLM career advice exist but are early (CareerNet by Renaissance Philanthropy blog (D); Warwick IER evaluation framework inception report (C)). [CareerNet](https://renaissancephilanthropy.org/insights/can-ai-give-reliable-career-advice-evaluating-llms-using-careernet) ; [Warwick](https://warwick.ac.uk/fac/soc/ier/researchthemesoverview/researchprojects/llmpoweredcareersadvice/careers-eval-fwork-inception-report-final-110926.pdf)

## Evidence table
| Source | Level | n | Key number |
|---|---|---|---|
| Reimers & Gurevych 2019 | A | n/a | 65 h -> about 5 s for 10k sentences |
| Saroglou et al. 2025 | C | n/a | ESCO linking tool + datasets; about 0.54 acc `[UNVERIFIED]` |
| Meisenbacher et al. 2025 | C | 155M job ads | O*NET extraction toolkit |
| Hua et al. 2024 | C | 4 LLMs | Social/Artistic bias; language-dependent |
| Salinas et al. 2023 | B/C | ChatGPT, LLaMA | gender/nationality bias in job recs |
| Nghiem et al. 2024 | B/C | 750k+ prompts, 320 names | salary gap up to 5% |
| Forcada Rodriguez et al. 2025 | C | 25 countries x 4 pronouns, 3 languages | intersectional bias persists |
| Auburn chatbot thesis | C | 229 + 88 | no criterion validity |

## Gaps / conflicts
- No benchmark for free-text interests -> O*NET; job-title -> occupation accuracies (54-72% at fine SOC levels, 93-98% in other schemes) are not transferable.
- No validated zero-shot LLM RIASEC inference. No study of LLM advice vs counsellor advice with outcome measures.
- Bias studies use English/other prompts and simplified profiles; effect on our structured (non-chat) pipeline is unknown.
- ESCO and O*NET overlap conceptually with near-duplicate occupations; crosswalk quality not assessed here.

## Implications for Career Compass
- Use LLMs/embeddings only as an optional input channel ("lost user" mode), not as the judge of careers: map free text to the same RIASEC latent space (e.g. embed text, similarity to item/activity descriptors and O*NET task/activity statements; calibrate against questionnaire scores in E7) and show the user how their text moved the profile.
- Prefer retrieval over generation: ground every recommendation in O*NET fields (tasks, interests, job zone); use an LLM only to write explanations from retrieved facts, with a rejection threshold for out-of-taxonomy input (model-card heuristic).
- Evaluate first with E7 (text -> top-k O*NET occupations vs questionnaire-based ranking; report recall@k with confidence intervals) before any user-facing claim.
- Mandatory bias testing: counterfactual prompts (gender/name/country/language ES vs EN) on the whole pipeline (see note 06), and keep demographics out of model inputs.
- Do not put raw free text in third-party LLM APIs before the privacy design exists (CLAUDE.md rule 5; minors).

## Open questions
Read the TaskMatch/NLx paper for metrics; confirm the SOC-classifier and OccCANINE numbers; find any zero-shot RIASEC-from-text study; evaluate multilingual (Spanish) sentence-embedding models on ESCO/O*NET.

## Sources
- Reimers, N., & Gurevych, I. (2019). Sentence-BERT. arXiv 1908.10084. https://arxiv.org/abs/1908.10084
- Saroglou, S., et al. (2025). Enhancing Job Matching: Occupation, Skill and Qualification Linking with the ESCO and EQF taxonomies. arXiv 2512.03195. https://arxiv.org/abs/2512.03195
- Meisenbacher, S., Nestorov, S., & Norlander, P. (2025). Extracting O*NET Features from the NLx Corpus to Build Public Use Aggregate Labor Market Data. arXiv 2510.01470. https://arxiv.org/abs/2510.01470
- Hua, M., Cheng, Y., & Zhu, H. (2024). The Career Interests of Large Language Models. arXiv 2407.08564. https://arxiv.org/abs/2407.08564
- JPLink (2020). arXiv 2002.02557. https://arxiv.org/pdf/2002.02557
- Salinas, A., et al. (2023). The Unequal Opportunities of Large Language Models. arXiv 2308.02053. https://arxiv.org/abs/2308.02053
- Nghiem, H., Prindle, J., Zhao, J., & Daume III, H. (2024). "You Gotta be a Doctor, Lin". arXiv 2406.12232. https://arxiv.org/abs/2406.12232
- Forcada Rodriguez, E., et al. (2025). Colombian Waitresses y Jueces canadienses. arXiv 2505.02456. https://arxiv.org/abs/2505.02456
- Misbahuddin. job-title-normalizer-e5-base (model card, D). https://huggingface.co/Misbahuddin/job-title-normalizer-e5-base
- LLM4Jobs. arXiv 2309.09708. https://arxiv.org/html/2309.09708v2 ; OccCANINE arXiv 2402.13604 https://www.arxiv.org/pdf/2402.13604
- Auburn ETD (2023). https://etd.auburn.edu/handle/10415/8815
- Letters from Future Self (2025). arXiv 2502.18881. https://arxiv.org/pdf/2502.18881
- RAG career guidance pilot, NHSJS. https://nhsjs.com/?p=26125
