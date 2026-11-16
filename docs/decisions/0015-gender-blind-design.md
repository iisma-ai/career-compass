# 0015 — Gender-blind design: gender plays no part in measuring interests or making recommendations
Date: 2026-11-16        Status: Accepted (decided by the project owner)

## Context
RESEARCH §10 Q4 asked whether the product should counter gender differences in results or only remove measurement bias.
The evidence behind the question:
- Answers differ by gender (Things–People d = .67 in our sample, [e2](../../research/findings/e2_structure.md)), so
  R-top (Realistic) occupations make up 1.7% of women's top-10 results vs 8.9% for men's ([e3](../../research/findings/e3_occupation_space.md)).
- Several items show gender DIF, meaning women and men with the same interest level answer them differently. The largest
  are E4, R3, A7, I8, R4 and E1, with |DIF| .30–.44 (E2).
- Supervised field-of-study prediction amplifies gender gaps (E6), and free text carries gender cues (E7).

The project owner's decision (2026-11-16): "We want the least involvement of gender possible. It shouldn't matter for the
interests or the recommendations."

## Options
1. **Faithful only:** results follow the answers, with no adjustment.
2. **Gender-aware broadening:** show extra counter-stereotypic careers depending on the user's gender. Rejected: it needs
   gender as an input, which is the opposite of what the owner asked for.
3. **Gender-blind design (chosen):** gender is never an input. Gender bias is removed from the measurement, and gender is
   used only to audit that the system behaves the same for everyone.

## Decision
Option 3.
- **No gender input.** The product never asks for, infers or stores gender. No model, rule, threshold or text depends on it.
  Identical answers always give identical results.
- **No gender-conditioned adjustment.** Results are never re-weighted, quota-balanced or re-ordered by gender, in either
  direction. Any exploration aid (for example adjacent hexagon types) is triggered only by the answers and shown the same
  way to everyone.
- **Measurement without gender bias.** Items with gender DIF are replaced (milestone 1.1). When choosing between candidate
  items that pass the bar, prefer the one with the smallest gender DIF. Item wording and settings are gender-neutral.
- **Free text:** gender cues are stripped before matching (ADR 0012).
- **Field of study (v3):** may never amplify gender gaps (milestone 3.2).
- **Explanations and copy** never frame a career by gender and never mention the user's gender.
- **The only use of gender is auditing** (CLAUDE.md rule 7). Audits run offline on research data: the OpenPsychometrics
  sample, or an optional, self-reported question in the consented research tier (ADR 0014), never in product mode. Audit
  results feed only gender-blind fixes (item changes, the differentiation gate), never gender-conditioned logic.

## Consequences
- Differences that come from people's actual answers stay in the results. For example, the R-top gap (1.7% vs 8.9%) is not
  closed artificially. "Gender shouldn't matter" is met in this sense: the same answers give the same results, and the
  questionnaire measures interests the same way for everyone. The docs must say this plainly and must not claim equal
  outcomes by group.
- Milestone 1.6 gains a check: product inputs contain no demographic field, and no code path reads one.
- RESEARCH §10 Q4 is resolved. The open "careers you might not have considered" idea is dropped as a gender mitigation. It
  may come back only as an answer-driven feature offered to everyone, which would need its own ADR.

## Evidence
RESEARCH §1, §9, §10 Q4; `research/findings/e2_structure.md`, `e3_occupation_space.md`, `e6_major_prediction.md`,
`e7b_cue_stripping.md`; ADRs 0012, 0014.
