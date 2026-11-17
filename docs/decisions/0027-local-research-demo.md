# 0027 — Engine completions and a local, research-only demo page on the standard library
Date: 2026-11-17        Status: Accepted

## Context
The v1 engine (ADR 0020) lacked:
- the refine step (MODELS L1);
- the conditional wording flags (L3 soft gate, low elevation, L4 thin pool);
- the explanation inputs (L6).

There was also no way to try the flow. A product UI can't ship while release blockers are open. A local page still
helps the owner, counsellors and the ethics committee see what participants would get.

## Options
1. A web framework (Flask/FastAPI). Rejected for now: a new dependency and attack surface for a page that only runs
   locally.
2. **Python's standard `http.server`, bound to 127.0.0.1 (chosen).** No new dependency.
3. A static HTML mock-up. Rejected: it wouldn't run the real engine.

## Decision
- **Engine additions:**
  - `refine_form` (30 items; the first 24 are the v1 form);
  - `prediger` (angle projection, for wording only);
  - conditional notices `mixed_profile`, `low_interest_talk_to_someone` and `top_type_thin_pool`;
  - `Result.prediger_xy`.
- **`src/career_compass/demo.py`:** `uv run python -I -m career_compass.demo` serves http://127.0.0.1:8765.
  - **Privacy and security:**
    - nothing is stored;
    - answers travel in a POST body, and the log prints only method and path;
    - no cookies and no scripts;
    - the CSP header allows only inline styles;
    - a 20 kB body limit;
    - all text is HTML-escaped.
  - **Gender-blind:** the page asks no demographic question.
  - **Page content:**
    - question wording is read at start-up from the local OpenPsychometrics codebook (research-only, ADR 0002) and
      never committed;
    - the O\*NET attribution text is the README's;
    - all copy, family labels and help links are drafts, marked "pending counsellor review".
- **The lost-user page shows no families** and says that the guided flow is still being designed (blocker 4).

## Consequences
- **Not deployable.** The demo is a review tool and must not be put on a network, since release blockers 1–8 are
  still open.
- **Seen in testing:** an Investigative/Artistic profile gets only "extensive preparation" examples by default. This is
  the known E3 skew; the preparation filter on the form is the mitigation (MODELS L4).

## Evidence
MODELS L1, L3, L4, L6; ADRs 0002, 0006, 0014, 0015, 0020; `tests/test_demo.py`.
