# Compact rollout ADP: panel d revision

Only panel d of A (the integrated alternative) has changed. Its outer frame,
reference palette and all input/output anchors are preserved. The prefix/tail
sketch is compressed and repeated outcome graphics are reduced. Panels a, b, c
and e, B1, B2, the manuscript and every preceding alternative are unchanged.

## Read the revised panel in three steps

1. **Exact lookahead:** enumerate all audited, unvisited actions in U_s(s) for
   the depth-d prefix. The three displayed leaves are schematic, not a branch
   cap or a declaration that d equals two. Full enumeration is unchanged.
2. **Full policy tails:** simulate the same deterministic, task-aware greedy
   policy from every leaf until the required goal is reached or completion
   fails within that leaf's remaining budget. V-hat_0 is the sum of all stage
   costs in the completed tail; otherwise it is positive infinity. The finite
   outcome card groups a category, not equal numerical values across leaves.
3. **Bellman backup:** propagate these terminal values through the exact prefix
   using the displayed recurrence. Discard actions whose backed-up Q is infinite.
   The adjoining, unchanged replanning panel chooses the minimum finite Q,
   appends the first arc, updates the state and rebuilds the lookahead search.

If all Q values are infinite, the algorithm reports no certified completion;
this is not a claim of physical infeasibility. A failure to complete the base
policy is distinct from a collision/motion audit. This is model-based rollout
ADP, not a learned terminal critic or neural-network training illustration.

The prefix/tail drawing now spans 180 vertical drawing units (including nodes),
compared with 294 previously, a 39 percent reduction. The outer frame stays the same size to preserve
alignment with the camera and replanning panels. The summary formula uses a
compact sum over all costs in each full tail; its precise limits are defined
in the manuscript's base-policy evaluation equation.

Open A_integrated.drawio for the revised integrated figure, or the three-page
OrbInspect_figure_options.drawio for all discussion alternatives. All new nodes,
connectors, labels, equation text and outcome cards are native editable objects.
Special mathematical glyphs are outlined only in review SVG/PDF exports to avoid
font substitutions. Ordinary text remains selectable. The QA report verifies
unchanged native/SVG objects elsewhere, and equal rendered paths and text with
only sub-0.01-unit renderer roundoff in coordinates (boundary antialiasing).
