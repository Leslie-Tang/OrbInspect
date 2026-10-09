# Ubuntu handover: required-target ROS validation and manuscript update

**Figure 7 coverage precision aligned (2026-10-09):**
The onboard-camera panel now displays weighted coverage as 76.3%, matching
observation 9 in Figure 6. Both labels represent the same saved ratio,
0.7627194404377868; coverage is held during transfer until the next accepted
observation. Only the displayed precision changed. The generator, panel-b
PDF/SVG/PNG exports, and integrity manifests are synchronized. Pixel comparison
confirms that changes are confined to the last coverage label; embedded camera
pixels, fonts, dimensions, layout, and panel a are unchanged. Figure preflight,
PDF font audit, compilation, all 68 figure checks, and page-12 visual review
passed. The main PDF remains 13 pages; root and build outputs are synchronized.

**Abstract depth comparisons clarified (2026-10-09):**
The abstract now identifies the separate comparison of rollout depths as the
reason for retaining depth three, then introduces the main benchmark with
"Using this depth". The 0.96% mean graph-cost gap remains explicitly tied to
the 27 cases with MILP-proven optima. The four-case visibility stress-test
sentence was removed from the abstract; its explanation and exclusion from
the 59-case primary denominator remain in the benchmark protocol. Numerical
results and figure assets are unchanged. Compilation, all 68 figure integrity
checks, and first-page visual review passed; the main PDF remains 13 pages.

**Figure 1 rectangular FOV illustrated (2026-10-09):**
Panel II now shows a perspective rectangular viewing pyramid with separate
horizontal and vertical half-angle labels, matching Eq. (3). Its far rectangle
illustrates the angular limits; range, incidence, and LOS remain separate
checks. The generic alpha_max label and principal-plane-only explanation have
been replaced in the figure, caption, system-model reference, and notation
notes. Native draw.io, SVG, PDF, and PNG exports are synchronized. The other
four panels are pixel-identical to the prior preview; camera imagery, palette,
typography, figure dimensions, and experimental data are preserved. The scoped
Python updater is `tools/paper/rectangular_figure1_fov.py`. Compilation, all 68
figure checks, whitespace checks, and manuscript-page visual review passed.
The main manuscript remains 13 pages and the supplement 2 pages; the root and
build manuscript PDFs are synchronized.

**Abstract condensed (2026-10-09):**
The abstract in `OrbInspectLatex/main.tex` was shortened from approximately 228
to 171 words. It retains the method's completion safeguard, conditional rollout
guarantee, depth-three rationale before the primary comparison, independently
certified all-solvable benchmark, mean 0.96% gap over 27 proven optima, separate
visibility stress cases, and the 11.05% confirmation maneuver saving. The
fixed-library completion counts remain in the Results section. No numerical
results or figures changed. Compilation, all 68 figure integrity checks,
whitespace checks, and first-page visual review passed; the main PDF remains
13 pages. Root and build manuscript PDFs are synchronized.

**Depth rationale added to abstract (2026-10-09):**
The abstract in `OrbInspectLatex/main.tex` now introduces the separate validation
depth diagnostic immediately before the 59-case benchmark comparison. It says
the diagnostic supports retaining depth three as a practical balance between
graph cost and computation, preserving the chronology of the earlier frozen
confirmation and subsequent all-solvable benchmark. No results or figures
changed. Compilation, all 68 figure integrity checks, whitespace checks, and
first-page visual review passed; the main PDF remains 13 pages. Root and build
manuscript PDFs are synchronized.

**Mean optimality-gap wording corrected (2026-10-09):**
The abstract, discussion, and conclusion in `OrbInspectLatex/main.tex` now
identify 0.96% as the mean relative graph-cost gap across the 27 cases with
proven optima. The former "within 0.96%" wording implied a per-case bound
that the reported mean does not establish. The runtime comparator is explicitly
the independent MILP. Results and cover-letter wording already stated the mean
correctly. No numerical results or figures changed. Compilation, all 68 figure
integrity checks, whitespace checks, and rendered-page review passed; the main
PDF remains 13 pages. Root and build manuscript PDFs are synchronized.

**Rectangular FOV model aligned with implementation (2026-10-09):**
Eq. (3) in `OrbInspectLatex/main.tex` now uses separate horizontal and vertical
camera-frame bounds, together with positive forward displacement. The forward,
horizontal, and vertical displacement components and both FOV half-angles are
defined at first use. Section V-B records the implemented 70-by-50-degree full
FOV and 35-/25-degree half-angles. Figure 1's existing alpha_max label is
explicitly identified as the half-angle of its schematic principal-plane
cross-section; its notation notes agree. All figure artwork is unchanged.
The tangent bounds were checked against the implemented angular gate using
10,000 random cases and 10 near-boundary/behind-camera cases. Compilation,
figure-integrity checks, rendered-page review, and whitespace checks passed;
the main PDF remains 13 pages. Root and build manuscript PDFs are synchronized.

**Transfer-distance and terminal-error notation clarified (2026-10-09):**
`OrbInspectLatex/main.tex` now defines the RMS distance to the fixed destination,
terminal position error, and terminal velocity error together in Eq. (7).
The RMS quantity uses all K post-step samples and enters the graph cost;
terminal errors use only the final sample and enter admissibility checks,
with zero desired terminal velocity. Both descriptions of the lambda_e weight
now say RMS distance to the destination. The formulas match the existing planner;
no implementation, results, or figure changes were needed. The rebuilt main PDF
remains 13 pages; compilation, figure-integrity checks, and rendered-page review
passed. The root main PDF and build output are synchronized.

**Depth diagnostic reordered (2026-10-09):** Results now begins with
“Rollout Depth and Computational Cost” (VI-A), followed by the method comparisons.
The protocol and supplement distinguish depth three fixed for the earlier
confirmation from its retention for the later all-solvable benchmark after the
validation diagnostic. Repeated development outcomes remain in Supplementary
Table S3. The main PDF is 13 pages and the supplement 2 pages; all 68 figure
assets, numerical tables, and displayed equations are preserved. Both root PDFs
and `build/` PDFs are current. See
`OrbInspectLatex/docs/DEPTH_DIAGNOSTIC_ORDER_20261009.md`.

**Submission-length revision completed (2026-09-17):** recommendations 1, 2,
4 and 5 were applied to the local manuscript. Repeated exposition was condensed,
the target inventories and full depth diagnostic moved to a standalone supplement,
and detailed ROS bookkeeping moved there with them. The former historical Table IV
was removed from the main results and retained as Supplementary Table S3 with its
development-only limitation stated explicitly. The main article is now 14 pages
(down from 16), with Tables I--V; `supplement.tex` compiles separately to 2 pages
with Tables S1--S3. All eight figure assets and their inclusion sizes are unchanged.
Figures 7 and 8 appear in order on page 13, and references 19--34 occupy page 14.
No Overleaf edit or Git push was performed.

**Figure 1 refreshed (2026-09-14):** the updated native draw.io source was
checked and exported to matching PDF/SVG/PNG assets. The revised workflow-arrow
routing is included in the local manuscript; the five-panel content, labels,
caption semantics and aspect ratio are unchanged. Figures 2--8 were not altered.

**Related-work references added (2026-09-14):** the manuscript now cites Luo,
Ning and Tang (2025) on online reinforcement-learning attitude stabilization
under spacecraft dynamic uncertainty, and Tang et al. (2025) on nonlinear
reach-avoid differential graphical games. Both entries were verified against
DOI metadata and are included in the local bibliography and compiled PDF.

**Contributions condensed (2026-09-14):** the introduction now groups the
contributions into three focused points covering the method, finite-graph
analysis, and reproducible evaluation evidence.

**System-model emphasis clarified (2026-09-14):** Section 3 now foregrounds
the deterministic system, observation, and feasibility model from which the
candidate graph is constructed. Planner operation and the offline-before-ROS
evaluation protocol remain described in the algorithm, experimental, and ROS
sections, where the lightweight depth-three timing is reported.

**Observation notation clarified (2026-09-14):** Section 3 explicitly defines
$p_i$ as the LVLH surface-sample position, $n_i$ as its outward unit normal,
and $a_i$ as represented area; required and visible target sets now use sample
indices consistently with the coverage masks.

**Pilot incorporated into the local manuscript (2026-09-14):**
`OrbInspectLatex/main.tex` now explains the original visibility-infeasible cases
and includes the three-graph pilot protocol, an independent MILP comparison,
Table VIII, and revised abstract/discussion/conclusion. The abstract and Table
VIII now lead with an independently certified all-solvable benchmark of 59 cases
(3 reference, 30 nominal and 26 shifted); depth-three ADP completes 59/59,
one-step ADP 57/59, and the greedy incumbent 33/59. The four shifted cases
failing the visibility certificate remain in a separate stress-test inventory.
The pilot is explicitly development evidence; the original confirmation counts,
data tables and all eight approved figure blocks/assets are retained. The compiled manuscript is
15 pages. Current dated PDF:
`output/pdf/OrbInspect_IEEE_TAES_viewpoint_pilot_20260914.pdf`.
The portable source ZIP and `OrbInspectLatex/main.pdf` are synchronized.
See `OrbInspectLatex/docs/VIEWPOINT_PILOT_MANUSCRIPT_20260914.md` and its QA record.
The reproducible subset generator is `tools/paper/materialize_solvable_benchmark.py`;
its derived files are under `data/results/20260914_073800_viewpoint_feasibility_pilot/raw/`.
No Overleaf edits or Git push were performed. The notes below describe earlier
stages, including the pilot's completion before manuscript integration.

**Viewpoint/feasibility pilot completed (2026-09-14):** new local experiment
`data/results/20260914_073800_viewpoint_feasibility_pilot/` contains three frozen
33-view graphs and 63 retained scenarios on the same ISS mesh and nine required
targets. Every target has at least three valid candidate views per graph.
Independent SciPy/HiGHS certification preceded ADP evaluation: 30/30 nominal and
26/30 shifted cases are feasible; four shifted cases lack any available view of
a required target. None is unresolved. Depth-three ADP completes every feasible
case (59/59 including three references), compared with 24/26 feasible shifted
cases for one-step ADP. ADP's mean gap is 0.9601% across the 27 independently
proven optima; MILP has a lower mean cost in both perturbed splits. Its 32
time-limited feasible routes are not claimed optimal. The predeclared feasibility
gate passed, supporting a larger confirmation with fresh seeds and a separately
frozen protocol. These are development results, not a replacement confirmation.

All 252 method-case rows and 3,267 numeric edge records passed post-run audit;
57 relevant Python tests passed and all 12 ROS packages built successfully.
Build with `colcon build --symlink-install --base-paths src` because archived
supplementary source trees otherwise produce duplicate package discovery.
Existing manuscript figures and the old 80-case confirmation remain intact.
Read the [completed pilot review](data/results/20260914_073800_viewpoint_feasibility_pilot/review.md)
and `docs/viewpoint_feasibility_pilot_protocol_20260914.md`.
The runner is `tools/paper/run_viewpoint_feasibility_pilot.py`; preserve its
frozen sources for reproducing this run. The independent post-run audit is
`tools/paper/audit_viewpoint_feasibility_pilot.py`.

**Single local TeX manuscript (2026-09-14):** `OrbInspectLatex/main.tex` now
contains all manuscript sections, tables and numerical macros. The twelve
earlier modular source files and their compiled PDF are preserved under
`OrbInspectLatex/archive/modular_tex_20260914/`. Figures and bibliography remain
supporting assets, including Figure 8's separate PDF panels with LaTeX labels.
This is a local change; no edits were made on Overleaf. See
`OrbInspectLatex/docs/SINGLE_TEX_20260914.md` for validation.

**Figure 8 LaTeX subfigures (2026-09-10):** the global and camera views now
use separate PDF/SVG/PNG exports. LaTeX generates their (a)/(b) labels and
subcaptions, consistent with the other native subfigures. Screenshot pixels,
printed image sizes, borders and progress annotations are preserved. The
manuscript remains 13 pages; Figures 1--7 are unchanged. See
`OrbInspectLatex/docs/FIGURE_8_LATEX_SUBFIGURES_20260910.md`.

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

**Coverage-mask notation ordered (2026-09-14):** Section 3 now defines
$m_k\in\{0,1\}^N$ immediately after the visibility equation as the cumulative
covered-target mask, initialized by $m_0=\mathbf 0$. The Figure 1 caption uses
plain-language completion wording so it does not introduce the mask notation
before the system-model definition. The manuscript was rebuilt and project
checks passed.

**Table I introduced before presentation (2026-09-14):** The System and
Observation Model now explicitly refers to Table~I before the assumptions table
is typeset, establishing its purpose and scope before the reader encounters it.

**Coverage-mask support defined (2026-09-14):** Section 3 now defines
$\operatorname{supp}(m)=\{i\in\mathcal T:m_i=1\}$ before the required-target
coverage and completion equations, making explicit that it is the set of sample
indices covered by the binary mask.

**Table I streamlined (2026-09-14):** The assumptions table now has four focused
rows. Circular-chief-orbit and fixed-LVLH assumptions are combined; deterministic
mesh/state, prescribed camera attitude, and sampled-mesh safety remain explicit.
The illumination/plume row was removed because the same limitation is already
stated in the scope and limitations discussion.

**Safety-clearance symbols defined (2026-09-14):** Section 3 now defines the
finite-body radius $r_{\mathrm{veh}}=0.80$ m and prescribed mesh-clearance margin
$d_{\mathrm{safe}}=2.0$ m before the sampled-state feasibility equation.

**Stage-cost weights ordered (2026-09-14):** Section 3 now defines the four
weight symbols and their maneuver, tracking, clearance, and per-edge action-cost
roles before presenting $\ell_{ij}$. The numerical values are stated in detail
in the simulation protocol.

**Graph-node notation separated from velocity (2026-09-14):** Individual graph
vertices are now denoted by $c_i,c_j$ (candidate nodes), while $\mathbf v$ and
$v_x,v_y,v_z$ remain reserved for translational velocity. The vertex set
$\mathcal V$ is unchanged.

**Terminology paragraph added (2026-09-14):** Section 3 now defines SOOA,
audit and shield admissibility, scenario feasibility/infeasibility, required
completion, optional coverage, and the limited sampled-audit meaning of ``safe''
before the dynamics and observation equations.

**Edge/action notation separated (2026-09-14):** The destination action index
$a$ is retained in the Markov and Bellman recursions, while the stored directed
edge is written $\mathsf a_{ij}$. This removes the ambiguity in expressions such
as $a_{j_ka}$ without changing the underlying graph or costs.

**Mask transition clarified (2026-09-14):** The Markov transition now uses
$m_k\lor\mathbf 1_{G_a}$, and the visibility subsection uses
$m_{k+1}=m_k\lor\mathbf 1_{G_j}$, because $G_j$ is a target-index set while
$m_k$ is a binary vector. The indicator-vector convention and the one-hot
destination vector $\mathbf e_a$ are defined before use.

**Candidate-count symbol ordered (2026-09-14):** Section 3 now defines $M$ as
the number of candidate observation nodes before using it in the inspectable-set
union, one-hot action vector, and graph-state dimensions.

**Shield predicate clarified (2026-09-14):** The edge certificate $\chi_{ij}$
now includes the enabled swept-segment no-intersection audit alongside the
stored-sample limits, terminal tolerances, and optional passive margin. The
shield action set also requires $h>0$ explicitly, so it is empty when the
finite mission budget is exhausted.

**Notation audit completed (2026-09-14):** The manuscript now defines camera
range and angle limits, dwell symbols, terminal tolerances, rollout dimensions,
route cost $J$, and the stacked command vector before use. Vector-valued surface
positions, normals, and boresights use bold notation; the visibility matrix is
distinct from the value function; the branching factor is $B_{\max}$; and the
illustrative figure caption explicitly distinguishes its schematic $v_i$ labels
from the formal candidate-node notation $c_i$. Acronym first uses and
the feasibility/admissibility terminology were clarified. The source rebuild
is 15 pages and all project/package checks pass.

**Bibliography flow corrected (2026-09-14):** Removed the stale
`\IEEEtriggeratref{29}` page-break trigger. References 1--35 now flow naturally
on the final reference page, reducing the manuscript from 16 to 15 pages.

**Figure notation synchronized (2026-09-14):** Figure 1 now uses bold
`\mathbf p_i`, `\mathbf n_i`, and `\mathbf b(\bar q_j)`, the stored-edge
notation `\mathsf a_{ij}`, and candidate nodes `c_i`. Figure 2 uses `c_i`
consistently, including the retained rollout tail. Native draw.io exports and
the PDF/PNG/SVG assets were regenerated and visually checked; the manuscript
was rebuilt to 15 pages.

**Figure caption layout refined (2026-09-14):** Figure captions are now set in
centered blocks with the same 0.9-linewidth measure as the artwork and fully
justified text. Figures 1, 2, and 7 were visually checked after rebuilding;
figure artwork and panel layouts are unchanged.

**Problem statement added (2026-09-15):** Added explicit Problem 1 at the end
of the system and observation model. It defines the finite SOOA sequence,
stage-cost objective, enabled audits, no-revisit rule, required-target terminal
condition, and graph-level infeasibility criterion. The problem is kept intact
within one column; the rebuilt manuscript is 16 pages.

**FOV terminology standardized (2026-09-15):** After the initial definition
“field of view (FOV)” in Figure 1, subsequent manuscript references use FOV and
LOS consistently, including the visibility-model explanation and the RViz
caption. The FOV half-angle remains represented by $\alpha_{\max}$.

**Coverage-mask notation clarified (2026-09-15):** The system model now defines
$m_k=[m_{1,k},\ldots,m_{N,k}]^{\mathsf T}$ and states that $m_{i,k}=1$ means
target/sample $i$ has been credited after $k$ observations. It distinguishes
the initial mask $m_0=\mathbf0$ from the generic decision-step mask $m_k$.

**Coverage-mask vector styling standardized (2026-09-15):** Coverage masks are
now written as bold vectors, $\mathbf m_k$ and $\mathbf m$, throughout the
manuscript; their scalar components remain $m_{i,k}$ and $m_i$.

**Equation 17 layout corrected (2026-09-17):** Wrapped the first-case condition
in the base-policy completion value onto two lines so the display fits its
column. Mathematical content, numbering, and font size are unchanged. Page 6
was visually checked; the rebuilt manuscript remains 16 pages and has no
overfull-box warnings.

**Table caption alignment corrected (2026-09-17):** Table captions now use
centered blocks of `0.9\linewidth`, matching the figure-caption measure.
Multiline caption text is fully justified without first-line indentation;
table numbers and single-line captions remain centered. All eight captions
were visually checked. Table data, font sizes, and figure styling are unchanged;
the rebuilt manuscript remains 16 pages.
