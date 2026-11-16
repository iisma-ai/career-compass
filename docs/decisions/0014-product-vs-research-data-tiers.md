# 0014 — Separate product mode (stores nothing) from research mode (consented studies)
Date: 2026-11-16        Status: Accepted. Supersedes the data-handling part of 0013.

## Context
ADR 0013 defined v1 as a pilot where "nothing is stored". The ethics review of the dossier (blocker B1, 2026-11-16) pointed
out that the v1 milestones need stored, linked data:
- calibration on a pilot sample (1.2);
- live vs simulated agreement (1.3);
- a controlled self-efficacy study (1.5);
- usability measures (1.7);
- later, a 12-month follow-up (2.6).

The two can't both be true. Leaving it unresolved would allow an unplanned data collection that could involve minors, which
CLAUDE.md rule 5 forbids.

## Options
1. Keep "nothing stored" and drop the pilot milestones. Then v1 could never be validated.
2. Store data in the product. Rejected: it isn't needed for the product, and it conflicts with data minimisation.
3. **Two tiers.** The product stores nothing. Research studies are a separate, explicitly consented, pseudonymous tier.

## Decision
Option 3.
- **Product mode:** no accounts, no stored answers, no analytics identifiers, and server logs without IP addresses. In-memory
  processing is still processing of personal data and is covered by the DPIA.
- **Research mode:** each study has its own protocol, DPIA, research-ethics approval, consent (with parental consent where GDPR
  Art. 8 / LOPDGDD Art. 7 require it), retention limit and deletion route. Participants are **18+** until the DPIA and a lawyer
  or DPO approve the inclusion of minors.
- Research-ethics approval is a new milestone (1.0) and a release blocker.

The rest of ADR 0013 still stands: v1 is a closed English pilot, questionnaire → families only, with free text, CAT and study
paths deferred.

## Consequences
- v1 validation can't start until milestone 1.0 is met.
- Calibration on adults only doesn't cover the teen target group. Including minors is a later, separately approved step, and
  results must not be generalised to teens before then (E1: minors are under-represented in the cleaned data).

## Evidence
Ethics review of the dossier (log 2026-11-16), `research/ROADMAP.md` (v1), CLAUDE.md rule 5, ADR 0013.
