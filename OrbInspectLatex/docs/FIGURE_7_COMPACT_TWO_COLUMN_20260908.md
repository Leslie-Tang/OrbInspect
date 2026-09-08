# Figure 7: compact double-column layout

## Scope and visual argument

The figure links ten synchronized camera views to the two orthogonal projections
of the accepted historical ROS survey trajectory. It documents execution and
rendered views, not an additional ADP method comparison. This is an image-plus-
trajectory composite; the central plots organize the evidence, while camera
identity, time and coverage are retained at the sides.

The new canvas is 170 by 74 mm and is included at the manuscript text width in a
`figure*` float. Each side uses two columns plus a centered fifth view. Long
leaders are replaced by matching observation numbers: 1--5 in the left x-z
projection and 6--10 in the right y-z projection. Inactive observations remain
hollow gray markers; their numbers can be read in the other projection. Active
labels, image metadata and legend text are approximately 7--8 pt at export size.
The fifth thumbnail is the same size as the other thumbnails, not enlarged.

## Preserved evidence

- All ten approved images, with unchanged pixels and aspect ratios. No image
  crop, brightness/contrast/gamma adjustment, new video timestamp or new rendering.
- All 18,918 recorded planned/executed trajectory rows and exact event positions.
- Mission times, cumulative coverage and the two displayed full-3-D clearances.
- The same 14,000 deterministic display triangles from the transformed ISS mesh.
  The full 247,525-triangle audit remains the source of safety evidence.
- Equal metric scaling in both projections, including equal scale between panels.
- Original observation colors, planned/executed line styles and initial-state star.
- All other manuscript figures, scientific results and bibliography entries.

The time/coverage labels are now outside the images, avoiding overlays on the
inspected structure. The caption describes the numbered correspondence and new
label placement; the rest of the section is unchanged.

## Portable source and provenance

`data/historical_ros/figure7/snapshot.json` records source hashes, exact image
pixel hashes, timing/frame indices, event rows and positions. The ten PNGs are
lossless extractions of image objects from the approved composite PDF. They
retain its existing export resampling and have sufficient resolution for the
small final thumbnails; original camera recordings remain in the historical
repository evidence. `trajectory_and_display_mesh.npz` stores the unchanged
trajectory coordinates and display-only geometry. This is a figure input
snapshot, not a new experiment or a replacement for the original logs.

From the manuscript directory, the optional generator can be run as:

```sh
python scripts/generate_ros_camera_figure.py
```

It requires NumPy, matplotlib and Pillow, stages outputs under
`build/figure7_compact_preview/`, and never overwrites historical experiment data.
It saves editable-text SVG first, followed by vector PDF and 600-dpi PNG. Use
`--output-dir` to choose a different destination. The resulting
`compact_layout_manifest.json` records verified pixels, trajectory coordinates,
aspect ratios, text bounds and export hashes. After visual review, update the
approved figure hashes in `figures/manifest.json` when promoting a new export.

## Recovery and verification

The previous Figure 7 PDF/PNG, figure manifest, section, README and baseline PDF
are preserved in `archive/figure7_single_column_20260908/`. No original is deleted.
The archive also stores hashes of protected manuscript sources, evidence and
Figures 1--6. The repository preparation utility validates every original source
hash, checks the approved PDF hash, and refuses to overwrite its snapshot/archive.
The prepared local snapshot allows figure reproduction without the repository,
ROS, OpenCV or a mesh loader. None of these Python dependencies is needed for
LaTeX compilation.

Final compilation places Figure 7 at the top of page 12 at 172.92 by 75.27 mm,
approximately 30.5% shorter than the old composition enlarged to the same width.
The camera time/coverage labels print at 7.22 pt. The paper remains 13 pages.
The float is declared at the start of the ROS subsection so it appears near the
discussion rather than inside the references. The existing manual reference
column break is retuned from entry 23 to entry 17; no bibliography content or
other `main.tex` text changes. The pre-change `main.tex` is also archived.

All 133 protected-file checks pass, allowing only that one reference-layout
setting in `main.tex`; the ROS section body is unchanged outside the float.
Pages 1--11 retain identical extracted text, and all 33 bibliography entries
remain. There are no overfull boxes, undefined citations/references or oversized
floats. The SVG has 69 editable text elements and ten embedded camera images;
the PDF also retains all ten images and embedded fonts. The compiled figure,
surrounding pages and final reference columns have been visually reviewed.
`FIGURE_7_COMPACT_QA_20260908.json` records the machine-readable final checks.
