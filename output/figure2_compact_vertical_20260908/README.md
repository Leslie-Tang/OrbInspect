# Figure 2: shorter single-column layout

The figure is 84.35 by 97.00 mm, down from 84.35 by 118.09 mm: a 17.86%
height reduction without shrinking fonts or altering information.

Only object geometry changed: the context banner shares the first heading
row, the audited graph is tighter, table rows are more compact, and panel
gaps are smaller. All three panels and their 79 native drawing objects remain.
All 52 editable labels, 45 mathematical expressions, 9 attached edges, colors,
font sizes, costs, masks, action choices, coverage counts and equations match
the preceding single-column source. Body text remains about 7.47 pt; the
smallest text is 7.17 pt.

## Outputs

- `adp_rollout_mechanism.drawio`: native editable drawing and LaTeX labels.
- `adp_rollout_mechanism.pdf`: vector publication export.
- `adp_rollout_mechanism.svg`: matching vector export.
- `adp_rollout_mechanism.png`: visual preview.
- `illustrative_graph.json`: unchanged numerical example.
- `QA.json`: recorded integrity and export checks.

All six numerical tests pass. Native draw.io export reports zero math errors;
the round-trip preserves cell IDs, values, notation sources, source/target
attachments and numerical geometry. Every non-geometric cell attribute is
identical to the preceding source. The publication and native previews and
the final 13-page manuscript were visually checked. Figure 2 is on page 6;
no overfull, unresolved-reference or oversized-float warnings remain.

The manuscript text and full caption are unchanged, as is Figure 1. The
example remains explicitly illustrative, not experimental HCW data. Both
earlier alternatives are preserved in their original output packages.

Regeneration: `OrbInspectLatex/scripts/compact_figure2_vertical.py` uses the
preceding single-column cell model and edits its geometry only. After manual
draw.io edits, re-export and inspect the PDF before updating the manuscript.
