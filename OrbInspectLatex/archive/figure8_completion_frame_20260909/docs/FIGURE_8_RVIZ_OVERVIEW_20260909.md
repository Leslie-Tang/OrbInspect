# Additional RViz overview: Figure 8

## Scope and evidence

Added Figure 8 at the user's request to supplement Figure 7. It shows the
global trajectory and onboard camera together at the completion of the
recorded twelve-observation repeat. Figure 7's artwork, caption and quantitative
ROS results are unchanged, as are Figures 1–6 and the offline study.

The repeat execution is `20260909_113140_hybrid12_rviz_video_execution` and uses
the same frozen twelve-view reference as the preceding execution reported in
Figure 7. The repeat accepted 12/12 observations and all nine required targets,
with 95.85771560419855% weighted coverage (39/41 inspectable samples). The
required-target/event audit, full-mesh audit and video quality audit passed.
The manuscript explicitly identifies it as a separate repeat execution; its
other execution metrics are not substituted into the preceding ROS results.

## Screenshot and layout contract

- One actual frame from the recorded RViz video: video time 1810.0 s, frame
  index 27150 at 15 fps, after mission completion.
- Both panels use the same frame. Panel (a) contains the station, full displayed
  planned/executed route and camera field of view; panel (b) contains the entire
  displayed onboard camera image. Exact crop coordinates and source checksums
  are in `data/rviz_overview/20260909_113140_hybrid12_rviz_video/source_manifest.json`.
- Only rectangular cropping is applied to the screenshot. Original pixel
  colors, brightness, contrast and image aspect ratios are retained. The
  panel headings and completion summary are added as editable vector text.
- The canvas is 85 by 46 mm, for one manuscript column. The global view is
  35.2 mm wide and the camera view 41.5 mm wide. Native image resolution is
  approximately 505 and 442 dpi respectively.
- Typography follows Figure 7's sans-serif family; labels are at least 7.2 pt
  in the standalone export. The camera border uses Figure 7's view-12 purple.
- This is an illustrative execution overview, with no uncertainty estimate
  or aggregate performance inference. The camera imagery does not independently
  validate target visibility credit or defect detection.

## Outputs and reproduction

The self-contained generator is `scripts/generate_rviz_overview_figure.py`.
It validates source hashes and completion counts before exporting PDF, SVG
and a 600 dpi PNG to `figures/fig08_rviz_overview/`. The accompanying
`overview_manifest.json` records layout, source identity and artifact hashes.
`figures/manifest.json` includes the approved Figure 8 files.

The manuscript callout and caption are in `sections/ros_verification_results.tex`.
Local spacing around the new figure keeps it on page 12; no global margins,
font sizes or existing figures were changed. The reviewed manuscript remains
13 pages. Pages 1–11 are pixel-identical to the preceding approved PDF at
72 dpi. Pages 12–13 were rendered and visually checked for readability,
complete content, caption placement and page balance.

Repository output: `output/pdf/OrbInspect_IEEE_TAES_with_RViz_overview_20260909.pdf`.
Portable source package: `OrbInspectLatex/build/OrbInspectLatex_source.zip`.

## Supplementary Video 1

The full normal-speed recording is supplied separately as
`output/supplementary/Supplementary_Video_1.mp4` in the parent repository.
It is an unchanged copy of
`data/results/20260909_113140_hybrid12_rviz_video/videos/OrbInspect_12_observations_RViz_realtime.mp4`.

- Duration: 1816.8 s (30 min 16.8 s).
- Video: 1920 by 1080, 15 fps, with twelve observation chapters.
- SHA-256: `129ffa710cf4dd53edccb1e3b066a8804a3d760571c769873b6c35aa5aac2622`.

The original capture, 10× preview and full execution logs remain in the dated
results directories. These large files are not included in the manuscript
source ZIP. The curated frame and audits needed to reproduce Figure 8 are
included. The recording shows a rendered ROS/Gazebo simulation, not a physical
spaceflight experiment. Its full global executed-track display was added
during recording from logged and live ROS states; the selected completion
frame includes the complete track. This display operation did not change the
spacecraft dynamics or mission acceptance.

## Verification

The machine-readable record is `FIGURE_8_RVIZ_OVERVIEW_QA_20260909.json`.
Static figure preflight found 18 passes, two warnings and no failures. The
warnings concern the absence of TIFF (PDF/SVG/PNG are the chosen manuscript
formats) and automatic width detection (85 mm is explicitly recorded and
visually checked). The PDF text audit passed with a 7.2 pt minimum. All prior
figure artifact hashes match the snapshot taken before this addition. The
LaTeX build has no overflow, oversized-float or unresolved-reference warnings.
