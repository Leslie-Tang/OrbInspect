# OrbInspect paper

This directory contains the IEEE Transactions on Aerospace and Electronic
Systems LaTeX manuscript for *Viability-Preserving Rollout Approximate Dynamic
Programming for Dynamics-Aware Orbital Inspection*.

The manuscript separates the deterministic offline graph comparison,
post-selection diagnostics, and one corrected ROS 2 closed-loop validation
task. The current numerical source of record is under `../data/results/`;
older experiment folders retained inside this directory are historical and
must not be substituted for the corrected evidence named in `main.tex`.

## Build

```bash
cd OrbInspectLatex
make
```

If `latexmk` is unavailable:

```bash
pdflatex main.tex
bibtex main
pdflatex main.tex
pdflatex main.tex
```

## Current manuscript inputs

- `main.tex`: complete article source.
- `sections/ros_verification_results.tex`: corrected closed-loop ROS
  result and its explicit evidence boundary.
- `IEEEtaes.cls` and `references.bib`: journal class and
  bibliography.
- `figures/orbinspect_sooa_framework_complete.pdf`: formulation and
  data-flow figure.
- `figures/adp_future/`: rollout architecture, frozen paired results,
  ablation/safety results, representative case, and corrected post-selection
  depth diagnostic.
- `figures/ros_key_camera_views_trajectory.pdf`: trajectory-linked
  frames from the accepted corrected ROS task.
- `data/adp_depth_sensitivity_corrected_20260905.csv`: source table
  for the current depth diagnostic.

## Current regeneration scripts

- `scripts/generate_adp_future_figures.py`: primary offline figures
  from the corrected result bundle.
- `scripts/generate_depth_tradeoff_figure.py`: corrected
  post-selection depth figure, CSV table, and provenance manifest.
- `scripts/evaluate_high_coverage_key_targets.py`: exploratory 95%
  and 98% coverage/sentinel stress test.
- `scripts/generate_ros_key_camera_views_figure.py`: accepted
  trajectory-linked camera-view figure.
- `scripts/compose_rviz_planning_demo_video.py`: accepted annotated
  ROS demonstration video.

The submission reproducibility package records exact result paths, hashes,
omissions, legacy-metadata corrections, and rerun commands.
