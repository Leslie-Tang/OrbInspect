# Redundant-viewpoint feasibility pilot

New viewpoint graphs on the same ISS mesh, with the original nine required IDs,
dynamics, camera and safety limits. All generated scenarios are retained.
Feasibility was certified independently before ADP evaluation. No manuscript figures changed; the later local manuscript revision uses the derived benchmark.

The primary planner success-rate analysis uses the independently certified
all-solvable subset: 59 cases (3 reference, 30 nominal and 26 shifted). The four
shifted cases failing the visibility certificate remain in the separate stress
test inventory. See [the materialized benchmark](raw/solvable_benchmark_summary.json)
and [the completed review](review.md).

| Split | Total | Independently feasible | Proven infeasible | Unresolved | Proven optimal |
|---|---:|---:|---:|---:|---:|
| reference | 3 | 3 | 0 | 0 | 0 |
| nominal | 30 | 30 | 0 | 0 | 9 |
| shifted | 30 | 26 | 4 | 0 | 18 |

| Split | Method | Complete / all | Complete / independently feasible | Median time (s) | Mean gap to proven optimum (%) |
|---|---|---:|---:|---:|---:|
| reference | incumbent | 1/3 | 1/3 | 0.001 | -- |
| reference | one_step_adp | 3/3 | 3/3 | 0.048 | -- |
| reference | adaptive_rollout_adp | 3/3 | 3/3 | 4.836 | -- |
| reference | independent_milp | 3/3 | 3/3 | 15.007 | -- |
| nominal | incumbent | 13/30 | 13/30 | 0.001 | 28.98 |
| nominal | one_step_adp | 30/30 | 30/30 | 0.046 | 4.40 |
| nominal | adaptive_rollout_adp | 30/30 | 30/30 | 4.173 | 0.86 |
| nominal | independent_milp | 30/30 | 30/30 | 15.007 | 0.00 |
| shifted | incumbent | 19/30 | 19/26 | 0.001 | 19.67 |
| shifted | one_step_adp | 24/30 | 24/26 | 0.035 | 7.80 |
| shifted | adaptive_rollout_adp | 26/30 | 26/26 | 2.005 | 1.01 |
| shifted | independent_milp | 26/30 | 26/26 | 5.180 | 0.00 |

## Interpretation

Optimality-gap means use completed cases with a proven independent optimum; denominators
can differ by method. Inspect paired case rows before claiming comparative savings.
Zero completion on a time-limited run means no completed route was returned within the budget.
A time limit without a checked witness is never labeled infeasible.

Geometry/feasibility scaling gate passed: **True**.
The gate was frozen before generation and does not depend on ADP outperforming any comparator.

## Output provenance

Graph and source hashes are in `config_snapshot/`. Every generated viewpoint and rejected
candidate attempt, directed edge audit, and sampled HCW state/control is retained in `raw/`.
The six standard CSVs materialize completed offline routes. Camera exposure is credited
under the existing stabilized-view assumption; no ROS, physical trial, or video is claimed.

## Limits

- Same ISS geometry, nine targets and start state across graphs.
- One timing measurement per method-case pair.
- The pilot is development evidence, not an independent confirmation.
- Physical closed-loop execution and ROS recording were not performed.

## Post-run review

See [the completed interpretation and audit](review.md) for paired comparisons, exact gap denominators, limitations and the next experiment. The JSON time-limit counts include 32 MILP runs with feasible witnesses at the limit; none of those runs is called optimal.
