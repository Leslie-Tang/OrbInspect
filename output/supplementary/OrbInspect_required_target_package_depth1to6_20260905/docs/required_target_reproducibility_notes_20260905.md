# Required-target ADP revision: evidence and reproducibility notes

This document accompanies the IEEE manuscript revision that makes completion of prescribed inspection items the mission requirement while retaining approximate dynamic programming (ADP) as the main algorithmic contribution. The experiments use the existing corrected, HCW-audited candidate graph. Fresh scenario seeds create new availability and priority perturbations; they do not create independent spacecraft geometries or a new flight experiment.

## Evidence lineage and status

| Artifact | Role in the revision | Status |
|---|---|---|
| `data/results/adp_future_full_transform_radius080_20260812/raw/hcw_graph.json` | Corrected source graph: 24 candidate viewpoints, 41 candidate-observable target samples, 576 archived directed transfers including initial transfers | Existing graph reused by both required-target campaigns |
| `data/results/20260905_093000_required_target_adp/` | First required-target campaign: nested 6-, 9-, and 12-item profiles; 50 test and 30 shifted scenarios per profile; 12 depth-sensitivity scenarios per profile | Completed; retained in full as development and sensitivity evidence |
| `data/results/20260905_101500_required_target_confirmation/` | Fresh confirmation using the same nine prescribed items and newly frozen seeds, with one-step ADP and a local-search baseline initialized by that ADP route | Frozen at `2026-09-05T09:43:18.172764+00:00`; completed at `2026-09-05T09:45:42.810915+00:00`; 400 evaluation rows and 36 depth-validation rows |

The source graph SHA-256 is `e90f40f0aaf87464ad5b5ef6b39979aa3c5f0b7049fe0ec17ad5e5b1a19b0af2`.

The first campaign was frozen before its own evaluation at `2026-09-05T09:32:41.812336+00:00`. It contains 276 unique scenario seeds: 240 evaluation scenarios and 36 validation scenarios. Its 1,200 evaluation rows cover five methods, and its 108 validation rows cover depths one, two, and three. No scenario was rejected because visibility was insufficient or a base policy failed. Five frozen input hashes and three implementation hashes accompany the campaign.

The first campaign revealed that the deterministic required-aware greedy constructor failed every scenario of the primary nine-item profile. Consequently, fixed-suffix rollout and local search that required its completed incumbent did not supply successful primary comparisons. This is preserved evidence about the constructor and its dependent methods. It does not establish a resource-saving advantage over an independently successful baseline. The fresh confirmation campaign addresses this comparison limitation with stronger, explicitly documented route initialization. It must be described as a new campaign motivated by development findings; its outcomes must not be substituted into the first campaign's frozen records.

The confirmation freezes 92 scenarios: 50 test, 30 shifted, and 12 validation scenarios. It scans the previous 362 archived seed identities for collisions. Its main comparator is `seeded_local_search`: three audited local-improvement passes initialized by a successful one-step ADP route. A failed one-step seed leaves this comparator without a certified route. `one_step_adp` is also reported separately. Both are ADP-based comparators, so this comparison cannot establish generic superiority over non-ADP planning. Depth-three ADP receives no one-step fallback. The primary endpoint is the paired all-scenario penalized graph-cost difference; completion and joint-success graph-cost/delta-v comparisons are secondary endpoints. These definitions precede confirmation evaluation.

Depth three was carried forward from previous development. The first campaign's depth sensitivity does not retrospectively select it. No result establishes a trained deep-reinforcement-learning policy: the evaluated contribution is model-based, safety-shielded graph ADP with an explicit completion policy.

## Required items, geometric scope, and denominators

The requirements are synthetic benchmark inspection items, not verified ISS critical components. The graph's 41 candidate-observable IDs and the coordinates of all 90 deterministic mesh samples were the only inputs to requirement selection. Selection did not use scenario node inventories, old routes, test outcomes, component-criticality labels, or defect locations.

Three equal-width slabs partition the longest axis of the 90-sample mesh extent, which is the model's z axis. Within each slab, selection begins with the candidate-observable sample nearest its normalized geometric centroid and adds samples by deterministic farthest-point sampling. The nested profiles contain two, three, or four items per slab. Normalization uses the extent along each coordinate; the manifest records exact slab boundaries and selected IDs. These slabs are model-coordinate regions, not validated spacecraft component boundaries or flight-frame axes.

The primary nine-item set is fixed across its scenarios and the confirmation campaign:

| Geometric region | Required target IDs |
|---|---|
| z slab 1 | `mesh_00055`, `mesh_00052`, `mesh_00059` |
| z slab 2 | `mesh_00007`, `mesh_00001`, `mesh_00079` |
| z slab 3 | `mesh_00033`, `mesh_00015`, `mesh_00019` |

Its archived 41-target bit mask is `275750586889`. Bit positions use the exact ordering in `raw/hcw_graph.json`; an integer mask must not be interpreted using a newly sorted or shortened target list.

Four quantities remain distinct:

1. **Required-item completion:** observed required IDs divided by the fixed 6, 9, or 12 prescribed IDs. A successful required-only mission has ratio one. A failed mission remains in the scenario denominator.
2. **Mission success rate:** completed missions divided by every sampled scenario in that split. This is not synonymous with required coverage on successful routes.
3. **Background coverage:** the priority-weighted fraction of all 41 candidate-observable samples observed by the route; the corresponding unweighted fraction uses a denominator of 41.
4. **Whole-sample coverage:** observed samples divided by all 90 mesh samples, including the 49 samples not observable from the archived candidate set. This is a sample fraction, not continuous physical surface-area coverage or defect-detection probability.

Weights are randomized for background reporting and the 80% coverage-only diagnostic. They do not change the unweighted prescribed-item denominator. Requirements stay fixed under candidate dropout. The union of available candidate masks gives only a necessary visibility condition. Missing a required item from this union proves that this candidate inventory cannot satisfy that requirement. Passing the condition does not certify a safe, budget-feasible route.

## Completed first-campaign results and interpretation

| Required profile | Test ADP3 completion | Test visibility-available count | Shifted ADP3 completion | Shifted visibility-available count |
|---|---:|---:|---:|---:|
| 6 items | 40/50 | 40/50 | 10/30 | 11/30 |
| 9 items | 37/50 | 37/50 | 10/30 | 10/30 |
| 12 items | 38/50 | 38/50 | 10/30 | 10/30 |

Every successful route satisfies every prescribed item. The primary profile completes all scenarios passing the necessary visibility condition. The six-item shifted profile includes one additional failure despite available visibility; it is a failure to obtain the planner's completion certificate, not a proof of graph infeasibility.

Primary-profile greedy, fixed-suffix, and incumbent-dependent local-search completion counts are all zero. Their paired successful cost cohorts are empty and must be reported as unavailable. Across the first campaign, the only scenario with a successful greedy base is `required12_ood_003`. This means empirical checks of the base-policy cost bound have little support in this campaign; absence of a bound violation must not be presented as a broad successful-cost comparison.

The first campaign's primary depth sensitivity completes all 12 scenarios at each depth. Mean graph costs for depths one, two, and three are respectively 136.266449, 135.086962, and 113.998416. These are sensitivity results on a common fixed graph and scenario set, separate from the confirmation comparison.

## Fresh confirmation results

Depth-three ADP completes 43/50 test scenarios and 9/30 shifted scenarios. One-step ADP and its seeded local-search comparator each complete 43/50 test and 8/30 shifted scenarios. Each completed mission covers all nine fixed requirements. These percentages describe mission success across all sampled scenarios; they do not replace the 100% required-item completion criterion within an individual successful mission.

The primary paired all-scenario penalized-cost difference, depth-three ADP minus seeded local search, is −12.255743 on the test split, with the archived bootstrap 95% interval [−14.154833, −10.212206]. The shifted difference is −31.999060 with interval [−91.494203, −1.240598]. The latter includes the effect of one additional completed mission and therefore must not be interpreted solely as a maneuver-resource improvement.

On the 43 jointly successful test scenarios, the mean paired graph-cost difference is −14.250863 and the mean paired percentage reduction is 10.9715%. The mean paired delta-v difference is −1.743769 m/s. Depth-three ADP has lower cost in 40 cases and higher cost in three. On the eight jointly successful shifted scenarios, the mean cost difference is −9.890342 and the mean paired percentage reduction is 7.5316%, with seven lower-cost cases and one higher-cost case. These are empirical improvements over this ADP-seeded local-search implementation, not a theorem that depth three dominates every shallower or locally improved policy.

The canonical confidence intervals in these notes come from the archived runner and its frozen bootstrap settings: 10,000 replicates with seed 60935 for confirmation. The figure and table generators now use the same settings. The generated paired table and `raw/manuscript_statistics.json` were checked against the confirmation summary and have matching paired means, cohort counts, and interval endpoints; the earlier bootstrap-seed mismatch is resolved. Percentage reduction averaged across pairs is distinct from percentage reduction computed from two aggregate means. In particular, the manuscript's 11.05% maneuver delta-v reduction is the ratio-of-means reduction from 15.777136 to 14.033367 m/s, whereas the 10.9715% figure above is the mean paired percentage reduction in graph cost.

## Costs, timing, and missing values

| Field | Meaning and units |
|---|---|
| `graph_cost` | Sum of archived weighted transfer costs plus the configured action charge of 0.05 per selected transfer; an objective score, not propellant mass |
| `total_delta_v` | Sum of archived transfer delta-v, in m/s |
| `min_clearance` | Minimum archived clearance along selected transfers, in m, using the archived collision-model definition |
| `peak_input` | Maximum selected-transfer acceleration norm, in m/s² |
| `selected_count` | Number of chosen observation/transfer nodes; routes obey the no-revisit and 14-step limits |
| `mission_duration_s` | Selected transfer count multiplied by the nominal 90 s transfer duration; does not add separate exposure, settling, or communication overhead |
| `online_time_s` | Host wall-clock planning time, in s; consult campaign-specific initialization accounting |
| `safe_action_evaluations` | Planner edge-screening count; not a new HCW trajectory propagation count |
| `coverage`, `required_coverage`, `inspectable_sample_coverage`, `whole_sample_coverage` | Fractions in [0, 1], not percentages |

The first-campaign evaluation score is `graph_cost + 500 × missing_required_fraction + 500 × failure_indicator`. These two penalty coefficients were set before evaluation to permit an all-scenario numerical comparison. They are arbitrary objective-score weights, not physical mission-loss costs. Completion counts and joint-success resource comparisons are needed alongside this score. Changing these coefficients changes the score without changing any route.

First-campaign timings include construction of the shared deterministic base route before each method. For non-incumbent methods, `safe_action_evaluations` reports the subsequent planner's own count and omits that separately timed base construction. Thus this count is not the total timed computation. For the incumbent, the returned count belongs to the base route itself. Confirmation timing and screening counts must likewise be interpreted using its explicit seeding fields and implementation; do not compare counts as though all route-initialization work were included automatically.

Confirmation `online_time_s` includes the greedy-base construction and, for seeded local search, both one-step ADP seeding and the subsequent local search. Its `seed_time_s` isolates the one-step computation, while `base_policy_time_s` isolates the greedy constructor. `safe_action_evaluations` for seeded local search reports the local planner's count only and excludes both initialization stages; for the one-step method it reports the one-step planner's count. `base_*` fields always refer to the original greedy policy. `seed_route_node_ids`, `seed_graph_cost`, and `seed_success` refer to one-step ADP only in `one_step_adp` and `seeded_local_search` rows. Other methods have empty/`NaN`/false seed placeholders that mean not applicable, not a tested failed seed. The seed route must remain reproducible from its target identities and audited edges.

First-campaign timings were measured sequentially on an Apple M4 workstation with macOS 26.6.2, Python 3.14.0, and NumPy 2.3.4. They are offline workstation measurements, not ROS 2 scheduling measurements or flight-computer guarantees. Failed certificates may terminate quickly; an all-scenario median, particularly under shifted availability, can therefore be smaller than the median over successful missions.

An empty route has zero accumulated transfer cost and delta-v, but its clearance and peak-input values are `NaN` because no selected transfer exists. `NaN` in a joint-success comparison means the cohort is empty. It must not be replaced with zero, interpreted as a safe physical measurement, or used as evidence of equal performance. Python's JSON writer may serialize this marker as `NaN`; strict JSON consumers should map unavailable numeric values to `null` and retain the cohort count. CSV booleans are `True`/`False`; routes and missing target lists are semicolon-delimited. A missing required-ID list is empty only when all required IDs were credited.

## Verification and reproduction

The independent audit of the first campaign reconstructed all 1,200 evaluation rows from the archived graph and scenario manifests. It verified route membership, no revisits, the step budget, target-mask unions, required-item lists, missing IDs, all three coverage denominators, transfer cost plus action charges, delta-v, nominal duration, minimum clearance, peak acceleration, safety predicates, failure scores, success flags, availability bounds, and aggregate counts. All five input hashes and three implementation hashes matched, all 276 scenario seeds were unique, and the target table contained exactly 90 rows with 41 candidate-observable entries. No discrepancy was found.

The same independent reconstruction audited all 400 confirmation evaluation rows and all 160 rows carrying one-step seed metadata. Six frozen input hashes and four implementation hashes matched. All 92 confirmation seeds were unique and disjoint from the first campaign, and the nine-item mask and profile record were copied unchanged. Seed routes in seeded local-search rows matched the corresponding one-step method routes, seed costs and success flags matched their archived edges and masks, and reported total times included the separately reported base and seed times. Route, metric, safety, availability, and aggregate-count checks found no discrepancy. The audit is an independent reconstruction from existing graph records, not a rerun of HCW propagation or ROS execution.

The benchmark's three focused tests check nested geometry-only requirements, retention of an all-node-dropout sample, and prevention of required-completion credit when an 80% background-coverage route misses a prescribed item. Core-planner and execution tests are recorded separately. Existing exact and reduced-graph unit tests support implementation behavior on those explicitly constructed problems; they are not a new exact-oracle campaign on the complete required-target graph and do not establish global optimality of the reported routes.

For the first campaign, use the frozen YAML, required-target manifest, scenario inventory, graph, and corresponding source hashes. The original runner is `OrbInspectLatex/scripts/run_required_target_study.py`; its `freeze`, `validation`, and `evaluation` commands are separate so input records exist before evaluation. New executions must use a new timestamped output directory rather than overwrite either archived campaign. Future runs can differ in wall-clock timing while retaining deterministic routes under the same interpreter, inputs, and implementation.

The confirmation runner is `OrbInspectLatex/scripts/run_required_target_confirmation.py`, with the same three-stage command sequence and its own frozen YAML. It imports the original runner's shared geometry/scenario/statistical helpers. Its freeze manifest therefore hashes both runners, the planner, the archived-study interface, and six frozen input files. Its copied target-coordinate table retains the earlier 6- and 12-item annotation columns as provenance; the confirmation's `required_targets.json` contains only the nine-item evaluated profile.

Graph-level accepted visibility is inherited from the archived camera and collision models. This campaign does not create a ROS bag, spacecraft camera image, defect-detection experiment, or flight result. Empty `rosbag/` and `videos/` directories document this boundary. Any later exported route is an execution input until a new run supplies accepted observation-ID logs. Existing ROS demonstrations belong to their original mission and cannot be relabeled as execution of these new requirements.

## Deposit and author actions

The reproducibility package must retain both campaigns, their manifests and raw results, and the scripts and source versions needed to reproduce each result. The original first-campaign evidence must remain accessible after the confirmation campaign becomes the main numerical comparison.

No public DOI or repository-wide license is asserted here. The author must choose and add the repository-level license, verify third-party asset terms, and obtain a persistent archive identifier before public deposit. A local directory or a proposed repository URL is not evidence that deposition has occurred. This note does not grant rights in NASA-derived or other third-party assets.
