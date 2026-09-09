# Figures 3--6: consistent typography at print size

The axis labels, tick labels, legends and notes now use **8 pt Arial** in the
compiled IEEE TAES manuscript. Mathematical scripts remain proportionally
smaller at 5.6 pt. LaTeX continues to generate the panel letters and captions.

The earlier figures used different effective sizes: Figure 3 was approximately
7 pt, Figures 4--5 were 9 pt, and Figure 6 contained text near 4--7 pt after
reduction. Setting the same native font size alone would not have corrected
the different inclusion scales. The revised native widths match the existing
LaTeX fractions of the 240-TeX-point column. Measured final text sizes are
8.000--8.001 pt, with the small difference caused by PDF/TeX dimension rounding.

## Scope and layout

- Figure 3 retains its three panels, scales, depth-three highlight and all
  statistics. Its left margins and note positions accommodate the larger text.
- Figures 4--5 retain their panel sizes, axes sizes, samples, error bars,
  confidence bands, hatches and shared test/shifted legend.
- Figure 6 retains the selected case, every trajectory sample, progress value,
  required target, display face, color and 24-degree/-56-degree camera view.
  The method legend is shared above the 3D panel. Alternate horizontal tick
  labels avoid crowding while every original grid plane remains. The goal
  legend sits above panel (b); ordinate labels are centered on the small canvases.
- The manuscript remains 13 pages. Figures 1, 2, 7 and 8, manuscript prose,
  captions, tables and all previous data files are unchanged.

The previous Figure 3--6 assets and generators are archived in
`archive/figure36_before_uniform_fonts_20260909/`.

## Reproduction

`scripts/figure_typography.py` defines the common print size and column width.
Arial must be installed or supplied through `--font-dir`; the generators report
a clear error instead of silently substituting a font with different metrics.
The existing mathematical font remains DejaVu Sans.

From the repository root, stage the figures for review:

```sh
python3 OrbInspectLatex/scripts/generate_depth_figure.py \
  --font-dir build/manuscript_fonts \
  --output-dir OrbInspectLatex/build/uniform_fonts/fig03_depth_tradeoff
python3 OrbInspectLatex/scripts/generate_result_figures.py \
  --font-dir build/manuscript_fonts \
  --output-root OrbInspectLatex/build/uniform_fonts
python3 OrbInspectLatex/scripts/generate_trajectory_figure.py \
  --font-dir build/manuscript_fonts \
  --output-dir OrbInspectLatex/build/uniform_fonts/fig06_representative_trajectory
```

All generators read the included frozen inputs. Figure 6 additionally uses
`data/confirmation/figure6/display_mesh.npz`: the same 1,800 display faces,
selected by the original generator from the 247,525-face model at scale 1.065.
Its provenance file records the mesh and frozen CSV hashes. This display-only
snapshot does not replace full-mesh geometry in any scientific calculation.
Neither planning nor simulation is invoked by these generators.

## Verification and output

`FIGURES_3_6_UNIFORM_FONTS_QA_20260910.json` records the checks:

- All 15 panel/legend PDFs have embedded fonts and editable SVG counterparts;
  PDF and SVG canvases agree, and PNG exports are 600 dpi.
- Actual glyph sizes pass the 5 pt floor; all text lies within each PDF canvas.
  Text extracted from manuscript pages 9--11 confirms the final 8 pt size.
- The original Figure 3 statistics and Figure 4--5 evidence objects match
  exactly. Figure 6 verifies archived routes, completion and final totals.
- All 343 protected source/data/artwork files match their pre-edit hashes.
- Every revised panel and manuscript pages 9--13 were visually inspected.

The generic static source preflight cannot resolve imported font constants or
loop-generated export suffixes and therefore reports missing-size/export
findings. These are resolved by the actual generated-file and compiled-PDF
audits above; its original findings are retained in the QA record.

Build, integrity check and package:

```sh
make -C OrbInspectLatex all
make -C OrbInspectLatex check
make -C OrbInspectLatex package
```

Current manuscript: `output/pdf/OrbInspect_IEEE_TAES_with_RViz_overview_20260909.pdf`.
Portable source: `OrbInspectLatex/build/OrbInspectLatex_source.zip`.
