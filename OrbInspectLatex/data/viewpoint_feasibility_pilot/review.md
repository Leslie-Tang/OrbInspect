# Viewpoint feasibility pilot: completed review

The pilot supports a larger, separately frozen confirmation using redundant viewpoints. Depth-three ADP completed every independently feasible case. The four remaining failures were impossible in their available viewpoint libraries because all views of a required target had been removed. This does not prove impossibility in continuous space.

The experiment contains three newly sampled 33-view graphs on the same ISS geometry. Each required target has at least three valid views before dropout. All 63 generated cases were retained: three reference, 30 nominal and 30 shifted cases.

## Primary all-solvable benchmark

For planner success-rate reporting, the independently certified feasible cases
define a 59-case all-solvable benchmark: three reference, 30 nominal and 26
shifted cases. This selection uses only the independent certificate, which was
completed before ADP evaluation; it does not use any planner outcome. On this
benchmark, the greedy incumbent completes 33/59 cases, one-step ADP completes
57/59, depth-three ADP completes 59/59, and the independent MILP returns
59/59 checked routes. The four shifted cases excluded from this denominator are
listed in [the visibility-loss stress inventory](raw/visibility_stress_cases.json)
and remain part of the full 63-case audit.

The derived machine-readable benchmark and result files are
[solvable_benchmark_summary.json](raw/solvable_benchmark_summary.json),
[solvable_benchmark_results.csv](raw/solvable_benchmark_results.csv), and
[solvable_benchmark_manifest.json](raw/solvable_benchmark_manifest.json).

| Method | Nominal completion | Shifted completion | Nominal median time (s) | Shifted median time (s) |
|---|---:|---:|---:|---:|
| Greedy base policy | 13/30 | 19/30 | 0.001 | 0.001 |
| One-step ADP | 30/30 | 24/30 | 0.046 | 0.035 |
| Depth-three ADP | 30/30 | 26/30 | 4.173 | 2.005 |
| Independent MILP | 30/30 | 26/30 | 15.007 | 5.180 |

Independent certification found 30/30 nominal and 26/30 shifted cases feasible, with no unresolved cases. Depth-three ADP also completed all three reference cases; its completion on the independently feasible set was 59/59. One-step ADP missed two feasible shifted cases.

## Cost and timing evidence

An independent optimum was proven for 27 cases: nine nominal and 18 shifted. Depth-three ADP's mean relative gap across these cases was 0.96%. The split means were 0.86% (n=9) and 1.01% (n=18). These optima concern the finite graph objective and its 14-observation budget.

Depth-three ADP did not have the lowest cost in every case. The independent MILP returned a lower mean graph cost in both perturbed splits. It reached its nominal 15-s limit in 32 cases (three reference, 21 nominal, eight shifted), returning a checked feasible route in every such case; those 32 costs are not proven optimal. There were no ADP timeouts. Solver termination and reporting can slightly exceed the requested 15 s. Each case was timed once; the MILP certification phase preceded the shuffled greedy/ADP evaluations, so these timings are pilot implementation measurements.

| Comparator | Split | Jointly complete cases | Mean ADP minus comparator cost | ADP wins / ties / losses |
|---|---|---:|---:|---:|
| Greedy base policy | nominal | 13 | -12.875 | 13 / 0 / 0 |
| One-step ADP | nominal | 30 | -5.493 | 20 / 7 / 3 |
| Independent MILP | nominal | 30 | 0.150 | 8 / 6 / 16 |
| Greedy base policy | shifted | 19 | -20.311 | 18 / 1 / 0 |
| One-step ADP | shifted | 24 | -7.012 | 20 / 4 / 0 |
| Independent MILP | shifted | 26 | 1.388 | 2 / 11 / 13 |

Negative paired differences favor ADP. Comparisons use only cases completed by both methods; the completion table supplies the excluded-case context. A win over MILP can occur only against its time-limited feasible route, not against a proven optimum.

## Implication for the manuscript

The earlier 43/50 and 9/30 completion counts reflected a fragile fixed viewpoint library: all 28 unsuccessful cases lacked an available view of at least one required target. Five required targets originally had only one candidate view. The new pilot addresses that observed bottleneck while preserving the old results. It changes the viewpoint library and perturbation protocol, so the two campaigns are not a paired performance comparison.

The predeclared geometry/feasibility gate passed. The next manuscript experiment should freeze the tested generation rules and all methods, then use fresh graph and scenario seeds for a larger confirmation. Retain every sampled case and report both all-case completion and completion conditional on independent feasibility. Report infeasible and unresolved cases separately, and preserve paired cost denominators. Do not tune the method on that confirmation set.

The pilot itself is development evidence. All graphs share the ISS mesh, target identities and initial state. Repeated dropout masks occur within the nominal splits (7, 9 and 10 distinct masks per ten cases), and cases share graph geometry; no population significance claim is justified by these three graphs. Camera visibility and geometric clearance use the existing geometry implementation. Independent certification means an independent route-optimization formulation, not a second geometry engine. Physical and ROS execution were not part of this pilot. The pilot run did not edit the manuscript; the subsequent local manuscript revision uses these results and preserves the approved figures.

## Audit and saved evidence

The post-run audit reconstructed 3,267 directed edge records and checked all 252 method-case rows. It also checked 66 applicable completed-base cost bounds and 208 independent lower-bound comparisons. The source, graph and scenario hashes match their frozen manifests.

- [Aggregate results](summary.md) and [machine-readable summary](summary.json)
- [All-solvable benchmark summary](raw/solvable_benchmark_summary.json)
- [All-solvable benchmark results](raw/solvable_benchmark_results.csv)
- [Visibility-loss stress cases](raw/visibility_stress_cases.json)
- [Independent audit and paired comparisons](raw/independent_audit.json)
- [Solver limit counts](raw/time_limit_counts.csv)
- [Prior confirmation audit](raw/previous_confirmation_audit.json)
- [Scenario diversity](raw/scenario_diversity.json)
- [Frozen protocol](config_snapshot/pilot.yaml)
- [Validation: Python tests, ROS packages and manuscript assets](config_snapshot/validation/validation.json)

The six standard CSVs and raw per-edge state/control arrays are retained. They describe offline planned routes with the existing stabilized-view observation assumption.
