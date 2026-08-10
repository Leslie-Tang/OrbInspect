# OrbInspect Ubuntu / ROS 2 Handover

Prepared: 2026-08-10  
Windows workspace: `D:\论文\OrbInspect`  
Target workspace: `~/orbinspect_ros2`  
Target platform: Ubuntu 24.04.4 LTS, ROS 2 Jazzy, Gazebo Harmonic, RViz2, Python 3.12

## Material Passport

- Origin Skill: `academic-research-suite/experiment-agent`
- Origin Mode: `plan`
- Origin Date: `2026-08-10`
- Verification Status: `UNVERIFIED` — repository references were checked on Windows, but the operational ROS gates require Ubuntu
- Version Label: `ubuntu_ros_handover_v1`
- Repro Lock: `null` — the concrete Git revision, frozen result root, configurations, and required hashes are recorded below
- Upstream Dependencies: Git `3054906e1c05b07f415c8dd99365cca4567954df`; offline study `adp_future_physical_heldout_20260810`

## 1. Read This First

The offline rollout-ADP study and manuscript are complete enough to freeze. The next task is **not** to rerun or retune the offline test study. The next task is to make its frozen routes executable through the ROS 2 HCW/controller/safety stack and collect real closed-loop replay evidence.

The first Ubuntu milestone is a trustworthy closed-loop replay, not online ADP planning. The current `advanced_safe_planner_node` publishes readiness/status only; it does not execute the ADP policy online.

The governing constraints remain those in `AGENTS.md`:

- use ROS 2 Jazzy, never ROS 1 or ROS 2 Humble;
- use Gazebo Harmonic, never Gazebo Classic;
- use `ament` and `colcon`, never `catkin`;
- the ROS HCW dynamics node is the source of truth for spacecraft state;
- Gazebo and RViz2 visualize ROS state and do not propagate the spacecraft;
- Basilisk remains optional;
- parameters belong in YAML;
- preserve established interfaces where possible;
- every experiment must produce logs under `data/results/<timestamp>/`.

## 2. Repository State at Handover

| Item | State |
|---|---|
| Git branch | `main` |
| Git HEAD | `3054906e1c05b07f415c8dd99365cca4567954df` |
| Working tree | Dirty: manuscript source/build artifacts and this handover are not committed |
| ROS tools on Windows | `ros2` and `colcon` unavailable |
| Last target-Jazzy build | Predates the current rollout-ADP planner changes |
| Current manuscript | 14 pages; LaTeX build passes with no errors, undefined references, or overfull boxes |
| Manuscript PDF SHA-256 | `70294725B262D41EDA089123CD6063F324225ACB19C5300B42F0163DF84D5499` |

Before moving or changing anything, run:

```bash
git status --short
git branch --show-current
git rev-parse HEAD
```

Do not discard uncommitted files. Do not run `git reset --hard` or mass-normalize line endings. Preserve the complete `data/results/` tree and ISS mesh assets during transfer.

## 3. Authoritative Files

| Purpose | File or directory |
|---|---|
| Project constraints | `AGENTS.md` |
| General setup and launch commands | `README.md` |
| Historical phase/build record | `PHASE_STATUS.md` |
| Main manuscript source | `OrbInspectLatex/main.tex` |
| ROS-results insertion scaffold | `OrbInspectLatex/sections/ros_verification_results.tex` |
| Current final PDF | `output/pdf/OrbInspect_rollout_ADP_manuscript.pdf` |
| Frozen ADP result root | `data/results/adp_future_physical_heldout_20260810/` |
| Frozen study configuration | `src/orbinspect_guidance/config/adp_future_study.yaml` |
| Existing replay launch | `src/orbinspect_bringup/launch/demo_proposed_trajectory_validation.launch.py` |
| Existing replay node | `src/orbinspect_guidance/orbinspect_guidance/planned_trajectory_replay_node.py` |
| Replay unit tests | `src/orbinspect_guidance/test/test_planned_trajectory_replay_node.py` |
| ADP core/status node | `src/orbinspect_guidance/orbinspect_guidance/advanced_safe_planner_node.py` |

## 4. Frozen Offline Evidence

The current paper result is under:

```text
data/results/adp_future_physical_heldout_20260810/
```

Primary methods:

- proposed: `adaptive_rollout_adp`;
- primary baseline: `local_search`.

Frozen study sizes:

- 24 training scenarios;
- 12 validation scenarios;
- 30 test scenarios;
- 20 shifted scenarios (stored internally with split name `ood`).

Offline test result:

- both proposed and local search succeed in 30/30 cases;
- proposed mean physical delta-v: 11.239 m/s;
- local-search mean physical delta-v: 12.946 m/s;
- proposed reduction: 13.18%;
- paired delta-v mean difference: -1.707 m/s;
- 95% bootstrap interval: [-2.199, -1.265] m/s;
- 28 wins, two numerical ties, no losses.

Representative case used in Fig. 6:

- scenario: `test_002`;
- seed: 20733;
- proposed: 10 SOOAs, 81.79% coverage, 12.026 m/s delta-v;
- local search: 11 SOOAs, 83.82% coverage, 13.574 m/s delta-v.

Important integrity boundary: `test_002` was selected post hoc as an illustrative median-effect case. It must not be used for controller tuning. Use validation scenarios such as `validation_000` for integration tuning, freeze all execution parameters, and only then run `test_002` or any other test/shifted case.

## 5. Why the Existing Replay Launch Is Not Yet Valid for This Paper

Do not launch the current proposed-trajectory demo against the new ADP result root without modifying the input bridge. It would not validate the manuscript trajectories faithfully.

Current incompatibilities:

1. `planned_trajectory_replay_node.py` expects:

   ```text
   raw/trajectory.csv
   raw/attitude.csv
   raw/viewpoints.csv
   ```

   The current ADP result root contains:

   ```text
   raw/representative_case_trajectory.csv
   raw/representative_case_progress.csv
   raw/representative_case_manifest.json
   raw/hcw_graph.json
   raw/scenarios.json
   raw/heldout_results.csv
   ```

2. The launch defaults still point to `data/results/offline_high_coverage_experiment` and method `set_cover_cw_tour`.

3. The launch does not accept `scenario_id`, so it cannot safely distinguish multiple paired routes for one method.

4. The launch defaults to `trajectory_source:=standoff`. That path constructor projects observations onto an older safe shell and therefore changes the audited route. Paper verification must use the archived CSV trajectory directly.

5. The launch hard-codes an older initial position:

   ```text
   [0.0047007014, -105.7618622, 30.2395186]
   ```

   The frozen study initial state is:

   ```text
   [0.0, -35.0, 10.0, 0.0, 0.0, 0.0]
   ```

   Each run must load its scenario-consistent initial state from the frozen archive, not from a launch literal.

6. The launch uses a 0.03 m/s^2 acceleration limit, while the frozen paper experiment uses 0.060 m/s^2. A 0.03 limit would change tracking and realized delta-v and would not be an apples-to-apples verification.

7. Only representative-case trajectories are currently materialized. `heldout_results.csv` contains aggregate rows, not complete time histories for every test/shifted route. The full ROS campaign therefore requires deterministic export of all proposed/local routes from the frozen graph and scenarios.

8. The launch starts the HCW dynamics, controller, and safety filter unconditionally. In `publish_mode:=replay`, the replay node also publishes `/chaser/odom`; this can create two authoritative odometry publishers. The launch must conditionally separate direct replay from closed-loop execution.

9. The controller and replay node both publish a path on `/chaser/trajectory`. Choose one authoritative executed-path publisher or remap the visualization-only path so logging and RViz cannot silently mix two streams.

## 6. Required Implementation Before the First Valid ROS Run

### 6.1 Preserve the Frozen Result Root

Treat `data/results/adp_future_physical_heldout_20260810/` as read-only evidence. Do not overwrite its CSV or JSON files.

Create a new export/run root, for example:

```text
data/results/ros_verification_<timestamp>/
```

Record the source result root, source Git revision, selected scenario, method, and exporter hash in its configuration snapshot.

### 6.2 Add a Deterministic ROS Input Exporter

Prefer a dedicated exporter over weakening the stable replay-node input contract. The exporter should:

1. load the frozen `hcw_graph.json`, `scenarios.json`, and study configuration;
2. deterministically recompute or load the selected `adaptive_rollout_adp` and `local_search` route;
3. assert that success, route cost, coverage, action count, delta-v, minimum clearance, and peak input match the corresponding frozen `heldout_results.csv` row before export;
4. emit normalized `trajectory.csv`, `attitude.csv`, and `viewpoints.csv` with both `scenario_id` and `method` columns;
5. map `time_s` to the replay time field and preserve the archived controls (`ux`, `uy`, `uz`) as feed-forward acceleration fields rather than replacing them;
6. derive camera attitude from archived candidate/boresight records, not from an unrelated visual approximation;
7. write a manifest containing input/output hashes and the exact route node IDs;
8. add focused tests for schema conversion, method/scenario filtering, hashes, and frozen-metric assertions.

For the first smoke run, exporting `validation_000` and `test_002` is enough. Before confirmatory ROS inference, export all 30 test and all 20 shifted pairs.

### 6.3 Extend the Replay Node Without Breaking Existing Inputs

Add an optional `scenario_id` parameter. Filter by both method and scenario when the column exists; retain backward compatibility with older single-scenario files.

Required behavior:

- `trajectory_source:=csv` uses exported states and controls directly;
- `loop:=false` for every evidence run;
- `publish_mode:=replay` is interface/visualization verification only;
- `publish_mode:=closed_loop` uses ROS dynamics and supplies execution evidence;
- direct replay disables the HCW dynamics/controller/filter path and owns odometry;
- closed-loop replay publishes references only, while the HCW dynamics node exclusively owns odometry;
- a missing/ambiguous scenario must fail loudly rather than select the first row;
- dropped or out-of-order references must be counted and logged.

### 6.4 Move Verification Parameters to YAML

Create a dedicated verification YAML file instead of adding more launch literals. It must snapshot at least:

```yaml
mean_motion: 0.00113137
safety_margin: 2.0
max_acceleration: 0.060
terminal_position_tolerance: 0.5
terminal_velocity_tolerance: 0.05
goal_coverage: 0.80
max_sooas: 14
loop: false
trajectory_source: csv
```

Load the scenario initial state and timing from the export manifest. Do not speed up the physical trajectory by changing simulated time. Faster-than-real-time execution may use simulator real-time factor or headless simulation while preserving ROS simulation time.

### 6.5 Update the Top-Level Launch

After the exporter and loader changes, the intended interface should support commands of this form:

```bash
ros2 launch orbinspect_bringup demo_proposed_trajectory_validation.launch.py \
  result_dir:=data/results/ros_verification_<timestamp> \
  scenario_id:=validation_000 \
  method:=adaptive_rollout_adp \
  trajectory_source:=csv \
  publish_mode:=replay \
  loop:=false \
  record:=true
```

This exact command is a target interface, not a currently valid command. Implement and test `scenario_id` first.

Add an explicit run ID or ensure the logger-generated ID contains scenario and method. Resolve duplicate `/chaser/trajectory` publishers by launch condition or topic remapping, and add a launch test that checks publisher cardinality in each mode.

## 7. Ubuntu Bring-Up Sequence

Follow this order. Do not skip directly to Gazebo closed-loop replay.

### Gate A: Environment and Package Build

```bash
cd ~/orbinspect_ros2
source /opt/ros/jazzy/setup.bash

rosdep update
rosdep install --from-paths src --ignore-src -r -y

colcon build --symlink-install
source install/setup.bash

ros2 pkg list | grep orbinspect
```

Expected package count: 12 OrbInspect packages.

If the build fails, fix the build before changing algorithms or experiment parameters. Record the complete command and first causal error.

### Gate B: Python and ROS Package Tests

```bash
pytest

colcon test --packages-select \
  orbinspect_dynamics \
  orbinspect_control \
  orbinspect_safety \
  orbinspect_guidance \
  orbinspect_perception \
  orbinspect_eval \
  orbinspect_bringup \
  --event-handlers console_direct+

colcon test-result --verbose
```

Do not treat skipped ROS-dependent tests as passes without reading the skip reason.

### Gate C: Baseline ROS Stack Smoke Test

Run the established baseline before the ADP bridge:

```bash
ros2 launch orbinspect_bringup demo_rviz.launch.py record:=false
```

Then verify a recorded baseline workflow:

```bash
ros2 launch orbinspect_bringup demo_greedy_inspection.launch.py record:=true
```

Confirm the HCW dynamics node publishes odometry, controller/safety topics connect, coverage changes, and the logger creates the expected result tree.

### Gate D: Direct Interface Replay on Validation Data

Use `validation_000`, not `test_002`, while tuning integration parameters.

Run both methods in `publish_mode:=replay`. Verify:

- exact scenario and method selection;
- all references emitted in order;
- coherent ROS timestamps and TF tree;
- planned path, camera attitude, RViz, and Gazebo visuals;
- zero dropped references;
- complete CSV/rosbag logging.

This gate validates the bridge only. It is not closed-loop or dynamical evidence.

### Gate E: Closed-Loop Validation-Only Tuning

Run the same validation routes with:

```text
publish_mode:=closed_loop
trajectory_source:=csv
loop:=false
```

The HCW dynamics node must remain the only odometry source. Tune tracking-controller and replay integration parameters only on the 12 validation scenarios. Do not inspect or tune against test/shifted execution outcomes.

After the validation criteria are met:

1. freeze the YAML configuration;
2. hash it;
3. store the hash in `config_snapshot/`;
4. record the Git revision and installed package versions;
5. prohibit further tuning before the paired test run.

### Gate F: Illustrative Paired Case

After the configuration freeze, run `test_002` for both:

```text
adaptive_rollout_adp
local_search
```

Use separate run IDs and the same scenario initial state. This case should produce the planned-versus-executed trajectory/safety figure for the future ROS results subsection, but it remains illustrative.

### Gate G: Confirmatory Paired Campaign

Run all frozen pairs in this order:

1. 30 test scenarios: primary ROS inference;
2. 20 shifted scenarios: secondary stress test.

Do not change the controller, safety filter, timing, or tolerances between methods or scenarios. If a software defect requires a change after opening the test split, document the defect, invalidate affected runs, create a new protocol/configuration revision, and rerun both methods for every affected pair.

## 8. Predeclared Execution Gates

These gates are already written into manuscript Section V-E.

At every credited observation:

- position error must be at most 0.5 m;
- terminal speed must be at most 0.05 m/s.

Throughout execution:

- clearance above the 2 m mesh safety margin must remain nonnegative;
- commanded acceleration magnitude must not exceed 0.060 m/s^2;
- no swept trajectory segment may intersect the ISS mesh;
- dropped-reference count must be zero.

At mission completion:

- inspectable coverage must be at least 0.80;
- completion must occur within 14 SOOAs.

Report, even when a gate fails:

- RMS and maximum planned-versus-executed position error;
- realized physical delta-v;
- minimum executed clearance;
- peak commanded input;
- safety-filter intervention count;
- achieved coverage;
- action count and completion time;
- dropped-reference count;
- completion/failure reason.

Primary paired ROS claim gate:

1. rollout ADP has no lower mission success than local search; and
2. the upper endpoint of the 95% paired-bootstrap interval for realized `delta_v_ADP - delta_v_local` is below zero.

Use 10,000 paired bootstrap resamples and report mean/median difference, confidence interval, wins/ties/losses, and the exact two-sided sign test after excluding numerical ties. Do not substitute offline graph delta-v for executed ROS delta-v.

## 9. Required Experiment Output

Every ROS run must produce:

```text
data/results/<timestamp-or-run-id>/
├── config_snapshot/
├── raw/
├── rosbag/
├── figures/
├── videos/
├── summary.json
└── summary.md
```

Required core CSV files:

```text
trajectory.csv
control.csv
coverage.csv
safety.csv
planner.csv
mission_events.csv
```

Add or preserve these fields where relevant:

```text
run_id
scenario_id
scenario_seed
split
method
source_result_root
source_graph_hash
source_scenario_hash
source_route_hash
git_revision
ros_distro
gazebo_version
configuration_hash
```

The summary must distinguish planned and executed quantities. Never overwrite a planned graph metric with an executed ROS metric under the same field name.

## 10. Runtime Checks During Each Launch

At minimum, inspect:

```bash
ros2 node list
ros2 topic list
ros2 topic hz /chaser/odom
ros2 topic echo /chaser/safety_status --once
ros2 bag info <bag-directory>
```

Confirm exactly one authoritative publisher for chaser odometry in closed-loop mode. In direct replay mode, the replay node may publish odometry for visualization; in closed-loop mode, it must not compete with the HCW dynamics node.

Monitor process health, topic rate, simulated time, disk space, and output-file growth. Stop and diagnose if timestamps regress, references are skipped, odometry has multiple publishers, safety logging stops, or rosbag serialization errors appear.

## 11. Failure Handling

Do not silently repair failed confirmatory runs.

- Build/test failure: fix before any experiment.
- Interface/schema failure: fix using validation data and rerun the interface gate.
- Tracking failure on validation: tune only validation configuration, then refreeze.
- Tracking/safety failure on test: retain the failed run and report it; do not tune against it.
- Rosbag/logger failure: the run is incomplete and must be repeated with the same frozen configuration after the logging defect is fixed.
- Gazebo visual failure with healthy ROS state: diagnose visualization separately; do not replace the HCW state source.
- Basilisk unavailable: continue with HCW. Basilisk is not required for this verification.

## 12. Updating the Manuscript After ROS Verification

The current PDF intentionally contains no fabricated or placeholder ROS measurements. Manuscript Section V-E is a prospective protocol, and ROS performance remains outside the present evidence boundary.

After the frozen campaign is complete:

1. populate `OrbInspectLatex/sections/ros_verification_results.tex` with real environment details, exclusions, paired results, and planned-versus-executed figures;
2. change `\includeROSVerificationResultsfalse` to `\includeROSVerificationResultstrue` in `OrbInspectLatex/main.tex`;
3. rename the prospective protocol only if the protocol was actually executed as written;
4. replace the pending-ROS sentences in the Discussion and Conclusion with evidence-bounded results;
5. update the Abstract only if the closed-loop claim gate passes;
6. retain all limitations concerning deterministic HCW dynamics, uncertainty, passive safety, attitude dynamics, and continuous-time robustness;
7. regenerate the PDF and visually inspect every affected page.

LaTeX build:

```bash
cd ~/orbinspect_ros2/OrbInspectLatex
latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex
```

Do not enable the ROS-results insertion file while any value remains unknown. If the ROS gate fails, report the failure rather than rewriting the gate or importing offline numbers.

## 13. Completion Checklist

The Ubuntu handover is complete only when all boxes below are satisfied.

- [ ] Workspace transferred with `.git`, frozen results, meshes, and manuscript intact.
- [ ] `git status` reviewed; no user changes discarded.
- [ ] All 12 packages build with `colcon build --symlink-install`.
- [ ] Relevant Python and colcon tests pass with skip reasons audited.
- [ ] Baseline RViz/greedy stack passes before ADP replay work.
- [ ] Frozen-route exporter added with metric/hash assertions and tests.
- [ ] Replay loader supports unambiguous `scenario_id` selection.
- [ ] Verification parameters moved to YAML.
- [ ] `trajectory_source:=csv`, `loop:=false`, and 0.060 m/s^2 limit enforced.
- [ ] Direct replay passes on validation data.
- [ ] Closed-loop validation tuning completes and configuration is frozen.
- [ ] `test_002` paired illustrative run completes after the freeze.
- [ ] Full 30-case paired test campaign completes without retuning.
- [ ] Full 20-case paired shifted campaign completes without retuning.
- [ ] Every run contains the required CSV, rosbag, summaries, hashes, and environment snapshot.
- [ ] Statistical analysis uses executed ROS quantities and the predeclared paired gate.
- [ ] Manuscript results scaffold populated only with audited measurements.
- [ ] Final PDF compiles and passes visual inspection.

## 14. Recommended First Ubuntu Session

The safest first session is deliberately modest:

1. inspect `git status` and verify frozen result files;
2. install dependencies with `rosdep`;
3. build all packages;
4. run Python and colcon tests;
5. launch the baseline RViz demo;
6. launch the recorded greedy baseline;
7. stop and review logs;
8. only then begin the frozen-route exporter and replay-node adapter.

Do not open `test_002` in closed loop until validation-only integration tuning is frozen.
