# docs/ — project journal

Everything we decide and every step we take is written down here (CLAUDE.md, hard rule 8).
`research/` holds the evidence (findings, dossier). `docs/` holds **how and why** we got there.
Link to findings; don't copy numbers here unless they're needed to explain a decision.

| Path | What goes in it |
|---|---|
| `STATUS.md` | Where the project is now, what's blocked, and the next steps. Update it whenever any of these changes. |
| `decisions/NNNN-<slug>.md` | One Architecture/Research Decision Record (ADR) per decision. |
| `log/YYYY-MM-DD.md` | Dated work log, with one entry per step. |
| `environment/` | Environment snapshots (e.g. package versions used for past runs). |

## When to write what
- **ADR:** whenever you choose between options, for example a method, threshold, dataset, tool, scope, UX rule,
  or reversing an earlier choice. If you'd have to explain "why did we do it this way?" later, it needs an ADR.
- **Log entry:** for every unit of work, such as an experiment run, pre-registration, download, refactor,
  environment change, review or doc update. Write it in the same commit as the work.

## ADR template (`decisions/NNNN-<slug>.md`)
```
# NNNN — <decision in a few words>
Date: YYYY-MM-DD        Status: Proposed | Accepted | Superseded by NNNN | Rejected
## Context        what problem / question forced a decision
## Options        each option considered, with pros and cons
## Decision       what we chose
## Consequences   what this commits us to, risks, what would make us revisit it
## Evidence       links to research/findings/*, notes, URLs, commits
```
Don't change the decision in an accepted ADR. Write a new ADR that supersedes it, and set the old one's status to
`Superseded by NNNN`. Fixing typos or adding links is fine.

## Log entry template (append to `log/YYYY-MM-DD.md`)
```
## HH:MM — <step title>
- **What:** ...
- **Why:** ... (link ADR / issue)
- **Commands:** `uv run python -I ...`
- **Files:** created / changed
- **Outcome:** result, verdict, or "failed because ..."
- **Follow-ups:** open items (also copy into STATUS.md)
```
Entries dated before 2026-11-15 22:00 were filled in afterwards from the git history and findings files, and are marked
*(backfilled)*.

## Index of decisions
| # | Decision | Status |
|---|---|---|
| [0001](decisions/0001-riasec-and-onet-core-model.md) | RIASEC interests + O\*NET occupations as the core model | Accepted |
| [0002](decisions/0002-openpsychometrics-research-only.md) | OpenPsychometrics data is research-only | Accepted |
| [0003](decisions/0003-preregister-and-commit-first.md) | Pre-register each experiment and commit it before running | Accepted |
| [0004](decisions/0004-pearson-matching-default.md) | Pearson profile correlation is the default matcher | Accepted |
| [0005](decisions/0005-fixed-24-item-form.md) | v1 uses a fixed 24-item form, not an adaptive test | Accepted |
| [0006](decisions/0006-show-unordered-families.md) | Show an unordered set of career families, not a ranking | Accepted |
| [0007](decisions/0007-free-text-retrieval-only-gated.md) | Free text is retrieval-only, optional, and gated on E7b | Accepted |
| [0008](decisions/0008-major-prediction-research-only.md) | Field-of-study prediction (E6) stays research-only | Accepted |
| [0009](decisions/0009-uv-environment.md) | Manage the Python environment with uv | Accepted |
| [0010](decisions/0010-docs-journal.md) | Keep a decisions + log journal in `docs/` | Accepted |
| [0011](decisions/0011-e7b-rule-based-cue-stripping.md) | E7b: rule-based demographic-cue stripping, frozen before the held-out test | Accepted |
| [0012](decisions/0012-adopt-cue-stripping-in-free-text-pipeline.md) | Adopt cue stripping in the free-text pipeline; free text still not user-facing | Accepted |
| [0013](decisions/0013-v1-scope-closed-pilot.md) | v1 scope: closed English pilot, questionnaire only | Accepted (data part superseded by 0014) |
| [0014](decisions/0014-product-vs-research-data-tiers.md) | Product stores nothing; research studies are a separate consented, 18+ tier | Accepted |

## Index of logs
- [2026-11-14](log/2026-11-14.md) *(backfilled)*: scaffolding, data pipeline, E1–E2
- [2026-11-15](log/2026-11-15.md): E3–E7, ethics review, E6, uv migration, docs journal, E7b
- [2026-11-16](log/2026-11-16.md): research dossier (RESEARCH, MODELS, ROADMAP)
