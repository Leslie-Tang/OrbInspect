# Figure 2: completion-certified rollout ADP

This figure supplements Figure 1's system overview with one worked decision:

- I. Motion admissibility does not ensure completion of the required targets.
- II. A zero-gain connector permits total cost 4 instead of the base-policy cost 8.
- III. After the first action, a finite cost-3 completion remains available.

The graph, costs, and audit flags are explicitly illustrative. They are not
sampled HCW trajectories, new experimental results, or evidence of a general
percentage improvement. The example uses two required targets, three available
actions, and an exact depth-two prefix with complete deterministic base tails.
The manuscript's primary experimental depth-three setting is unchanged.

## Editable source and exports

- `adp_rollout_mechanism.drawio`: native shapes, connected arrows, and editable
  text/LaTeX, with mathematical typesetting enabled. No flattened picture layer.
- `.svg`: vector export with selectable ordinary text and outlined math glyphs.
- `.pdf`: 182 × 80.82 mm manuscript vector figure.
- `.png`: 240-dpi preview.
- `illustrative_graph.json`: full graph, costs, masks, decisions, and state trace.
- `QA.json`: source/export and numerical verification.

The figure uses exactly Figure 1's existing colors, rounded panel borders,
Arial body text, serif mathematical notation, and Roman-numbered headings.

To regenerate, run `OrbInspectLatex/scripts/redesign_figure2_adp.py` with the
project's figure environment. The draw.io geometry and canonical mathematical
labels drive the review export. Formulas are editable in draw.io; their review
glyphs are vector outlines to preserve accent and subscript rendering. After
manual draw.io edits, re-export the modified file and check all formulas and
arrow attachments before replacing the manuscript PDF.

## Scientific checks

The checker implements the manuscript's lexicographic gain/cost base policy,
no-revisit mask, remaining action budget, complete base tails, and exhaustive
Bellman prefix. It verifies the displayed values 8, 4, and positive infinity,
the excluded transfer, the zero-gain connecting view, and the successor mask.
Completion and no-degradation inequalities are checked at every reachable state
for depths 1 through 6. These checks validate this illustrative example only.

Six tests pass, including independent exhaustive route enumeration. The source
was also opened and exported through draw.io's native renderer: 48 mathematical
expressions rendered without errors, and a round trip preserved all 94 objects,
labels, geometry, and node connections. Explicit vertical centering keeps node
labels in place after MathJax typesetting. The native and publication renderers
share mathematical tokens and geometry; glyph rasterization is renderer-specific.
The manuscript remains 13 pages, with the new Figure 2 on page 6. Figure 1 and
all experimental results remain unchanged.
