# Higher-background-coverage ROS candidates

These are independently checked planning predictions for the current ROS scenario, not new ROS measurements. The confirmed run remains 77.22% weighted background coverage and 9/9 required-target completion.

Target IDs, weights, available viewpoints, visibility masks and graph safety gates are fixed. Fresh ADP plans add a background goal while retaining all nine required targets. The frozen offline study and manuscript are unchanged.

| Candidate | Observation views | Background coverage | Inspectable samples | Nominal duration with existing settling |
|---|---:|---:|---:|---:|
| Best nine-view route found in existing inventory, re-evaluated under current weights | 9 | 79.29% | 31/41 | 22.5 min |
| New ADP plan, 85% background goal | 10 | 85.50% | 34/41 | 25.0 min |
| New ADP plan, 90% background goal | 11 | 91.72% | 37/41 | 27.5 min |
| New ADP plan, 95% background goal | 12 | 95.86% | 39/41 | 30.0 min |
| New ADP plan, 97% background goal | 13 | 97.93% | 40/41 | 32.5 min |

The scenario's static observability ceiling is 97.93% (40/41 samples). The unavailable sample is mesh_00009; the 13-view route reaches this ceiling in the frozen model. This is not 100% coverage of the physical structure or the 90-sample full-mesh universe.

The 12-view candidate offers 95.86% predicted coverage and permits a regular two-by-six camera layout. All selected graph edges pass the frozen safety gates. Predicted completion must still be checked with production tracking and safety filtering, a fresh recorded ROS execution, full-mesh trajectory auditing, and synchronized camera evidence before updating manuscript results.

The configured ADP search did not find an 80%-or-higher route with a nine-observation budget. That search failure is not an infeasibility proof. Simply extending the original nine-view route can reach 83.43% with one extra observation or 89.64% with four; the larger gains require replanning the sequence.
