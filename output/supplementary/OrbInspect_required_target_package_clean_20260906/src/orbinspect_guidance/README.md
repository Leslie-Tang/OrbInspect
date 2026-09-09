# orbinspect_guidance

Build type: `ament_python`.

Purpose: Inspection waypoint generation and planning package.

## Required-target graph ADP

`SafeGraphProblem` has an explicit `goal_mode`: `coverage` keeps the existing
weighted-coverage goal, `required` completes all bits in a nonempty
`required_target_mask`, and `hybrid` requires both. Required-only problems may
set `goal_coverage=0.0`; weighted coverage is still reported independently.
The legacy `coverage` mode with a required mask retains its conjunctive goal.

`AdvancedSafePlanner.base_policy_plan(problem)` runs the deterministic base
used by adaptive rollout, ranking safe actions by newly covered required items
per stage cost while any required item remains. Required and hybrid missions
admit safe unvisited transit nodes even when they add no target coverage; the
finite decision budget and no-revisit rule remain enforced. Exact, rollout,
reference, and learned policies share the same completion predicate.

Plan diagnostics distinguish missing required items from weighted coverage.
`base_completion_failed` and `no_certified_completion` report heuristic failure,
not proof of graph infeasibility. The ADP cost bound is conditional on a
successful deterministic base completion and exhaustive finite-depth prefix
evaluation. The reduced-graph exact solver can separately certify feasibility.

The 26-dimensional critic interface is retained. For required goals its gap
features describe unmet required items, so checkpoints should be trained and
evaluated under the intended task specification.

## Offline result and figure workflow

Run either offline simulator first:

```bash
ros2 run orbinspect_guidance offline_coverage_planner \
  --config src/orbinspect_guidance/config/offline_coverage_planner.yaml

ros2 run orbinspect_guidance offline_planning_experiment \
  --config src/orbinspect_guidance/config/offline_planning_experiment.yaml

ros2 run orbinspect_guidance offline_adp_study \
  --config src/orbinspect_guidance/config/offline_planning_experiment.yaml
```

These commands save CSV, JSON, and Markdown results under
`data/results/<run-id>/` and do not import or call plotting code. Render figures
from a completed result directory in a separate command:

```bash
ros2 run orbinspect_guidance offline_planning_plots \
  --result-dir data/results/<run-id>
```

Pass `--figure <name>` to render one figure. The
`offline_planning_plots.py` module provides one public function per figure.
The ADP study adds standalone `adp_primary_tradeoff`,
`primary_trajectory_case_study`, `adp_policy_costs`,
`adp_component_ablation`, `adp_oracle_gap`, `adp_compute_tradeoff`, and
`adp_initial_condition` figures. The trajectory case study reads the archived
primary `trajectory.csv`, `viewpoints.csv`, and `method_comparison.csv` files.

Run only the matched component-ablation family with:

```bash
ros2 run orbinspect_guidance offline_adp_study \
  --config src/orbinspect_guidance/config/offline_planning_experiment.yaml \
  --families components
```

This family compares critic-only, critic-plus-safeguard, rollout, local-search,
no-local-search, complete-policy, and incumbent variants. Every method starts
with an empty HCW transfer cache.

## Frozen-critic validation workflow

Train once on related scenarios and evaluate a frozen critic on disjoint splits:

```bash
ros2 run orbinspect_guidance offline_adp_superiority_study \
  --graph-cache data/results/<graph-run>/raw/hcw_graph.json \
  --splits validation
```

Use validation only for model selection. Aggregate the completed validation
runs and apply the preregistered success, paired-cost, and online-latency gate:

```bash
ros2 run orbinspect_guidance offline_adp_validation_decision \
  --run-id adp_superiority_validation_decision_<date>
```

Generate the standalone decision figures only after the aggregate CSV files
exist:

```bash
ros2 run orbinspect_guidance offline_adp_superiority_plots \
  data/results/adp_superiority_validation_decision_<date>
```

The plotting module reads archived CSV files and provides one function per
figure. Test and OOD splits should remain unopened when no validation candidate
passes the complete gate.

## Required-target replay and accepted observation credit

`ros_route_exporter` emits version-3 replay manifests with a self-contained
`mission` entry for each route: the fixed target IDs and weights, required IDs,
`goal_mode` (`coverage`, `required`, or `hybrid`), coverage threshold, and a
content hash. Required mode completes only when every prescribed target is
credited; hybrid mode also requires the background coverage threshold. The
background denominator remains the full archived candidate-observable target
universe. Explicit archived routes are audited and materialized without
replanning, including any zero-gain transit observations.

```bash
ros2 run orbinspect_guidance ros_route_exporter \
  --source-dir data/results/<required-target-run> \
  --scenario-id <scenario-id> --run-id <required-target-replay>
ros2 launch orbinspect_bringup ros_verification.launch.py \
  result_dir:=data/results/<required-target-replay> \
  scenario_id:=<scenario-id> method:=adaptive_rollout_adp
```

The evaluator unions the per-observation `visible_target_ids` only after its
position and terminal-speed gates pass. Rejected observations contribute no
targets; a later accepted view cannot import earlier planned cumulative credit.
Coverage messages retain their existing fields, but inspected and new-target
counts now derive from this accepted union. JSON verification events additionally
report required coverage, missing target IDs and mission identity. Route mission
metadata is authoritative; YAML coverage settings provide the legacy fallback.
Version-2 routes require their hash-verified source graph and scenarios to recover
the original target weights; re-export a route if that source archive is absent.
The existing all-observations-pass execution-success condition is retained.

These changes support new ROS experiments; offline tests and replay exports alone
do not constitute a new closed-loop validation result. The supported build and
execution environment remains Ubuntu 24.04 with ROS 2 Jazzy.
