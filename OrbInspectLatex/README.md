# OrbInspect Paper

This folder contains the IEEE Transactions on Aerospace and Electronic Systems
LaTeX manuscript for OrbInspect.

The manuscript is self-contained: the final study bundle, every plotted PDF,
the editable framework diagram, and the replay evidence cited by the paper are
copied into this directory. The paper deliberately separates HCW simulation,
saved numerical results, read-only figure generation, ROS execution/logging
validation, and Gazebo Harmonic visual replay.

All active manuscript LaTeX code, including every section and algorithm, is in
`main.tex`. The manuscript does not use per-section `\input` files.

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
- `templates/official_elsevier_elsarticle_2024/`: downloaded official Elsevier
  template archive retained only as a reference.
