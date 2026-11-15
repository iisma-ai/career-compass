# 0003 — Pre-register each experiment and commit it before running
Date: 2026-11-15 *(backfilled)*        Status: Accepted

## Context
Several early bars turned out to be mis-specified: the E2 archetype bar was too weak, E3 reach too lenient, and the E4 bar
unreachable. The temptation to adjust bars after seeing results is real, so the order of events must be verifiable.

## Options
1. Write the pre-registration in the findings file and run in the same session. The order can't be verified.
2. **Commit the pre-registration on its own before any full run.** Git timestamps prove the order.

## Decision
Option 2, from E6 onward (commit `bdbdaba`). A bar is never changed after results are in. If it was wrong, the discussion
says so, and the original bar still decides the verdict.

## Consequences
Every experiment takes at least two commits (pre-registration, then results). `--quick` smoke runs are allowed before
the pre-registration only if they touch nothing the bar measures.

## Evidence
`.claude/skills/feasibility-experiment/SKILL.md`; commits `bdbdaba`, `915aeff`.
