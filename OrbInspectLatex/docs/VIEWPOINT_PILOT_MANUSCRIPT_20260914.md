# Manuscript revision for the viewpoint feasibility pilot

The local single-file manuscript now incorporates the completed pilot. Its
principal claim remains completion-certified sequencing for prescribed-target
inspection on audited finite graphs. The new evidence addresses the observed
viewpoint-availability bottleneck and supplies an independent route-optimization
comparison. The abstract and Table V now lead with a 59-case,
independently certified all-solvable benchmark; the four visibility-loss cases
remain a separate stress test, with the development boundary explicit.

## Changes

- The abstract leads with the 59-case all-solvable benchmark and its 59/59,
  57/59 and 33/59 planner success rates. It then identifies the four retained
  visibility-loss stress cases and explains the original 43/50 test and 9/30
  shifted completion counts, with the 27-case optimality-gap denominator.
- The protocol describes three 33-view graphs, deterministic geometry-based
  selection, the retained 63 cases, the independent MILP formulation, the common
  nominal 15-s budget and single-measurement timing limitations.
- The original completion discussion now identifies seven test and 21 shifted
  cases with missing required visibility, and five required targets with only
  one original candidate view. Feasibility is bounded to the available library.
- A new results subsection and Table V make the independently certified
  all-solvable benchmark the primary planner-success denominator: 59 cases,
  with 3 reference, 30 nominal and 26 shifted cases. The four visibility-loss
  cases remain in a separate stress-test inventory. Timing and paired cost
  comparisons are retained, and the MILP's 32 time-limited feasible routes are
  distinguished from its 27 proven optima.
- Discussion, limitations and conclusion distinguish the primary confirmation
  from the later development evidence, and finite-graph optimization from
  continuous-space or physical inspection.
- The complete target inventories, depth diagnostic, historical campaign and
  detailed ROS provenance are retained in a standalone two-page supplement.
- The last bibliography page is balanced using the existing publisher mechanism.
  All eight figure blocks, asset files and inclusion sizes are preserved. No
  figures were regenerated.

## Terminology and paragraph logic

| Canonical term | Meaning used in this revision |
|---|---|
| Depth-three ADP | Original rollout policy, unchanged during the pilot |
| Task-aware incumbent | Original deterministic greedy base policy |
| Development pilot | Later sampled-viewpoint experiment; separate from primary confirmation |
| Independent MILP | Independent route formulation on the same audited graph and geometry |
| Graph cost, J | Additive objective including the observation charge |
| Physical delta-v | Integrated maneuver velocity increment; distinct from graph cost |
| Feasible | A valid route exists within the available finite graph and action budget |
| Proven optimum | A solver-certified minimum, excluding time-limited incumbents |

The added protocol moves from viewpoint generation to scenario retention,
independent certification and timing. The results move from feasible denominators
to completion, cost trade-offs and audit limits. The abstract retains the existing
technical challenge-to-contribution structure. No missing results were filled by
assumption, and no new literature or external generalization claim was introduced.

## Claim-evidence map

| Claim | Evidence | Boundary |
|---|---|---|
| Original incomplete cases lack required visibility | `raw/previous_confirmation_audit.json` | Seven test and 21 shifted cases; finite library only |
| Every required target has at least three views | `raw/graph_summary.json` and each graph's masks | Before scenario dropout; same ISS mesh |
| 59-case all-solvable benchmark | `raw/solvable_benchmark_summary.json` | Three reference, 30 nominal, 26 shifted; selection precedes planner evaluation |
| ADP completes 59/59 solvable cases | `raw/solvable_benchmark_results.json` | Four visibility-infeasible cases retained in `raw/visibility_stress_cases.json` |
| 0.96% mean graph-cost gap | Successful ADP rows with independently proven optima | 27 cases: nine nominal and 18 shifted |
| Independent MILP has lower mean cost in both perturbed splits | `raw/independent_audit.json`, paired comparisons | 30 nominal and 26 shifted joint successes; timed incumbent costs included |
| Reported timing trade-off | Per-case timing and `raw/time_limit_counts.csv` | One measurement; native solver can slightly overrun nominal limit |
| 66 applicable base-cost checks | `raw/independent_audit.json` | Two ADP depths on 33 completing greedy cases |

All relative evidence paths above refer to `data/viewpoint_feasibility_pilot/`
inside the manuscript package. That directory contains the 70 audited pilot
files with manifest hashes, plus derived solvable-benchmark files and an explanatory README. The original
confirmation snapshot and figure data remain unchanged.

## Outputs and verification

The previous single-file TeX and compiled PDF are preserved in
`archive/before_viewpoint_pilot_20260914/`. The 14-page article remains one
editable `main.tex`; the moved supporting material is in standalone
`supplement.tex`. The compiled files are `build/main.pdf` and
`build/supplement.pdf`. The article is mirrored as `main.pdf`, and the dated
article and supplement PDFs are stored under `output/pdf/` in the parent
repository. `build/OrbInspectLatex_source.zip` contains the updated portable source.

Numerical, source-integrity, compilation and visual checks are recorded in
`VIEWPOINT_PILOT_MANUSCRIPT_QA_20260914.json`. The local revision changes no ROS
code or mathematical module. No new experiments, Overleaf edits or Git push were
performed during the manuscript revision.
