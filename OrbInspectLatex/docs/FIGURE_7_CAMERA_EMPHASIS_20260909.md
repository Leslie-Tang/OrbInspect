# Figure 7: larger camera views and compact central plots

This layout-only refinement follows the request to retain the accepted Figure 7
style while enlarging its key observation captures and reducing the middle plots.
The figure continues to link all nine synchronized, uncropped camera views to
the two trajectory projections from the validated 9/9 required-target execution.
It is an image-and-trajectory composite from one run; no new experiment,
statistical comparison, visibility credit or scientific claim is introduced.

## Layout

| Element | Previously accepted | Updated |
|---|---|---|
| Canvas | 170 × 74 mm | 170 × 72 mm |
| Each camera image | 17.8 mm wide | 24 mm wide; 34.8% larger in each dimension |
| Central trajectory scale | Original | 70% of original; equal scale in both panels |
| Camera metadata | Three lines | Two lines: time and Req together, then Bg |
| Camera grouping | Five left, four right | Preserved |

The camera image area increases by 81.8%. Both central plots shrink uniformly
in physical scale; an extra 0.6 mm of viewport on the right keeps marker 9 fully
inside the axes at its unchanged printed size. This extends only the positive
along-track display bound, from 60.385 to 63.315 m. All coordinates, ticks and
the other bounds are preserved. The shared margin annotation and legend move
closer to the plots. Colors, Arial fonts, text sizes, marker sizes, mesh styling,
line weights and line styles remain unchanged. The minimum rendered glyph size
is 7 pt.

## Evidence and reproduction

The source remains
`data/required_target_ros/20260909_040344_required09_dwell60_visual/figure7/`.
All 70 files in the execution snapshot pass their retained hashes. All nine
image arrays, all 27,188 trajectory rows, the planned path, event coordinates,
camera times, required-target counts, background coverage and clearance remain
unchanged. Images receive no crop, color adjustment, brightness adjustment or
replacement. Python/matplotlib remains the rendering backend.

From the repository root:

```sh
python3 OrbInspectLatex/scripts/generate_ros_camera_figure.py \
  --snapshot-dir OrbInspectLatex/data/required_target_ros/20260909_040344_required09_dwell60_visual/figure7 \
  --font-dir build/manuscript_fonts \
  --output-dir OrbInspectLatex/build/figure7_camera_emphasis/preview
make -C OrbInspectLatex
make -C OrbInspectLatex check
```

The font option can point to another local Arial directory. The current SVG,
vector PDF, 600-dpi PNG and layout manifest are in `figures/fig07_ros_camera_views/`.
Only Figure 7 records change in the overall figure manifest; all 67 protected
files outside this group remain byte-identical. The previous reviewed manuscript
is retained in `output/pdf/OrbInspect_IEEE_TAES_ROS_full_required_completion_20260909.pdf`
relative to the repository root. The dated full-completion report describes that
previous artwork; this note and the current layout manifest describe its successor.

The machine-readable checks are in `FIGURE_7_CAMERA_EMPHASIS_QA_20260909.json`.
They cover source and pixel integrity, unchanged styling, uncropped trajectories
and markers, equal spatial scaling, text bounds, PDF glyph size and compatibility
with the historical ten-view snapshot. The manuscript prose and caption retain
their existing scientific content.

The rebuilt manuscript has 13 pages, with Figure 7 on page 12. The figure page
and final bibliography page were visually inspected; compilation reports no
LaTeX warnings, undefined references or overfull boxes. Project validation passes
for all seven figure groups and 60 figure files. The reviewed output is
`output/pdf/OrbInspect_IEEE_TAES_ROS_full_required_completion_camera_emphasis_20260909.pdf`
relative to the repository root.
