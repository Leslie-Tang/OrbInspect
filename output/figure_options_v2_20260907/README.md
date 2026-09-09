# OrbInspect editable figure alternatives - revision 2

The manuscript, current publication figures and first alternatives are unchanged.
Use A as a single integrated figure, or use B1 and B2 as a complementary pair.
All three pages are in `OrbInspect_figure_options.drawio`, and individual native
draw.io files and SVG/PNG previews are included. This is still for author discussion.

## What changed

- Camera/LOS: native field-of-view cross-section, boresight b(q_j), range rho,
  target p_i, outward normal n_i, incidence theta, clear ray and mesh-blocked ray.
  A valid observation requires range, FOV, incidence and unobstructed LOS to pass.
  The cone is a 2-D cross-section, not a claim of a circular physical camera FOV.
  The two target/ray examples are schematic, not a newly measured camera test.
- HCW: actual archived C70-to-C68 controlled transfer in x-z projection, with
  the full control-norm history and its 0.06 m/s² bound, source/arrival positions
  and projected control arrows. Position axes use equal
  scale; control-arrow lengths are normalized for direction visibility. The 90-s
  transfer is rest-to-rest subject to terminal tolerances. Input, full-mesh and
  terminal audits are separate checks; their pass marks come from the archived
  feasible edge. Do not infer 3-D clearance from apparent 2-D separation.
- ADP: the supplied reference's colored prefix nodes, complete task-aware greedy
  tails, finite-cost/noncompletion groups and highlighted Bellman backup are
  redrawn as editable objects. State is s=(j,m,b,h), K is fixed, and safe actions
  include connecting actions without immediate gain. No gradient backpropagation
  or newly trained DRL model is implied. Q is an action value; finite-value
  minimization is a separate policy update. If all values are infinite, no
  certified completion is returned; this is not a physical infeasibility proof.

The ADP tree is schematic, with compressed levels and illustrative completions.
The base policy runs to the required goal or the remaining budget, not for just
one more step. The loop updates the graph-planning state. No new physical/ROS
mission execution is claimed. Passive-drift auditing remains disabled in the
reported study and is not depicted as an active check.

## Sources, credits and editability

ISS geometry: NASA GLB from the repository, full hierarchy/SDF transform and
orthographic vector projection, with archived required-target positions. Subpixel
faces below 0.15 square drawing units are omitted for display only, never audits.
The planned route is the archived representative case with all 9 required targets
covered; other mesh samples are not mandatory. The five-node graph excerpt
(three nodes in the integrated option) has unique candidate IDs and only
archived passed directed arcs.

Camera: Alexander Lucke, CC BY-SA 3.0. The independently embedded original photo
is unchanged: no crop, retouching or AI editing. It is illustrative hardware,
not a selected or space-qualified camera. Source/license links are included in
`assets/IMAGE_CREDITS.md`. All ray/cone/angle annotations are separate objects.

The entire drawing is not flattened. Labels, equations, branches, arrows, targets,
plots and colored containers remain editable in draw.io. ISS and surface geometry
are native vector stencils. Equations use vector outlines in review exports to
avoid font substitution, while native draw.io equations remain editable text.
The included generators run in the original repository environment; the editable
drawings themselves are self-contained.
