# Brief for legal review: EU AI Act and GDPR scope of Career Compass v1

Prepared 2026-11-16 for a lawyer or DPO. **This is not legal advice.** It sets out facts about the product and the
questions we need answered. It covers release blockers 1 and 6 in `research/ROADMAP.md`.

## 1. What v1 does (facts)
- **Flow:** a website asks 24 Likert interest questions and estimates six RIASEC interest scores (GRM-EAP; `research/MODELS.md` L1–L2).
- **Output:** about 3 **unordered** career families with 2–3 example US occupations each (O\*NET 31.0) and a short explanation. No
  scores, ranks or percentages are shown (ADR 0006).
- **Framing:** "careers worth exploring"; a printable summary for a counsellor; links to human help (MODELS L3, L6).
- **Inputs:** no free text, no demographic inputs, and gender is never asked or inferred (ADR 0015). No accounts, no stored
  answers, no analytics identifiers, and server logs without IP addresses (ADR 0014). Answers are processed in memory only.
- **Audience:** people choosing a career, including secondary-school students, some under 16. v1 is a closed English pilot.
- **Decisions:** none are made about the user. The tool does not admit, assign, grade or rank anyone, and nobody else
  (school, employer) receives the result unless the user shares the printout.
- **Model type:** a fixed psychometric scoring model (item response theory) plus correlation matching against published
  occupation profiles. No model is trained on user data.
- **Research mode:** separate consented studies, 18+ only until approved otherwise, each with its own ethics approval (ADR 0014).

## 2. What we know about the law (verified status)
- **AI Act:** Regulation (EU) 2024/1689 ([policy page](https://digital-strategy.ec.europa.eu/en/policies/regulatory-framework-ai)).
- **Annex III point 3** (education and vocational training) lists high-risk uses. Secondary summaries say it covers:
  - admission or assignment to institutions;
  - evaluating learning outcomes;
  - assessing the appropriate level of education;
  - monitoring students during tests.

  **Not yet read from the official text** `[UNVERIFIED]`. Point 4 (employment) covers recruitment and decisions about
  workers `[UNVERIFIED]`.
- **Article 6(3):** secondary sources say an Annex III system can fall outside high-risk if it doesn't pose a significant
  risk, **except where it performs profiling of natural persons** `[UNVERIFIED]`.
- **Timing:** the AI Omnibus entered into force on 27 July 2026. Annex III high-risk rules apply from **2 December 2027**
  ([Commission](https://digital-strategy.ec.europa.eu/en/news/ai-omnibus-enters-force)). Article 50 transparency duties
  apply already, according to secondary sources `[UNVERIFIED]`.
- **GDPR:**
  - Art. 8 sets the consent age for information society services at 16 by default, at least 13
    ([GDPR Art. 8](https://gdpr-info.eu/art-8-gdpr/)). Spain sets it at 14 ([LOPDGDD Art. 7](https://www.boe.es/buscar/act.php?id=BOE-A-2018-16673)).
  - Estimating interest profiles is likely "profiling" under GDPR Art. 4(4) `[UNVERIFIED: our reading]`.

## 3. Questions for counsel
1. Is v1 an AI system under Art. 3(1)? It's a fixed statistical scoring model with no learning from users.
2. Does v1 fall under Annex III(3) or (4)? It gives career exploration suggestions to individuals, including students, and
   makes no admission, assignment, evaluation or level decision.
3. If it does fall under Annex III, does the Art. 6(3) exception apply? Is producing an interest profile "profiling", which
   would rule the exception out?
4. If v1 is not high-risk, which obligations still apply: Art. 50 transparency, Art. 4 AI literacy, and any others?
5. **GDPR legal basis** for in-memory processing of answers with nothing stored: consent, legitimate interest, or
   performance of a service? Does Art. 8 apply when nothing is stored, and what age verification is proportionate?
6. **DPIA:** is one mandatory, given profiling of possibly vulnerable persons (minors)? What should child-friendly
   information say?
7. **v3 field-of-study suggestions** ("people with similar interests studied…", research-only today, ADR 0008): does this
   change the answer to question 2?
8. **Spain-specific requirements**, if the pilot runs there (LOPDGDD, education-sector rules).

## 4. What we need back
- A written scope classification (high-risk or not, with the article references).
- The list of applicable obligations and their dates.
- The GDPR legal basis and the age rules.
- Whether a DPIA is required.

Record the outcome as a new ADR and clear blockers 1 and 6 in `docs/STATUS.md`.
