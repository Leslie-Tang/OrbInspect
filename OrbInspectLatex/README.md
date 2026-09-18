# OrbInspect manuscript

Self-contained LaTeX source for the IEEE Transactions on Aerospace and Electronic
Systems manuscript. The current text, tables, figure artwork and editable
draw.io diagrams are included. No parent-repository files, ROS installation,
Python plotting environment or network connection are required to compile.
A standard TeX installation is still required.

## Build or share

The 2026-09-14 revision adds a redundant-viewpoint development pilot and an
independent feasibility/cost comparison. Section V-E describes the protocol;
Section VI-E and Table V use the independently certified all-solvable benchmark
as the primary planner-success denominator: 59 cases, with the four visibility-loss
cases retained separately as a stress test. Depth-three ADP completes 59/59
solvable cases, with a 0.96% mean graph-cost gap on 27 proven optima. The main
manuscript is 14 pages, its separate supplement is 2 pages, and all eight approved
figure assets and inclusion sizes are preserved. See
[the revision record](docs/VIEWPOINT_PILOT_MANUSCRIPT_20260914.md) and
[the complete local evidence](data/viewpoint_feasibility_pilot/README.md).

The 2026-09-09 ROS revision reports a supplemental twelve-observation execution
with all nine required targets accepted and 95.86% weighted background coverage
(39/41 inspectable samples). Two viewpoints were refined after a failed tracking
diagnostic, with the original safety settings and target weights retained.
Figure 7 uses synchronized frames from this normal-speed run; Figures 1–6 and
the offline results are unchanged. The reference-timing diagnostic is disclosed.
See [the twelve-observation report](docs/ROS_TWELVE_OBSERVATIONS_20260909.md) and
[the evidence snapshots](data/required_target_ros/README.md).

Figure 8 adds a compact RViz overview from a separate recorded repeat of the
same twelve-observation reference. It pairs the global trajectory with the
onboard camera from one frame during transfer 9 to 10. Figure 7 and its results remain
unchanged. That revision was 13 pages, with both figures on page 12.
See [the Figure 8 record](docs/FIGURE_8_RVIZ_OVERVIEW_20260909.md).

Run from this folder:

```sh
make          # PDFs: build/main.pdf and build/supplement.pdf
make check    # Check local dependencies, figure hashes and embedded images
make package  # Portable source ZIP: build/OrbInspectLatex_source.zip
```

Requirements: pdfLaTeX, BibTeX and latexmk, with the usual LaTeX science,
graphics and publisher packages (TeX Live or MacTeX). The journal class
`IEEEtaes.cls` and bibliography style `IEEEtran.bst` are included locally.
`make check` and packaging use only Python 3's standard library. On Ubuntu,
review `scripts/install_tex_ubuntu.sh` before using it to install TeX packages.

All main-article text, sections, tables and numerical macros are edited in the
single `main.tex`. Supporting tables and detailed ROS provenance moved during
page reduction are in the standalone `supplement.tex`; it is not included by
the main article. The bibliography, journal class, bibliography style and
original figure PDFs remain supporting files. The earlier modular TeX sources
are preserved under `archive/modular_tex_20260914/`; they are not compilation
inputs. If study tables are regenerated, update the corresponding block in
`main.tex` or `supplement.tex` explicitly. See
[the consolidation record](docs/SINGLE_TEX_20260914.md).

For Overleaf, upload the source ZIP and select `main.tex` with pdfLaTeX for the
article, or select `supplement.tex` to compile the separate supplement.
The ZIP excludes historical archives, repository-dependent tools and build
debris. It retains the editable figures, local evidence snapshots and docs.
For manual builds without latexmk, use `pdflatex main.tex`, `bibtex main`,
then `pdflatex main.tex` twice. Apply the same sequence with the basename
`supplement` for the supplement; that fallback writes temporary files in the root.

The bibliography prints author names in every reference, including consecutive
entries with identical authors. The `IEEEfullAuthorNames` control entry in
`references.bib`, activated before the first citation in `main.tex`, disables
repeated-name dashes and forced author-list truncation without modifying the
publisher's bibliography style. It does not appear as a numbered reference.

## Folder map

```text
OrbInspectLatex/
├── main.tex                 Complete article, all sections, tables and numerical macros
├── supplement.tex           Standalone supporting tables and ROS execution provenance
├── references.bib           Bibliography
├── IEEEtaes.cls             Local journal class
├── IEEEtran.bst             Local bibliography style
├── figures/                Eight numbered figure folders and an index
├── data/                   Local copies of current evidence for inspection
├── scripts/                Standalone checks, packaging and TeX installer
├── docs/                   Provenance, integrity and organization notes
├── build/                  Generated PDF, logs and shareable ZIP
└── archive/                Preserved pre-organization files and alternatives
```

## Find and edit a figure

| Figure | Folder | Editable/source format |
|---|---|---|
| 1 | `figures/fig01_framework/` | draw.io, SVG, PDF, PNG; credits/assets |
| 2 | `figures/fig02_rollout_example/` | draw.io, SVG, PDF, PNG; checked graph |
| 3 | `figures/fig03_depth_tradeoff/` | Three PDF/SVG/PNG panels |
| 4 | `figures/fig04_heldout_performance/` | Four separate PDF/SVG/PNG panels; LaTeX subfigures; data manifest |
| 5 | `figures/fig05_ablation_safety/` | Four separate PDF/SVG/PNG panels and shared legend; LaTeX subfigures; data manifest |
| 6 | `figures/fig06_representative_trajectory/` | Three PDF/SVG/PNG panels |
| 7 | `figures/fig07_ros_camera_views/` | Compact two-column SVG/PDF/PNG; local snapshot and Python generator |
| 8 | `figures/fig08_rviz_overview/` | Two independent PDF/SVG/PNG panels with LaTeX subcaptions; local frame and generator |

The manuscript uses the PDFs. For Figures 1 and 2, edit the native `.drawio`
file and export a matching PDF at its original aspect ratio, retaining its
filename. Keep SVG/PNG previews synchronized. Do not stretch the export or
substitute an older diagram. `figures/manifest.json` records the approved
files and hashes at organization time; an intentional later revision should
update this manifest after visual review. Figure 2 remains the compact
three-panel design with unchanged information.

Figures 3--6 use the shared **8-point Arial** typography at their actual
manuscript inclusion sizes. Axis labels, tick labels, notes and legends share
this size; mathematical subscripts/superscripts use 5.6 pt. Native panel widths
match the LaTeX widths, avoiding inconsistent scaling. The setting is defined in
`scripts/figure_typography.py`. See
`docs/FIGURES_3_6_UNIFORM_FONTS_20260910.md` for reproduction and print-size QA.

Figure 3 retains its
single-column, three-panel size. Its standalone generator,
`scripts/generate_depth_figure.py`, reads only the included six-depth diagnostic
CSV and verifies every plotted statistic against the frozen reference manifest.
It stages three editable SVGs and matching PDF/PNG exports under
`build/figure3_readable_preview/`; review them before updating the active figures
and their hashes. The previous small-type exports are preserved in
`archive/figure3_small_type_20260909/`. See
`docs/FIGURE_3_READABLE_FONTS_20260909.md` for the typography revision.

Figures 4 and 5 retain their original panel dimensions with the shared typography.
Each uses four independent vector PDFs assembled into a 2-by-2 grid with
`\subfloat` in `main.tex`. LaTeX generates the letters
and subcaptions; individual labels end in `-a`, `-b`, `-c`, and `-d`. Figure 5
also includes an unnumbered shared-legend strip. Do not add panel letters to
the image files or replace the subfigures with a composite export.
Their optional local generator is `scripts/generate_result_figures.py` (NumPy
and matplotlib); it reads only the included frozen confirmation snapshot and
verifies the original cohorts and statistics before exporting. The previous
two-column panel exports are preserved in `archive/figure45_two_column_20260908/`.
See `docs/FIGURES_4_5_SINGLE_COLUMN_20260908.md` for the layout and checks.
The subsequent native-subfigure conversion is documented in
`docs/FIGURES_4_5_LATEX_SUBFIGURES_20260908.md`; its previous composites are
preserved in `archive/figure45_composite_20260908/`.

Figure 6 can be regenerated without ROS or a planner using
`scripts/generate_trajectory_figure.py`. It reads the archived trajectory and
progress CSVs plus the exact original display-mesh selection under
`data/confirmation/figure6/`. A shared method legend above its 3D panel keeps
the progress curves unobstructed. The panel arrangement, case and camera view
are retained; alternate horizontal tick labels avoid crowding in the 3D view.

Figures 3--6 share the teal/purple palette of Figures 1 and 2. The earlier palette
revision changed colors only, including the editable SVGs and matching PDF/PNG exports.
`scripts/figure_palette.py` defines the shared colors; the optional
`scripts/recolor_result_figures.py` stages and checks the full four-figure set.
See `docs/FIGURE_PALETTE_20260908.md` for the role mapping and verification.
The previous figure files remain in `archive/figure36_prepalette_20260908/`.

Figure 7 uses two equally scaled trajectory projections on the left and twelve
uncropped camera views in two chronological rows of six on the right. Odd-numbered
observations are highlighted in the first projection and even-numbered ones in
the second to avoid crowded labels. The approved Arial typography, path and mesh
styles are preserved, with two additional observation colors. Req and Bg labels
distinguish required-target completion from weighted background coverage.
Camera panels are 18.1 mm wide on a 170 by 47 mm canvas. The approved nine-view
170 by 44 mm figure is archived in `archive/figure7_nine_view_two_rows_20260909/`.
The current snapshot is `data/required_target_ros/20260909_093200_hybrid12_visual/figure7/`.
Regenerate from the repository root with:

```sh
python3 OrbInspectLatex/scripts/generate_ros_camera_figure.py \
  --snapshot-dir OrbInspectLatex/data/required_target_ros/20260909_093200_hybrid12_visual/figure7 \
  --output-dir OrbInspectLatex/build/figure7_preview
```

NumPy, matplotlib, Pillow and the Arial font family reproduce the figure;
`--font-dir` can supply a local Arial directory. No ROS, video decoder or mesh
loader is required for this portable snapshot. The historical compact artwork
and caption are preserved in `data/historical_ros/figure7/artwork/`; the older
single-column version remains in `archive/figure7_single_column_20260908/`.
See `docs/ROS_TWELVE_OBSERVATIONS_20260909.md` for the current evidence and style checks.

Trajectory waypoint numbers now use 5.2 pt Arial Bold so IDs 10--12 fit inside
the original colored circles. Camera labels, marker sizes and all other figure
styling remain unchanged. See `docs/FIGURE_7_MARKER_LABELS_20260909.md`.

Figure 8 uses two independent exports, `rviz_execution_overview_a.pdf` and
`rviz_execution_overview_b.pdf`, assembled by LaTeX `\subfloat` at one-column
width. LaTeX generates (a) Global trajectory and (b) Onboard camera beneath
the panels, with separate reference labels ending in `-a` and `-b`.
The panel files contain no embedded letters or subcaptions. Screenshot colors,
original image widths, borders and progress annotations are unchanged. Both panels are exact
rectangular crops of the same video frame. Its optional generator reads only
the included screenshot and audit snapshots:

```sh
python3 scripts/generate_rviz_overview_figure.py
```

The generator also accepts `--output-dir` to stage exports for review.
See `docs/FIGURE_8_LATEX_SUBFIGURES_20260910.md` for the layout and checks.
This requires matplotlib, NumPy and Pillow. The selected transfer frame shows
central-module detail from a different perspective than Figure 7's observation
stops; its labels report progress at that frame (9/12 observations, 7/9 required
targets and 76.27% weighted coverage). Figure 8 illustrates a separate
repeat execution; it does not replace Figure 7's twelve synchronized observation
frames or its execution metrics. Supplementary Video 1 is supplied separately
from the source ZIP; its provenance and checksum are in the Figure 8 record.

## Evidence and historical material

`data/` separates development, confirmation, six-depth diagnostic and historical
ROS evidence, plus the separately dated required-target execution snapshots.
The offline snapshots remain unchanged. Large original ROS bags remain local,
with hashes and metadata retained in the compact manuscript snapshots. See `data/README.md` for scope and provenance.
The primary contribution remains rollout ADP; Figure 2 is an illustrative graph,
not experimental HCW data.

`archive/preorganization_20260908/` preserves the entire previous LaTeX tree,
including older templates, figures, data, scripts and build files. Additional
Figure 2 alternatives are in `archive/figure2_alternatives/`. Nothing was
deleted. Archives are not used by compilation or included in the source ZIP.

Repository-dependent experiment and figure-generation tools now live in
`tools/paper/`, relative to the repository root. They remain separate from this
portable manuscript and require the full OrbInspect repository and their
recorded environments. Start with that folder's README before regenerating.

The organization changed file paths only, not scientific content. Existing
concurrent figure-width edits were preserved. See `docs/ORGANIZATION.md` and
`docs/organization_manifest.json` for the inventory and verification record.

The main article now contains Tables I--V; the separate supplement contains
Tables S1--S3. The approved caption measure, data and font sizes are preserved.
See `docs/TABLE_LAYOUT_20260908.md` for the earlier layout verification.

The later terminology cleanup replaces internal run/profile keys with academic
display labels, preserving exact identifiers in `docs/MANUSCRIPT_IDENTIFIER_MAP.md`
and the evidence snapshots. `docs/TAES_CODE_SHARING.md` records review-stage
repository guidance; it does not assert that a public code release exists.
