# Figure 8: native LaTeX subfigures

Figure 8 now includes two independent assets using the existing `subfig`
package. LaTeX generates the subcaptions **(a) Global trajectory** and
**(b) Onboard camera**, in the same publisher caption typography as the other
native subfigures. The parent figure remains Figure 8.

- `figures/fig08_rviz_overview/rviz_execution_overview_a.pdf`
- `figures/fig08_rviz_overview/rviz_execution_overview_b.pdf`

Each has matching editable SVG and 600 dpi PNG exports. The image assets
contain no (a)/(b) lettering or subcaption text. Separate LaTeX references are
`fig:rviz-execution-overview-a` and `fig:rviz-execution-overview-b`.

The two crops still come from video time 1375 s during transfer 9--10, with
the same 9/12 observations, 7/9 required targets and 76.27% weighted coverage.
No source image, evidence, crop, brightness, contrast, color or border changed.
The existing progress annotations retain their embedded DejaVu Sans fonts
at 7.2/7.5 pt. The new panel widths and LaTeX inclusion fractions preserve the
original printed screenshot dimensions; both image canvases have equal height.

The generator is `scripts/generate_rviz_overview_figure.py`. From this manuscript
directory, stage a review copy with:

```sh
python3 scripts/generate_rviz_overview_figure.py --output-dir build/figure8_preview
```

After promoting reviewed outputs and updating `figures/manifest.json`, use
`make all check package`. The former composite files, generator and section are
preserved in `archive/figure8_composite_labels_20260910/`.

Verification is recorded in `FIGURE_8_LATEX_SUBFIGURES_QA_20260910.json`.
Both embedded PDF images exactly match the previous embedded image bytes and,
after accounting for their PDF drawing orientation, the original source crops.
The exports contain no embedded panel labels; compiled references resolve to
8a and 8b on page 12. Both subcaptions share the same baseline and publisher
font. Image panels and pages 12--13 were visually inspected for clipping and
spacing. Pages 1--11 render identically to the preceding PDF, and all protected
data and Figure 1--7 files retain their hashes. The manuscript remains 13 pages.

Current output: `output/pdf/OrbInspect_IEEE_TAES_with_RViz_overview_20260909.pdf`.
Portable source: `OrbInspectLatex/build/OrbInspectLatex_source.zip`.
