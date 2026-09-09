# OrbInspect figure options - for discussion

Nothing in the manuscript or its current figures has been replaced.

## Two alternatives

- **A: Integrated figure.** Recreates the new reference's mission / graph / ADP /
  replanning organization, with corrected technical logic and shorter labels.
- **B: Two-figure set.** B1 is the visual mission-to-plan overview; B2 explains the
  ADP mechanism. Use B1 and B2 together, rather than B1 plus the integrated option.

Open `OrbInspect_figure_options.drawio` in diagrams.net; its three page tabs are A,
B1 and B2. Individual editable files are also supplied. Labels, nodes, connectors,
target markers, route and trees are native objects. The ISS is a native vector
stencil (one independently movable/resizable object, with editable shape source).
The camera is an independently replaceable, original embedded photograph. No
complete diagram is flattened into an image. SVG and PNG exports are included.
Review-export equation glyphs are vector outlines for reliable symbol rendering;
the corresponding draw.io equations remain editable text.

These are draft alternatives, not a recommendation to insert three figures.
The PDF presents the three proposals in the same order, at 182-mm figure width.

## Logic and evidence

- State is s=(j,m,b,h), with K fixed; masks and remaining budget are not omitted.
- Motion audits define available arcs. Full base-policy tails provide completion
  certificates; the two tests are not interchangeable.
- The depth-d prefix is followed by a full deterministic task-aware greedy tail.
  The tree is schematic, with compressed levels and illustrative terminal marks.
- Q is an action value; the policy selects the minimum finite value. The operation
  is a Bellman backup, not gradient backpropagation or a newly trained DRL model.
- The loop appends a planned arc and updates the graph state. It is not a claim
  that the required-target mission has been executed in a new physical/ROS run.
- Passive-drift auditing was disabled in this study and is not depicted as active.
- If no value is finite, the output is no certified completion, not a proof of
  infeasibility of the physical mission.

The required goal is full coverage of K, not every mesh sample. The route inset is
the archived representative planned route, with all nine required targets covered.
Its x-z axes have equal physical scale. Gray dots show other sampled targets;
gold rings show required samples; a black dot denotes the initial position.
The graph is a five-node excerpt of the archived safe directed graph. Candidate
IDs are shortened with the prefix C. No quantitative performance claim is added.
The small HCW trace is the archived C70-to-C68 radial/time profile, normalized
to its display box; it illustrates a transfer record rather than a spatial path.

## Image and geometry integrity

The ISS is projected from the repository's NASA GLB using the same full scene
hierarchy and SDF rotation/scale as the experiment loader. The target overlay uses
the same projection on archived world coordinates. For display only, triangle
faces smaller than 0.15 square drawing units are omitted. This is a visualization
simplification, never a collision or visibility approximation. The projection is
orthographic, uniformly scaled and rotated in the image plane. Face color is
neutral illumination shading, not a measured field; target rings are annotations.

Camera credit: Alexander Lucke, SVCam-ECO Series black with Tubus,
CC BY-SA 3.0. The original image is reproduced without cropping, retouching,
background removal, or AI editing. It is illustrative hardware, not a selected
or space-qualified inspection camera. See `assets/IMAGE_CREDITS.md` for source
links and license. ISS geometry credit: NASA; original repository GLB.

`assets/evidence.json` preserves the graph, route, target positions and provenance
hashes. `QA.json` records editability, figure dimensions and preservation checks.
The generator sources are included for use in the original repository environment;
the editable diagrams and their embedded illustrations are fully self-contained.
