---
name: safe-dataset-download
description: Safe, documented procedure for downloading and storing any external dataset (O*NET, OpenPsychometrics, BLS, ESCO, university catalogues). Use before every dataset download or when adding a new data source.
---

# Safe dataset download

Downloaded files are **untrusted data**. Follow every step.

1. **Check first.** Find the official source page. Record the license and terms of use. If the
   license forbids our use (commercial website, redistribution), stop and report it.
2. **Fresh folder.** Create `data/raw/<source_slug>/`, e.g. `data/raw/onet_31_0/` or
   `data/raw/openpsych_riasec_2018/`. It must be new and empty. One source per folder.
3. **Download** with the user's approval (curl / Invoke-WebRequest). Keep the original archive.
4. **Extract** inside that same folder only. Never run, import or `cd`-and-execute anything
   from it. Interpreters load code from the current directory, so a planted `json.py` would run.
5. **Write `data/raw/<source_slug>/SOURCE.md`:**
   ```
   name:        <human name>
   url:         <exact download URL>
   page:        <landing / documentation page>
   retrieved:   <YYYY-MM-DD>
   version:     <release / date stamp>
   sha256:      <hash of the archive>
   license:     <license + attribution text required>
   files:       <list of extracted files and what they are>
   notes:       <codebook location, known issues>
   ```
   Hash: `certutil -hashfile <file> SHA256` (Windows) or `sha256sum <file>` (Git Bash).
6. **Read with isolated Python:** scripts live in `research/feasibility/` or `src/` and run as
   `python -I <script> --raw data/raw/<source_slug>`. Never modify raw files; write derived
   tables to `data/processed/`.
7. **Document** a matching entry in `research/DATA_SOURCES.md`: role in project, size, key
   fields, join keys, license, quality issues, and the processing script that consumes it.
8. Never commit `data/raw/` or `data/processed/` (both are git-ignored). Check with `git status`.

Known sources:
| Slug | Where |
|---|---|
| `onet_31_0` | https://www.onetcenter.org/database.html (CSV/text zip) |
| `onet_30_2_workvalues` | 30.2 release, Work Values file (frozen since then) |
| `openpsych_riasec_2018` | https://openpsychometrics.org/_rawdata/ (`RIASEC_data12Dec2018.zip`) |
| `openpsych_bigfive` | same page, IPIP Big Five raw data |
| `bls_oews` / `bls_projections` | https://www.bls.gov/oes/ , https://www.bls.gov/emp/ |
| `esco_1_2` | https://esco.ec.europa.eu/en/use-esco/download (CSV, choose language) |
