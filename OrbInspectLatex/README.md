# OrbInspect manuscript

Self-contained LaTeX source for the IEEE Transactions on Aerospace and Electronic
Systems manuscript. The current text, tables, figure artwork and editable
draw.io diagrams are included. No parent-repository files, ROS installation,
Python plotting environment or network connection are required to compile.
A standard TeX installation is still required.

## Build or share

Run from this folder:

```sh
make          # PDF: build/main.pdf
make check    # Check local dependencies, figure hashes and embedded images
make package  # Portable source ZIP: build/OrbInspectLatex_source.zip
```

Requirements: pdfLaTeX, BibTeX and latexmk, with the usual LaTeX science,
graphics and publisher packages (TeX Live or MacTeX). The journal class
`IEEEtaes.cls` and bibliography style `IEEEtran.bst` are included locally.
`make check` and packaging use only Python 3's standard library. On Ubuntu,
review `scripts/install_tex_ubuntu.sh` before using it to install TeX packages.

For Overleaf, upload the source ZIP and select `main.tex` with pdfLaTeX.
The ZIP excludes historical archives, repository-dependent tools and build
debris. It retains the editable figures, local evidence snapshots and docs.
For manual builds without latexmk, use `pdflatex main.tex`, `bibtex main`,
then `pdflatex main.tex` twice; that fallback writes temporary files in the root.

The bibliography prints author names in every reference, including consecutive
entries with identical authors. The `IEEEfullAuthorNames` control entry in
`references.bib`, activated before the first citation in `main.tex`, disables
repeated-name dashes and forced author-list truncation without modifying the
publisher's bibliography style. It does not appear as a numbered reference.

## Folder map

```text
OrbInspectLatex/
├── main.tex                 Main article and entry point
├── references.bib           Bibliography
├── IEEEtaes.cls             Local journal class
├── IEEEtran.bst             Local bibliography style
├── sections/               Included manuscript sections
├── tables/                 Nine included TeX tables/numerical files
├── figures/                Seven numbered figure folders and an index
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

The manuscript uses the PDFs. For Figures 1 and 2, edit the native `.drawio`
file and export a matching PDF at its original aspect ratio, retaining its
filename. Keep SVG/PNG previews synchronized. Do not stretch the export or
substitute an older diagram. `figures/manifest.json` records the approved
files and hashes at organization time; an intentional later revision should
update this manifest after visual review. Figure 2 remains the compact
three-panel design with unchanged information.

Figure 3 uses approximately 7-point axis and tick lettering at its actual
single-column, three-panel size. Its standalone generator,
`scripts/generate_depth_figure.py`, reads only the included six-depth diagnostic
CSV and verifies every plotted statistic against the frozen reference manifest.
It stages three editable SVGs and matching PDF/PNG exports under
`build/figure3_readable_preview/`; review them before updating the active figures
and their hashes. The previous small-type exports are preserved in
`archive/figure3_small_type_20260909/`. See
`docs/FIGURE_3_READABLE_FONTS_20260909.md` for the typography revision.

Figures 4 and 5 use approximately 9-point lettering at the actual column width.
Each uses four independent vector PDFs assembled into a 2-by-2 grid with
`\subfloat` in `sections/required_target_study.tex`. LaTeX generates the letters
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

Figures 3--6 now share the teal/purple palette of Figures 1 and 2. The revision
changes colors only, including the editable SVGs and matching PDF/PNG exports.
`scripts/figure_palette.py` defines the shared colors; the optional
`scripts/recolor_result_figures.py` stages and checks the full four-figure set.
See `docs/FIGURE_PALETTE_20260908.md` for the role mapping and verification.
The previous figure files remain in `archive/figure36_prepalette_20260908/`.

Figure 7 uses a compact two-column layout: two central trajectory projections
and five camera views on each side, in two columns plus a centered final view.
Matching numbers preserve the view-to-position correspondence without long
leaders. The original camera pixels, trajectory coordinates and equal spatial
scales are retained. The optional `scripts/generate_ros_camera_figure.py` reads
only `data/historical_ros/figure7/` and exports editable SVG plus PDF/PNG;
it requires NumPy, matplotlib and Pillow, but no ROS, video decoder or mesh loader.
The original single-column figure and section are preserved in
`archive/figure7_single_column_20260908/`. See
`docs/FIGURE_7_COMPACT_TWO_COLUMN_20260908.md` for the layout and checks.

## Evidence and historical material

`data/` separates development, confirmation, six-depth diagnostic and historical
ROS evidence. These are unchanged local inspection snapshots, not new results
or a complete ROS rerun package. See `data/README.md` for scope and provenance.
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

The subsequent table-layout revision uses single-column floats for Tables II
and IV and full-width alignment for Tables III, V and VI. Data, captions and
font sizes are unchanged. See `docs/TABLE_LAYOUT_20260908.md` for verification.

The later terminology cleanup replaces internal run/profile keys with academic
display labels, preserving exact identifiers in `docs/MANUSCRIPT_IDENTIFIER_MAP.md`
and the evidence snapshots. `docs/TAES_CODE_SHARING.md` records review-stage
repository guidance; it does not assert that a public code release exists.
