# Figures 4 and 5: native LaTeX subfigures

## Scope and evidence contract

The revision changes figure assembly only. Figure 4 compares physical effort and
paired graph cost for jointly completed ADP/local missions. Figure 5 separates
component effort, full-cohort task success, and accepted-edge safety metrics.
No new experiment, selection rule, claim, statistical value, color, marker, or
unit is introduced.

- Figure 4: four independent PDF/SVG/PNG panels, arranged by LaTeX in two rows.
- Figure 5: four independent PDF/SVG/PNG panels plus an unnumbered shared legend.
- `subfig` was already loaded with `caption=false`; no new caption package is used.
- The image exports contain no panel letters or panel titles. `\subfloat` creates
  the letters and short subcaptions in the manuscript's caption font.
- Individual cross-reference labels are `fig:paired-performance-a` through `-d`
  and `fig:paired-safety-a` through `-d`. The original whole-figure labels remain.

## Geometry and editable/export consistency

The plots retain their previous 77-point axes widths and nine-point lettering.
Figure 4 panels use `0.49\linewidth` each. Figure 5 uses `0.46\linewidth` for the
left panels and `0.54\linewidth` for the right panels. These differing outer
margins accommodate the decimal SI tick labels in panel (d); the plotted axes
have equal dimensions. Figure 5's full-width legend uses matching bars/hatches
and point markers for the test and shifted cohorts.

The generator re-renders a native Matplotlib axes for each panel after removing
all other axes and the former panel title. This is not raster cropping. PDF and
SVG remain vector outputs with selectable/editable text; PNG previews are 600 dpi.
LaTeX assembles the panels in `sections/required_target_study.tex`.

## Validation

- Frozen confirmation CSV SHA-256:
  `335ec2b4e176e8425a0e30fea30a31f859ef07fa413c2a7c7472ca054988f068`.
- The original 43 test pairs, 8 shifted pairs, 43 matched-effort cases, full
  success denominators, means, and bootstrap intervals are preserved.
- All eight panel exports contain exactly one plotted axes; the legend has none.
- Tests check data offsets, limits, bar values, confidence bands, printed font
  size, tick separation, text bounds, PDF/SVG/PNG dimensions, embedded PDF fonts,
  editable SVG text, and absence of raster content and burned-in panel labels.
- The relevant regression suite passes 47 tests.
- The manuscript compiles to 12 pages with resolved individual panel labels,
  no overfull boxes, and no undefined references. Pages 9--12 were rendered and
  visually checked. The class reports existing underfull-box diagnostics and a
  float-only left column on page 11; the rendered column is correctly populated
  by Figures 5 and 6. Natural text/float reflow does not change other figure assets.
- Approved hashes for Figures 1--3 and 6--7 are unchanged. The active manifest
  tracks the new Figure 4/5 panel files and legend.

## Reproduction and preservation

Use `scripts/generate_result_figures.py` with NumPy and Matplotlib installed to
re-export these panels. Do not use the older repository-wide figure generator.
Run `make`, `make check`, and `make package` from this LaTeX folder for the paper
and portable source bundle. Plot-generation dependencies are not needed to compile.

The preceding composites, generator, manuscript section and figure manifest are
preserved in `archive/figure45_composite_20260908/`. Retired composite exports are
outside the active figure folders and are excluded from the portable source ZIP.
