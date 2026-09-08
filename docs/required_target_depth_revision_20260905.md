# IEEE TAES revision: rollout depths one through six

## Completed change

The validation depth diagnostic now tests depths 1–6 rather than stopping at the primary depth-three setting. All six depths were recomputed on the same 12 confirmation validation scenarios in one sequential pass, producing 72 records. The fixed nine required target IDs, available-node sets, graph, costs, 14-action budget, and ADP implementation were unchanged. The diagnostic was frozen before execution at 2026-09-05T10:07:46.071662+00:00.

The extension is explicitly post-selection. It explains the computation–cost trade-off of the already frozen operating point; it does not retrospectively select depth three. It introduces no additional test/shifted evaluation, trained DRL policy, exact full-graph oracle, physical exposure model, or ROS execution.

## Measured trade-off

All depths complete the same nine of 12 tasks. The other three lose required visibility and remain in the completion, penalty, timing, and workload denominators. Mean graph costs use the same nine completed tasks at every depth.

| Depth | Mean graph cost | Median planning time (s) | Time / depth 3 | Mean safety screens |
|---:|---:|---:|---:|---:|
| 1 | 135.714329 | 0.027213 | 0.026961 | 7,131.833 |
| 2 | 133.449700 | 0.220704 | 0.218656 | 65,928.250 |
| 3 | 118.520436 | 1.009366 | 1.000000 | 322,349.000 |
| 4 | 115.271611 | 4.675955 | 4.632565 | 1,527,408.167 |
| 5 | 115.271611 | 17.660148 | 17.496271 | 5,757,081.000 |
| 6 | 115.271611 | 53.013305 | 52.521370 | 17,454,611.083 |

Depth three reduces mean cost by 11.19% relative to depth two and captures 84.11% of the observed cost decrease from depth one to the best mean among depths 1–6. Depth four gives another 2.741% reduction relative to depth three, at 4.633 times its median planning time and 4.738 times its mean screen count. Depths five and six give no further improvement: their per-scenario routes, costs, delta-v, and completion flags equal depth four, but their workload continues to grow.

The appropriate interpretation is a practical computational compromise, not a uniquely optimal depth. Depth four is preferable on cost alone in these cases if the extra computation is acceptable. The observed plateau does not certify exact graph optimality, and realized receding-policy costs need not be monotonic in depth.

Times describe complete-route generation in Python 3.14 on an Apple M4/macOS desktop. They include preliminary base construction, exclude graph loading and serialization, and represent one observation per scenario–depth pair. Ascending-depth order, background scheduling, and thermal effects limit timing inference. Ratios are ratios of all-case medians, not medians of paired speedups. Screen counts exclude the separate preliminary base call and provide a complementary implementation-workload measure. Raw data and the manuscript statistics file retain all-case penalty scores and timing ranges.

## Manuscript and figure changes

- The complexity discussion now points to depths 1–6.
- Experimental Protocol discloses chronology, identical-case comparison, timing scope, and the quantitative depth-three rationale.
- Table III has six depth rows, completion counts, common-cohort cost, percent cost change, planning time, screen count, and ratios relative to depth three.
- Figure 3 retains the established three-panel layout, panel dimensions, fonts, colors, circular data markers, and red depth-three square. Only the depth range/data, labels, and annotation positions were updated. The computation axes remain logarithmic. Shortened labels and relocated annotations prevent clipping or overlap.
- The ADP theory, primary test and shifted results, other figure assets, required-target mission definition, and historical ROS evidence remain unchanged.

## Evidence and verification

The versioned source is data/results/20260905_100500_required_target_depth_diagnostic/. The independent audit in docs/required_target_depth_audit_20260905.md reconstructs all 72 rows and 471 selected-edge uses. All eight frozen inputs and five source hashes pass. All 36 depth-one-to-three records reproduce the confirmation's non-timing fields exactly. The 400 primary test/shifted method records and original 36 validation records are byte-identical to the preserved earlier package.

Ten aggregation/provenance tests pass. They check shared-success cohorts, all-case computation statistics, missing/duplicate depths or scenarios, validation-only scope, and accidental mixing of methods, profiles, seeds, or target counts. The manuscript builds as 14 IEEE TAES pages with no overfull boxes or unresolved references. All 14 pages were rendered and inspected, with full-size inspection of the revised figure and table.

## Reproduction

To inspect or regenerate the depth figure/table from the completed archive:

~~~bash
python OrbInspectLatex/scripts/generate_required_target_depth_figures.py \
  --depth-study data/results/20260905_100500_required_target_depth_diagnostic
pytest test/test_required_target_depth_summary.py
~~~

Run this generator after the general confirmation table/detail generators, which preserve the older three-depth regeneration behavior. The interpretation in OrbInspectLatex/data/required_target_depth_rationale.tex is authored against the archived statistics and must be reviewed if a new run changes them.

For an independent new timing run, use a fresh result directory and preserve the archived evidence:

~~~bash
python OrbInspectLatex/scripts/run_required_target_depth_diagnostic.py freeze \
  --output data/results/<new_timestamp>_required_target_depth_diagnostic
python OrbInspectLatex/scripts/run_required_target_depth_diagnostic.py run \
  --output data/results/<new_timestamp>_required_target_depth_diagnostic
~~~

Replace the angle-bracket timestamp placeholder before executing. The runner verifies frozen inputs and checkpoints each result; rerunning the run command resumes missing rows rather than silently replacing completed measurements. Obtain new timing observations through a new freeze directory, not by treating resume as a repeat benchmark.

New deliverables use the suffix depth1to6_20260905; the previous revision remains intact.
