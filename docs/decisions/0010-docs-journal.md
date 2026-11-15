# 0010 — Keep a decisions + log journal in `docs/`
Date: 2026-11-15        Status: Accepted

## Context
Decisions were scattered across findings files ("Implications"), commit messages and CLAUDE.md status bullets. There was
no single place that answered "why did we do X, and when?" The user asked for every decision and step to be documented
in a docs folder, as a CLAUDE.md requirement.

## Options
1. A single CHANGELOG. It mixes decisions with steps, and the reasons for choices get lost.
2. **ADRs (one file per decision) + dated work logs + a STATUS page.**
3. A wiki or external docs tool. Off-repo, so it isn't versioned with the code.

## Decision
Option 2, made mandatory as CLAUDE.md hard rule 8. Format and templates are in `docs/README.md`. Subagents report
their decisions and steps (added to every agent's Boundaries section), and the main session writes the entries.
Earlier decisions (0001–0008) and logs were backfilled from the git history and findings.

## Consequences
Every commit that does work also touches `docs/log/`. Every choice between options also adds an ADR. `STATUS.md` must be
kept current.

## Evidence
`CLAUDE.md` (rule 8), `docs/README.md`.
