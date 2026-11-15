# Carrier_helper — project memory

## Mission
Help people find careers that fit their interests and passions — including people who are
lost and have no idea what they like — through a short, adaptive questionnaire on a website.
The system estimates the user's interest profile (Holland RIASEC model) and matches it to
careers (O*NET occupations), explaining *why* each career fits.

- **v1 scope: careers only.** Universities / degrees come later (v3).
- Recommendations are framed as **"careers worth exploring"**, never "your perfect career".
- The bar is high: results must be as accurate, well-evidenced and satisfying as possible.

## Current phase: v0 — research & feasibility
Produce an evidence-backed research dossier that doubles as the project blueprint:

| Deliverable | Content |
|---|---|
| `research/RESEARCH.md` | Feasibility verdict, literature, architecture, evaluation, risks |
| `research/DATA_SOURCES.md` | Every dataset: URL, license, fields, join keys, known issues |
| `research/MODELS.md` | Technical spec of each model layer |
| `research/ROADMAP.md` | v1 → v3 phases with success metrics |
| `research/feasibility/eN_*.py` | Reproducible experiments on real data |
| `research/findings/eN_*.md` (+ charts) | Experiment results cited by the docs |

Feasibility experiments (details in the `feasibility-experiment` skill; results in `research/findings/`):
- E1 data audit: **proven** (80k clean rows, α .83–.90; sample young, 67% female, 49% US, no license)
- E2 structure: hexagon holds and loadings are invariant across gender and age, but **scalar invariance fails** and
  CFA fit is poor (CFI about .80); archetypes are soft (never user-facing labels)
- E3 occupation space: **proven against a lenient reach bar**. Pearson matching works, but exposure is
  concentrated (Gini .77), the A/S/I catalogue is thin, and results skew to high-prep careers (open problems).
  Match r is not accuracy.
- E4 adaptive test: CAT not better than a fixed form → **v1 = fixed 24-item form** (pre-registered bar unreachable)
- E5 stability: **promising** (full test only about 55% top-10 stable → show an unordered set of families, not a ranking)
- E6 supervised major prediction: **proven against its bar** (LR on items, top-3 .565 vs majority .40 / centroid .32;
  beats boosting/MLP). Not user-ready: Psychology over-predicted 2×, small fields nearly invisible, large gender gaps
  amplified (STEM-core ×1.11, Psychology ×1.65), and items predict gender (AUC .84). Research-only.
- E7 free-text matching: **not viable as pre-registered**. Retrieval is strong (.95 family / .86 occupation
  Hit@5, rejection threshold works), but gender/name-swap top-10 overlap is .73 < .90. Negation isn't handled.
  E7b with demographic-cue stripping is needed.
- Ethics review (2026-11-15): release blockers are attribution (done: README), privacy/legal design + DPIA,
  re-audited DIF on the final item set, a validated lost-user flow, and permission before shipping anything
  derived from OpenPsychometrics. Never quote r or match scores as accuracy.
- Process rule: commit each pre-registration on its own **before** running the experiment.

_Update this section whenever the phase changes._

## Repo layout
```
CLAUDE.md
research/            docs, notes/, feasibility/ (scripts), findings/ (results)
data/raw/<source>/   untouched downloads + SOURCE.md   (git-ignored, untrusted)
data/processed/      derived parquet/CSV tables        (git-ignored)
src/carrier_helper/  package: data/ (build scripts), matching.py (person↔occupation matching; reuse it)
notebooks/           exploration only — never the source of truth
.claude/agents/      project subagents
.claude/skills/      project skills
```

## Domain glossary
- **RIASEC / Holland code** — six interest types: Realistic, Investigative, Artistic, Social,
  Enterprising, Conventional. A Holland code is the top 2–3 letters (e.g. "IAS").
- **Hexagon** — RIASEC types arranged R-I-A-S-E-C; adjacent types correlate more than opposite ones.
- **Prediger axes** — two underlying dimensions: Data↔Ideas and People↔Things.
- **O\*NET-SOC code** — occupation ID, e.g. `15-2051.00`. Join key across O*NET files.
- **Element IDs 1.B.1.a–f** — O*NET RIASEC elements (R, I, A, S, E, C). Scale `OI` = interest score.
- **Job Zone** — O*NET preparation level; in 31.0 the values are 2 ("Job Zone 1–2", little prep) to 5 (extensive prep).
- **IRT / GRM** — Item Response Theory / Graded Response Model for Likert items.
- **CAT** — Computerized Adaptive Testing: choose each next question to maximise information.
- **θ (theta)** — latent trait (interest level) estimated by IRT.
- **Congruence** — degree of fit between a person's profile and an occupation's profile.

## Hard rules
1. **Evidence:** every factual or quantitative claim in research docs cites a source URL or a
   `research/findings/` file. Anything uncited is marked `[UNVERIFIED]`. Never invent numbers,
   papers or dataset fields. (See the `evidence-and-citations` skill.)
2. **Untrusted data:** each download goes into its own new `data/raw/<source>/`. Never run code
   from inside it; scripts live in `research/feasibility/` or `src/` and run with `python -I`.
   Never modify raw files. (See the `safe-dataset-download` skill.)
3. **Reproducibility:** fixed seeds, one command re-runs an experiment, outputs go to
   `research/findings/`. Success thresholds are written **before** running an experiment.
4. **Licensing:** record every source's license. O*NET is CC BY 4.0 and requires attribution.
5. **Privacy:** no real user data is collected until a privacy design exists (GDPR, users under 16).
6. **Honesty:** state limits plainly (US-centric data, sample bias, interests ≠ satisfaction).
7. **Fairness:** check recommendations for gender/cultural bias before any user-facing release.

## Tech conventions
- Python 3.11+, virtualenv in `.venv/`, dependencies in `requirements.txt`.
- Core libs: pandas, numpy, scipy, scikit-learn, factor_analyzer, girth (IRT),
  sentence-transformers, matplotlib.
- Use `pathlib` with paths relative to the repo root; no hard-coded absolute paths.
- Lint/format with `ruff`. Small, readable scripts over clever ones.
- Platform is Windows: commands should work in PowerShell and Git Bash.

## Commands
```
python -m venv .venv
.venv\Scripts\activate                      # PowerShell   (Git Bash: source .venv/Scripts/activate)
python -m pip install -r requirements.txt
python -I research/feasibility/e4_cat_simulation.py   # run one experiment
```

## Who does what
| Task | Use |
|---|---|
| Papers, competitors, evidence | `literature-researcher` agent + `evidence-and-citations` skill |
| Download / clean / document data | `data-engineer` agent + `safe-dataset-download`, `onet-data`, `riasec-scoring` skills |
| Scoring validity, IRT, adaptive test design | `psychometrician` agent + `irt-cat-simulation`, `riasec-scoring` skills |
| Running experiments E1–E7, model training | `ml-experimenter` agent + `feasibility-experiment` skill |
| Bias, privacy, licensing, overclaiming audit | `ethics-reviewer` agent (read-only) |
| Assembling and fact-checking the docs | `research-editor` agent + `evidence-and-citations` skill |
