# Figure 1: visual simplification

## Figure contract

- Claim: rollout ADP turns a predefined inspection task and an audited action graph into a required-target-completing plan.
- Archetype: schematic-led composite, with the ADP search as the dominant visual.
- Panels: (a) real ISS and camera context plus fixed required set; (b) a small archived directed graph; (c) an illustrative lookahead tree, complete base-policy tails, first-action choice, and internal replanning loop; (d) the existing representative planned trajectory and required targets.
- Backend: retain the existing Python/native draw.io workflow. Output native draw.io, SVG, mixed-media PDF, and PNG; approximately 172 mm wide in the paper.
- Reading budget: short stage labels and essential symbols only. Remove in-panel prose, audit checklists, record tables, repeated definitions, and output-interface details.
- Evidence: graph connectivity, route coordinates, and required-target positions come from the frozen confirmation archive. The ADP tree is explicitly schematic and its drawing depth does not assert a tested search depth. No new experiments or comparative evidence.
- Integrity: retain the original NASA and Alexander Lucke photograph bytes. No raster retouching. Keep source attribution and the planning/execution distinction in the caption and manuscript.
- Risk checks: the visual graph must not invent edges; the planned route must not imply a new execution; 9/9 applies only to the displayed completed example; the short tree must not imply that base-policy evaluation stops at the lookahead limit.

## Verification

- In-diagram whitespace-delimited text tokens reduced from 234 to 49 (79.1%), including panel labels, numbers, and symbols. The diagram has four stages rather than five text-heavy columns.
- The five displayed graph nodes and ten directed edges match the frozen graph exactly. Candidate IDs are abbreviated with C, without zero padding.
- The route uses all 270 archived post-step positions plus the original source position. All 90 mesh target samples and the fixed nine required targets are plotted in the x-z projection at equal coordinate scale. The displayed 9/9 is the archived representative plan's result, not a success rate across experiments.
- The ADP tree is schematic, with compressed levels and illustrative goal/noncompletion outcomes. It does not claim measured branch costs or a particular integer search depth. The full ADP recursion, state, shield, and execution-accounting definitions remain in the manuscript.
- The original photograph bytes are preserved. Five frozen source-file hashes are recorded and checked in `VISUAL_EXAMPLES.json`.
- Native text-width checks pass. The source contains 197 editable geometry/text elements and two independent photographs (201 XML cells including the two document roots).
- The manuscript compiles to 12 pages without overfull boxes, undefined references, duplicate labels, or LaTeX errors. All seven figures are explicitly cited.
- Only the Figure 1 caption changes in manuscript source. Twenty-nine other source inputs, including the other figure inputs, formal material, and numerical data, are byte-identical to the preceding technical revision. The smaller diagram changes page flow from page 3 onward; all rendered pages were visually reviewed.
- The previous technical, photographic, clean, and depth-diagnostic deliveries remain preserved. No algorithm, numerical result, or ROS execution has been added or changed.
