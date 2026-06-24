# OrbInspect Paper

This folder contains an Elsevier/Aerospace Science and Technology LaTeX
manuscript for OrbInspect. The active template files are taken from Elsevier's
official `elsarticle_April2024` journal article template package.

The manuscript is self-contained: every figure, raw CSV, summary, configuration
snapshot, preview frame, and validation video cited by the paper is copied into
this directory. The paper deliberately separates the high-coverage offline mesh
planning result, ROS execution/logging validation, and Gazebo Harmonic visual
validation.

## Build

The source uses the Elsevier `elsarticle` class, which is the standard template
family used for Aerospace Science and Technology submissions.

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

The folder vendors `elsarticle.cls` and `elsarticle-num.bst` extracted from the
official Elsevier template package, so the build uses the same class and
numbered bibliography style shipped by Elsevier.

## Structure

- `main.tex`: manuscript entry point.
- `elsarticle.cls`: official Elsevier class extracted from
  `elsarticle_April2024`.
- `elsarticle-num.bst`: official Elsevier numbered bibliography style.
- `sections/`: paper sections.
- `references.bib`: initial bibliography placeholders.
- `figures/high_coverage/`: trajectory, coverage, delta-v, efficiency, and
  safety comparison figures for the updated mesh experiment.
- `figures/iss_mesh/`: NASA ISS mesh preview figures.
- `figures/offline_planner/`: legacy target, trajectory, and coverage figures.
- `figures/gazebo_validation/`: Gazebo frames and ROS smoke-run figures.
- `figures/monte_carlo/`: method-comparison figure.
- `data/offline_high_coverage_experiment/`: updated offline mesh comparison
  CSV, JSON, Markdown, and config snapshot artifacts.
- `data/iss_mesh/`: copied NASA ISS GLB used to regenerate mesh-overlaid
  trajectory figures without leaving this folder.
- `data/offline_planner_publish/`: offline planner CSV, JSON, Markdown, and
  config snapshot artifacts from the earlier proxy run.
- `data/phase10_smoke/`: ROS execution CSV, JSON, Markdown, manifest, and
  config snapshot artifacts.
- `data/monte_carlo_20260621_155201/`: comparison summary and run tables.
- `data/video_capture/`: Gazebo validation videos and preview frames.
- `algorithms/`: algorithm pseudocode snippets.
- `scripts/generate_mesh_trajectory_figures.py`: reproducible generator for
  the mesh-overlaid trajectory figures in `figures/high_coverage/`.
- `templates/official_elsevier_elsarticle_2024/`: downloaded official Elsevier
  template archive and extracted source files.
