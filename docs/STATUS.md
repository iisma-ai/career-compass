# Status — updated 2026-11-15

**Phase:** v0, research & feasibility (see CLAUDE.md "Current phase").

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
| E7b cue stripping | planned | — |

## Release blockers (ethics review 2026-11-15)
- [x] O\*NET attribution (README)
- [ ] Privacy/legal design + DPIA (users under 16, GDPR)
- [ ] Re-audited DIF on the final item set
- [ ] Validated lost-user flow
- [ ] Permission from OpenPsychometrics, or our own calibration data (0002)

## Next steps
1. E7b: demographic-cue stripping, tested on a held-out counterfactual set (ADR 0011).
2. Assemble the missing dossier docs: `research/RESEARCH.md`, `MODELS.md`, `ROADMAP.md` (research-editor).
3. Negation handling for free text (after E7b).
4. Item-bank work: DIF-balanced rewrites, plus non-biology Investigative items (E2, E6).
