# Candidate replacement items, v1 draft (not yet screened)

Drafted 2026-11-16 for ROADMAP milestone 1.1. **None of these items has response data yet.** Their DIF, reliability and
loadings are unknown until they are calibrated on a consented pilot sample in research mode (ADR 0014, milestones 1.0
and 1.2). The "expected risk" notes are hypotheses, not evidence. Machine-readable copy: `candidate_items_v1.csv`.

## Why these items are needed (evidence)
| Problem | Items | Evidence |
|---|---|---|
| Gender DIF \|.30\|–\|.44\| | E4 beauty salon (+.44), R3 oil rig (−.34), A7 stunts (−.34), I8 ocean-floor map (−.33), R4 electronic parts (−.32), E1 restaurant franchises (−.30) | [e2](../findings/e2_structure.md), item-level DIF (+ = women higher at equal scale level) |
| Age DIF (teens vs 25+) | S1 career guidance (−.53), R6 faucet (−.36) | e2 JSON `item_dif_age_13_17_minus_25plus_sd` |
| Weak items (excluded in E4) | R1, A7, S4 | MODELS L1; [e4](../findings/e4_cat_simulation.md) |
| Investigative is mostly biology or medicine (I1–I7), which helps explain why the items over-predict Psychology and biology fields | I1–I7 | [e6](../findings/e6_major_prediction.md) |
| Enterprising is mostly selling (E1, E2, E6, E7) | E1, E2, E6, E7 | item texts (E2 appendix) |

## Writing rules (applied to every draft)
1. **One activity per item,** in plain language at a reading age of about 12, phrased as an activity ("Repair a
   bicycle"), not a job title. This keeps the existing Likert format "How much would you like to …".
2. **Gender-neutral settings and tools** (ADR 0015). Avoid activities whose appeal rests on gendered appearance, physical
   danger or stereotyped settings, because those carry DIF in E2: salon, oil rig, stunts.
3. **Teen-appropriate:** activities a 14-year-old can picture, with no adult-only business deals (E1 franchises) or
   work that needs life experience (S1 career guidance, which had age DIF).
4. **Broaden content within each scale:** non-biology Investigative items (physics, chemistry, computing, data,
   earth science, social research) and non-sales Enterprising items (leading, starting, persuading, organising).
5. **Own wording.** Not copied from OpenPsychometrics, which has no license (ADR 0002). Check any overlap with the
   O\*NET Interest Profiler items before use. If wording matches, attribute it under CC BY 4.0.
6. **No gendered or culturally specific references:** no named sports, holidays or brands.

## Candidates
| ID | Scale | Replaces / adds | Item: "How much would you like to …" | Rationale | Expected risk (hypothesis) |
|---|---|---|---|---|---|
| R9 | R | R3 | Repair a bicycle | Hands-on mechanical task; familiar to teens | Mild male DIF possible |
| R10 | R | R4 | Build a piece of furniture from wood | Making things with tools; neutral setting | Low |
| R11 | R | R1 | Grow vegetables in a large garden | Outdoor, physical, plant-related | Could cross-load on I (plants); check |
| R12 | R | R6 | Set up the lights and sound for a concert | Technical, hands-on, in a creative setting | Could cross-load on A; check |
| R13 | R | (add) | Use a 3D printer to make replacement parts | Modern tool use | Could cross-load on I |
| R14 | R | (add) | Cook meals in a busy restaurant kitchen | Manual craft; balances gender settings | Possible female DIF; check |
| I9 | I | I8 | Find out why a chemical reaction happens | Non-biology science | Low |
| I10 | I | (I-content) | Write a computer program to solve a puzzle | Computing, analytical | Possible male DIF; check |
| I11 | I | (I-content) | Study how earthquakes and volcanoes work | Earth science, not marine-specific | Low |
| I12 | I | (I-content) | Analyse data to find out why something happens | Data and research, not biology | Could cross-load on C |
| I13 | I | (I-content) | Test how a bridge design holds weight | Physics and engineering reasoning | Could cross-load on R |
| I14 | I | (I-content) | Research how people make decisions | Social-science research, balancing the biology tilt | Could cross-load on S |
| A9 | A | A7 | Take and edit photographs | Visual creation; no physical-risk content | Low |
| A10 | A | (add) | Design a character for a video game | Modern creative medium | Possible male DIF; check |
| A11 | A | (add) | Make a short film | Creative storytelling | Low |
| S9 | S | S1 | Explain a difficult topic to a classmate | Helping and teaching, at teen level | Low |
| S10 | S | S4 | Welcome and show around a new member of a group | Helping others belong; no fitness content | Low |
| S11 | S | (add) | Listen to someone who is going through a hard time | Core S content | Possible female DIF; check |
| S12 | S | (add) | Help a community group plan an event for neighbours | Social, cooperative | Could cross-load on E |
| E9 | E | E1 | Start your own small business | Non-sales enterprising, teen-imaginable | Low |
| E10 | E | E4 | Lead a team to get a project done | Leadership, neutral setting | Low |
| E11 | E | (E-content) | Convince people to support an idea | Persuasion without selling | Low |
| E12 | E | (E-content) | Organise a campaign for a cause | Persuading and organising | Could cross-load on S |
| E13 | E | (E-content) | Negotiate a deal between two groups | Negotiation | Low |
| C9 | C | (add) | Keep a spreadsheet of a club's money up to date | Organising data; teen context | Low |
| C10 | C | (add) | Check a document carefully for errors | Accuracy, detail | Low |

There are 26 candidates: 6 R, 6 I, 3 A, 4 S, 5 E and 2 C. Extra candidates are deliberate, since some will fail screening.

## How they will be screened (plan; each step is pre-registered before it runs)
1. **Expert review:** the psychometrician agent and at least one human counsellor rate each item for clarity,
   scale fit, reading level and stereotype risk. Revise or drop items before any data is collected.
2. **Pilot (research mode, after milestone 1.0):** administer the 48 current items plus all candidates in random order,
   with an optional self-reported gender question used only for the audit (ADR 0015). The sample size is set by a
   power analysis for detecting |DIF| ≥ .30 with the E2 method.
3. **Retention bar (milestone 1.1):**
   - |gender DIF| and |age DIF| below the E2 flag of .30. Among items that pass, prefer the smallest gender DIF
     (ADR 0015).
   - Item-rest correlation ≥ .40 on its own scale, with no cross-loading above .30 on another.
   - The final 24-item form keeps 4 items per scale, and per-scale α ≥ .80 (milestone 1.2).
4. **Re-audit:** re-run DIF on the final item set (release blocker 3) and re-run E4 and E5 on the new form.

## Open questions
- Should the response scale stay at 5-point "dislike ↔ enjoy"? (Unchanged for now.)
- Spanish versions are written after the English set is fixed (v2, milestone 2.2), with forward and back translation.
