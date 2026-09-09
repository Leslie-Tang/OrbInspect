# Figure 1: technical redesign and logic audit

## Figure contract

- Core conclusion: rollout ADP composes audited source-dependent transfers into a route that completes a fixed required-target task by using finite-depth Bellman improvement with complete base-policy tails.
- Archetype: schematic-led, mixed-media method overview; not comparative evidence or a performance claim.
- Target/output: IEEE TAES two-column figure, native editable draw.io with matching SVG, PDF, and preview PNG.
- Backend: existing Python generator; no changes to the plotting style or layout of Figures 2–7.
- Final size: approximately 172 mm wide; 1800-unit source canvas, with main labels at least 25 units (approximately 7 pt when placed in the paper).
- Panel map: (a) fixed mission data; (b) observation-dependent visibility and source-dependent HCW motion; (c) node masks and audited edge records; (d) exhaustive finite-depth prefix, base-policy completion, action choice and graph-state update; (e) planned route/records followed by a separate execution interface.
- Evidence hierarchy: ADP is the largest and strongest panel. Photographs establish physical context; the one HCW trace and mask excerpts illustrate real archived inputs. They do not constitute new experiments.
- Statistics: none; no invented quantitative observations or illustrative performance comparisons.
- Sources: the frozen confirmation graph, representative-case manifest, and trajectory; unchanged NASA ISS and Alexander Lucke camera photographs.
- Image integrity: original photograph bytes remain unchanged; only aspect-fitting is used. The camera is illustrative hardware, not a flight-qualified or experimentally validated component.
- Reviewer risks: confusing node visibility with edge properties; confusing a failed base-policy certificate with proven infeasibility; implying execution credit from planned masks; drawing arbitrary curves as HCW motion; presenting a truncated tree without its complete tail policy.

## Logic decisions before authoring

1. Mesh and prescribed observation poses supply visibility. Source/destination states supply HCW transfers. Both are needed to construct the finite graph.
2. A node owns its terminal pose and target mask. A directed edge owns trajectory, control, cost, and enabled audit results. These are separate records.
3. Static edge admissibility is combined with the current selected-view mask inside ADP. Zero-gain but admissible connections remain available.
4. The depth limit is the boundary between exhaustive prefix search and complete simulation of the same deterministic base policy. It is not a terminal reward after only d steps.
5. A complete branch has finite total cost. A non-completing tail gets infinity. If all branches are infinite, the planner returns "no certified completion", not proven infeasibility.
6. The finite minimizing first action is appended to the plan, and the internal graph state is updated. The feedback arrow is a planning loop, not a ROS sensor-feedback claim.
7. Only a goal-reaching plan is delivered as a completed route. Planned observation identities do not imply execution acceptance. Execution credit requires a separate observation-acceptance gate.

## Verification

- The illustrative trace is action 4 of the already selected representative case `required09_test_000`, from `cand_0070` to `cand_0068`. All 30 archived post-step radial positions are retained, with the stored source-node coordinate added at time zero. No smoothing or resimulation is used.
- Node masks are exact excerpts for `cand_0005`, `cand_0000`, and `cand_0070`. The directed-audit pair `cand_0070` / `cand_0009` illustrates real asymmetric admissibility. Neither excerpt is a comparative performance claim.
- `TECHNICAL_EXAMPLES.json` preserves all plotted coordinates, mask IDs, directed pass/reject records, the representative selection rule, and SHA-256 hashes of four frozen inputs. Those source hashes were rechecked after generation.
- The draw.io file contains 112 native editable shapes, text labels, connectors, and curve elements, plus two separately embedded original photographs (116 XML cells including two document roots). It was imported into draw.io and inspected for native text wrapping, symbols, image display, and connector layout.
- Native text-width checks pass. PDF export contains two independent photographs and vector text/geometry; the original image bytes are unchanged.
- The paper compiles to 12 pages with no overfull boxes, undefined references, duplicate labels, or LaTeX errors. All seven figures retain explicit body citations.
- The only manuscript-source change is the Figure 1 caption. Twenty-nine other source inputs, including formal material, tables, data macros, and the other figure inputs, match the previous photographic delivery byte for byte.
- Pixel comparison changes only pages 3 and 4: Figure 1 and its caption are on page 3, with a small text reflow into page 4. Both pages were visually reviewed; the other ten pages are pixel-identical to the previous delivery.
- Earlier clean, depth-one-to-six, and photographic deliveries are preserved. This revision contains no new ROS execution, algorithm change, or experimental result.
