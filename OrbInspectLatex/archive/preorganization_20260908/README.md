# OrbInspect paper

This directory contains the IEEE Transactions on Aerospace and Electronic
Systems LaTeX manuscript for *Viability-Preserving Rollout Approximate Dynamic
Programming for Required-Target Orbital Inspection*.

The manuscript separates the first required-target development campaign,
fresh nine-target confirmation, and one historical corrected ROS 2 survey
execution. The main theoretical contribution is model-based rollout ADP,
not a newly trained DRL policy. Current evidence is under `../data/results/`;
older experiment folders retained inside this directory are historical and
must not be substituted for the corrected evidence named in `main.tex`.

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

## Current manuscript inputs

- `main.tex`: complete article source.
- `sections/required_target_study.tex`: new required-target protocol,
  confirmation results, discussion, and evidence boundaries.
- `sections/ros_verification_results.tex`: corrected closed-loop ROS
  result and its explicit evidence boundary.
- `IEEEtaes.cls` and `references.bib`: journal class and
  bibliography.
- `figures/required_target/viability_preserving_rollout_adp.drawio`: current
  editable Figure 1, with mission inputs, detailed camera/LOS geometry, audited
  HCW-to-SOOA construction, rollout ADP, and graph-state replanning. Matching SVG
  and PDF exports accompany it; the paper uses the PDF across two columns.
  The current Roman-numbered source is in
  `../output/figure1_roman_labels_20260908/`, derived from the compact-typography and notation-aligned
  `A_integrated` alternative. It includes notation notes, provenance, and export
  QA. ISS geometry is from the NASA mesh; the camera
  photograph remains independently embedded. Credits are in the caption and
  the source package. The earlier `orbinspect_framework.*` files are retained
  as historical alternatives, not used by the current manuscript.
- `figures/required_target/adp_rollout_mechanism.drawio`: current editable
  Figure 2, with an explicitly illustrative, numerically checked ADP decision.
  Matching SVG/PDF/PNG exports use Figure 1's palette and typography. The
  current single-column layout stacks the audited graph, rollout decision,
  and retained completion at 84.35 by 97.00 mm, with approximately 7.5 pt body
  labels. The two-target graph is not experimental HCW data. The former four-block
  `adp_rollout_architecture.*` is retained as a historical alternative.
- `figures/required_target/`: current ADP mechanism, primary confirmation
  comparison, safety, representative route, and validation depth diagnostic.
- `figures/adp_future/`: historical survey figures, not current primary data.
- `figures/ros_key_camera_views_trajectory.pdf`: trajectory-linked
  frames from the accepted corrected ROS task.
- `data/required_target_*.tex`: generated current tables and numerical macros.

## Current regeneration scripts

- `scripts/compact_figure2_vertical.py`: generates the current shorter
  single-column Figure 2 by changing only cell geometry. All 79 cell identities,
  labels, notation, fonts, colors, and edge relationships are unchanged from
  the first single-column version. Output is in
  `../output/figure2_compact_vertical_20260908/`.
- `scripts/figure2_single_column.py`: generates the earlier single-column
  Figure 2, reusing the checked example and common native/vector export model.
  Output is in `../output/figure2_single_column_20260908/`. The manuscript uses
  a one-column `figure` float at `\columnwidth`; Figure 1 stays full-width.
- `scripts/redesign_figure2_adp.py`: generates the earlier wide Figure 2
  and vector exports from the same cell model, and checks every displayed cost,
  policy choice, mask update, and completion bound on the illustrative graph.
  Output and source data are in `../output/figure2_adp_mechanism_20260908/`.
  The figure uses depth two solely for a compact example; the primary study
  remains depth three. The older general figure generator writes only the
  historical architecture filename and does not replace this new asset.
- `scripts/romanize_figure1_panels.py`: changes only the five panel prefixes
  from a--e to I.--V. in the preceding compact-typography source. The manuscript
  caption uses the same Roman numerals. Other drawing objects remain identical.
- `scripts/refine_figure1_typography.py`: produces the current Figure 1 from
  the notation-aligned A alternative, removing the repeated title and compacting
  the typography and vertical layout. Native draw.io cells drive the matching
  SVG/PDF exports, including one canonical LaTeX source for each formula.
- `scripts/align_figure_notation.py`: produces the preceding notation-aligned
  A/B1/B2 alternatives. After manual edits, re-export the matching PDF from the
  edited source and inspect its mathematical labels before replacing the asset.
- `scripts/generate_visual_framework.py`: historical four-stage Figure 1,
  using the shared draw.io/SVG geometry and PDF/PNG export helpers in
  `scripts/generate_editable_framework.py` (requires PyMuPDF). Neither script
  regenerates the current five-panel manuscript figure.
- `scripts/run_required_target_study.py`: unchanged first frozen campaign;
  the 6/9/12 requirements are selected from geometry, not successful routes.
- `scripts/run_required_target_confirmation.py`: fresh nine-target comparison
  with the stronger one-step-ADP-seeded local-search comparator. This change
  follows the first campaign's failed greedy initializations and is disclosed.
- `scripts/write_required_target_tables.py`: current primary statistics and
  separately labeled development-profile table.
- `scripts/generate_required_target_figures.py` and
  `scripts/generate_required_target_details.py`: current primary and route
  figures using the existing Python styles, panel dimensions, and layouts.
- `scripts/run_required_target_depth_diagnostic.py`: post-selection depths
  one through six on the exact 12 confirmation validation cases. The source
  confirmation and primary test outcomes remain unchanged.
- `scripts/generate_required_target_depth_figures.py`: current six-depth
  figure and Table III. Run this **after** the general table/detail generators,
  which retain the historical three-depth regeneration behavior.
- `scripts/generate_adp_future_figures.py`: primary offline figures
  from the historical corrected survey bundle, plus shared style helpers.
- `scripts/generate_depth_tradeoff_figure.py`: corrected
  post-selection depth figure, CSV table, and provenance manifest.
- `scripts/evaluate_high_coverage_key_targets.py`: exploratory 95%
  and 98% coverage/sentinel stress test.
- `scripts/generate_ros_key_camera_views_figure.py`: accepted
  trajectory-linked camera-view figure.
- `scripts/compose_rviz_planning_demo_video.py`: accepted annotated
  ROS demonstration video.

The submission reproducibility package records exact result paths, hashes,
omissions, legacy-metadata corrections, and rerun commands.

## Extended depth diagnostic

The new diagnostic is stored separately in
`data/results/20260905_100500_required_target_depth_diagnostic/` relative to the
repository root. It records all 72 scenario-depth rows, a single sequential
timing pass, per-plan checkpoints, input/source hashes, and machine-readable
summaries. Its purpose is to quantify the practical cost-workload trade-off
beyond depth three, not retrospectively select the already-tested policy or
claim a universally optimal depth.

The interpretation in data/required_target_depth_rationale.tex is authored
against the archived six-depth statistics. Review its numerical statements
if a new diagnostic run changes those statistics.

## September 6 prose and figure revision

All seven figures are cited in the body. The paper is reduced from 14 to 12
pages by consolidating repeated explanations and evidence qualifications, with
model-based ADP remaining the main contribution. Formal mathematical blocks,
numerical data, and all existing figures other than the replacement Figure 1
are unchanged. The revision notes are in
`../docs/manuscript_cleanup_20260906.md`.

The subsequent photographic update replaces only the ISS and camera sketches.
Both photographs remain unmodified and separately replaceable; image credits are
in the caption and source assets. See `../docs/figure1_photographic_revision_20260906.md`.

The technical redesign removes the remaining decorative network, target, and
route sketches. It distinguishes node visibility from directed motion/audit
records, exact ADP prefixes from complete base-policy tails, and planned target
records from execution acceptance. The plotted transfer and graph excerpts are
traceable to four frozen source files in `framework_assets/TECHNICAL_EXAMPLES.json`.
See `../docs/figure1_technical_revision_20260906.md` for the logic audit and verification.

The subsequent visual simplification condenses the figure to four stages and
reduces in-diagram text by approximately 79%, retaining only short labels and
essential symbols. The ADP tree is schematic; the graph and planned route are
archived data, documented in `framework_assets/VISUAL_EXAMPLES.json`. Detailed
definitions and execution-accounting boundaries remain in the manuscript.
See `../docs/figure1_visual_revision_20260906.md`.

## September 8 Figure 1 replacement

Figure 1 now uses the selected five-panel **Viability-preserving rollout ADP
for orbital inspection** diagram. Its colors, geometry, and mathematical labels
are unchanged from the reviewed notation-aligned A alternative. The caption
describes the five panels, the full-tail cost, and offline planning, and credits
the NASA mesh rather than the earlier ISS photograph. Other manuscript text,
equations, results, and figure numbering are unchanged. The larger full-width
figure brings the compiled manuscript to 13 pages, with Figure 1 on page 3.
The figure/layout and PDF checks found no undefined references, overflowing
content, clipped labels, or caption overlap. The final PDF is also copied to
`../output/pdf/OrbInspect_IEEE_TAES_figure1_updated_20260908.pdf`.

The subsequent typography refinement removes only the repeated in-image title,
limits bold text to the five panel headings, and reduces the canvas height by
14.66% at unchanged width. Scientific illustrations are repositioned without
stretching, and colors, mathematical tokens, camera pixels, and archived data
are preserved. Native draw.io cells and SVG/PDF exports share the same geometry
and canonical label source. The manuscript text and caption remain byte-identical
to the preceding replacement; compilation and rendered-page QA pass. The paper
remains 13 pages, with Figure 1 on page 3. Current output:
`../output/pdf/OrbInspect_IEEE_TAES_figure1_typography_refined_20260908.pdf`.

The panel labels subsequently change from a--e to I.--V., with matching caption
identifiers and no further typography or layout changes. Latest output:
`../output/pdf/OrbInspect_IEEE_TAES_figure1_roman_labels_20260908.pdf`.

## September 8 Figure 2 redesign: preserved wide alternative

The first redesign complements the overview with an illustrative decision example:
motion admissibility versus goal completion, exact-prefix/full-tail cost
comparison, and the completion retained after replanning. It uses Figure 1's
palette, typography, and Roman panel headings, with a compact two-column layout.
All 94 draw.io objects are editable; the native renderer and round-trip checks
pass, including 48 mathematical expressions. Six numerical tests pass, including
an independent enumeration of the graph's two completing routes. Costs and audit
flags are explicitly illustrative, not experimental HCW results. Only the
Figure 2 introduction and figure block changed in the article source. Figure 1,
theorems, algorithm, and experimental data remain unchanged. The compiled paper
is 13 pages, with Figure 2 on page 6. Preserved wide-version output:
`../output/pdf/OrbInspect_IEEE_TAES_figure2_redesigned_20260908.pdf`.

## September 8 Figure 2 single-column revision: preserved taller alternative

The first single-column version recomposes the same verified example into three stacked
panels: I. Audited graph; II. Rollout decision; III. Retained completion. It is
84.35 by 118.09 mm at the actual IEEEtaes column width, with approximately
7.5 pt body text (minimum 7.17 pt). Action labels are integrated into the cost
table, and the caption is shorter. This is a layout revision, not a change to
the example's costs, masks, policy choices, or theoretical claims.

All 79 drawing objects remain editable. Native draw.io export renders all 45
mathematical expressions without errors; a round-trip preserves cell IDs,
labels, notation sources, attached edges, and geometry. All six numerical tests
pass. The native preview and compiled page have been visually checked.
The paper remains 13 pages, with Figure 2 in the left column of page 6. There
are no overfull boxes, unresolved references, or oversized-float warnings;
underfull spacing diagnostics remain elsewhere in the document. Only the
Figure 2 float and caption changed in the manuscript, and all Figure 1 assets
remain byte-identical. The earlier wide source and exports remain available.

Preserved editable package: `../output/figure2_single_column_20260908/`.
Preserved paper: `../output/pdf/OrbInspect_IEEE_TAES_figure2_single_column_20260908.pdf`.

## September 8 Figure 2 vertical compaction: current

Figure 2 is now 97.00 mm high instead of 118.09 mm (17.86% shorter), while
remaining 84.35 mm wide. The context banner shares the first heading row;
graph spacing, table rows and panel gaps are tighter. Text sizes are unchanged,
including approximately 7.47 pt body text and a 7.17 pt minimum. Every
non-geometric cell attribute is identical to the preceding editable source:
no labels, equations, costs, masks, colors or connections were altered.

The manuscript source, including the complete caption, is byte-identical to
the preceding revision. Only the Figure 2 assets and compiled layout changed.
Figure 1 is unchanged. All six numerical tests and native draw.io round-trip
checks pass; the native renderer reports zero errors for 45 math expressions.
The 13-page paper and Figure 2 on page 6 were visually checked. There are no
overfull boxes, unresolved references or oversized-float warnings. Earlier
wide and taller single-column alternatives remain available.

Current editable package: `../output/figure2_compact_vertical_20260908/`.
Current paper: `../output/pdf/OrbInspect_IEEE_TAES_figure2_compact_vertical_20260908.pdf`.
