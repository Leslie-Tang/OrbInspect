# Figures 4 and 5: single-column revision

## Figure contract

- Figure 4 compares physical velocity increment and graph-cost improvement for
  the same jointly completed ADP/local-search missions. The top row contains
  the 43 test pairs, and the bottom row the eight shifted pairs. Physical
  resource comparisons are on the left; ordered cost differences are on the
  right. The selection rule, data, mean lines and bootstrap bands are retained.
- Figure 5 separates matched-completion effort and all-scenario success (top)
  from clearance and input checks on accepted edge records (bottom). It does
  not generalize those checks to untested continuous trajectories.
- Both are quantitative 2-by-2 grids, drawn with the existing Python workflow
  and color/marker/hatch conventions. The final width is the actual manuscript
  column: 240 TeX points, or approximately 84.35 mm. Text is designed at its
  printed size, not shrunk from the former panel exports.
- The complete numerical annotations from Figure 4 move to the caption.
  Shorter axis labels retain quantities, comparison direction and units.
- PDF and SVG retain editable text; PNG previews match the vector exports.
  All plotted data and statistical summaries are exported for verification.
- No experiment is rerun. Original figures and the included manuscript section
  are preserved in `archive/figure45_two_column_20260908/`.

The optional `scripts/generate_result_figures.py` reproduces these two figures
from the included confirmation snapshot using NumPy and matplotlib. It checks
the snapshot and statistics against `data/confirmation/figure_reference.json`.
It is not needed to compile the paper.

## Implemented layout

- Figure 4: 84.35 by 93.84 mm; Figure 5: 84.35 by 98.07 mm.
- Axes, ticks, panel headings and legend use 9-point type at final size;
  mathematical subscripts and superscripts retain normal reduced sizing.
- Figure 5(b) uses horizontal success bars so method labels fit without
  rotation or abbreviation beyond the defined Base, Local and ADP depths.
- A shared Figure 5 legend shows both the bar and point encodings.
- Original color, marker and hatch identities, every data point, all success
  denominators and every mean/interval are preserved. Tick density is reduced
  to fit the compact axes, with no filtering of the plotted observations.
- Both captions retain the former panel information; Figure 4's numerical
  mean/interval annotations move from inside the plots to its caption.

## Verification

- The frozen input CSV hash and the original 43-test/eight-shifted matched
  scenario IDs, means and bootstrap intervals agree exactly.
- Tests check the plotted offsets, all success-bar values, the common-effort
  sample, safety-axis containment, text size, tick separation, text bounds,
  manuscript references and transferred numerical caption values.
- All 29 relevant regression tests pass. PDF/SVG/PNG canvas dimensions agree;
  exported PDF fonts are embedded, and the compiled figure labels are 9 points.
- The compiled manuscript remains 12 pages. Figures 4 and 5 appear on pages
  9 and 11, respectively. All pages were reviewed as a contact sheet, with
  pages 9-11 checked at full size. There are no overfull boxes, unresolved
  references or oversized floats. The class still reports underfull-box
  diagnostics; these were assessed through the rendered layout.
- Figures 1-3 and 6-7 and all tables are unchanged. Only the two figure
  environments/captions differ in the manuscript section.
- Matching PDF/SVG/PNG composites, evidence manifests and the optional
  generator are included in the refreshed standalone LaTeX source package.
