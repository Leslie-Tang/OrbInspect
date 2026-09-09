# Required-target execution-accounting validation

Date: 2026-09-05.

## Scope

This report covers identity-preserving observation credit, goal handling, and
materialization of frozen graph routes as ROS replay inputs. It does not report
a new closed-loop ROS experiment. The available host is macOS (Darwin); `ros2`
and `colcon` are unavailable. No supported remote Ubuntu/Jazzy runner was
identified in the project documentation. The required Jazzy build and live
execution therefore remain unperformed for this change.

## Implemented behavior

- `observation_credit.py` stores an immutable fixed target universe, target
  weights, required target identities, goal mode and mission content hash.
- Required mode completes exactly when every prescribed target is accepted.
  Hybrid mode additionally requires the background coverage threshold.
  Coverage mode retains the existing threshold and the legacy conjunction when
  an explicit mandatory set is supplied.
- `verification_evaluator_node.py` unions each observation's target IDs only
  after its position and terminal-speed gates pass. A rejected observation
  cannot contribute target IDs or be imported through the planned cumulative
  coverage of a later accepted view. Overlapping observations do not double
  count. The existing all-observations-pass mission-success gate is preserved.
- Existing ROS `CoverageMap` fields remain unchanged. Counts are computed from
  accepted identities; additional JSON status fields carry required coverage,
  missing IDs, goal attainment and mission identity.
- `ros_route_exporter.py` preserves explicit archived routes, including
  zero-gain transit actions. It checks node availability, no revisits, action
  budget, stored edge audits, target masks, mission completion and numerical
  route metrics before exporting. Version-3 route manifests contain the fixed
  weights and requirement IDs and can be loaded without the original source
  archive. Legacy version-2 manifests recover weights only from hash-verified
  graph/scenario sources.

## Focused checks

Command (from the repository root):

```bash
PYTHONPATH=src/orbinspect_guidance:src/orbinspect_dynamics:src/orbinspect_perception:src/orbinspect_safety:src/orbinspect_utils \
  .venv-review/bin/python -m pytest \
  src/orbinspect_guidance/test/test_verification_evaluator_node.py \
  src/orbinspect_guidance/test/test_ros_route_exporter.py -q
```

Result: **16 passed**. The tests exercise terminal gate boundaries, actual node
tick logic through ROS-independent AST loading, rejected-then-accepted credit,
duplicate observations, strict required completion below 80% background
coverage, hybrid and legacy goal behavior, unknown/mismatched requirements,
portable mission metadata, preservation of per-view IDs, zero-gain transit and
rejection of altered archive masks/costs or repeated/empty routes. These are
unit and integration-logic tests, not ROS executor or transport tests.

Python compilation of all three changed runtime modules and the whitespace
diff check passed.

## Historical compatibility check

The accepted-ID union was recomputed for all **124** historical ADP/local-search
routes in `data/results/ros_verification_inputs_full_transform_radius080_20260812`.
Each route's fixed weights were loaded from its verified graph/scenario source.
With every planned observation accepted, all 124 recomputed weighted coverages
matched the corresponding archived planned coverage within `1e-12` absolute
tolerance. Thus the new accounting preserves the all-accepted historical
coverage values while correcting partial-rejection accounting.

## Replay output contract

Every new replay input bundle contains `config_snapshot/`, `raw/`, `rosbag/`,
`figures/`, `videos/`, `manifest.json`, `summary.json` and `summary.md`. The raw
directory contains all six core CSVs (`trajectory.csv`, `control.csv`,
`coverage.csv`, `safety.csv`, `planner.csv`, `mission_events.csv`) plus
`attitude.csv` and `viewpoints.csv`. Additional planned-data CSVs explicitly
identify their record basis; summaries state `execution_performed: false`.
Empty media/rosbag directories denote that execution has not occurred.

The earlier replay bundles `20260905_103000_required_target_replay` and
`20260905_104000_required_target_replay` are development exports from the
development benchmark. They are not confirmation or executed ROS evidence.

## Fresh confirmation replay

The final replay input is
`data/results/20260905_111500_required_target_confirmation_replay/`, exported
from the sealed confirmation campaign
`data/results/20260905_101500_required_target_confirmation/`.

It contains the frozen `required09_test_000` / `adaptive_rollout_adp` route
(scenario seed `202609360000`). No route was replanned or selected from a
different requirement profile during export.

| Planned or offline-checked quantity | Value |
|---|---:|
| Required target set | 9 fixed target IDs |
| Planned required completion | 9/9 (100%) |
| Planned background sample coverage | 30/41 (73.1707%) |
| Planned weighted background coverage | 77.2174% |
| Planned actions | 9 |
| Planned duration | 810 s |
| Archived graph cost | 113.4719195872 |
| Materialized velocity increment | 13.7688852945 m/s |
| Minimum archived/materialized clearance | 2.8075398733 m |
| Peak requested input | 0.0592012914 m/s² |

The explicit route target mask, strict required completion, graph cost,
velocity increment, minimum clearance and peak input passed the exporter's
archive consistency checks. Replaying its per-view target IDs through the
pure accumulator with every observation accepted produced exactly the archived
weighted coverage and all 9 required IDs. This is an offline all-accepted
accounting check, not a claim that these observations have been accepted by
physical sensing or a new ROS run.

All eight raw output-file hashes and the exporter source hash match the final
manifest. The six core CSVs are nonempty; all required directories and both
summary files exist. The summary explicitly records `execution_performed:
false`. The final source version retains the **16/16** focused test result.

Reproduction on a configured workspace:

```bash
ros2 run orbinspect_guidance ros_route_exporter \
  --source-dir data/results/20260905_101500_required_target_confirmation \
  --scenario-id required09_test_000 --methods adaptive_rollout_adp \
  --run-id <new-replay-run-id>
```

Actual closed-loop credit remains to be measured with the documented
`ros_verification.launch.py` command on Ubuntu 24.04 / ROS 2 Jazzy.
