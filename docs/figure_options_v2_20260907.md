# Figure alternatives v2: sensing, transfer dynamics and rollout ADP

## Figure contract

The revision remains a discussion draft. The manuscript, published-figure
sources and first alternatives are preserved. The established Python/native
draw.io workflow remains the exclusive drawing/export backend.

Claim: camera-valid targets and dynamically audited directed arcs form the
decision model, while full base-policy completions support finite-depth rollout
ADP. A clear visual separation of these operations is required.

Archetype: schematic-led composite. ADP is the central methodological panel.
Export: editable three-page draw.io master plus individual pages, SVG/PNG,
three-page PDF review at 182-mm width, source data and a ZIP bundle.

Changes:

1. A detailed native LOS schematic replaces camera-only symbolism: camera
   boresight, field-of-view cone, target range, surface normal, incidence angle,
   unobstructed ray and mesh-blocked ray. It explains the four visibility tests;
   it is not a new measured camera result.
2. HCW transfers use an actual archived source-to-destination trajectory and
   projected control directions, with clearly separated dynamics/clearance/
   terminal audits and directed arc output. Avoid a decorative unlabelled curve.
3. The ADP panel adopts the supplied reference's colored branch hierarchy,
   task-aware base-policy tails and emphasized value backup. Correct the state
   to s=(j,m,b,h), keep K fixed, and distinguish noncompletion from motion failure.
   Use Bellman backup, not gradient backpropagation. Q is not itself a minimized
   value; minimizing the finite Q values is a separate selection operation.
4. Keep one integrated option and a complementary two-figure option. The latter
   allocates sensing/dynamics to the overview and mathematical detail to the
   mechanism figure, avoiding repeated state definitions.

Review risks: overlapping ray/angle labels, FOV and normal direction errors,
false clearance claims from a 2-D projection, state/graph notation mismatch,
confusing static motion audits with completion certificates, or implying a new
closed-loop execution result. Original camera bytes are preserved; all numeric
trajectory and audit examples remain traceable to the frozen experiment.

## Completed revision and verification

Outputs are in `output/figure_options_v2_20260907/`, with a three-page review PDF
in `output/pdf/OrbInspect_figure_options_v2_20260907.pdf` and a self-contained ZIP.
Page A is integrated; pages B1 and B2 form the two-figure alternative. No choice
has been applied to the manuscript.

The LOS panel uses native editable rays, angle arcs, an outward surface normal,
camera boresight, range annotation and explicit first mesh intersection. The
camera photograph is unchanged and independently embedded. The HCW panel shows
the full control norm against the 0.06 m/s² bound, projected control directions,
actual C70-to-C68 motion and separate input/mesh/terminal audit badges. Its 30
archived control intervals span 90 s and have peak norm 0.0425361504 m/s².

The reference-inspired ADP tree distinguishes finite completion costs from
infinite noncompletion values. Both feed the Bellman backup, followed by a
separate finite-value minimization and planning-state update. The tree is a
compressed schematic; its branches are not new experimental results.

All three pages were imported into draw.io and visually inspected. The final
review PDF was independently rendered with Poppler and checked page by page.
No label-width warnings or out-of-page text were found. The master matches all
three individual draw.io files; native stencil geometry, original photo bytes,
source-data hashes, exact control/position records and ZIP contents were checked.
Labels, equations, paths and containers remain editable; ISS and LOS surface
geometry are native vector stencils. Mathematical labels use vector outlines
only in review exports to prevent font substitution.

The manuscript, current paper Figure 1, and first discussion alternatives retain
their pre-revision hashes. No mathematical planner code or ROS interfaces were
changed, so ROS build and mathematical-module tests are not applicable.
