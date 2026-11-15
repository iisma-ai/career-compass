# 0001 — RIASEC interests + O*NET occupations as the core model
Date: 2026-11-14 *(backfilled)*        Status: Accepted

## Context
The product has to estimate what a person is interested in and map that to careers, including for users who don't
know what they like. We need a measurement model and an occupation catalogue that are evidence-based and openly licensed.

## Options
1. **Holland RIASEC + O\*NET interest profiles.** This is the field standard. O\*NET rates every occupation on the same six
   types (elements 1.B.1.a–f) and is CC BY 4.0. On the downside, the data is US-centric and the profiles are largely ML-estimated.
2. Big Five personality → careers. The link to occupation choice is weaker, and there's no occupation-level profile in O\*NET.
3. Free-text or LLM recommendations only. These can't be validated and are hard to make fair (see 0007).

## Decision
Option 1. People get a RIASEC profile, occupations come from O\*NET 31.0, and person↔occupation congruence is the
matching signal. v1 covers careers only. Results are framed as "careers worth exploring".

## Consequences
- We inherit O\*NET's limits: US labour market, ML-estimated profiles, and a thin A/S/I catalogue (E3).
- Attribution is required (README).
- Universities and degrees are deferred to v3.

## Evidence
`research/notes/01-interest-theory-and-outcomes.md`, `research/DATA_SOURCES.md`, `research/findings/e3_occupation_space.md`.
