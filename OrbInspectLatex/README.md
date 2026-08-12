# OrbInspect Paper

This folder contains the IEEE Transactions on Aerospace and Electronic Systems
LaTeX manuscript for OrbInspect.

The manuscript is self-contained: the final study bundle, every plotted PDF,
the editable framework diagram, and the replay evidence cited by the paper are
copied into this directory. The paper deliberately separates HCW simulation,
saved numerical results, read-only figure generation, ROS execution/logging
validation, and Gazebo Harmonic visual replay.

The main manuscript and algorithms are in `main.tex`; the compact, separately
corrected ROS closed-loop validation evidence is included from
`sections/ros_verification_results.tex`.

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

## Structure

- `main.tex`: complete manuscript source, including all sections and algorithms.
- `IEEEtaes.cls`: manuscript document class.
- `references.bib`: manuscript bibliography.
- `figures/01_orbinspect_sooa_framework.pdf`: publication figure inserted in
  the manuscript.
- `figures/orbinspect_sooa_framework_editable.pptx`: fully editable source for
  the framework figure.
- `figures/high_coverage/`: standalone primary tradeoff and trajectory case
  study, seven-way component ablation, exact-oracle, initial-condition, and
  compute figures.
- `figures/iss_mesh/`: NASA ISS mesh preview figures.
- `figures/gazebo_validation/`: Gazebo frames and ROS smoke-run figures.
- `figures/ros_visual_interface.pdf`: synchronized live Gazebo-camera and RViz2
  views from the accepted corrected verification task. This source artifact is
  retained for provenance but is no longer a separate manuscript figure because
  the trajectory-linked camera-view figure supplies the same interface evidence
  with task context. Its source streams and SHA-256 provenance manifest remain under
  `../data/results/ros_rviz_full_planning_demo_corrected_`
  `validation002_radius080_20260812/figures/`.
- `figures/ros_key_camera_views_trajectory.pdf`: all ten synchronized credited
  camera views linked by local numbered leader lines to their exact locations
  in radial--cross-track and along-track--cross-track projections of the complete
  corrected closed-loop trajectory.
- `figures/ros_key_camera_views/`: the same ten synchronized camera views saved
  individually as annotated vector PDF and 600-dpi PNG files, named by
  sequence, waypoint ID, and mission time.
- `data/adp_paper_study_20260731_final/`: final independent-case study archive,
  including the primary, exact-oracle, initial-condition, and compute cases.
- `data/adp_component_ablation_20260801/`: cold-cache critic, rollout,
  safeguard, and local-search component ablation.
- `data/iss_mesh/`: copied NASA ISS GLB used to regenerate mesh-overlaid
  trajectory figures without leaving this folder.
- `data/phase10_smoke/`: ROS execution CSV, JSON, Markdown, manifest, and
  config snapshot artifacts.
- `data/video_capture/`: Gazebo validation videos and preview frames.
- `../src/orbinspect_guidance/orbinspect_guidance/offline_adp_study.py`: runs
  the simulation cases and saves their records.
- `../src/orbinspect_guidance/orbinspect_guidance/offline_planning_plots.py`:
  loads only saved records; each manuscript result figure has one public
  plotting function.
- `scripts/generate_corrected_ros_visual_interface_figure.py`: validates the
  accepted corrected task and version-2 mesh audit, extracts synchronized
  Gazebo-camera/RViz frames, and regenerates the manuscript PDF/PNG plus its
  provenance manifest.
- `scripts/generate_ros_key_camera_views_figure.py`: extracts each credited
  terminal camera frame, aligns it with the exact executed trajectory sample,
  overlays the fully transformed ISS mesh, and generates the trajectory-linked
  publication PDF/PNG and source-hash manifest.
- `scripts/compose_rviz_planning_demo_video.py`: validates the completed
  corrected `validation_002` ROS run, synchronizes the retained RViz and
  chaser-camera streams, and regenerates the annotated H.264 full-task video,
  milestone preview, and SHA-256 provenance manifest. The authoritative output
  remains under `../data/results/ros_rviz_full_planning_demo_corrected_`
  `validation002_radius080_20260812/videos/`.
- `templates/official_elsevier_elsarticle_2024/`: downloaded official Elsevier
  template archive retained only as a reference.
