# orbinspect_guidance

Build type: `ament_python`.

Purpose: Inspection waypoint generation and planning package.

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
