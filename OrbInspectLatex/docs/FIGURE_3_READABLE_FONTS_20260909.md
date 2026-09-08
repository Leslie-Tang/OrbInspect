# Figure 3: final-size typography

The former panel PDFs were scaled down to approximately 4-point axis labels
in the manuscript. The new exports are drawn at their intended print size:
26.6 mm wide by 40 mm tall per panel, with 7.2-point axis labels, 7-point ticks
and 6.5-point contextual notes. The three-across single-column LaTeX assembly
and its subcaptions are retained. Axis wording is shortened to fit; the
unchanged subcaptions and caption retain the full metric descriptions.

The approved teal curve and slate square at depth three are retained.
Depths 1--6, the nine common-completion cases for cost, all twelve validation
cases for time and screen count, logarithmic scales in (b)/(c), and every
plotted statistic are unchanged. This is a readability revision, not a new
experiment or a new depth-selection claim.

## Regenerate and verify

Run `python scripts/generate_depth_figure.py` from this LaTeX folder with
NumPy and matplotlib installed. The default output is a preview directory
under `build/`, not the active artwork. The generator verifies the frozen CSV
hash, the cohorts, all eighteen summary values, and text canvas bounds before
exporting. SVG text remains editable; PDFs are vector graphics; PNG previews
are 600 dpi. `readable_typography_manifest.json` records the plotted series,
fonts, input hashes and output hashes. Preserve the original
`required_target_depth_figure_manifest.json` as the statistical reference.

After visual review, copy the three PDF/SVG/PNG sets and their typography
manifest into `figures/fig03_depth_tradeoff/`, refresh Figure 3's hashes in
`figures/manifest.json`, and run `make package`. Inspect the compiled paper at
its actual column width. No ROS runtime or parent-repository data is needed.

The former exports, manuscript source, compiled PDF and protected-file hashes
are retained in `archive/figure3_small_type_20260909/`.

## Manuscript verification

The compiled figure appears on page 9, adjacent to its depth-diagnostic table.
Its axis labels measure approximately 7.19 pt, with 6.99-point ticks and
6.49-point notes. The document remains 13 pages. The manual bibliography
column break was adjusted from reference 17 to 16 to accommodate the changed
float flow without introducing a sparse extra page. No bibliography content,
scientific text, tables, data, captions or other figure assets were changed.
Figure 7 remains on page 12 with its approved compact two-column layout.
