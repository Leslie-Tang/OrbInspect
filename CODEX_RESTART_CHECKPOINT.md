# OrbInspect Codex restart checkpoint

Updated: 2026-08-12 Asia/Shanghai

## Final Windows handoff archive

- A second corrected graphical `validation_002` execution was completed at
  `data/results/20260812_174012_ros_final_validation002_radius080/` with
  rosbag recording enabled and an explicit environment snapshot.
- It credited 10/10 observations, reached 81.331% coverage, completed at
  mission time 900.008 s, and passed the version-2 audit with zero crossings
  and 5.708 m finite-body clearance above the required margin.
- The Jazzy MCAP is 2.0 GiB and contains 152,348 messages on 12 active mission
  topics. Its SHA-256 is
  `81f962360fd845b68608fb4b6d2daa970273a0c0392cb07a84bf02b0574744f6`.
- This bag-complete confirmation supplements rather than replaces the earlier
  media-backed accepted run used by Fig. 7 and the annotated video.
- `handover.md` is the authoritative Windows transfer and evidence-boundary
  guide. The final bag bundle contains `SHA256SUMS.txt` for copy verification.

## Correction completed

The Gazebo collision reported by the user was real. The former custom GLB
loader accumulated node translations but ignored ancestor rotations, including
the 60-degree rotations that place the ISS solar-array trusses. Re-auditing the
old `test_006` route with full transforms found a swept intersection at recorded
segment 5118 and a minimum finite-body clearance of -2.753 m.

Corrections now in the worktree:

- The mesh loader applies the complete glTF scene hierarchy (matrix or TRS),
  followed by the SDF pitch and scale.
- Planning and audit clearance include a conservative 0.80 m chaser bounding
  radius, covering the approximately 0.776 m visual half-diagonal.
- Consecutive samples use a 1-Lipschitz continuous center-distance lower bound,
  and direct mesh crossings remain an explicit rejection.
- The online safety proxy includes oriented boxes for the transformed S4, S6,
  P4, and P6 solar-array structures.
- RViz viewpoint and boresight markers are smaller and less opaque; confusing
  auxiliary TF/current-point overlays are disabled.
- Regression tests cover parent rotation and the formerly missed S4 collision.

## Corrected evidence

- Corrected offline study:
  `data/results/adp_future_full_transform_radius080_20260812/`
  - 24 nodes, 576 edges, 264 safe edges, 41 inspectable targets.
  - Rollout ADP and local search both succeed on 30/30 test and 20/20 shifted
    scenarios.
  - Test paired graph-cost difference: -4.093, 95% interval
    [-7.028, -1.143].
  - Test paired delta-v difference: -0.496 m/s, 95% interval
    [-0.863, -0.137].
- Corrected 124-route export bundle:
  `data/results/ros_verification_inputs_full_transform_radius080_20260812/`.
- Single-route demo input:
  `data/results/ros_verification_input_validation002_radius080_20260812/`.
- Headless validation:
  `data/results/ros_corrected_headless_validation002_radius080_20260812/`.
- Accepted graphical closed-loop task:
  `data/results/ros_rviz_full_planning_demo_corrected_validation002_radius080_20260812/`.
  - 10/10 credited views, 81.331% coverage, no failed action.
  - Audit v2: zero mesh crossings, 0.80 m body radius, 5.692 m minimum
    finite-body clearance above the required 2 m margin.
  - Final H.264 video:
    `videos/orbinspect_rviz_full_planning_demo_validation_002.mp4`.
  - 2975 frames, about 198.3 s, 1600x1080, approximately 15 fps.
  - Main view: RViz2; inset: live `/chaser/camera/image` from Gazebo.
  - Launch log: 12 process starts and 12 clean exits, no child death.

## Invalidated evidence

- The former accepted `test_006` run and video were moved without deletion to
  `data/results/quarantine_invalid_geometry_20260812/`
  `translation_only_test006_visual_collision/`.
- Incomplete/unfinalized capture and export attempts remain under
  `data/results/quarantine_corrected_rviz_capture_20260812/`.
- All paired ROS campaign claims from the old translation-only route bundle are
  excluded from the corrected manuscript. A new full 124-run closed-loop
  campaign would be required before making paired ROS superiority claims.

## Validation

- Relevant mathematical tests: 14 passed.
- `colcon build --symlink-install`: 12 packages passed after the geometry and
  radius corrections.
- Corrected headless and graphical validation tasks passed all mission and
  version-2 mesh-audit gates.
- The annotated video and 2x2 milestone preview were generated and visually
  inspected.

## Manuscript camera-view figure

- The former Fig. 8 composite is regenerated as two orthogonal trajectory
  projections: views 1--5 link locally to the radial--cross-track projection,
  and views 6--10 link locally to the along-track--cross-track projection.
- Both projections retain all ten numbered observations; markers not linked in
  that projection are hollow gray context. The caption states that projected
  overlap is not a collision decision, and the figure annotates the full-3-D
  safety margins for views 2 and 3 (+11.36 m and +9.84 m).
- The ten camera frames remain available individually as PDF and 600-dpi PNG
  under `OrbInspectLatex/figures/ros_key_camera_views/` and are mirrored in the
  accepted run evidence directory with matching SHA-256 hashes.
- The old interface-only manuscript figure was removed as redundant, while its
  source PDF/PNG and provenance remain retained. Natural LaTeX renumbering makes
  the revised camera-view composite Fig. 7.
- `OrbInspectLatex/main.pdf` compiles successfully as a 15-page manuscript; the
  revised Fig. 7 appears on page 14.

## Worktree caution

The worktree remains intentionally dirty with accumulated implementation,
paper, and generated manuscript changes. Preserve
`output/supplementary/OrbInspect_reproducibility_package_20260810/COLCON_IGNORE`.
Do not reset or discard user changes.
