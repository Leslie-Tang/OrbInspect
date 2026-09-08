# Local evidence snapshots

These unchanged copies make the paper's tabular/figure evidence inspectable
without accessing the parent repository. They are not a complete simulation
rerun package; no new results were produced during organization.

- `development/`: first frozen required-target campaign (6/9/12 targets),
  originally `data/results/20260905_093000_required_target_adp/`.
- `confirmation/`: current primary nine-target confirmation, originally
  `data/results/20260905_101500_required_target_confirmation/`.
- `depth_diagnostic/`: post-selection depths 1--6 on the same validation cases,
  originally `data/results/20260905_100500_required_target_depth_diagnostic/`.
- `historical_ros/`: summary and mesh audit from the corrected survey execution,
  originally `data/results/ros_rviz_full_planning_demo_corrected_validation002_radius080_20260812/`.

The first three snapshots include existing CSV/JSON tables, graphs, scenario
definitions and configuration records, plus summaries. The ROS snapshot is
summary/audit only; video, bags and full execution logs remain in the repository.
Figure 2's educational graph is kept beside that figure, not mixed with results.

Original manifests retain their original paths and hashes as provenance.
They are not live dependencies of the LaTeX build. The local-copy locations and
checksums are recorded in `docs/organization_manifest.json`, relative to the
manuscript root. Editable TeX table fragments used by the paper are in `tables/`.
Changing a snapshot does not regenerate the manuscript automatically.
