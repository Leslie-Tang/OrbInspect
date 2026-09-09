# Required-target ROS execution and manuscript revision — 2026-09-09

This report preserves the initial failed execution and its first manuscript revision.
The subsequent completion with terminal settling is documented in
[the full-completion report](ROS_FULL_COMPLETION_20260909.md).

The first Ubuntu required-target execution **failed mission completion**. It accepted 7/9 observations and 7/9 required targets. The full-mesh geometric, finite-body, acceleration, and reference-stream checks passed. This is a retained failed attempt, not an accepted camera demonstration or a ROS planner comparison.

The main PDF reports this outcome separately from the accepted historical survey. All 72 files under the approved figure directory, including the seven figure groups and their integrity manifest, remain byte-identical. Figure 7 retains its historical ten-view layout, source images, size, typography, line styles, and colors. Figures 1–6, the abstract, theorem text, offline tables, and the 11.05% offline comparison are unchanged.

## Runs and provenance

- Execution: `data/results/20260909_031355_required09_adp_closed_loop`.
- Frozen route export: `data/results/20260909_031013_required09_replay`.
- Portable evidence: `data/required_target_ros/20260909_031355_required09_adp_closed_loop/` relative to the manuscript directory.
- Source revision: `a835dbf35e4f9422958bb9f15a0354a7c73be3ae`. No ROS computational source or runtime configuration was changed. The recorded dirty files were pre-existing root-level LaTeX build products and the user's ZIP.
- Scenario: `required09_test_000`; seed `202609360000`; method `adaptive_rollout_adp`. Selection follows the frozen median-effect rule.
- Mission SHA-256: `b9e4fd35640bda2a8258f0603ee2daa12883072d67f35817bbcf81b5b1b3738d`.
- Environment: Ubuntu 24.04.4 LTS, ROS 2 Jazzy, Python 3.12.3. Gazebo Harmonic 8.11.0 was installed; this execution was headless and did not launch Gazebo or RViz.
- Clock: normal wall time, scale 1.0. Terminal event at 810.035453120 s. Bag duration 819.600061420 s includes the shutdown buffer.

The source MCAP is retained locally under the execution directory. The portable snapshot includes metadata and its SHA-256, not the 1.7 GiB MCAP. Its `snapshot_manifest.json` hashes every copied evidence file. The frozen graph, scenarios, held-out results, and mesh all match the four handover checksums. Original manifest paths have not been rewritten.

## Planned and measured quantities

| Quantity | Frozen plan | Recorded execution |
|---|---:|---:|
| Required-target completion | 9/9 | 7/9 |
| Terminal observations accepted | 9 expected | 7/9 |
| Weighted background coverage | 77.2174% | 65.9162% |
| Unweighted inspectable target fraction | 30/41 | 26/41 |
| Duration to final event | 810 s | 810.035453 s |
| Maneuver velocity increment | 13.768885 m/s | 15.319716 m/s through final event |
| Minimum finite-body clearance above 2 m margin | 2.807540 m | 5.352142 m, continuous segment lower bound |

The missing IDs are `mesh_00007` and `mesh_00079`. They are synthetic prescribed mesh samples, not verified operational components. Both `/verification/status` and `/mission/event` reproduce the same accepted-ID unions. Rejected observations contribute nothing, and repeated IDs are counted once.

| Observation | Candidate | Decision | Position error (m) | Speed (m/s) | Required | Weighted background | Filter interventions |
|---|---|---|---:|---:|---:|---:|---:|
| 1 | cand_0005 | Accepted | 0.004957 | 0.000683 | 1/9 | 4.1423% | 0 |
| 2 | cand_0000 | Rejected | 4.276307 | 0.245872 | 1/9 | 4.1423% | 426 |
| 3 | cand_0070 | Accepted | 0.016053 | 0.001903 | 1/9 | 11.3012% | 0 |
| 4 | cand_0068 | Accepted | 0.080923 | 0.007041 | 1/9 | 22.6024% | 247 |
| 5 | cand_0021 | Accepted | 0.013031 | 0.001776 | 3/9 | 38.0459% | 0 |
| 6 | cand_0015 | Accepted | 0.006089 | 0.000831 | 4/9 | 44.2593% | 0 |
| 7 | cand_0052 | Accepted | 0.027257 | 0.003704 | 6/9 | 57.6317% | 0 |
| 8 | cand_0062 | Rejected | 1.382556 | 0.097243 | 6/9 | 57.6317% | 300 |
| 9 | cand_0045 | Accepted | 0.024589 | 0.002953 | 7/9 | 65.9162% | 263 |

There were 16,391 trajectory samples, 16,391 control samples, and 1,236 filter interventions. Position-tracking RMS error was 1.167560 m; maximum error was 5.671294 m. Peak safe acceleration was 0.060000 m/s². The complete transformed audit mesh has 247,525 triangles. No logged segment crossed the surface. Minimum sampled center distance was 8.166800 m, continuous center-distance lower bound 8.152142 m, and body-distance lower bound 7.352142 m. Subtracting the required 2 m gives the reported 5.352142 m margin.

The 15.319716 m/s execution integral uses zero-order-held safe-command norms and their ROS header stamps, from the first command through receipt of the final verification event. The recording brackets the endpoint. `raw/safe_control_integral_samples.csv` preserves these stamps and norms for reproduction without ROS. The logger's 15.431224 m/s covers the whole recording and uses receipt-time integration; it has a different endpoint and convention. No saving percentage is computed for this failed execution.

The maximum safe-command stamp gap was 0.051969051 s. Reference publication completed with 16,393 messages, maximum gap 0.051347732 s, below the configured 0.075 s diagnostic threshold. The spread of event receipt time minus reported mission time was 0.000263453 s. These observed diagnostics do not establish a strict latency guarantee.

## Failure diagnosis and outstanding work

The runtime projection filter uses simplified keep-out primitives, whereas the frozen planner and post-run audit use the full transformed mesh. On the second arc, 426 recorded interventions involved `left_solar_array`; on the eighth, 300 involved `p6_array_starboard`. These interventions coincide with the failed terminal observations. A controlled isolation study was not run, so the evidence does not establish their exclusive causal contribution.

A separate diagnostic applies the unchanged filter to archived planned samples. At planned time 156 s, the proxy gives a 3.157563 m center distance, versus 14.946707 m for the full mesh. The planned second arc enters the proxy's caution region at ten of its thirty stored samples; its minimum full-mesh center distance is 13.571729 m. These are diagnostic values on the planned route, not executed measurements.

A future implementation should reconcile planning geometry with runtime filtering and verify terminal tracking on the same frozen task. Do not relax target-credit, terminal, radius, margin, or success gates to relabel this run. A new accepted headless run must precede a separate graphical run with camera/clock synchronization. Until then, replacement Figure 7 evidence and a successful required-target demonstration remain outstanding. No seeded-local-search ROS comparison or cohort was run.

`planner.csv` is intentionally header-only: the offline sequence is fixed, so there is no online-planner log. The other five core CSV streams contain recorded data. No camera images or video were generated for this failed headless attempt. The launch processes exited cleanly; an evaluator shutdown coroutine warning is retained in `launch.log`.

## Reproduction and checks

From the repository root, source the installed Jazzy workspace. Use a fresh run ID and preserve failed attempts:

```bash
source /opt/ros/jazzy/setup.bash
source install/setup.bash
ros2 run orbinspect_guidance ros_route_exporter \
  --source-dir "$PWD/OrbInspectLatex/data/confirmation" \
  --scenario-id required09_test_000 --methods adaptive_rollout_adp \
  --output-root "$PWD/data/results" --run-id <fresh-replay-id>
ros2 launch orbinspect_bringup ros_verification.launch.py \
  result_dir:="$PWD/data/results/<fresh-replay-id>" \
  scenario_id:=required09_test_000 method:=adaptive_rollout_adp \
  publish_mode:=closed_loop headless:=true time_scale:=1.0 \
  record:=true record_bag:=true save_figures:=false run_id:=<fresh-run-id>
ros2 run orbinspect_guidance ros_evidence_audit data/results/<fresh-run-id> \
  --safety-margin 2.0 --vehicle-radius 0.80 --max-acceleration 0.060
python3 tools/paper/audit_required_target_ros.py data/results/<fresh-run-id>
```

Both audits intentionally return exit status 1 for this failed mission while preserving their reports. This outcome is distinct from a software exception. The new audit helper adds derived event/control records and does not alter mission success or the original six CSVs.

- Dependency check and all four input hashes passed.
- `colcon build --symlink-install`: 12 packages built; all 12 were discovered.
- Full package tests: 184 tests, 0 errors, 2 failures, 10 skipped. Existing guidance formatting and docstring checks failed; this is not a clean full-suite pass.
- Handover focused checks: 66 passed. An initial missing-PyMuPDF collection error is retained; PyMuPDF 1.28.2 was installed under the ignored workspace build directory, then the checks passed with system Python 3.12.
- New event-union and control-integration tests: 2 passed.
- Manuscript: build and local-input/figure integrity checks pass; final PDF remains 13 pages. Rendered ROS/figure/reference pages were inspected. No ZIP was generated.

## Manuscript changes

- `main.tex`: execution-check wording in the contribution list; disabled the obsolete forced bibliography break after repagination. The abstract and offline contribution are unchanged.
- `sections/required_target_study.tex`: updated ROS execution protocol, fixed target-credit rules, actual numerical runtime settings, and the inactive sharing statement.
- `sections/ros_verification_results.tex`: added the measured failed required-target check and shortened historical prose while retaining its successful outcome, separate run identity, principal metrics, and limitations. Historical supplemental details remain in the unchanged snapshot.
- `data/README.md`, manuscript and repository READMEs: link the new unsuccessful-run evidence and explain its scope.
- `tools/paper/audit_required_target_ros.py` and its tests: independent event accounting and timestamped control integration.
- Figures and all frozen offline datasets/tables: unchanged.
