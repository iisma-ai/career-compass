# 0013 — v1 scope: closed English pilot, questionnaire only, no stored data
Date: 2026-11-16        Status: Accepted. Data-handling part superseded by 0014 (the product stores nothing; research studies are a separate consented tier)

## Context
When assembling the dossier we had to decide what v1 contains. The evidence supports the questionnaire → families pipeline
(E1–E5). Free text is research-only (ADR 0007/0012), field-of-study prediction is research-only (ADR 0008), CAT gives no
gain (ADR 0005), and the five release blockers from the ethics review are still open.

## Options
1. **Closed pilot:** English only; 24-item questionnaire → families with explanations, plus the lost-user flow. Answers are
   processed in memory, nothing is stored and there are no accounts.
2. A public launch with the same scope. Rejected because the privacy design, DIF re-audit, lost-user validation and data
   permission are all unresolved.
3. Include free text in v1. Rejected because negation isn't handled and the bias test isn't independent.
4. Spanish in v1. Deferred because there's no Spanish calibration or invariance evidence (Rounds & Tracey 1996; E2 caveat).

## Decision
Option 1. Spanish, the EU catalogue, free text and CAT move to v2, and study paths to v3. The v1 milestones and proposed success
criteria are in `research/ROADMAP.md`. Each criterion is pre-registered before it is tested.

## Consequences
- v1 can't start user testing until blocker 1 (privacy/DPIA) and blocker 2 (shippable item parameters) are resolved.
- The proposed criteria are targets, not evidence. They may be revised before pre-registration, but not after.

## Evidence
`research/RESEARCH.md` §1, §9; `research/MODELS.md`; `research/ROADMAP.md`; ADRs 0002, 0005–0008, 0012.
