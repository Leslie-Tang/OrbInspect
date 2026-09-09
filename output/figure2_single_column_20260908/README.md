# Figure 2: single-column rollout ADP example

This package implements the approved single-column redesign. It preserves
Figure 1's palette and the earlier, numerically checked illustrative example.
It does not report new HCW experiments.

## Files

- `adp_rollout_mechanism.drawio`: native editable diagram, including editable
  LaTeX labels and attached graph edges.
- `adp_rollout_mechanism.pdf`: vector publication export.
- `adp_rollout_mechanism.svg`: vector review/export source.
- `adp_rollout_mechanism.png`: preview.
- `illustrative_graph.json`: unchanged graph costs, masks, policies and checks.
- `QA.json`: geometry, typography, notation and export checks.

## Layout

Three stacked panels: I. Audited graph; II. Rollout decision; III. Retained
completion. Canvas 800 by 1120; printed size 84.35 by 118.09 mm, matching the
IEEEtaes column width. Body labels are approximately 7.47 pt, minimum text
7.17 pt, and headings 8.97 pt. The decision annotations are integrated into
the cost table rather than placed in a separate panel.

The manuscript uses a one-column figure on page 6 and a shortened caption.
Figure 1, all other manuscript text, and the illustrative numerical example
remain unchanged. The earlier wide alternative is retained in
`../figure2_adp_mechanism_20260908/`.

## Verification

- Six numerical tests pass, including an independent enumeration of the
  completing routes. Base cost 8, rollout cost 4, retained tail cost 3.
- The depth-two illustration is explicitly distinguished from the primary
  study's depth-three setting.
- All 79 native objects, 52 editable labels, and 9 attached edges are present.
- Native draw.io export renders 45 mathematical expressions with no errors.
- Native round-trip preserves IDs, labels, canonical notation, endpoints,
  waypoint order and numerical geometry; XML whitespace, attribute order and
  equivalent numeric formatting are ignored in the comparison.
- Native and publication previews were inspected for clipping and overlap.
- Compiled manuscript: 13 pages; Figure 2 occupies one column on page 6.
  No overfull boxes, unresolved references or oversized-float warnings.
  Existing underfull spacing diagnostics remain elsewhere.

Regenerate with `OrbInspectLatex/scripts/figure2_single_column.py` using the
project's review Python environment. After editing the draw.io source,
re-export and visually check the PDF before replacing the manuscript asset.
