# Figure 7: two camera rows to save vertical space

The requested shorter composition places both trajectory projections on the
left and the nine camera views on the right. Views 1–5 occupy the first row;
views 6–9 occupy the second row, with the shared legend and minimum full 3-D
body margin in the spare tenth position. Matching numbers still link all
observations to the appropriate projection.

The exported figure is **170 × 44 mm**, down from 170 × 72 mm: **38.9% less
height**. Each camera view is 20.8 mm wide, a 13.3% reduction from the preceding
24 mm version and a 16.9% increase over the original 17.8 mm version. This
two-row arrangement provides a larger camera view than a single nine-image strip
while eliminating the former third row. A final 3 mm of unused bottom canvas
is omitted from the export; no camera image or plotted content is cropped.

The projections retain equal physical scaling in both panels and share vertical
tick labels. Their scale is 66% of the original 74 mm layout, versus 70% in the
preceding layout. The right viewport retains a 0.6 mm padding strip so marker 9
remains fully visible at its unchanged printed size. Camera borders, observation
colors, fonts, text sizes, marker sizes, mesh styling and path styles are unchanged.
The caption describes the new row correspondence and omits redundant line/star
definitions already given in the shared legend. Scientific prose is unchanged.

All nine image arrays, 27,188 trajectory rows, planned-path coordinates, event
positions, displayed metrics and all 70 files in the source execution snapshot
pass integrity checks. All 67 protected figure files outside Figure 7 remain
unchanged. This is the same validated required-target execution, with no new
simulation or target-credit calculation. The current PDF has a 7 pt minimum
rendered glyph size; generator checks cover text bounds, marker bounds and scale.
The historical ten-view snapshot remains supported, with a footer and 47 mm
canvas; it is not used by the current manuscript.

The previous approved generator, caption and artwork are preserved in
`archive/figure7_camera_emphasis_20260909/`. Current SVG, vector PDF, 600-dpi PNG
and the layout manifest are in `figures/fig07_ros_camera_views/`. Reproduce from
the repository root with:

```sh
python3 OrbInspectLatex/scripts/generate_ros_camera_figure.py \
  --snapshot-dir OrbInspectLatex/data/required_target_ros/20260909_040344_required09_dwell60_visual/figure7 \
  --font-dir build/manuscript_fonts \
  --output-dir OrbInspectLatex/build/figure7_two_rows/preview
make -C OrbInspectLatex
make -C OrbInspectLatex check
```

The font directory may point to another local Arial installation. Detailed
verification is recorded in `FIGURE_7_TWO_ROWS_QA_20260909.json`.

The reviewed manuscript remains 13 pages, with Figure 7 on page 12. Compilation
and project checks pass, with no LaTeX warnings, undefined references or overfull
boxes. The final figure and manuscript pages 12–13 were visually inspected.
The delivered PDF is
`output/pdf/OrbInspect_IEEE_TAES_ROS_full_required_completion_two_rows_20260909.pdf`
relative to the repository root.
