# Editable figure alternatives - review drafts

The current manuscript and accepted figure files remain unchanged. These are
alternatives for author discussion, not new results or publication numbering.

## Figure contract

- Claim: rollout ADP combines audited graph actions, finite lookahead and complete
  task-aware base-policy tails to select a completion-certified first action.
- Evidence chain: mission requirements and ISS geometry -> visibility and audited
  transfers -> graph -> rollout ADP -> planned route and state-update loop.
- Archetype: schematic-led composite, with ADP as the hero panel.
- Backend: the established Python/native mxGraph workflow; draw.io is the editable
  master requested by the author. No flattened full-diagram raster.
- Option A: one integrated diagram adapted from the new reference, with mission
  context on the left, graph and ADP in the middle, and replanning on the right.
- Option B: two complementary figures: mission-to-plan overview, then ADP mechanism.
- Exports: three native draw.io pages (also individual files), SVG/PNG previews,
  one three-page review PDF, and a portable source-data/credits bundle.
- Final-size check: double-column width 182 mm; minimum label size about 7 pt.
- Integrity: ISS depiction comes from the repository's NASA GLB, transformed by
  the same mesh loader as the experiments. Target positions and route are frozen
  archived records. Camera photograph is original and unmodified. Tree is schematic.

## Technical guardrails

Use s=(j,m,b,h), keep K fixed, and distinguish motion audits from finite-completion
tests. Use Bellman backup (not gradient backpropagation). A safe arc alone does
not certify mission completion. Do not depict disabled passive-drift audits as
enabled. The closed loop is graph-state replanning, not a newly executed mission.
An infinite estimate means no certified completion, not a proof of infeasibility.
No claims of a newly trained DRL model or new performance results are introduced.

## Preservation baseline

- main.tex: b9f55331f459eba887a0f2f18c4710e299e146f0783c84ccae2b75ccb7b0147d
- main.pdf: 2ddbe42ab1a3b822972042d12e0c001d92e5b2bda67493174b06e711b305b281
- current Figure 1 draw.io: 835a81472933fd08b44ecdc631b03b5504b0e067246f029d4ab9e9c301262c04
- current Figure 1 PDF: bbb00d620f0ebe19c2b6ff814fd05af09fa044bda3868354ce551a03bd7a0e31

## Delivered drafts and review

- A: integrated reference-based organization; 121 label words, 318 native cells.
- B1: mission-to-plan overview; 72 label words, 298 native cells.
- B2: ADP mechanism; 131 label words, 99 native cells.
- All three pages were imported and visually checked in draw.io. Original
  photographs remain separate embedded objects. ISS geometry uses native vector
  stencils; graph, route, target annotations and all labels remain editable.
- Three-page PDF reviewed after independent Poppler rendering at 182-mm width.
  Minimum ordinary label sizes are 6.76-7.06 pt. Equations are vector outlines in
  review exports to avoid font substitution; their draw.io text remains editable.
- State feedback returns to s, and the infinite-value exit is distinguished from
  motion-safety rejection. The supplied mesh is used for the ISS illustration;
  no experiment, manuscript text or existing figure was modified.
- Outputs are in `output/figure_options_20260907/`, with a combined three-tab
  draw.io master, individual draw.io files, previews, assets and source files.
  The separate review PDF is `output/pdf/OrbInspect_figure_options_20260907.pdf`.
  The ZIP includes every deliverable. Final choice remains with the authors.
