# Status — updated 2026-11-16

**Phase:** v0, research & feasibility, wrapping up. All four dossier docs exist (`research/RESEARCH.md`, `DATA_SOURCES.md`,
`MODELS.md`, `ROADMAP.md`). The v1 scope is fixed in ADR 0013.

## Experiments
| ID | Verdict | Decision |
|---|---|---|
| E1 data audit | proven | 0002 |
| E2 structure | hexagon proven; scalar invariance fails | item rewrites pending |
| E3 occupation space | proven (lenient bar) | 0004 |
| E4 adaptive test | not viable as specified | 0005 |
| E5 stability | promising | 0006 |
| E6 major prediction | proven, research-only | 0008 |
| E7 free text | not viable (bias bar) | 0007 |
| E7b cue stripping | proven (held-out overlap .92; names .84; coverage 67%) | 0011, 0012 |
| E7c names v2 + negation | not viable (negation 4/12); names .906 met on blind set | 0016, 0017 |
| E8 pilot DIF power | min 300 per gender group; plan 400 | 0018 |
| E9 study power | 1.6: 2,052/group; 1.5: 176/arm; 1.7: 90; gender agreement gap .044 | 0019 |

## Release blockers (ethics review 2026-11-15)
- [x] O\*NET attribution (README)
- [ ] Privacy/legal design + DPIA (users under 16, GDPR)
- [ ] Re-audited DIF on the final item set
- [ ] Validated lost-user flow
- [ ] Permission from OpenPsychometrics, or our own calibration data (0002)
- [ ] Legal assessment of EU AI Act Annex III(3) for v1 (brief ready: `docs/legal/ai-act-v1-brief.md`; needs a lawyer/DPO)
- [ ] Human-help signposting content reviewed by a counsellor
- [ ] Research-ethics approval before any research-mode study (0014)

## Next steps
2. Primary-source checks of the `[UNVERIFIED]` items (RESEARCH §10). The AI Omnibus timing is verified (Annex III applies from
   2 Dec 2027). Still open: whether Annex III(3) covers v1 (needs a legal review), Hoff 2020 ρ (paywalled), Mini-IP/Short Form
   reliability, Prediger weights, the Morris 2016 correction, Strong item count/alphas. These need a human with library access.
3. E7d: learned negation (NLI or a polarity classifier) with a human-written held-out set; fix the Devanagari
   combining-mark bug in names (ADR 0017).
4. A human-written held-out set for name and gender invariance (ROADMAP 2.4).
6. Item bank: 26 drafts in `research/items/candidate_items_v1.md`. Pilot size done (E8, ADR 0018: plan 400 adults per
   gender group, floor 300; items cleared by 90% CI inside ±.30). Next: psychometrician + counsellor review of the
   drafts.
7. Sample sizes done (E9, ADR 0019). Owner decision: run 1.6 at 2,052 per group, or ~1,000 with a relaxed S-top
   precision bar. Next experiment: E10, a gender-blind mitigation for the 24-item agreement gap (.044).
