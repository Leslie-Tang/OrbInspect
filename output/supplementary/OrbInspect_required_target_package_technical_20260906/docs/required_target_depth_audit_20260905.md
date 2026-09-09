# Required-target depth 1–6 diagnostic audit

## Design and evidence boundary

The requested extension evaluates rollout depths one through six on the same 12 validation scenarios archived in `data/results/20260905_101500_required_target_confirmation/`. The diagnostic output is `data/results/20260905_100500_required_target_depth_diagnostic/`. Scenario identities, seeds, available candidates, weights, nine prescribed target IDs, 14-action budget, graph, and stage costs must match the confirmation inputs. No scenario may be removed or replaced after its outcome is known.

Depth three was fixed before the confirmation campaign. Depths four through six were added in response to the subsequent user request. The six-depth sweep is therefore a post-confirmation diagnostic, not a prospectively predeclared depth-selection exercise. It does not change the confirmation's main-method results, target definitions, or evidence status. The directory name is an artifact identifier; actual freeze and execution times in the manifest establish chronology.

The experiment uses model-based rollout ADP and the existing deterministic greedy leaf policy. It does not fit a neural critic, train DRL, rerun HCW propagation, certify the full graph with an exact oracle, or execute a new ROS mission.

The diagnostic was frozen at `2026-09-05T10:07:46.071662+00:00`. Independent pre-run verification found the 12 scenario records, including their ordering, byte-equivalent in content to the confirmation validation subset. The graph and required-target manifest are byte-identical to the source campaign, and all eight frozen input hashes and five source hashes match.

## Correct comparison cohorts

| Quantity | Required cohort and interpretation |
|---|---|
| Required-mission success | Every one of the 12 original validation scenarios at each depth; completion means all nine fixed required IDs |
| Mean realized graph cost and delta-v across depths | The same intersection of scenarios completed at all six depths; report the intersection size |
| All-scenario penalized graph cost | All 12 scenarios; retain the fixed `J + 500 × missing fraction + 500 × failure` score and state that its penalties are not physical costs |
| Runtime | All 12 scenarios per depth, with median and preferably range or upper quantile; any successful-only timing is a separately labeled cohort |
| Safety-screen count | All 12 scenarios; specify whether separately timed base construction is excluded from the counter |
| Safety and target identity | Reconstruct every chosen edge and observation mask, including partial or empty failed routes |

A mean graph cost over each depth's own successful subset can change because the subset changed. A mean that substitutes zero cost for an unsuccessful empty route can make failure appear economical. Neither is an adequate cost-versus-depth comparison. The fixed common-success cohort avoids both ambiguities, while the all-scenario completion and penalty rows retain failures.

The diagnostic executes one plan at a time in ascending depth order, with a checkpoint after every plan. Each reported online time includes preliminary greedy-base construction and ADP planning; ADP safety-screen counts omit the preliminary base call. There is one timing observation per scenario-depth, so background scheduling and thermal variation remain uncontrolled. `process_peak_rss_bytes` is the running process's cumulative memory high-water mark; it is not an isolated per-plan memory measurement. `modeled_additional_exposure_time_s = 0` describes the model's lack of additional dwell overhead and must not be interpreted as a claim that a physical camera needs no exposure time.

The three visibility-deficient validation scenarios remain unsuccessful at every depth. Their empty-route cost is zero accumulated expenditure, not zero-cost successful inspection. Their clearance and peak-input values remain unavailable. Passing the union-of-available-views condition is a necessary visibility condition only; a completion route provides the separate constructive feasibility witness.

## What the theory supports

The manuscript's finite-graph Bellman prefix uses the complete deterministic base-policy cost as a terminal value, with infinite value for failed completion. Under exhaustive action evaluation, fixed masks and edge records, deterministic tie-breaking, the no-revisit rule, and the decreasing horizon, a finite prefix-plus-base certificate remains viable under replanning. When the greedy base completes, the realized fixed-depth rollout cost is bounded by its rollout value and by the base-policy cost.

Increasing the exact prefix can provide a nonincreasing approximate value at a fixed state. This does **not** establish a monotone sequence of realized costs for policies that repeatedly rebuild different-depth trees. The deeper and shallower policies can choose different first actions and visit different states; the separate bounds `J_d ≤ Vhat_d ≤ V_mu` do not compare `J_(d+1)` directly with `J_d`. A nonmonotonic realized-cost row is therefore not, by itself, a theorem violation or an implementation error. The diagnostic must retain such outcomes rather than smooth or reorder them.

This distinction already has an observed example in the frozen confirmation: `required09_validation_004` has realized cost 135.723185 at depth one and 137.738263 at depth two. Both routes complete the same fixed requirement.

Nor does depth six certify optimality: a remaining greedy leaf completion can still approximate the residual problem. Exhaustive reduced-graph recursion has a different scope from a finite-prefix rollout. Existing exact/reduced unit tests are implementation evidence on their stated small problems, not new full-graph oracle results for these 12 scenarios.

## Interpreting depth three

The appropriate claim is that depth three is the fixed operating point used by the main confirmation, with its computation–cost balance examined afterward. A practical justification can compare marginal graph-cost improvement beyond depth three with runtime and safety-screen growth on the same scenarios. It should state the measured cost trade-off and platform, not claim a universally optimal depth, an onboard deadline guarantee, or a depth selected without access to these diagnostic outcomes.

If later depths give lower cost, disclose the improvement even when keeping depth three as the manuscript's main method. If their extra computation is modest, a strong claim that depth three is the uniquely best balance would not follow. The user's choice to retain or change an operating point would be a separate decision requiring a correspondingly labeled new evaluation; this diagnostic does not silently replace the already frozen confirmation.

## Completed diagnostic and practical interpretation

All 72 plans completed. Every depth completed the same nine of 12 validation scenarios. The remaining three scenarios lack available observations for a required item, and the requirement denominator was not reduced. Cost and delta-v means below use those same nine completed scenarios; median online times and mean safety-screen counts include all 12 scenarios.

| Depth | Complete | Mean graph cost | Mean delta-v (m/s) | Median time (s) | Time / depth 3 | Mean ADP safety screens |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | 9/12 | 135.714329 | 16.483699 | 0.027213 | 0.026961 | 7,131.833 |
| 2 | 9/12 | 133.449700 | 16.207567 | 0.220704 | 0.218656 | 65,928.250 |
| 3 | 9/12 | 118.520436 | 14.384975 | 1.009366 | 1.000000 | 322,349.000 |
| 4 | 9/12 | 115.271611 | 13.988316 | 4.675955 | 4.632565 | 1,527,408.167 |
| 5 | 9/12 | 115.271611 | 13.988316 | 17.660148 | 17.496271 | 5,757,081.000 |
| 6 | 9/12 | 115.271611 | 13.988316 | 53.013305 | 52.521370 | 17,454,611.083 |

Depth three reduces mean common-cohort graph cost by 12.67% relative to depth one and 11.19% relative to depth two. Depth four obtains a further 2.741% reduction relative to depth three at 4.633 times its median online time. Depths five and six produce exactly the same per-scenario routes, success flags, graph costs, and delta-v as depth four, while increasing median time to 17.496 and 52.521 times that of depth three. Mean safety-screen counts increase by factors of 4.738, 17.860, and 54.148 from depth three to depths four, five, and six.

These results support depth three as a practical lower-computation operating point in the existing confirmation and disclose the additional improvement available at depth four. They do not make depth three cost-optimal: depth four is empirically better on mean cost here. Nor does the depth-four-to-six plateau prove global graph optimality. The diagnostic changes the explanation of the operating point, not which policy generated the primary test and shifted results.

## Independent numerical audit findings

The independent audit reconstructed all 72 rows and 471 selected-edge uses from the copied graph and scenarios. Required-item masks and missing IDs, all coverage denominators, graph cost including 0.05 per action, delta-v, nominal duration, edge clearance and acceleration, passive audit conditions where present, no revisits, action budget, completion flags, availability bounds, and penalty scores all matched. No selected unsafe edge or numerical discrepancy was found. All six depth groups contain the same 12 scenario identities exactly once; the common-success cohort is the same nine identities recorded in the summary. Recomputed aggregate cost, delta-v, penalty, median timing, and evaluation-count statistics match the archived summary.

All 36 new depth-one through depth-three rows were compared with the original confirmation validation rows. Every original non-timing field matches, including routes, masks, costs, completion flags, and safety-screen counts. Timing values are new measurements and are intentionally not required to match. The final eight frozen input hashes and five source hashes still match their recorded values.

The primary confirmation records were independently compared byte for byte with the preserved package at `output/supplementary/OrbInspect_required_target_package_20260905/data/results/20260905_101500_required_target_confirmation/`. Both `raw/scenario_results.csv` and its `raw/heldout_results.csv` alias are unchanged, with SHA-256 `335ec2b4e176e8425a0e30fea30a31f859ef07fa413c2a7c7472ca054988f068`. The original `raw/validation_depth_results.csv` is also unchanged, with SHA-256 `f56b3246530fa8e720425b3f2ee40ac58876583bc82830c041182f13b5f0488e`. Thus the existing 400 test/shifted method rows and 36 confirmation depth-validation rows were preserved while the new diagnostic ran.

The final audit therefore found no discrepancy and established that the main test/shifted evidence remained unchanged while the requested post-confirmation depth diagnostic was added.
