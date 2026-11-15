# 0002 — OpenPsychometrics data is research-only
Date: 2026-11-14 *(backfilled)*        Status: Accepted

## Context
The OpenPsychometrics 2018 RIASEC dump (48 items, about 80k clean rows) is the only large open item-level dataset we found.
It has **no stated license**.

## Options
1. Use it freely, including for product parameters. Rejected because there's no license.
2. **Use it for research only and publish only aggregates.** Ask the owner for permission before shipping anything derived from it.
3. Don't use it. That would leave no item-level data for E1–E6.

## Decision
Option 2. Raw and person-level data is never committed, and findings contain only aggregate statistics. Item parameters,
the 24-item order (0005) and the E6 models are **not shippable** until we get permission or recalibrate on our own data.

## Consequences
- This is a release blocker (ethics review 2026-11-15): we need permission or our own calibration sample.
- The sample is young, 67% female and 49% US, so it doesn't represent our target users.

## Evidence
`research/findings/e1_data_audit.md`, README "Data and attribution", `.gitignore`.
