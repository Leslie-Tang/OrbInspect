# Ubuntu handover: required-target ROS validation and manuscript update

**Figures 3--6 font consistency (2026-09-10):** axes, ticks, legends and notes
now use 8 pt Arial at the final manuscript size (math scripts: 5.6 pt).
The Figure 6 generators now read frozen CSVs and a portable snapshot of its
original display faces; no planner or simulation was rerun. Its method legend
is shared above the 3D panel, and alternate horizontal tick labels prevent
crowding. The manuscript remains 13 pages, with unchanged data, captions,
colors and Figures 1, 2, 7 and 8. Current PDF:
`output/pdf/OrbInspect_IEEE_TAES_with_RViz_overview_20260909.pdf`.
See `OrbInspectLatex/docs/FIGURES_3_6_UNIFORM_FONTS_20260910.md`.

**Figure 7 number fit (2026-09-09):** waypoint numbers in the two trajectory
projections now use 5.2 pt Arial Bold, reduced from 7 pt to fit the original
circles, including IDs 10--12. Circle sizes, paths, camera panels and Figure 8
are preserved. The current PDF remains
`output/pdf/OrbInspect_IEEE_TAES_with_RViz_overview_20260909.pdf`.
See `OrbInspectLatex/docs/FIGURE_7_MARKER_LABELS_20260909.md`.

**Additional Figure 8 (2026-09-09):** the manuscript now includes a compact
RViz overview from one transfer frame of the recorded repeat below.
The frame at video time 1375 s shows central-module detail during transfer
9 to 10, avoiding the final camera view already illustrated in Figure 7.
Both panels are synchronized; their progress labels report 9/12 observations,
7/9 required targets and 76.27% coverage. The repeat still completes with the
final totals recorded below. The earlier completion-frame Figure 8 is archived
under `OrbInspectLatex/archive/figure8_completion_frame_20260909/`.
Figure 7 and all prior figure artwork are unchanged. Both figures fit on page 12
of the 13-page manuscript. The new output is
`output/pdf/OrbInspect_IEEE_TAES_with_RViz_overview_20260909.pdf`; the portable
source ZIP is `OrbInspectLatex/build/OrbInspectLatex_source.zip`.
The video is also staged as `output/supplementary/Supplementary_Video_1.mp4`.
See `OrbInspectLatex/docs/FIGURE_8_RVIZ_OVERVIEW_20260909.md` for provenance and checks.

**RViz video follow-up (2026-09-09):** the same twelve-observation input bundle
was rerun at normal speed as `20260909_113140_hybrid12_rviz_video_execution`.
It accepted 12/12 observations, all nine required targets, and 95.8577156%
weighted coverage. Target/event, full-mesh and reference-timing checks passed.
The recording shows the live spacecraft camera beside the global RViz trajectory
view. The full 1080p MP4 (30:16.8), 10× preview (3:01.7), original capture and
validation notes are in
[`data/results/20260909_113140_hybrid12_rviz_video/summary.md`](data/results/20260909_113140_hybrid12_rviz_video/summary.md).
This video task did not change the manuscript or Figure 7.

**Current result, twelve-observation follow-up (2026-09-09):** the supplemental
normal-speed run `20260909_093200_hybrid12_visual` accepted 12/12 observations,
all nine required targets and 95.8577156% weighted background coverage (39/41).
It keeps the parent target IDs, weights and safety settings, adds a 95% hybrid
goal, and refines two viewpoints after an archived 10/12 tracking diagnostic.
The 90-s transfers retain 60-s terminal settling. Execution, full-mesh and camera
alignment audits passed. The publisher's 0.248723-s maximum reference interval
exceeded the 0.075-s nominal timing diagnostic and is explicitly disclosed;
reference-count completion passed. Figure 7 now uses twelve original frames in
a 170 by 47 mm, two-by-six layout with the approved style. The nine-view figure
is archived separately. See `OrbInspectLatex/docs/ROS_TWELVE_OBSERVATIONS_20260909.md`.
The reviewed output is `output/pdf/OrbInspect_IEEE_TAES_ROS_12_observations_20260909.pdf`.
All updates below are earlier history; the frozen offline study remains unchanged.


Prepared: 2026-09-09. Implementation baseline: `440c476` on `main`.
Repository: https://github.com/Leslie-Tang/OrbInspect

**Completed execution follow-up, 2026-09-09:** the original 810-s headless run
accepted 7/9 required targets and is retained. A subsequent normal-speed
graphical run of the same median-effect route, with a declared uniform 60-s
terminal settling interval after each transfer, accepted all nine observations
and required targets in 1,350.038 s. Execution, full-mesh and per-view camera
alignment audits passed. The ROS manuscript and Figure 7 now use this run;
the approved figure style and Figures 1–6 are preserved. See
`OrbInspectLatex/docs/ROS_FULL_COMPLETION_20260909.md` and
`OrbInspectLatex/docs/ROS_SETTLING_PROTOCOL_20260909.md` for the search inventory,
retained failures, timing adjustment and evidence. No paired ROS saving is
claimed. The original handover instructions below are retained as history.

**Figure 7 layout follow-up, 2026-09-09:** two trajectory projections now appear
on the left, with camera views 1--5 above views 6--9 on the right. The legend fills
the spare tenth position. The 170 by 44 mm export saves 38.9% of the previous
72 mm height; each camera view is 20.8 mm wide. Colors, typography, frame pixels
and execution evidence are preserved. See
`OrbInspectLatex/docs/FIGURE_7_TWO_ROWS_20260909.md`; the preceding 24 mm camera
layout is archived in `OrbInspectLatex/archive/figure7_camera_emphasis_20260909/`.

This replaces the earlier Windows finishing guide, preserved unchanged in
`docs/handover_windows_20260812.md`. That historical guide's figure paths,
page count and completion status are not the current required-target workflow.

## 1. Objective and completion criteria

Run the current required-target inspection task on **Ubuntu 24.04.4 LTS,
ROS 2 Jazzy, Gazebo Harmonic, RViz2, and Python 3.12**, then update the ROS
execution subsection and Figure 7 using the new, audited evidence.

Read `AGENTS.md` first. Keep ROS-native HCW dynamics as the spacecraft-state
source of truth; Gazebo provides rendering and camera imagery. Do not introduce
ROS 1, Humble, Gazebo Classic, catkin, or a mandatory Basilisk dependency.

Deliver in two stages:

1. **Minimum:** one audited required-target ADP closed-loop run, synchronized
   real simulator camera frames, and a revised ROS subsection/Figure 7.
2. **Stronger comparison:** replay the same frozen scenario with the manuscript's
   `seeded_local_search` comparator, then a predeclared paired cohort if a
   ROS-level maneuver-saving claim is desired. This needs the small compatibility
   changes in Section 4; it is not enabled by changing a command-line label.

The main theoretical contribution remains **viability-preserving rollout ADP**.
Tracking a frozen ADP route is not online ADP replanning, trained DRL, or evidence
of global optimality. Do not change the offline study to improve the ROS outcome.

This handover does not report a new ROS execution. Only documentation is changed
by this handoff. Ubuntu execution and its manuscript revision remain to be done.

## 2. Current evidence: do not mix these records

| Evidence | Current status and location |
|---|---|
| Required-target offline confirmation | Frozen; `OrbInspectLatex/data/confirmation/` is tracked and contains the exporter inputs. |
| Required-target execution interface | Implemented: portable route mission metadata and accepted-target-ID unions. Relevant local checks passed; no new Jazzy execution is claimed. |
| Previous required-target replay export | `data/results/20260905_111500_required_target_confirmation_replay/` is a local, unexecuted input bundle, **not tracked**. Re-export from the tracked snapshot on Ubuntu. |
| Current manuscript ROS result | Historical 80%-survey execution, not the new required-target mission. |
| Current Figure 7 | Historical ten-observation, 900-s run; compact two-column layout. Its snapshot is `OrbInspectLatex/data/historical_ros/figure7/`. |

The historical media-backed run and the later bag-complete confirmation are
different executions. The former is
`data/results/ros_rviz_full_planning_demo_corrected_validation002_radius080_20260812/`;
the latter is `data/results/20260812_174012_ros_final_validation002_radius080/`.
Do not mix their sample counts, completion times or clearance values.

The representative scenario is already selected by the manuscript's median-effect
rule, not by future ROS outcomes:

- Scenario: `required09_test_000`; seed: `202609360000`.
- Selection record: `OrbInspectLatex/data/confirmation/raw/representative_case_manifest.json`.
- Required IDs: `mesh_00055`, `mesh_00052`, `mesh_00059`, `mesh_00007`,
  `mesh_00001`, `mesh_00079`, `mesh_00033`, `mesh_00015`, `mesh_00019`.
- These are synthetic prescribed mesh samples, not verified ISS critical components.

| Frozen planned quantity for this scenario | Rollout ADP | Seeded local search |
|---|---:|---:|
| Required completion | 9/9 | 9/9 |
| SOOAs | 9 | 8 |
| Duration | 810 s | 720 s |
| Maneuver velocity increment | 13.7688852945 m/s | 15.7436178074 m/s |
| Weighted background coverage | 77.2174% | 64.9707% |

These are **planned values**, not future executed results. ADP's unweighted
background coverage is 30/41; its whole-sample fraction is 30/90. Neither is
the required-target completion fraction. Required-only success does **not**
require 80% background coverage. The existing 11.05% manuscript improvement
is an offline aggregate over 43 paired test missions, not this single-case
difference and not a measured ROS saving.

## 3. Update and validate the Ubuntu checkout

Commands below assume the repository root is `~/orbinspect_ros2` and contains
`src/` and `OrbInspectLatex/`. If it is elsewhere, change the initial `cd`; do
not introduce a second nested workspace. Stop on any failed command. Preserve
local changes instead of resetting or automatically stashing them.

```bash
cd ~/orbinspect_ros2
git status --short --branch
git remote -v
# Proceed only when local work is committed or otherwise safely accounted for.
git pull --ff-only origin main
git merge-base --is-ancestor 440c476 HEAD
# Optional if the historical bags/videos are needed (includes a large MCAP):
# git lfs pull
source /opt/ros/jazzy/setup.bash
test "$ROS_DISTRO" = jazzy
python3 --version
gz sim --versions

orbinspect_handover_id=$(date -u +%Y%m%d_%H%M%S)
orbinspect_handover_dir="$PWD/data/results/${orbinspect_handover_id}_ubuntu_preflight"
mkdir -p "$orbinspect_handover_dir"
set -o pipefail
rosdep check --from-paths src --ignore-src --rosdistro jazzy
# If dependencies are missing, resolve them before building:
# rosdep install --from-paths src --ignore-src --rosdistro jazzy -r -y
colcon build --symlink-install 2>&1 | tee "$orbinspect_handover_dir/build.log"
source install/setup.bash
ros2 pkg list | grep '^orbinspect'
colcon test --event-handlers console_direct+ 2>&1 | tee "$orbinspect_handover_dir/colcon_test.log"
colcon test-result --verbose
python3 -m pytest -q \
  src/orbinspect_guidance/test/test_advanced_safe_planner.py \
  src/orbinspect_guidance/test/test_required_target_study.py \
  src/orbinspect_guidance/test/test_ros_route_exporter.py \
  src/orbinspect_guidance/test/test_verification_evaluator_node.py \
  test/test_required_target_depth_summary.py \
  tools/paper/tests/test_figure2_example.py
make -C OrbInspectLatex check
```

The focused command passed 66 tests on the preparation host, using its local
Python environment; this does not replace the Ubuntu build/test result. Retain
actual Ubuntu versions and logs. Use system Python 3.12 with the Jazzy overlay,
not the Mac `.venv-review` environment. The source check does not require ROS.
The tracked mesh and confirmation snapshot suffice to export the new route;
historical video/bag downloads are not required for a fresh execution.

Validate the tracked input bytes before exporting:

```bash
sha256sum \
  OrbInspectLatex/data/confirmation/raw/hcw_graph.json \
  OrbInspectLatex/data/confirmation/raw/scenarios.json \
  OrbInspectLatex/data/confirmation/raw/heldout_results.csv \
  src/orbinspect_description/models/iss_real/meshes/ISS_stationary.glb
```

Expected SHA-256 values, in the same order:

```text
e90f40f0aaf87464ad5b5ef6b39979aa3c5f0b7049fe0ec17ad5e5b1a19b0af2
074ff868201907242ff4954ff6adc932a254b6ddcee5f1b52d64f31669f163ae
335ec2b4e176e8425a0e30fea30a31f859ef07fa413c2a7c7472ca054988f068
26dba905b4b7555edbcb0c5f5a61b5c18659f5166076ab27dbb0e64025759fca
```

Do not edit historical paths inside freeze manifests to make them look local.
They are provenance. The exported v3 mission metadata is self-contained; the
runtime need not recover target weights from the original Mac result directory.

## 4. Known implementation limits and required follow-up

| Area | What to check or implement on Ubuntu |
|---|---|
| ADP-only exporter | Ready for the explicit command in Section 5. Always specify `--methods adaptive_rollout_adp`; its default includes legacy `local_search`. |
| Paired exporter | `ros_route_exporter.py` accepts only `adaptive_rollout_adp` and legacy `local_search`. Add explicit support for archived `seeded_local_search` (optionally `one_step_adp`), preserve those method names, and materialize their recorded `route_node_ids`. Require the archived row; never silently replan or rename a method. |
| Campaign runner | `ros_verification_campaign.py` hard-codes the legacy pair in `METHODS`, CLI choices, aggregation, paired helpers and claim gates. Update all of these consistently before using it for the confirmation comparator. A CLI-only change is insufficient. |
| Required-target reporting | Add goal mode, mission hash, fixed requirement count, accepted required count, missing IDs, accepted-ID union and required-completion rate to new campaign outputs. Background `coverage` alone is insufficient. |
| Paired denominators | Preserve the frozen selection inventory and failures. Record planning failures as non-executable cases, not successful zero-cost runs. Report execution rates separately from the offline scenario rates; calculate maneuver comparisons on explicitly reported jointly completed and audited ROS pairs. The current aggregator does not impose that joint-success filter. |
| Camera recording | `record_bag:=true` records verification/status and trajectory topics, but the default topic list omits `/chaser/camera/image` and `/clock`. Add a separate camera recorder or extend the recorder with tests before the visual run. |
| Figure 7 generator | The current portable generator hard-codes ten views, the historical snapshot, and two historical clearance values. Parameterize it for the new verified snapshot; do not merely point it at a nine-view run. |

Relevant files:

- `src/orbinspect_guidance/orbinspect_guidance/observation_credit.py`
- `src/orbinspect_guidance/orbinspect_guidance/verification_evaluator_node.py`
- `src/orbinspect_guidance/orbinspect_guidance/ros_route_exporter.py`
- `src/orbinspect_guidance/orbinspect_guidance/ros_verification_campaign.py`
- `src/orbinspect_guidance/orbinspect_guidance/ros_evidence_audit.py`
- `src/orbinspect_eval/orbinspect_eval/logger_node.py`
- `src/orbinspect_eval/orbinspect_eval/rosbag_manager.py`
- `src/orbinspect_bringup/launch/ros_verification.launch.py`

Keep existing ROS messages stable. Prefer additive JSON fields and YAML
parameters. Add exporter/campaign regression tests for the new method IDs,
unequal route lengths, missing/failed routes, failed observation credit and
joint-success cohorts. Rebuild and rerun relevant tests after code changes.

## 5. Export the fixed ADP route and run a closed-loop check

Use the tracked confirmation snapshot directly. No ZIP package is needed.
Run from the workspace root with both ROS setup files sourced.

```bash
orbinspect_replay_id="$(date -u +%Y%m%d_%H%M%S)_required09_replay"
ros2 run orbinspect_guidance ros_route_exporter \
  --source-dir "$PWD/OrbInspectLatex/data/confirmation" \
  --scenario-id required09_test_000 \
  --methods adaptive_rollout_adp \
  --output-root "$PWD/data/results" \
  --run-id "$orbinspect_replay_id"
orbinspect_replay_dir="$PWD/data/results/$orbinspect_replay_id"
```

Before launching, inspect `manifest.json` and verify one matching route, v3
schema, `mission.goal_mode == "required"`, the nine exact required IDs, 41
fixed target weights, nine actions, 810-s duration, corrected mesh transform,
0.80-m vehicle radius and 2-m safety margin. Verify all `output_files_sha256`
entries against the emitted raw CSVs. Confirm the exact route sequence:

```text
cand_0005 -> cand_0000 -> cand_0070 -> cand_0068 -> cand_0021
-> cand_0015 -> cand_0052 -> cand_0062 -> cand_0045
```

The replay summary must still say `execution_performed: false`. These CSVs are
planned inputs. Do not copy them into a run directory as executed measurements.
The YAML retains `goal_mode: coverage` for legacy compatibility; route mission
metadata overrides it. Do not change the global default to relabel the old run.

```bash
orbinspect_run_id="$(date -u +%Y%m%d_%H%M%S)_required09_adp_closed_loop"
test ! -e "$PWD/data/results/$orbinspect_run_id"
ros2 launch orbinspect_bringup ros_verification.launch.py \
  result_dir:="$orbinspect_replay_dir" \
  scenario_id:=required09_test_000 method:=adaptive_rollout_adp \
  publish_mode:=closed_loop headless:=true time_scale:=1.0 \
  record:=true record_bag:=true save_figures:=false \
  run_id:="$orbinspect_run_id" \
  2>&1 | tee "$orbinspect_handover_dir/$orbinspect_run_id.launch.log"
orbinspect_run_dir="$PWD/data/results/$orbinspect_run_id"
cp "$orbinspect_handover_dir/$orbinspect_run_id.launch.log" "$orbinspect_run_dir/launch.log"

ros2 run orbinspect_guidance ros_evidence_audit "$orbinspect_run_dir" \
  --mesh-path "$PWD/src/orbinspect_description/models/iss_real/meshes/ISS_stationary.glb" \
  --safety-margin 2.0 --vehicle-radius 0.80 --max-acceleration 0.060
ros2 bag info "$orbinspect_run_dir/rosbag/orbinspect_run"
```

The launch normally shuts down after the planned duration plus a buffer. A
successful launch exit or timeout alone is not mission success. Inspect child
process failures, final verification status, reference-stream completion and
audit gates. Use a new run ID for retries; preserve failed attempts and explain
any fix. Do not pre-create the execution directory: the launcher otherwise
selects a suffixed directory. Read the actual output path in the launch log.

The current execution configuration uses 20-Hz publishing, a 0.05-s HCW
integration step, 0.5-m terminal position tolerance and 0.05-m/s terminal speed
tolerance. Its safety filter speed limit is 1.50 m/s, whereas the offline
planning setting differs; report the actual execution configuration rather
than claiming every offline and online parameter is identical.

## 6. Visual run and camera/LOS evidence

After the headless check, make a **separate, newly named graphical run** with
`headless:=false visual_startup_delay:=10.0`, a unique `gz_partition`, and the
same explicit replay/scenario/method. Keep `time_scale:=1.0` for the initial
recording. Use the same `ros_verification.launch.py` interface, not the default
`demo_corrected_rviz` scenario, which selects the historical survey task.

Before starting the mission, start an additional recorder in another sourced
terminal, on the same ROS domain. Use a distinct timestamped output directory:

```bash
orbinspect_camera_id="$(date -u +%Y%m%d_%H%M%S)_required09_camera"
mkdir -p "$PWD/data/results/$orbinspect_camera_id/rosbag"
ros2 bag record -o "$PWD/data/results/$orbinspect_camera_id/rosbag/camera" \
  --topics /chaser/camera/image /chaser/odom /chaser/attitude_reference \
  /verification/status /clock
```

Stop that recorder cleanly after launch completion, verify its metadata/message
counts, and copy the capture into the **graphical run's** `rosbag/camera/` with
its original manifest and hashes. Record the relationship between the two run
directories. `/clock` can be absent at unaccelerated wall time; record that
clock basis explicitly. Inspect camera-topic discovery, timestamps, nonblank
images, pose/orientation and scene alignment before treating the capture as usable.

The launch does not automatically create raw MP4 screen/camera captures.
If a video is needed, retain original frames/bag messages, encoder settings,
screen-capture timing, and the mapping between camera, ROS/mission and wall
clocks. Match each accepted observation to an actual camera frame; quantify
timestamp mismatch and dropped frames. Do not silently clamp a missing frame
to the first/last image or assume a constant frame rate proves synchronization.
Run the full execution audit on the graphical run itself; do not combine its
images with the headless run's metrics.

At each accepted terminal observation, show the simulator image and its
trajectory position. Required-target credit is still computed from **frozen
geometric visibility masks gated by tracking**, not image-based defect detection
or fresh LOS raycasting from every executed camera pose. State this accurately.

## 7. Evidence acceptance and paired comparison

Every delivered execution directory must contain:

```text
data/results/<timestamped_run_id>/
  config_snapshot/   # YAML, input/run manifests, environment, source revision
  raw/              # trajectory, control, coverage, safety, planner, mission_events CSVs
  rosbag/           # verified core topic bag; camera bag for graphical runs
  figures/          # derived outputs with source hashes
  videos/           # retained video, or explicit explanation if not generated
  launch.log
  mesh_execution_audit.json
  summary.json
  summary.md
```

For an accepted required-target run, require all of the following:

- Closed-loop dynamics/control actually ran; the manifest does not say `replay`.
- Final `summary.json.verification`: `goal_mode == "required"`, requirement
  count 9, accepted required count 9, ratio 1, no missing IDs, correct mission
  hash, `mission_goal_reached == true`, and execution `success == true`.
- Exactly the intended observation sequence was evaluated. The retained
  all-observations-pass rule requires no failed action, in addition to target
  completion and the action budget; do not weaken it to obtain a success.
- Reconstruct accepted target unions from the bag's `/verification/status`
  or `/mission/event` JSON. Rejected views contribute nothing and repeated IDs
  count once. CSV coverage/planned cumulative values alone are insufficient.
  The logger keeps final verification JSON in the summary, but its CSV columns
  are not a full per-event required-target audit trail.
- Reference-stream completion, data-presence, acceleration and all full-mesh
  audit gates pass. The complete transformed model has 247,525 triangles;
  do not audit only the decimated display mesh or translation-only geometry.
  Report message-gap diagnostics separately: a reference-count completion gate
  is not a strict inter-message latency guarantee.
- Use `minimum_body_clearance_m` for the swept-segment finite-body margin
  **above** the required 2 m, not `minimum_mesh_clearance_m` (sampled center
  margin). Keep radius subtraction, surface distance and required margin
  distinct. The continuous lower bound concerns segments between logged
  samples; it is not a guarantee about all unmodeled physical motion.
- Report executed delta-v from the timestamped safe-control integration,
  together with tracking errors, filter interventions, duration and clearances.
  Do not substitute the planned `total_delta_v` for execution effort.

`planner.csv` may legitimately be header-only because this workflow executes
an offline-planned route. Explain this in the summary; do not insert synthetic
online-planner records to fill it. Missing trajectory/control evidence is a
different issue and must fail the execution audit.

For paired work, finish Section 4 first. Freeze the scenario list, methods,
configuration, clock scale and inclusion rules before running. A single
representative pair is an illustrative comparison, not a confidence-interval
study. A larger cohort must retain unsuccessful attempts and distinguish
original offline counts, executable routes, attempted ROS runs and jointly
audited completions. Keep the original 43/50 test and 9/30 shifted ADP planning
results unchanged. Do not relabel replay effort as online planning latency or
claim the historical 11.05% saving was measured in ROS.

## 8. Figure 7 and manuscript revision map

Keep the approved figure style. Figure 7 remains a compact two-column layout
with two central equal-scale trajectory projections and camera groups on both
sides. For the nine-action ADP run, use five genuine views on one side and four
on the other; preserve order and numbered position correspondence. Do not
invent a tenth observation or stretch the panels. Keep approximately 7--8 pt
text at print size. Required completion and background coverage must have
distinct labels; avoid an unlabeled percentage. Preserve Figures 1--6,
including Figure 3's enlarged fonts and native LaTeX subfigures.

Implementation work for the new Figure 7:

1. Preserve the historical snapshot/artwork and caption. Add a separate new
   required-target ROS snapshot, for example under
   `OrbInspectLatex/data/required_target_ros/<run_id>/`, with source/bag/frame
   hashes, accepted event IDs, timestamps, planned/executed coordinates and
   per-event audit quantities. Include enough data to regenerate without ROS.
2. Adapt `OrbInspectLatex/scripts/generate_ros_camera_figure.py` to accept a
   snapshot path and actual observation count, while retaining the compact
   layout. Replace the hard-coded historical `c_2`/`c_3` values with verified
   new quantities or a clearly identified overall body-clearance margin.
3. Do not run `tools/paper/prepare_compact_ros_camera_figure.py` over the current
   files: it is a one-time historical conversion. The older
   `generate_ros_key_camera_views_figure.py` also assumes ten observations and
   writes the obsolete tall layout. The video compositor has historical timing
   assumptions; adapt and test it before use with new captures.
4. Export matching editable SVG, vector PDF and PNG; inspect label bounds,
   frame/trajectory correspondence, coordinate scaling and source integrity.
   Update only the affected records in `OrbInspectLatex/figures/manifest.json`.

| Manuscript file | Required change after evidence passes |
|---|---|
| `OrbInspectLatex/sections/ros_verification_results.tex` | Replace or clearly separate the historical subsection; report the new task, environment, execution gates, accepted required/background metrics and measured effort. Update Figure 7 caption and supporting statements together. |
| `OrbInspectLatex/sections/required_target_study.tex` | Update “Execution Interface and Historical ROS Evidence,” especially the statement that no required-target ROS campaign was executed. Change only what the new evidence establishes. Review the commented sharing statement for stale scope. |
| `OrbInspectLatex/main.tex` | Check the introduction's historical-evidence statement; keep the ADP theorem and offline abstract/11.05% result intact. Add an execution statement only if supported. |
| `OrbInspectLatex/data/README.md`, `README.md` and provenance docs | Explain the new snapshot, exact input/implementation versions, run commands, figure regeneration and separation from historical survey data. |

Use IEEE Transactions wording and paper-facing labels, not raw run IDs in
narrative text. Store exact IDs in reproducibility records. Keep the sensing
and deterministic-model limitations concise and accurate. Do not remove a
limitation solely because a graphical replay succeeds.

Build with `make -C OrbInspectLatex` and `make -C OrbInspectLatex check`.
Inspect rendered pages, cross-references, Figure 7 at final size and the final
bibliography balance. The current PDF has 13 pages; extra verified evidence
may justify more, but avoid sparse pages. Do not regenerate ZIPs by default:
the user requested their removal, so avoid `make package` for this handoff.

## 9. Return and Git handoff

Return a short execution report with actual pass/fail status, run paths,
planned-versus-executed metrics, build/test results, retained failed attempts,
remaining limitations and a file-by-file manuscript change list. Include the
reviewed PDF, editable artwork, compact evidence snapshot and regeneration
instructions. If execution is blocked, keep the historical manuscript claims
unchanged and document the exact blocker instead of inserting projected results.

New `data/results/*` directories are ignored by default. Explicitly curate the
required evidence; otherwise a push will omit it. Use narrow Git LFS patterns
for newly retained large bags/video as needed, verify the LFS upload and record
hashes. Do not force-add all generated results, duplicate export folders,
build/install logs, system caches or ZIPs. Preserve third-party asset attribution.

Before pushing, inspect `git diff`, stage only intentional changes, commit the
execution implementation separately from evidence/manuscript updates when useful,
and use a normal fast-forward push. Never force-push or overwrite frozen studies.
If working on a separate Ubuntu branch, use the `codex/` prefix and report the
branch/commit for review rather than assuming a merge into `main`.

Further context: `docs/required_target_execution_validation_20260905.md`,
`docs/required_target_reproducibility_notes_20260905.md`,
`OrbInspectLatex/docs/FIGURE_7_COMPACT_TWO_COLUMN_20260908.md`, and
`tools/paper/README.md`. Some older notes name `OrbInspectLatex/scripts/` for
experiment tools; their current repository-dependent location is `tools/paper/`.
