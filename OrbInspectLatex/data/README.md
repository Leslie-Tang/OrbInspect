# Local evidence snapshots

These snapshots make the paper's tabular, figure, and execution evidence
inspectable without accessing the parent repository. The original organization
copied existing results; the separately dated ROS snapshots retain the original
failed execution, a successful nine-view run and the supplemental twelve-view run. These are not complete simulation
rerun packages.

- `development/`: first frozen required-target campaign (6/9/12 targets),
  originally `data/results/20260905_093000_required_target_adp/`.
- `confirmation/`: current primary nine-target confirmation, originally
  `data/results/20260905_101500_required_target_confirmation/`.
- `depth_diagnostic/`: post-selection depths 1--6 on the same validation cases,
  originally `data/results/20260905_100500_required_target_depth_diagnostic/`.
- `historical_ros/`: summary and mesh audit from the corrected survey execution,
  originally `data/results/ros_rviz_full_planning_demo_corrected_validation002_radius080_20260812/`.
- `required_target_ros/`: the current supplemental twelve-view run
  `20260909_093200_hybrid12_visual` reaches 95.86% coverage and all nine required
  targets. Separate snapshots retain the original failed 7/9 headless
  execution and `20260909_040344_required09_dwell60_visual`, which accepted all nine required
  targets after uniform terminal settling. The successful graphical snapshot
  includes original selected RGB images, figure arrays, six executed CSV streams,
  event/control audits, camera timing/pose checks, input hashes, and the search
  inventory. Original MCAPs remain local; hashes and metadata are included.
  See [scope and reproduction](required_target_ros/README.md).
- `rviz_overview/`: selected transfer frame, mission events and completion/video audit snapshots from the
  separate recorded repeat `20260909_113140_hybrid12_rviz_video_execution`, used
  only for Figure 8. The displayed progress is 9/12 observations, 7/9 required
  targets and 76.27% weighted coverage; the run eventually accepted 12/12,
  all nine required targets and 95.86% coverage. The full video is supplied separately as Supplementary
  Video 1. See [the frame provenance](rviz_overview/README.md).

The first three snapshots include existing CSV/JSON tables, graphs, scenario
definitions and configuration records, plus summaries. The historical ROS
snapshot contains summary/audit and Figure 7 inputs; historical video, bags and full
execution logs remain in the repository.
Figure 2's educational graph is kept beside that figure, not mixed with results.

Original manifests retain their original paths and hashes as provenance.
They are not live dependencies of the LaTeX build. The local-copy locations and
checksums are recorded in `docs/organization_manifest.json`, relative to the
manuscript root. Editable TeX table fragments used by the paper are in `tables/`.
Changing a snapshot does not regenerate the manuscript automatically.
