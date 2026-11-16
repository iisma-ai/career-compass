# 0009 — Manage the Python environment with uv
Date: 2026-11-15        Status: Accepted

## Context
The environment was a pip `.venv` with an unpinned `requirements.txt`, so a fresh install could pull different versions
than the ones E1–E7 ran with. The user asked to switch to uv.

## Options
1. Keep pip and add a pinned `requirements.txt`. That works, but there's no lockfile with hashes and no Python-version pin.
2. **uv with `pyproject.toml` + `uv.lock` + `.python-version`.** One command (`uv sync`) rebuilds the exact environment.
3. conda. Heavier, and it offers no benefit here.

## Decision
Option 2.
- `pyproject.toml` lists the direct dependencies, with lower bounds set to the versions E1–E7 used.
- `uv.lock` pins every package, and `.python-version` is 3.14 (the interpreter used so far).
- `requires-python >= 3.12`, because numpy ≥ 2.5 needs 3.12. CLAUDE.md previously said 3.11+.
- `ruff` is a dev dependency.
- The package `career_compass` is installed in editable mode (`uv_build` backend). The `sys.path` lines in the scripts are kept, so
  they still work under `python -I`.
- Run everything with `uv run python -I ...`. Add packages with `uv add`, never pip.

## Consequences
- The rebuilt environment differs from the old one only in numpy 2.5.4 → 2.5.5, regex and wrapt (a dev build was replaced
  by a release), plus ruff. Re-running E3 gave identical results apart from timing fields (log 2026-11-15).
- The old versions are kept in `docs/environment/pre-uv-freeze-2026-11-15.txt`.
- Run commands quoted in older findings files (`.venv/Scripts/python -I ...`) are left as historical records.

## Evidence
`docs/log/2026-11-15.md` (uv migration entry), `pyproject.toml`, `uv.lock`.
