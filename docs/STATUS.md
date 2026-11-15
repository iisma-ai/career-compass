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

## Release blockers (ethics review 2026-11-15)
- [x] O\*NET attribution (README)
- [ ] Privacy/legal design + DPIA (users under 16, GDPR)
- [ ] Re-audited DIF on the final item set
- [ ] Validated lost-user flow
- [ ] Permission from OpenPsychometrics, or our own calibration data (0002)

## Next steps
1. Ethics review of the dossier (ethics-reviewer, read-only), then fix what it finds.
1b. Primary-source checks of the `[UNVERIFIED]` items in RESEARCH.md §10.
2. E7c: name coverage (NER or broader rules) plus a held-out set written blind to the rules (ADR 0012).
3. Negation handling for free text.
4. Behaviour-neutral lint cleanup of the old scripts (135 ruff findings).
5. Item-bank work: DIF-balanced rewrites, plus non-biology Investigative items (E2, E6).
